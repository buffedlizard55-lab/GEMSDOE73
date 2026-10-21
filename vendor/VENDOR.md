# Shared template — vendored byte-identical, do not fork

`vendor/gems57/` is byte-identical to `vendor/gems57/` in
buffedlizard55-lab/GEMSDOE70 (verified by `diff -r` in this session), itself
byte-identical to `src/gems57/` in buffedlizard55-lab/60GEMSDOE at
32024716f218d06a94e01464157392119c03cb15 (see VENDOR_UPSTREAM_README.md).
Evaluator version: `gems57-pooled-hide-v2`. Key file SHA-256:
evaluate_holdout.py ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a;
submission_writer.py 41220185ac2823fe5358603d38f2a915ea3e5f1ab1f94f0b237295b38b4a2565.
No shared-tool defect was found in this lane; the metric was re-verified
against the official worked example and a brute-force transcription
(tests/test_metric_and_submission.py). A future shared defect must be fixed
upstream once, not patched here.
