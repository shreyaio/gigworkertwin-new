"""M0 acceptance tests. `docs/11_BUILD_PLAN.md` -> M0.

Five things are asserted, one per bullet of the milestone's Accept list:

1. both entrypoints serve the same `gr.Blocks` and neither contains logic;
2. the eight routes render in the order of `docs/06` section 0, with a working navbar;
3. `spaces` is never imported and no `@spaces.GPU` decorator exists;
4. an import-linter contract enforces the layer table in `ARCHITECTURE.md` section 4;
5. nothing is named after, or refers to, a "Google Sheet".
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import gradio as gr
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
PY_FILES = sorted(
    p
    for p in [*SRC.rglob("*.py"), REPO_ROOT / "app.py", REPO_ROOT / "app_docker.py"]
    if "__pycache__" not in p.parts
)

from twinlab.ui.theme import ROUTES  # noqa: E402


def executable_source(path: Path) -> str:
    """Source with comments and docstrings removed.

    The bans below are scanned for by text, and this file's own subjects — `@spaces.GPU`,
    "Google Sheet" — are named in prose in the very modules that forbid them. Stripping
    commentary keeps a scan for a banned construct from being tripped by a note saying it is
    banned, while leaving ordinary string literals (which carry user-facing text) intact.
    """
    source = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return source
    tree = ast.parse(source)

    docstring_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", None)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            first = body[0].value.lineno
            docstring_lines.update(range(first, (body[0].value.end_lineno or first) + 1))

    # Line-based, NOT token-based. An earlier version re-joined tokens with newlines, which splits
    # every multi-token construct: `@spaces.GPU` became `@`, `spaces`, `.`, `GPU` on four lines, so
    # the scan below could never match and the ban was a gate that could not fail. Dropping whole
    # docstring and comment lines removes the prose without breaking the patterns.
    return "\n".join(
        line
        for number, line in enumerate(source.splitlines(), start=1)
        if number not in docstring_lines and not line.strip().startswith("#")
    )


# --------------------------------------------------------------------------- entrypoints


def test_both_entrypoints_build_the_same_blocks() -> None:
    """ARCHITECTURE section 8.2 rule 1: one `gr.Blocks`, two thin entrypoints."""
    import app as gradio_entry
    import app_docker as docker_entry

    assert isinstance(gradio_entry.demo, gr.Blocks)
    # The Docker entrypoint mounts the same builder rather than composing its own UI.
    assert docker_entry.build_ui is gradio_entry.build_ui


@pytest.mark.parametrize("entry", ["app.py", "app_docker.py"])
def test_entrypoints_hold_no_logic(entry: str) -> None:
    """Neither entrypoint may contain logic - otherwise the two can drift (8.2 rule 1).

    "No logic" is read strictly: no function or class definitions, and no branching beyond the
    `sys.path` shim and the `__main__` guard.
    """
    tree = ast.parse((REPO_ROOT / entry).read_text(encoding="utf-8"))

    defs = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    assert defs == [], f"{entry} defines {[d.name for d in defs]}; logic belongs in services/"

    # Permitted `if` statements: the sys.path shim and `if __name__ == "__main__"`.
    ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)]
    assert len(ifs) <= 2, f"{entry} branches {len(ifs)} times; it should only shim and launch"


def test_gradio_entrypoint_is_the_space_app_file() -> None:
    """The Space card must point at `app.py` and pin the SDK, Python version and OAuth."""
    card = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    header = card.split("---")[1]
    assert "sdk: gradio" in header
    assert 'python_version: "3.13"' in header
    assert "app_file: app.py" in header
    assert "hf_oauth: true" in header


# --------------------------------------------------------------------------- routes


def test_eight_routes_in_the_mandatory_order() -> None:
    """`docs/06` section 0: eight routes, in this order. Ordering is mandatory."""
    assert ROUTES == (
        ("Main menu", "/"),
        ("Driver survey", "/survey"),
        ("Twin Lab", "/lab"),
        ("Generator", "/generator"),
        ("Twin Studio", "/studio"),
        ("Agent Studio", "/agents"),
        ("Statistics", "/statistics"),
        ("Research model", "/research"),
    )


def test_built_ui_exposes_every_route_in_order() -> None:
    """The Blocks actually serves the eight paths, in the specified order, with a navbar."""
    from twinlab.ui.app import build_ui

    demo = build_ui()

    # Gradio records pages as (path-without-leading-slash, name, show_in_navbar); the root
    # page's path is "" and its label comes from the navbar's `main_page_name`.
    assert [f"/{path}".replace("//", "/") for path, _, _ in demo.pages] == [
        path for _, path in ROUTES
    ]

    navbars = [c for c in demo.blocks.values() if isinstance(c, gr.Navbar)]
    assert navbars, "no navbar was built"

    labels = [navbars[0].main_page_name] + [name for _, name, _ in demo.pages[1:]]
    assert labels == [label for label, _ in ROUTES]

    # Every route is reachable from the navbar; none is a hidden URL.
    assert all(show for _, _, show in demo.pages)


def test_every_route_renders_its_header() -> None:
    """A route that builds but shows nothing is an empty screen, not a scaffold."""
    from twinlab.ui.app import build_ui

    demo = build_ui()
    html = " ".join(
        c.value for c in demo.blocks.values() if isinstance(c, gr.HTML) and isinstance(c.value, str)
    )
    for label, _ in ROUTES:
        assert label in html, f"route {label!r} rendered no header"


# --------------------------------------------------------------------------- portability


def test_spaces_is_never_imported() -> None:
    """ARCHITECTURE section 8.2 rule 4. All inference is remote; ZeroGPU is a free CPU Space."""
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in PY_FILES
        if re.search(r"^\s*(import spaces|from spaces\b)", executable_source(p), re.M)
    ]
    assert offenders == [], f"`spaces` imported in {offenders}"


def test_no_spaces_gpu_decorator() -> None:
    """ARCHITECTURE section 8.2 rule 4."""
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in PY_FILES
        if "@spaces.GPU" in executable_source(p)
    ]
    assert offenders == [], f"@spaces.GPU found in {offenders}"


def test_python_313_is_pinned_everywhere() -> None:
    """3.13 is the target; a fallback to 3.12 is a decision, not a drift (`docs/11`)."""
    assert 'requires-python = ">=3.13"' in (
        REPO_ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert "FROM python:3.13" in (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- layers


def _run_import_linter() -> subprocess.CompletedProcess[str]:
    """Run the contracts in `.importlinter` in a subprocess, with `src/` importable.

    Invoked through the click command object rather than `python -m importlinter.cli`: that
    module has no `__main__` handling, so it imports cleanly and exits 0 without linting
    anything — a silent pass, which is the one outcome a gate like this must never produce.
    """
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command as c; c.main([])",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_import_linter_contracts_hold() -> None:
    """The layer table in ARCHITECTURE.md section 4, enforced rather than documented."""
    pytest.importorskip("importlinter", reason="import-linter is a declared dependency")
    result = _run_import_linter()
    output = result.stdout + result.stderr

    # A run that checked nothing must not read as a pass.
    assert "Contracts:" in output, f"import-linter did not run:\n{output}"
    assert "0 broken" in output, output
    assert result.returncode == 0, output


def test_import_linter_fails_on_a_violation(tmp_path: Path) -> None:
    """M0 Accept: the contract "fails on a violation".

    A gate is only a gate if it is known to reject. A `db` import is temporarily appended to a
    `ui/` module, the linter is re-run, and the file is restored whatever the outcome.
    """
    pytest.importorskip("importlinter", reason="import-linter is a declared dependency")
    target = SRC / "twinlab" / "ui" / "theme.py"
    original = target.read_text(encoding="utf-8")
    try:
        target.write_text(original + "\nfrom twinlab import db  # noqa: E402,F401\n", "utf-8")
        result = _run_import_linter()
    finally:
        target.write_text(original, encoding="utf-8")

    assert result.returncode != 0, "a ui/ -> db/ import was not rejected"
    assert "BROKEN" in (result.stdout + result.stderr).upper()


def test_supabase_is_imported_in_exactly_one_file() -> None:
    """ARCHITECTURE section 3: `supabase` is imported in one file - `db/client.py`."""
    importers = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in PY_FILES
        if re.search(r"^\s*(import supabase|from supabase\b)", executable_source(p), re.M)
    ]
    assert importers in ([], ["src/twinlab/db/client.py"]), importers


def test_pydantic_models_are_declared_only_in_models() -> None:
    """`ARCHITECTURE.md` section 4: a Pydantic model is declared once, in `models/`."""
    offenders = []
    for p in PY_FILES:
        if p.is_relative_to(SRC / "twinlab" / "models"):
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                isinstance(b, ast.Name) and b.id == "BaseModel" for b in node.bases
            ):
                offenders.append(f"{p.relative_to(REPO_ROOT).as_posix()}::{node.name}")
    assert offenders == [], offenders


# --------------------------------------------------------------------------- Google Sheet


def test_nothing_refers_to_a_google_sheet() -> None:
    """`docs/06` section 0: "Google Sheet is removed."

    No route, card, component or user-facing text. Scanned across code, config and the Space
    card - the prototype's database interface must leave no trace in the application.
    """
    scanned = [
        *PY_FILES,
        *(REPO_ROOT / "config").glob("*.yaml"),
        REPO_ROOT / "README.md",
    ]
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in scanned
        if re.search(r"google\s*sheet|gspread|sheets\.google", executable_source(p), re.I)
    ]
    assert offenders == [], f"Google Sheet referenced in {offenders}"
