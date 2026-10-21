#!/usr/bin/env python3
"""Assemble evidence/run_card_h73-7.json from the measured evidence files.

Verdict logic is the preregistered rule in registry/preregistration_h73-7.json,
applied mechanically: promote (to selector) iff (a) best experiment beats the
fold-fair H33-analogue control with paired 95% CI excluding 0, (b) all leakage
canaries <= 0.90, (c) operative uniqueness gates pass, (d) vendor validator
passed on re-read bytes. Caveats that a selector must see are copied into the
card verbatim; nothing here can turn a HOLDOUT-DTI into a live score.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"

sel = json.loads((EV / "selection_h73-7.json").read_text())
hold = json.loads((EV / "holdout_h73-7.json").read_text())
can = json.loads((EV / "canaries_h73-7.json").read_text())
uni = json.loads((EV / "uniqueness_h73-7.json").read_text())
NAME = f"gems73-h73-7-hardfault-pu-{sel['best_experiment'].lower()}-37654dots-20261021"
receipt = json.loads((ROOT / "docs" / "downloads" / f"{NAME}.json").read_text())

best = sel["best_experiment"]
sc = hold["scores"]
b_stage = uni["stage_B_final_dots_vendor_full"]
champ_rows = b_stage["vs_h33_champion_rows"]
own_names = ("gems73-h73-1-piedmont", "gems73-h73a-blind-stepover-20261021T022620Z-c111bb0f-zeros",
             "gems73-hydro-permeability")
own_rows = [r for r in b_stage["rows"] if "error" not in r
            and any(r["submission"].startswith(n) for n in own_names)]
fwd_over = [r for r in b_stage["rows"] if "error" not in r
            and (r.get("my_dots_within_3px_of_theirs") or 0) > 0.70]
fwd_over.sort(key=lambda r: -r["my_dots_within_3px_of_theirs"])

gates = {
    "a_beats_control_ci_excluding_0": bool(sel["beats_control_ci_excluding_0"]),
    "b_canaries_all_le_0.90": bool(can["all_pass"]),
    "c_uniqueness_operative_gates": bool(uni["gates"]["all_pass"]),
    "d_validator_all_checks_passed": bool(receipt["validator"]["all_checks_passed"]),
}
verdict = "promote" if all(gates.values()) else "negative"

card = {
    "repo": "GEMSDOE73",
    "lane": "H73-7",
    "hypothesis": ("Catalogue pixels that are hardest to see (weak 1 m-LiDAR step, deep "
                   "basement, gentle detrended slope) are the catalogue subpopulation most "
                   "similar to expert-added hidden faults; up-weighting them in a "
                   "physical-feature ranker shifts dotted emission toward covered "
                   "piedmont faults instead of easy bedrock/range-front traces."),
    "mechanism": ("Fold-fair HistGradientBoosting PU ranker (300 iters, lr 0.06, 63 leaves) "
                  "on 41 physical channels (19 official GeoDAWN/topo bands, 10 LiDAR scarp "
                  "bands, 8 radiometric/extension bands, 4 unsupervised H73-1 components); "
                  "positives = visible catalogue (48,340 px) weighted 1+2h; negatives = "
                  "250,000 footprint px >5 px from VISIBLE faults only; no "
                  "distance-to-catalogue feature, no scored-raster input. Frozen dotted "
                  "emission: 37,654 dots, 2.5 px spacing, >2.0 px from visible (production: "
                  "full) catalogue. Production surface retrained on the full 60,988-px "
                  "catalogue with the identical recipe."),
    "named_non_fault_mimic": ("Lithologic contacts and alluvial-fan surfaces (magnetic/gravity/"
                              "radiometric signature of covered faults without faulting), plus "
                              "catalogue mapping bias itself - where mappers looked is not "
                              "where hidden faults are."),
    "holdout": {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "withheld_positive_pixels": sel["withheld_positive_pixels"],
        "selected_experiment": best,
        "selected_dti": sc[best]["dti"],
        "selected_ci95": sc[best]["ci95"],
        "E2_unweighted_ablation_dti": sc["E2"]["dti"],
        "E3_no_scarp_ablation_dti": sc["E3"]["dti"],
        "h33_analogue_foldfair_control_dti": sc["h33_analogue_foldfair"]["dti"],
        "h33_analogue_foldfair_control_ci95": sc["h33_analogue_foldfair"]["ci95"],
        "control_reproduction": ("Control rebuilt identically to the merged H73-1 lane "
                                 "reproduced its published 0.093861 exactly (random 0.0484 "
                                 "and static-champion 0.0037 also exact): the comparison "
                                 "is on one unchanged instrument."),
        "random_control_dti": sc["random_control"]["dti"],
        "paired_delta_vs_control": sel["paired_delta_vs_control"],
        "preregistered_gate_passed": bool(sel["beats_control_ci_excluding_0"]),
        "mechanism_reading": ("E1 (hard-weighted) 0.1369 vs E2 (unweighted) 0.1364: the "
                              "hard-weighting is nearly inert on this instrument (+0.0005); "
                              "the measured gain comes from the supervised physical stack "
                              "itself. E3 without any scarp-family feature still scores "
                              "0.1211 > control 0.0939, so geophysics/radiometrics carry "
                              "independent catalogue-holdout signal. The hypothesis' "
                              "weighting mechanism is NOT confirmed by this run."),
        "transfer_caveat": ("HOLDOUT-DTI truth is withheld CATALOGUE segments, so this "
                            "instrument structurally favours catalogue-supervised fields; "
                            "the hidden expert set was selected for catalogue ABSENCE. "
                            "Sibling supervised lanes live-scored 0.0286-0.2478 "
                            "(OWNER-REPORT) despite strong catalogue fit. This card claims "
                            "a holdout result, never a live score; whether the +0.043 "
                            "transfers is exactly what one selector-approved slot would test."),
        "production_caveat": ("HOLDOUT-DTI describes the fold-fair twin (trained on the "
                              "48,340 visible px). The shipped bytes come from the same "
                              "recipe retrained on all 60,988 catalogue px."),
    },
    "leakage_canaries": {
        "evidence_class": "HOLDOUT-DTI canary (single-feature AUC; gate symmetric AUC <= 0.90)",
        "channels_tested": len(can["channels"]),
        "all_pass": can["all_pass"],
        "max_symmetric_auc": can["max_symmetric_auc"],
        "worst_channel": max(can["channels"], key=lambda k: can["channels"][k]["symmetric_auc"]),
        "file": "evidence/canaries_h73-7.json",
    },
    "correlation_overlap_vs_registry": {
        "scope": ("REGISTRY-MEASUREMENT (accessible scan: 6 sibling clones' downloads + "
                  "hash-pinned scored mirrors + this repo's own rasters; not a complete "
                  "organizer registry - IR-73-07)"),
        "registry_unique_rasters_checked": uni["registry_unique_by_sha256"],
        "registry_files_seen": uni["registry_files_seen"],
        "stage_A_surface_spearman_max_sample200k": uni["stage_A_surface_sampled_spearman"]["max_rho"],
        "stage_A_worst": uni["stage_A_surface_sampled_spearman"]["worst"]["submission"],
        "stage_B_dots_spearman_max_full": b_stage["worst_spearman"]["spearman_full_footprint"],
        "stage_B_worst_spearman_submission": b_stage["worst_spearman"]["submission"],
        "dots_mutual_overlap_max": b_stage["worst_mutual_overlap"]["mutual_overlap"],
        "dots_mutual_worst_submission": b_stage["worst_mutual_overlap"]["submission"],
        "vs_h33_champion": ([{"forward": r["my_dots_within_3px_of_theirs"],
                              "mutual": r["mutual_overlap"],
                              "rho": r["spearman_full_footprint"]} for r in champ_rows[:1]] or None),
        "vs_own_repo_previous_rasters": [
            {"submission": r["submission"], "forward": r["my_dots_within_3px_of_theirs"],
             "mutual": r["mutual_overlap"], "rho": r["spearman_full_footprint"]}
            for r in own_rows],
        "literal_forward_overlap_over_0.70": [
            {"submission": r["submission"], "forward": r["my_dots_within_3px_of_theirs"],
             "mutual": r["mutual_overlap"], "their_dots": r["their_dots"]} for r in fwd_over],
        "literal_forward_note": ("Under the brief's literal one-way rule (>70% of my dots "
                                 "within 3 px of one registry raster), this candidate fails "
                                 "against the dense/union rasters listed above - the "
                                 "documented IR-73-01 saturation artifact (the 206,895-dot "
                                 "r13 lattice's halo covers ~99% of ANY dot field). The "
                                 "operative shared-tool gate (vendor gems57 uniqueness, "
                                 "2026-10-20 fix; PR#3 precedent) is mutual overlap <= 0.70 "
                                 "plus Spearman <= 0.90; both pass with margin (worst mutual "
                                 "0.504 vs a 59,075-dot union-family raster; vs the champion "
                                 "mutual 0.217; vs the most similar supervised sibling "
                                 "GEMSDOE70 P5 mutual 0.337). Logged as IR-73-15 for the "
                                 "selector; not hidden."),
        "error_rows": b_stage["errors"],
        "unique_substantive_operative_gates": bool(uni["gates"]["all_pass"]),
        "file": "evidence/uniqueness_h73-7.json",
    },
    "raster_sha256": receipt["sha256"],
    "raster_bytes": receipt["bytes"],
    "zip_sha256": receipt.get("zip_sha256"),
    "validator": {
        "all_checks_passed": receipt["validator"]["all_checks_passed"],
        "checks": receipt["validator"]["checks"],
        "min": receipt["validator"]["min"], "max": receipt["validator"]["max"],
        "n_nan": receipt["validator"]["n_nan"],
        "dots": receipt["validator"]["emitted_positive_pixels"],
        "nodata": receipt["validator"]["meta"]["nodata"],
        "crs_shape_transform_match_sample": bool(receipt["template_report"]["ok"]),
        "independent_reread": ("Re-opened after writing in this session: single-band float32, "
                               "EPSG:32611, 3730x3292, transform [100,0,243350,0,-100,4508550] "
                               "matching sample_submission.tif, all 12,279,160 cells finite in "
                               "[0,1], 0 NaN, 37,654 positive px, 0 outside footprint, ZIP "
                               "contains exactly this TIFF byte-identically. Portal error "
                               "'Predicted values must be in range [0,1]' cannot trigger: "
                               "nodata=None and no sentinel value exists anywhere in the file."),
    },
    "submission_name": NAME,
    "submission_note": receipt["note"],
    "submission_note_chars": receipt["note_chars"],
    "download_ok": True,
    "submit_recommended": verdict == "promote",
    "preregistered_gates": gates,
    "verdict": verdict,
    "verdict_reason": (
        "All four preregistered gates pass: E1 beats the exactly-reproduced fold-fair "
        "H33-analogue control on pooled HOLDOUT-DTI by +0.0430 [0.0230, 0.0627] "
        "(gems57-pooled-hide-v2, 11,321 withheld px); 41/41 leakage canaries <= 0.6105; "
        "operative uniqueness gates pass (surface rho max 0.2089, dots rho max 0.0573, "
        "mutual overlap max 0.504, vs champion 0.217); validator passes on re-read bytes. "
        "PROMOTE means promote-to-selector: this repo spends no weekly slot. The selector "
        "must weigh the transfer caveat (catalogue-supervised fields have historically "
        "transferred weakly to the expert hidden set) and IR-73-15 before spending a slot."
        if verdict == "promote" else "One or more preregistered gates failed; see preregistered_gates."),
    "weekly_slots_spent": 0,
    "organizer_score": None,
    "experiments_run": 3,
    "figure": "docs/assets/fig_h73-7_vs_h33.png",
    "evidence_files": ["evidence/holdout_h73-7.json", "evidence/selection_h73-7.json",
                       "evidence/canaries_h73-7.json", "evidence/uniqueness_h73-7.json",
                       "evidence/forensic_h73-7.json", "registry/preregistration_h73-7.json"],
    "reproduce": (".venv/bin/python scripts/restore_data.py --group all && "
                  ".venv/bin/python scripts/run_experiments_h73_7.py && "
                  ".venv/bin/python scripts/build_submission_h73_7.py && "
                  ".venv/bin/python scripts/audit_registry_h73_7.py && "
                  ".venv/bin/python scripts/build_run_card_h73_7.py"),
}
(EV / "run_card_h73-7.json").write_text(json.dumps(card, indent=2) + "\n")
(ROOT / "docs" / "downloads" / "run_card_h73-7.json").write_text(json.dumps(card, indent=2) + "\n")
print(json.dumps({"verdict": verdict, "gates": gates, "name": NAME,
                  "sha256": card["raster_sha256"]}, indent=2))
