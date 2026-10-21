"""GEMSDOE73 — 2D Multi-Scale Dilated Residual U-Net with Exact 300 m Differentiable DTI Loss.

Adapts the competition's official U-Net concept (Lipor, Portland State) to:
  1. Strict 4-quadrant spatially blocked out-of-fold validation with a 3.0 km (30 px) boundary
     exclusion buffer and integral-image zero-patch-crossing guarantee.
  2. 24 multi-resolution physical channels combining 100 m GeoDAWN potential fields, 10 m 3DEP
     asymmetric scarp breaklines, 1 m 3DEP LiDAR micro-scarps, cross-drainage bajada
     orthogonality, and Pleistocene Lake Lahontan paleo-shoreline mimic indicators.
  3. Differentiable Exact 300 m Triangular-Kernel Distance-Weighted Tversky Loss
     (alpha = 0.2, beta = 0.8, R = 300 m = 3.0 px) coupled with 1-px centerline localization.
  4. Low-memory overlap-tile Hanning-window + reflection test-time equivariant inference.
"""
from __future__ import annotations

import gc
import resource
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

UNET_SELECTED_CHANNELS: tuple[str, ...] = (
    "cross_fan_scarp_score",
    "cross_drainage_orthogonality",
    "dem10_onesided",
    "dem10_onesided3",
    "dem10_hgm20_max",
    "topo10_slope_p90",
    "topo10_curv_prof_absmax",
    "topo10_hs_lineament",
    "lidar_step_max",
    "lidar_crest_toe_dipole",
    "lidar_has_coverage",
    "along_strike_elev_std_1600m",
    "lahontan_shoreline_mimic_index",
    "tiger_road_logdist",
    "chi_ksn_max",
    "chi_log10_area",
    "radon_anisotropy_2100m",
    "hessian_centerline_1d",
    "mag_hg_worm",
    "grav_hg_worm",
    "depth_to_base_surf",
    "basement_grad",
    "cond_surf",
    "paleo_sinter_tufa_s18",
)


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class _SepBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, dilation: int = 1) -> None:
        super().__init__()
        self.proj = nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False) if in_ch != out_ch else nn.Identity()
        self.dw1 = nn.Conv2d(
            in_ch, in_ch, kernel_size=3, padding=dilation, dilation=dilation, groups=in_ch, bias=False
        )
        self.pw1 = nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False)
        self.gn1 = nn.GroupNorm(num_groups=min(8, out_ch), num_channels=out_ch)
        self.dw2 = nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, groups=out_ch, bias=False)
        self.pw2 = nn.Conv2d(out_ch, out_ch, kernel_size=1, bias=False)
        self.gn2 = nn.GroupNorm(num_groups=min(8, out_ch), num_channels=out_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.proj(x)
        h = F.silu(self.gn1(self.pw1(self.dw1(x))))
        h = self.gn2(self.pw2(self.dw2(h)))
        return F.silu(h + res)


class MultiScaleDilatedUNet(nn.Module):
    """Compact ~56k-parameter 2D U-Net with 7.6 km multi-scale dilated ASPP bottleneck."""

    def __init__(self, in_channels: int) -> None:
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 24, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(6, 24),
            nn.SiLU(inplace=True),
            _SepBlock(24, 24, dilation=1),
        )
        self.enc1 = _SepBlock(24, 40, dilation=1)
        self.enc1_dil = _SepBlock(40, 40, dilation=2)

        self.bot_a = _SepBlock(40, 32, dilation=1)
        self.bot_b = _SepBlock(40, 32, dilation=3)
        self.bot_c = _SepBlock(40, 32, dilation=6)
        self.bot_fuse = nn.Sequential(
            nn.Conv2d(96, 64, kernel_size=1, bias=False),
            nn.GroupNorm(8, 64),
            nn.SiLU(inplace=True),
        )

        self.dec1 = _SepBlock(64 + 40, 40, dilation=1)
        self.dec0 = _SepBlock(40 + 24, 32, dilation=1)
        self.head = nn.Conv2d(32, 1, kernel_size=1)
        nn.init.constant_(self.head.bias, -3.8)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        s0 = self.stem(x)
        p1 = F.max_pool2d(s0, kernel_size=2)
        s1 = self.enc1_dil(self.enc1(p1))
        p2 = F.max_pool2d(s1, kernel_size=2)
        b = self.bot_fuse(torch.cat([self.bot_a(p2), self.bot_b(p2), self.bot_c(p2)], dim=1))
        u1 = F.interpolate(b, size=s1.shape[-2:], mode="bilinear", align_corners=False)
        d1 = self.dec1(torch.cat([u1, s1], dim=1))
        u0 = F.interpolate(d1, size=s0.shape[-2:], mode="bilinear", align_corners=False)
        d0 = self.dec0(torch.cat([u0, s0], dim=1))
        return self.head(d0)


class ExactKernelDTILoss(nn.Module):
    """Memory-lean Differentiable 300 m Triangular Distance-Weighted Tversky + Centerline Loss."""

    def __init__(self, alpha: float = 0.2, beta: float = 0.8, radius_px: float = 3.0) -> None:
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        offsets: list[tuple[int, int, float]] = []
        r_int = int(np.ceil(radius_px))
        for dy in range(-r_int, r_int + 1):
            for dx in range(-r_int, r_int + 1):
                d = float(np.hypot(dy, dx))
                if d < radius_px:
                    offsets.append((dy, dx, 1.0 - d / radius_px))
        self.offsets = offsets
        self.pad = r_int

    def _max_kernel(self, t: torch.Tensor) -> torch.Tensor:
        # Incremental running torch.maximum over 29 shifted views: ZERO 29-channel intermediate tensor!
        tp = F.pad(t, (self.pad, self.pad, self.pad, self.pad), mode="constant", value=0.0)
        H, W = t.shape[-2], t.shape[-1]
        best = torch.zeros_like(t)
        p = self.pad
        for dy, dx, kval in self.offsets:
            view = tp[:, :, p + dy : p + dy + H, p + dx : p + dx + W] * kval
            best = torch.maximum(best, view)
        return best

    def forward(
        self, logits: torch.Tensor, truth: torch.Tensor, active: torch.Tensor
    ) -> torch.Tensor:
        probs = torch.sigmoid(logits) * active
        g = truth * active
        c_p = self._max_kernel(probs)
        with torch.no_grad():
            q_g = self._max_kernel(g)

        tp_w = (g * c_p).sum(dim=(1, 2, 3))
        fn_w = (g * (1.0 - c_p)).sum(dim=(1, 2, 3))
        fp_w = (probs * (1.0 - q_g) * active).sum(dim=(1, 2, 3))
        dti = (tp_w + 1e-4) / (tp_w + self.alpha * fp_w + self.beta * fn_w + 1e-4)
        loss_dti = (1.0 - dti).mean()

        pos_w = torch.tensor(6.0, device=logits.device, dtype=logits.dtype)
        bce = F.binary_cross_entropy_with_logits(logits, g, pos_weight=pos_w, reduction="none")
        loss_center = (bce * active).sum() / (active.sum() + 1.0)
        return 0.68 * loss_dti + 0.32 * loss_center


def build_normalized_spatial_stack_f16(
    X_mmap: np.memmap,
    feat_names: list[str],
    fp: np.ndarray,
    out_mmap_path: Path,
) -> np.memmap:
    """Create a 563 MB float16 (C, H, W) spatial tensor normalized per physical channel."""
    H, W = fp.shape
    fp_idx = np.flatnonzero(fp)
    C = len(UNET_SELECTED_CHANNELS)
    if out_mmap_path.is_file() and out_mmap_path.stat().st_size == C * H * W * 2:
        return np.memmap(out_mmap_path, dtype=np.float16, mode="r", shape=(C, H, W))

    out_mmap_path.parent.mkdir(parents=True, exist_ok=True)
    Z = np.memmap(out_mmap_path, dtype=np.float16, mode="w+", shape=(C, H, W))
    for c_i, ch_name in enumerate(UNET_SELECTED_CHANNELS):
        col = np.asarray(X_mmap[feat_names.index(ch_name), :], dtype=np.float32)
        fin = np.isfinite(col)
        med = float(np.median(col[fin]))
        iqr = float(np.percentile(col[fin], 85) - np.percentile(col[fin], 15)) + 1e-6
        z_fp = np.clip((np.where(fin, col, med) - med) / iqr, -4.0, 5.0)
        arr2d = np.zeros((H, W), dtype=np.float16)
        arr2d.ravel()[fp_idx] = z_fp.astype(np.float16)
        Z[c_i, :, :] = arr2d
        del col, fin, z_fp, arr2d
    Z.flush()
    gc.collect()
    return Z


def train_and_predict_oof_unet(
    Z_f16: np.memmap,
    cat: np.ndarray,
    fp: np.ndarray,
    quad_2d: np.ndarray,
    boundary_excl_2d: np.ndarray,
    patch_size: int = 128,
    epochs: int = 5,
    patches_per_epoch: int = 288,
    batch_size: int = 12,
    seed: int = 7302,
) -> np.ndarray:
    """Strict 4-quadrant out-of-fold 2D Dilated U-Net training & Hanning overlap-tile inference."""
    torch.set_num_threads(2)
    t_u0 = time.monotonic()
    H, W = fp.shape
    C = Z_f16.shape[0]
    Z_ram = np.array(Z_f16, dtype=np.float16, copy=True)
    oof_surf = np.zeros((H, W), dtype=np.float32)
    print(f"    [UNet init] Loaded {C}x{H}x{W} f16 stack into RAM (maxRSS={_rss_mb():.0f} MiB)", flush=True)

    w1d = np.hanning(patch_size + 2)[1:-1].astype(np.float32)
    win2d = np.outer(w1d, w1d)
    W_grid = W - patch_size + 1

    for q_id in range(4):
        rng = np.random.default_rng(seed + 97 * q_id)
        torch.manual_seed(seed + 97 * q_id)

        train_mask = fp & (quad_2d != q_id) & (~boundary_excl_2d)
        test_q_dil = (quad_2d == q_id) | boundary_excl_2d

        integ_forbid = np.pad(test_q_dil.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        forbid_ok = (
            integ_forbid[patch_size:, patch_size:]
            - integ_forbid[:-patch_size, patch_size:]
            - integ_forbid[patch_size:, :-patch_size]
            + integ_forbid[:-patch_size, :-patch_size]
        ) == 0
        del integ_forbid

        integ_fp = np.pad(train_mask.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        fp_ok = (
            integ_fp[patch_size:, patch_size:]
            - integ_fp[:-patch_size, patch_size:]
            - integ_fp[patch_size:, :-patch_size]
            + integ_fp[:-patch_size, :-patch_size]
        ) >= int(0.35 * patch_size * patch_size)
        del integ_fp

        integ_cat = np.pad((cat & train_mask).astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        cat_sum = (
            integ_cat[patch_size:, patch_size:]
            - integ_cat[:-patch_size, patch_size:]
            - integ_cat[patch_size:, :-patch_size]
            + integ_cat[:-patch_size, :-patch_size]
        )
        del integ_cat

        legal = forbid_ok & fp_ok
        pos_flat = np.flatnonzero(legal & (cat_sum >= 12)).astype(np.int32)
        neg_flat = np.flatnonzero(legal & (cat_sum == 0)).astype(np.int32)
        del forbid_ok, fp_ok, cat_sum, legal
        gc.collect()

        model = MultiScaleDilatedUNet(in_channels=C)
        criterion = ExactKernelDTILoss(alpha=0.2, beta=0.8, radius_px=3.0)
        opt = torch.optim.AdamW(model.parameters(), lr=2.4e-3, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=2e-4)

        model.train()
        n_pos_p = int(0.80 * patches_per_epoch)
        n_neg_p = patches_per_epoch - n_pos_p

        for ep in range(epochs):
            p_sel = pos_flat[rng.choice(pos_flat.size, size=n_pos_p, replace=True)]
            n_sel = neg_flat[rng.choice(neg_flat.size, size=n_neg_p, replace=True)]
            flat_sel = np.concatenate([p_sel, n_sel])
            rng.shuffle(flat_sel)

            ep_loss = 0.0
            n_b = 0
            for b_start in range(0, flat_sel.size, batch_size):
                b_flat = flat_sel[b_start : b_start + batch_size]
                B_cur = b_flat.size
                xb = np.empty((B_cur, C, patch_size, patch_size), dtype=np.float32)
                gb = np.empty((B_cur, 1, patch_size, patch_size), dtype=np.float32)
                ab = np.empty((B_cur, 1, patch_size, patch_size), dtype=np.float32)

                for i_b, idx_f in enumerate(b_flat):
                    r0 = int(idx_f // W_grid)
                    c0 = int(idx_f % W_grid)
                    patch_x = Z_ram[:, r0 : r0 + patch_size, c0 : c0 + patch_size].astype(np.float32)
                    patch_g = cat[r0 : r0 + patch_size, c0 : c0 + patch_size].astype(np.float32)
                    patch_a = train_mask[r0 : r0 + patch_size, c0 : c0 + patch_size].astype(np.float32)
                    if rng.random() < 0.5:
                        patch_x = patch_x[:, :, ::-1]
                        patch_g = patch_g[:, ::-1]
                        patch_a = patch_a[:, ::-1]
                    if rng.random() < 0.5:
                        patch_x = patch_x[:, ::-1, :]
                        patch_g = patch_g[::-1, :]
                        patch_a = patch_a[::-1, :]
                    xb[i_b] = patch_x
                    gb[i_b, 0] = patch_g
                    ab[i_b, 0] = patch_a

                opt.zero_grad(set_to_none=True)
                logits = model(torch.from_numpy(xb))
                loss = criterion(logits, torch.from_numpy(gb), torch.from_numpy(ab))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
                opt.step()
                ep_loss += float(loss.detach())
                n_b += 1
            sched.step()
            print(
                f"      [Fold {q_id} Ep {ep+1}/{epochs} +{time.monotonic()-t_u0:5.1f}s] "
                f"loss={ep_loss/max(n_b,1):.4f} maxRSS={_rss_mb():.0f} MiB",
                flush=True,
            )

        model.eval()
        q_rows, q_cols = np.where(quad_2d == q_id)
        r_min = max(0, int(q_rows.min()) - 16)
        r_max = min(H, int(q_rows.max()) + 16)
        c_min = max(0, int(q_cols.min()) - 16)
        c_max = min(W, int(q_cols.max()) + 16)

        stride = patch_size // 2
        rs = sorted(set(list(range(r_min, max(r_min + 1, r_max - patch_size + 1), stride)) + [max(0, r_max - patch_size)]))
        cs = sorted(set(list(range(c_min, max(c_min + 1, c_max - patch_size + 1), stride)) + [max(0, c_max - patch_size)]))
        coords = [(r0, c0) for r0 in rs for c0 in cs]

        acc_pred = np.zeros((H, W), dtype=np.float32)
        acc_wgt = np.zeros((H, W), dtype=np.float32)

        with torch.no_grad():
            for b_start in range(0, len(coords), 8):
                chunk_rc = coords[b_start : b_start + 8]
                xb = np.stack(
                    [Z_ram[:, r0 : r0 + patch_size, c0 : c0 + patch_size].astype(np.float32) for r0, c0 in chunk_rc],
                    axis=0,
                )
                xt = torch.from_numpy(xb)
                p_fwd = torch.sigmoid(model(xt)).numpy()[:, 0]
                p_flp = torch.sigmoid(model(torch.flip(xt, dims=[3]))).flip(dims=[3]).numpy()[:, 0]
                p_avg = 0.5 * (p_fwd + p_flp)
                for (r0, c0), pm in zip(chunk_rc, p_avg):
                    acc_pred[r0 : r0 + patch_size, c0 : c0 + patch_size] += pm * win2d
                    acc_wgt[r0 : r0 + patch_size, c0 : c0 + patch_size] += win2d

        q_mask = (quad_2d == q_id) & fp
        oof_surf[q_mask] = acc_pred[q_mask] / np.maximum(acc_wgt[q_mask], 1e-6)
        print(
            f"    [UNet Fold {q_id}/4 DONE +{time.monotonic()-t_u0:5.1f}s] "
            f"oof_mean={float(oof_surf[q_mask].mean()):.4f} | oof_p99={float(np.percentile(oof_surf[q_mask], 99)):.4f} | "
            f"maxRSS={_rss_mb():.0f} MiB",
            flush=True,
        )
        del model, acc_pred, acc_wgt, pos_flat, neg_flat
        gc.collect()

    del Z_ram
    gc.collect()
    return oof_surf
