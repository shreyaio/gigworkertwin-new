"""Emit the two JSON assets the Edge Function imports. `docs/04` §8.

The Edge Function runs in Deno and cannot read `config/form_map.yaml` or the frozen reference
`.json` files at request time, so it imports two generated assets:

    supabase/functions/survey_intake/form_map.json       the map, verbatim
    supabase/functions/survey_intake/register_spec.json  the item register, reduced

**They are generated, never hand-edited.** ``--check`` re-derives them and exits non-zero if either
has drifted, which is what stops the Edge Function's copy of the map from diverging from the YAML the
Python side reads — the exact drift `docs/04` §8's "one contract, two implementations" exists to
prevent. It runs in CI beside `build_reference.py --check`.

Usage:
    python tools/gen_edge_assets.py            # write
    python tools/gen_edge_assets.py --check    # verify, exit 1 on drift
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO_ROOT / "src"), str(REPO_ROOT)]

OUT_DIR = REPO_ROOT / "supabase" / "functions" / "survey_intake"


def build_form_map() -> dict:
    import yaml

    from config.settings import CONFIG_DIR

    raw = yaml.safe_load((CONFIG_DIR / "form_map.yaml").read_text(encoding="utf-8"))
    return {"version": str(raw["version"]), "map": dict(raw["map"])}


def build_register_spec() -> dict:
    """The register reduced to what `rows.mjs` actually needs.

    Reduced rather than copied: the Edge Function has no business knowing item stems, constructs or
    scales beyond the points it needs, and a smaller asset is a smaller thing to drift.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.survey_intake import _attention_expectations
    from twinlab.models.twin import WHY_PROBE_ANCHOR

    ref = reference()
    return {
        "itemIds": sorted(ref.items),
        "scalePoints": {
            i: ref.scale_points(i) for i in sorted(ref.items) if ref.items[i].scale_id
        },
        "batteryItemIds": list(ref.battery_item_ids),
        "attention": _attention_expectations(ref),
        "whyProbeAnchor": dict(sorted(WHY_PROBE_ANCHOR.items())),
        # Part 15 offers the four arms by label; `survey_submissions.mc_correct` is
        # `mc_answer = arm`, which compares against an id. Without this map the Edge Function
        # would store the label and `mc_correct` would be false for every real respondent.
        # Case-folded keys, because the comparison is on wording a driver picked, not on a code.
        "armIds": sorted(ref.arms),
        "armLabels": {
            str(arm.label).strip().casefold(): arm_id
            for arm_id, arm in sorted(ref.arms.items())
            if getattr(arm, "label", None)
        },
    }


ASSETS = {
    "form_map.json": build_form_map,
    "register_spec.json": build_register_spec,
}


def serialise(payload: dict) -> str:
    """Stable bytes: sorted keys, two-space indent, trailing newline."""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    failed = False
    for name, builder in ASSETS.items():
        path = OUT_DIR / name
        wanted = serialise(builder())
        if check:
            got = path.read_text(encoding="utf-8") if path.exists() else ""
            if got != wanted:
                print(f"DRIFT  {name} — regenerate with `python tools/gen_edge_assets.py`")
                failed = True
            else:
                print(f"OK     {name}")
        else:
            path.write_text(wanted, encoding="utf-8")
            print(f"wrote  {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
