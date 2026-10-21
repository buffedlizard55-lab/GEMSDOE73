#!/usr/bin/env python3
from pathlib import Path
import sys, json, argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems73.submission import validate_submission_geotiff

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geotiff", type=Path)
    ap.add_argument("--template", type=Path, default=Path("data/sample_submission.tif"))
    ap.add_argument("--strict-finite", action="store_true")
    args = ap.parse_args()
    rep = validate_submission_geotiff(args.geotiff, args.template, strict_whole_array_finite=args.strict_finite)
    print(json.dumps(rep.to_dict(), indent=2))
    print("PASSED" if rep.passed else "FAILED")
    return 0 if rep.passed else 2

if __name__ == "__main__":
    raise SystemExit(main())
