"""Generate a batch of synthetic survey respondents and store them. `docs/06` §4, `docs/04` §2.

The Generator screen now does all of this, and does it better: it has the whole of `docs/06` §4's
dashboard, while this script has a seed and a count. Keep it for scripted and repeatable runs —
seeding a fresh project, regenerating a cited batch in CI, or deleting a batch without opening the
UI. Everything it calls is the service layer the screen calls.

    python tools/generate_synthetic.py --count 300 --seed 20260930
    python tools/generate_synthetic.py --count 300 --seed 20260930 --dry-run
    python tools/generate_synthetic.py --delete-synthetic

**Deterministic in `(seed, count)`.** The same pair reproduces the same respondents, which is what
makes a synthetic run citable (`docs/09` §2). Change the seed to get different people; re-use it to
get the same ones.

**Raw objects are written before rows** (I16), through :class:`SupabaseStorage`, in the same order
live intake uses — a synthetic row whose raw object is missing is a different kind of record from a
real one, and `replay_raw.py` would report it as an orphan forever.

**The Storage client is `db/client.py`'s**, not this script's. It used to hold its own
`SupabaseStorage`, which put the `supabase` SDK outside the one file allowed to import it
(`CLAUDE.md` — Boundaries) and left the Generator screen with nothing to call, so *Generate
surveys* shipped disabled. `get_storage()` is now the one mirror and both callers use it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from twinlab.db.client import get_backend, get_storage  # noqa: E402
from twinlab.generator.synthetic import generate_batch  # noqa: E402
from twinlab.services.surveys import (  # noqa: E402
    counts_by_type,
    delete_synthetic,
    store_batch,
)


class DryRunStorage:
    """Counts what would be written. `--dry-run` never touches Storage or the database."""

    name = "dry-run"

    def __init__(self) -> None:
        self.written = 0

    async def put(self, path: str, body: str) -> None:  # noqa: ARG002
        self.written += 1


def _describe(batch: dict) -> str:
    """A one-screen summary of who was generated, so a batch is inspected before it is stored."""
    subs = batch["submissions"]
    by = {}
    for row in subs:
        key = (row.get("city"), row.get("service"), row.get("arm"))
        by[key] = by.get(key, 0) + 1

    eligible = sum(1 for r in subs if r.get("eligible"))
    consented = sum(1 for r in subs if r.get("consent_twin"))
    attention = sum(1 for r in subs if r.get("attention_passed"))
    straight = sum(1 for r in subs if r.get("straight_liner"))

    lines = [
        f"  respondents        {len(subs)}",
        f"  answers            {len(batch['answers'])}",
        f"  eligible           {eligible}",
        f"  consented to twin  {consented}",
        f"  passed attention   {attention}",
        f"  straight-liners    {straight}",
        "  city | service | arm:",
    ]
    for (city, service, arm), n in sorted(by.items(), key=lambda kv: str(kv[0])):
        lines.append(f"    {city or '-':10s} {service or '-':8s} {arm or '-':8s} {n:4d}")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=300, help="respondents to generate")
    parser.add_argument(
        "--seed", type=int, default=20260930,
        help="the batch is deterministic in (seed, count); reuse it to reproduce",
    )
    parser.add_argument("--name", default=None, help="batch name; defaults to seed and count")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="generate and describe, write nothing",
    )
    parser.add_argument(
        "--delete-synthetic", action="store_true",
        help="remove every synthetic submission, its answers and its twins, and stop",
    )
    args = parser.parse_args()

    backend = get_backend()
    print(f"backend: {backend.name}")
    if backend.name != "supabase" and not args.dry_run:
        print(
            "\nThe in-memory backend is not shared between processes: a batch written here would\n"
            "vanish when this script exits and the running app would never see it. Set\n"
            "SUPABASE_URL and SUPABASE_SERVICE_KEY, or pass --dry-run to inspect a batch.",
            file=sys.stderr,
        )
        return 2

    if args.delete_synthetic:
        result = await delete_synthetic(backend=backend)
        print(f"deleted: {json.dumps(result, default=str)}")
        print(f"remaining by data_type: {await counts_by_type(backend)}")
        return 0

    name = args.name or f"synthetic seed={args.seed} n={args.count}"
    batch = generate_batch(seed=args.seed, count=args.count, name=name)
    print(f"\ngenerated '{name}'\n{_describe(batch)}")

    if args.dry_run:
        print("\n--dry-run: nothing was written.")
        return 0

    storage = get_storage()
    result = await store_batch(batch, storage=storage, backend=backend)

    print(
        f"\nstored batch {result['batch_id']}: {result['submissions']} submissions, "
        f"{len(batch['payloads'])} raw objects via {storage.name}"
    )
    print(f"by data_type: {await counts_by_type(backend)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
