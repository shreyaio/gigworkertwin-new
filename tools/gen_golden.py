"""Recompute the golden dataset's expected values. `docs/07` §10.

    ./venv/Scripts/python.exe tools/gen_golden.py            # show the diff, write nothing
    ./venv/Scripts/python.exe tools/gen_golden.py --write    # rewrite golden.py's constants

**Read the diff before writing.** These values are what makes "our wiring of the engine is
correct" a testable claim; a change to one of them is a change to a number in the paper, and the
only acceptable reasons to move one are a deliberate change to the model specification, to the
fixture, or to the engine version. Drift with none of those is a bug you have just papered over.

This lives in `tools/` and not in a test because a test that can rewrite its own expectations is
not a test.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from twinlab.stats import golden, plssem  # noqa: E402
from twinlab.stats.spec import build_model_spec  # noqa: E402

GOLDEN_PY = ROOT / "src" / "twinlab" / "stats" / "golden.py"


def _round(value: float | None) -> float | None:
    """Six places: three more than the |delta| < 0.001 the test asserts."""
    return None if value is None else round(float(value), 6)


def compute() -> dict:
    """Run every stage on the reference dataset and collect the pinned statistics."""
    spec = build_model_spec()
    matrix = golden.golden_matrix(spec=spec)
    results = plssem.run_all_stages(
        matrix, spec, samples=golden.GOLDEN_BOOTSTRAP, seed=golden.GOLDEN_SEED
    )

    reliability = {
        r.construct_code: {
            "alpha": _round(r.cronbach_alpha), "rho_a": _round(r.rho_a),
            "rho_c": _round(r.rho_c), "ave": _round(r.ave),
        }
        for r in results["reliability"] if r.status != "na"
    }
    htmt = {
        f"{r.lv_a}|{r.lv_b}": _round(r.htmt) for r in results["discriminant"]["htmt"]
    }
    fornell = {
        r.construct_code: _round(r.sqrt_ave)
        for r in results["discriminant"]["fornell_larcker"] if r.sqrt_ave is not None
    }
    vif = {
        f"{r.scope}|{r.target}|{r.predictor}": _round(r.vif)
        for r in results["collinearity"]
    }
    loadings = {
        f"{r.construct_code}|{r.item}": _round(r.loading) for r in results["outer_model"]
    }
    paths = {
        f"{r.source}->{r.target}": _round(r.original_sample) for r in results["paths"]
    }
    effects = {
        f"{r.kind}|{r.source}->{r.target}": _round(r.estimate)
        for r in results["indirect_total"] if r.kind in ("direct", "indirect", "total")
    }
    explained = {
        r.construct_code: {
            "r2": _round(r.r_squared), "r2_adj": _round(r.r_squared_adj),
            "q2": _round(r.q_squared),
        }
        for r in results["r2_f2_q2"]["explained"]
    }
    f_squared = {
        f"{r.source}->{r.target}": _round(r.f_squared)
        for r in results["r2_f2_q2"]["f_squared"]
    }
    predict = {
        f"{r.construct_code}|{r.indicator}": {
            "q2_predict": _round(r.q2_predict), "rmse_pls": _round(r.rmse_pls),
            "rmse_lm": _round(r.rmse_lm),
        }
        for r in results["plspredict"]["rows"]
    }
    fit = {r.statistic: _round(r.value) for r in results["model_fit"]}

    return {
        "digest": golden.matrix_digest(matrix),
        "fingerprint": spec.fingerprint(),
        "n_cases": matrix.n_cases,
        "expected": {
            "reliability": reliability,
            "htmt": htmt,
            "fornell_larcker": fornell,
            "vif": vif,
            "loadings": loadings,
            "paths": paths,
            "effects": effects,
            "explained": explained,
            "f_squared": f_squared,
            "plspredict": predict,
            "predict_verdict": results["plspredict"]["summary"].verdict,
            "model_fit": fit,
        },
    }


def render(block: dict) -> str:
    """The `EXPECTED` literal, deterministically ordered so a diff is readable."""
    return json.dumps(block, indent=4, sort_keys=True).replace(": null", ": None")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="rewrite golden.py's pinned constants"
    )
    args = parser.parse_args()

    computed = compute()
    source = GOLDEN_PY.read_text(encoding="utf-8")

    current_digest = re.search(r'^GOLDEN_DIGEST = "([^"]*)"', source, re.M).group(1)
    current_print = re.search(r'^GOLDEN_FINGERPRINT = "([^"]*)"', source, re.M).group(1)

    print(f"n_cases      {computed['n_cases']}")
    print(f"digest       {current_digest} -> {computed['digest']}")
    print(f"fingerprint  {current_print} -> {computed['fingerprint']}")
    total = sum(
        len(v) if isinstance(v, dict) else 1 for v in computed["expected"].values()
    )
    print(f"statistics   {total} pinned")

    if not args.write:
        print("\nnothing written; re-run with --write once the diff above is intended")
        return 0

    source = re.sub(
        r'^GOLDEN_DIGEST = "[^"]*"',
        f'GOLDEN_DIGEST = "{computed["digest"]}"',
        source, count=1, flags=re.M,
    )
    source = re.sub(
        r'^GOLDEN_FINGERPRINT = "[^"]*"',
        f'GOLDEN_FINGERPRINT = "{computed["fingerprint"]}"',
        source, count=1, flags=re.M,
    )
    source = re.sub(
        r"^EXPECTED: dict\[str, Any\] = \{.*\Z",
        "EXPECTED: dict[str, Any] = " + render(computed["expected"]) + "\n",
        source, count=1, flags=re.M | re.S,
    )
    GOLDEN_PY.write_text(source, encoding="utf-8")
    print(f"\nwrote {GOLDEN_PY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
