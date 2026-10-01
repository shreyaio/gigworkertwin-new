"""Upload this repository to a Hugging Face Space.

A Space is a git repository, but this uploads over the HTTP API instead, so deploying does not
require the repository to be in git and does not create a commit here. `ARCHITECTURE.md` §8.2
rule 1 is what makes this safe: the Space runs `app.py`, which holds no logic, so there is
nothing to configure at the deployment boundary.

    python tools/deploy_space.py <user>/<space-name>
    python tools/deploy_space.py <user>/<space-name> --probe
    python tools/deploy_space.py <user>/<space-name> --create --dry-run

Authenticate first with `huggingface-cli login`, or set `HF_TOKEN`. The token needs **write**
access.

This uploads code only. Secrets (`SUPABASE_*`, `OLLAMA_API_KEY`, `INTAKE_HMAC_SECRET`) are set
in the Space's own settings and are never written into the repository or sent from here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Caches and local state. Applied to every upload, including the probe's.
ALWAYS_IGNORE = [
    ".venv/*",
    "venv/*",
    "**/__pycache__/*",
    "*.pyc",
    ".pytest_cache/*",
    ".ruff_cache/*",
    ".import_linter_cache/*",
    ".git/*",
    "data/temp/*",
    # Never upload a filled-in environment file. `.env.example` is uploaded; `.env` is not.
    ".env",
]

# Rebuild scaffolding and source documents the running app never reads. Keeping the upload
# small keeps Space rebuilds fast; nothing here is referenced at runtime.
IGNORE = [
    *ALWAYS_IGNORE,
    "_v1_removed/*",
    "_preserve/*",
    "_probe/*",
    "additional_data/*",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_id", help="Target Space, e.g. shreya/twin-lab")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Upload _probe/ instead of the application (the M1 ZeroGPU gate).",
    )
    parser.add_argument("--create", action="store_true", help="Create the Space if it is absent.")
    parser.add_argument("--private", action="store_true", help="Create it private.")
    parser.add_argument(
        "--hardware",
        default="zero-a10g",
        help=(
            "Space hardware on --create. ZeroGPU is the tier a free account gets for a Gradio "
            "Space (ARCHITECTURE.md 8.1); cpu-basic is NOT free here, so omitting this and "
            "letting the API default to cpu-basic returns 402. Nothing is decorated with "
            "@spaces.GPU, so ZeroGPU is being used as a free CPU Space. Pass '' to send no "
            "hardware at all."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would be uploaded and stop."
    )
    args = parser.parse_args()

    from huggingface_hub import HfApi

    folder = REPO_ROOT / "_probe" if args.probe else REPO_ROOT
    ignore = ALWAYS_IGNORE if args.probe else IGNORE

    if args.dry_run:
        # The same filter the upload uses, so the preview cannot disagree with what ships.
        from huggingface_hub.utils import filter_repo_objects

        files = sorted(
            filter_repo_objects(
                [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()],
                ignore_patterns=ignore,
            )
        )
        print(f"{len(files)} file(s) would be uploaded to {args.repo_id}:")
        for f in files:
            print(" ", f)
        return 0

    api = HfApi()
    if args.create:
        from huggingface_hub.errors import HfHubHTTPError

        try:
            api.create_repo(
                repo_id=args.repo_id,
                repo_type="space",
                space_sdk="gradio",
                space_hardware=args.hardware,
                private=args.private,
                exist_ok=True,
            )
        except HfHubHTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 402:
                # Counter-intuitive on this platform: cpu-basic is NOT the free tier for a
                # Gradio Space, ZeroGPU is. A 402 here usually means no hardware was sent and
                # the API defaulted to cpu-basic. Reported rather than retried on another
                # tier - which tier this study deploys on is the researcher's decision
                # (ARCHITECTURE.md section 10, q6).
                print(
                    f"402 Payment Required creating {args.repo_id}"
                    f"{f' on {args.hardware}' if args.hardware else ' with no hardware set'}.\n"
                    "  On a free account a Gradio Space must be created on ZeroGPU:\n"
                    "  cpu-basic and Docker are paid tiers (ARCHITECTURE.md section 8.1).\n"
                    "  Retry with --hardware zero-a10g.",
                    file=sys.stderr,
                )
                return 2
            if status == 403:
                print(
                    f"403 Forbidden creating {args.repo_id}. Either the token lacks write\n"
                    "  access, or the account is under a moderation restriction.",
                    file=sys.stderr,
                )
                return 3
            raise

        where = f" on {args.hardware}" if args.hardware else " on the default (free) tier"
        print(f"Space {args.repo_id} ready{where}.")
        print("  exist_ok: an existing Space keeps the hardware it already has - check Settings.")

    url = api.upload_folder(
        repo_id=args.repo_id,
        repo_type="space",
        folder_path=str(folder),
        ignore_patterns=ignore,
        commit_message="Twin Lab: probe" if args.probe else "Twin Lab: M0 shell",
    )
    print(f"Uploaded.\n  {url}\n  https://huggingface.co/spaces/{args.repo_id}")
    print("\nRemember: set the Space's secrets in Settings, not in the repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
