"""Why a batch of twins passed or failed its H3 gate, in four numbers. Read-only.

`twin_quality_runs.mae` says a twin failed. It does not say **which** failure: a twin biased two
points high and a twin that answers every driver identically can share an MAE and need opposite
fixes. Distinguishing them by hand is what the 2026-10-12 and 2026-10-13 diagnoses each cost, so
this is the measurement, kept so the next one is a command rather than an afternoon.

The four numbers, in the order they decide things:

1. **`r(reactivity band, twin H3 mean)`** — does the twin *read* what the persona says about how
   far this driver moves? The generator puts that signal in (`react:*`, `docs/DECISIONS.md`
   2026-10-13); this says whether any of it comes back. Reported beside the same correlation
   against the **driver's** answers, which is the ceiling the twin is being measured against: a
   low number means nothing if the generator never encoded it either.
2. **Spread ratio** — the twin's between-driver spread as a share of its drivers'. A twin
   answering the batch mean for everyone scores a respectable MAE and is not a twin. Reported for
   H2 and H3 separately because the two differ sharply: H2 mirrors the battery and is nearly
   transcribable from the persona, while H3 asks new questions on new scales and is the only place
   extrapolation is tested.
3. **`pct_within_1`** — the gate's *other* threshold, and the one that binds once the level bias
   is gone. Close on average by being wildly wrong occasionally is not the same twin
   (`validity/quality.h3_verdict`).
4. **Mean MAE and the per-outcome signed error** — level bias, separated by outcome, because
   fairness, pushback and staying have failed by different amounts at every stage.

**Filtered by batch prefix, always.** Pooling two generator versions is how test 3 came to be
measured across respondents drawn under two different construct mappings. Pass `--prefix` and it
will only ever read one batch.

Reads the live database and writes nothing. No model call, no LLM, no gate run.

    python tools/gate_diagnostic.py --prefix SYN-13102026
    python tools/gate_diagnostic.py --prefix SYN-13102026 --label "stage 1"
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT / "src"), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from twinlab.db.client import DbBackend, get_backend  # noqa: E402
from twinlab.generator.voice import CIRCUMSTANCE  # noqa: E402
from twinlab.ingest.reference_store import ReferenceData, reference  # noqa: E402
from twinlab.validity.quality import pearson_r  # noqa: E402

#: The reactivity bands, low to high, as an ordinal for the correlation.
_BAND_ORDER: dict[str, int] = {"react:low": 0, "react:mid": 1, "react:high": 2}


def _band_of_persona(passage: str) -> str | None:
    """Which reactivity band a persona speaks in, or ``None`` if it speaks in none.

    Matched on the clause text rather than read from a column because the band is not stored
    anywhere: it is a property of the drawn respondent that reaches the twin only as prose, which
    is exactly the thing being tested.
    """
    lowered = passage.lower()
    for band in _BAND_ORDER:
        if any(clause.lower() in lowered for clause in CIRCUMSTANCE[band]):
            return band
    return None


async def _answers_of(db: DbBackend, submission: str) -> dict[str, int]:
    rows = await db.select("survey_answers", [("eq", "submission_id", submission)])
    return {r["item_id"]: int(r["value_num"]) for r in rows if r.get("value_num") is not None}


async def _latest_runs(
    db: DbBackend, holdout: str, prefix: str
) -> list[dict]:
    """The latest verdict per twin for one holdout set, for twins under ``prefix``.

    `is_latest` rather than every row: the table is append-only, so a twin re-gated three times
    has three rows and pooling them would average a superseded instrument with a current one.
    """
    rows = await db.select(
        "twin_quality_runs",
        [("eq", "holdout_set", holdout), ("eq", "is_latest", True)],
        limit=1000,
    )
    return sorted(
        (r for r in rows if str(r["twin_id"]).startswith(prefix)),
        key=lambda r: str(r["twin_id"]),
    )


def _spread_ratio(driver_means: list[float], twin_means: list[float]) -> float | None:
    """Twin between-driver spread as a share of the drivers' own. ``None`` when undefined.

    ``None`` rather than 0.0 when the drivers themselves do not vary: a twin cannot be asked to
    reproduce a spread that is not there, and reporting 0% would read as the twin's failure.
    """
    if len(driver_means) < 2:
        return None
    driver_sd = statistics.pstdev(driver_means)
    if driver_sd == 0:
        return None
    return statistics.pstdev(twin_means) / driver_sd


async def _refuse_mixed_versions(db: DbBackend, twins: dict) -> str | None:
    """Refuse a reading that spans two generator versions. Rule 8, enforced at the measurement.

    `--prefix` was supposed to guarantee one batch, and a **prefix is not a batch**: the seeds
    `20261013` and `2026101311` produce `SYN-20261013-…` and `SYN-2026101311-…`, so the shorter
    prefix silently matches both and the diagnostic reported eleven twins for a batch of ten.
    That is precisely the pooling the flag exists to prevent, arriving through the flag itself.

    So the guard is on the thing that actually matters rather than on naming hygiene: resolve
    every matched twin to the batch that drew it and refuse if more than one generator version is
    present. A real driver has no synthetic batch and is skipped rather than counted as a version.

    Keyed on the batch rather than on the generator version, because two batches drawn under one
    version are still two different draws of respondents (`CLAUDE.md` rule 10).

    Returns the refusal text, or ``None`` when the reading is of one batch.
    """
    batches = {
        str(b["batch_id"]): b for b in await db.select("synthetic_batches", limit=500)
    }
    seen: dict[str, list[str]] = {}
    for twin_id, row in sorted(twins.items()):
        submission = str(row.get("submission_id") or twin_id)
        found = await db.select(
            "survey_submissions", [("eq", "submission_id", submission)], limit=1
        )
        if not found:
            continue
        batch_id = str(found[0].get("batch_id") or "")
        batch = batches.get(batch_id)
        if batch is None:
            continue
        config = batch.get("config") or {}
        version = str(config.get("generator_version") or "unrecorded")
        # Keyed on the BATCH, not the version: two batches drawn under one generator version are
        # still two different draws of respondents, and a cell answered by a different set of
        # twins is a different experiment (`CLAUDE.md` rule 10). The version is carried in the
        # label so the refusal says which is which.
        seen.setdefault(f"{batch_id[:8]} ({version})", []).append(str(twin_id))

    if len(seen) <= 1:
        return None
    lines = [
        "REFUSED: this prefix matches twins from more than one BATCH, and pooling two batches "
        "in one measurement is meaningless (a prefix is not a batch).",
        "",
    ]
    for version, ids in sorted(seen.items()):
        lines.append(f"  {version}: {len(ids)} twin(s), e.g. {ids[0]}")
    lines += [
        "",
        "Pass a prefix that selects exactly one of them — a longer one usually does.",
    ]
    return "\n".join(lines)


async def diagnose(prefix: str, label: str, db: DbBackend, ref: ReferenceData) -> int:
    h3_items = ref.holdout_h3_item_ids
    h2_items = ref.holdout_h2_item_ids

    runs = await _latest_runs(db, "H3", prefix)
    if not runs:
        print(f"no H3 verdict for any twin under {prefix!r}. Run the gate first.")
        return 1

    twins = {
        t["twin_id"]: t
        for t in await db.select("twins", [("like", "twin_id", f"{prefix}%")], limit=200)
    }

    refused = await _refuse_mixed_versions(db, twins)
    if refused is not None:
        print(refused)
        return 1

    bands: list[float] = []
    driver_h3: list[float] = []
    twin_h3: list[float] = []
    signed: dict[str, list[int]] = {"FAIR": [], "PUSH": [], "KEEP": []}
    rows_out: list[tuple[str, str, float, float, float, float]] = []

    for run in runs:
        twin_id = str(run["twin_id"])
        row = twins.get(twin_id)
        if row is None:
            continue
        human = await _answers_of(db, str(row.get("submission_id") or twin_id))
        vector = (run.get("detail") or {}).get("answers") or {}
        shared = [i for i in h3_items if i in human and i in vector]
        if not shared:
            continue
        driver_mean = statistics.mean(human[i] for i in shared)
        twin_mean = statistics.mean(vector[i] for i in shared)
        driver_h3.append(driver_mean)
        twin_h3.append(twin_mean)
        for item_id in shared:
            suffix = item_id.rsplit("_", 1)[-1]
            if suffix in signed:
                signed[suffix].append(vector[item_id] - human[item_id])
        band = _band_of_persona(str(row.get("persona_passage") or ""))
        if band is not None:
            bands.append(float(_BAND_ORDER[band]))
        rows_out.append(
            (
                twin_id,
                band or "-",
                driver_mean,
                twin_mean,
                float(run["mae"]),
                float(run["pct_within_1"]),
            )
        )

    print(f"=== H3 gate diagnostic: {prefix}" + (f"  [{label}]" if label else "") + " ===")
    print(f"{len(rows_out)} twins with a latest H3 verdict\n")
    print("twin                      band         driver  twin    mae    within-1  kept")
    for twin_id, band, dm, tm, mae, within in rows_out:
        kept = "KEPT" if mae <= 1.0 and within >= 0.80 else "dropped"
        print(f"{twin_id:25s} {band:12s} {dm:6.2f}  {tm:6.2f}  {mae:5.2f}  {within:7.1%}  {kept}")

    maes = [r[4] for r in rows_out]
    withins = [r[5] for r in rows_out]
    kept_n = sum(1 for r in rows_out if r[4] <= 1.0 and r[5] >= 0.80)

    print("\n--- 1. does the twin read how far this driver moves? ---")
    if len(bands) == len(driver_h3) and len(bands) >= 3:
        in_signal = pearson_r(bands, driver_h3)
        out_signal = pearson_r(bands, twin_h3)
        print(f"  r(band, DRIVER h3)  {_fmt(in_signal)}   <- what the generator encoded (ceiling)")
        print(f"  r(band, TWIN h3)    {_fmt(out_signal)}   <- what the twin gave back")
        if in_signal is not None and abs(in_signal) < 0.2:
            print("  the generator encoded almost no reactivity signal, so the twin's number")
            print("  says nothing about the twin. Check reactivity_spread before reading on.")
    else:
        print("  not enough personas speak a reactivity band to correlate (needs 3).")

    print("\n--- 2. does the twin individuate at all? ---")
    for holdout, items, name in (
        ("H2", h2_items, "H2 (mirrors the battery; near-transcribable)"),
        ("H3", h3_items, "H3 (new questions, new scales; extrapolation)"),
    ):
        dm: list[float] = []
        tm: list[float] = []
        for run in await _latest_runs(db, holdout, prefix):
            row = twins.get(str(run["twin_id"]))
            if row is None:
                continue
            human = await _answers_of(db, str(row.get("submission_id") or run["twin_id"]))
            vector = (run.get("detail") or {}).get("answers") or {}
            shared = [i for i in items if i in human and i in vector]
            if not shared:
                continue
            dm.append(statistics.mean(human[i] for i in shared))
            tm.append(statistics.mean(vector[i] for i in shared))
        ratio = _spread_ratio(dm, tm)
        if ratio is None:
            print(f"  {name}: drivers do not vary, so no ratio is defined")
        else:
            print(
                f"  {name}:\n"
                f"      driver spread {statistics.pstdev(dm):.3f}  "
                f"twin spread {statistics.pstdev(tm):.3f}  -> twin recovers {ratio:.0%}"
            )

    print("\n--- 3. the gate's two thresholds ---")
    print(f"  mean MAE        {statistics.mean(maes):.3f}   (keep at or below 1.00)")
    print(f"  mean within-1   {statistics.mean(withins):.1%}   (keep at or above 80.0%)")
    print(f"  KEPT            {kept_n} of {len(rows_out)}")

    print("\n--- 5. did passing require telling the six versions apart? ---")
    # The 2026-10-13 diagnosis. The one real driver answered the six Part 17 versions within a
    # range of exactly one scale point, so a twin that reads the PERSON perfectly and ignores the
    # VERSION entirely scored 0.50 against them and passed with room to spare, while the same
    # twin scores 1.01 against a synthetic driver. That was the whole of the one pass and the ten
    # failures. Reported beside every verdict from now on, because an MAE alone cannot say
    # whether a pass demonstrated the thing H3 exists to test (`docs/08` section 2.3: whether the
    # mapping from stimulus to response transfers, not just the level).
    blind: list[float] = []
    for run in await _latest_runs(db, "H3", prefix):
        row = twins.get(str(run["twin_id"]))
        if row is None:
            continue
        human = await _answers_of(db, str(row.get("submission_id") or run["twin_id"]))
        vector = (run.get("detail") or {}).get("answers") or {}
        shared = [i for i in h3_items if i in human and i in vector]
        if not shared:
            continue
        by_outcome: dict[str, list[int]] = {}
        for item in shared:
            by_outcome.setdefault(item.rsplit("_", 1)[-1], []).append(human[item])
        per_outcome = {k: statistics.mean(v) for k, v in by_outcome.items()}
        blind.append(
            statistics.mean(
                abs(human[i] - per_outcome[i.rsplit("_", 1)[-1]]) for i in shared
            )
        )
    if blind:
        under = sum(1 for b in blind if b <= 1.0)
        print(
            f"  version-blind oracle MAE {statistics.mean(blind):.2f}  "
            f"(range {min(blind):.2f}-{max(blind):.2f}; under the 1.00 cap for "
            f"{under} of {len(blind)})"
        )
        print("  A twin that reads the person perfectly and ignores which version it was asked")
        print("  about would score this. Where it is under the cap, a PASS does NOT demonstrate")
        print("  that the twin tells the six versions apart - read it beside number 1 above.")
    else:
        print("  no twin has both a driver and an H3 vector, so there is nothing to bound.")

    print("\n--- 4. level bias, by outcome ---")
    for suffix in ("FAIR", "PUSH", "KEEP"):
        values = signed[suffix]
        if not values:
            continue
        print(
            f"  {suffix}: signed {statistics.mean(values):+.2f}  "
            f"sd {statistics.pstdev(values):.2f}  "
            f"|err| {statistics.mean(abs(v) for v in values):.2f}"
        )
    return 0


def _fmt(value: float | None) -> str:
    """A correlation, or why there is none. Never 0.00 standing in for undefined."""
    return "undefined" if value is None else f"{value:+.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        required=True,
        help="twin_id prefix naming ONE batch, e.g. SYN-13102026. Required: pooling two "
        "generator versions measures respondents drawn under different construct mappings.",
    )
    parser.add_argument("--label", default="", help="a note for the printed header, e.g. 'stage 1'")
    args = parser.parse_args()
    return asyncio.run(diagnose(args.prefix, args.label, get_backend(), reference()))


if __name__ == "__main__":
    raise SystemExit(main())
