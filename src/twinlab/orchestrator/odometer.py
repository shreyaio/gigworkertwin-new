"""Version-code arithmetic. `ARCHITECTURE.md` §5 and §5.1.

Five digits, left to right: Pay · Conditions · Contracts · Management · Representation. Base-3
with **Representation least significant**, which is what makes the Results grid's row/column
split (`pay × conditions` by `contracts × management × representation`) a contiguous scan.

Written in M1 because `seed_db.py`'s specified post-seed assertion includes the digit-sum
identity, so the seeder depends on it. **M3 owns its acceptance test** (`docs/DECISIONS.md`).

Pure functions, no state, no I/O.
"""

from __future__ import annotations

from twinlab.models.reference import LEVER_BY_POSITION

N_CODES = 243
CODE_LENGTH = 5
#: Place values, left to right. Representation (position 5) is least significant.
PLACES: tuple[int, ...] = (4, 3, 2, 1, 0)

#: The control cells. Exactly two, ever (`CLAUDE.md` rule 9).
CONTROL_CODE = "00000"
SHAM_CODE = "SHAM"


class InvalidVersionCode(ValueError):
    """A version code that is not five digits each in 0–2."""


def validate_code(code: str) -> str:
    if code == SHAM_CODE:
        return code
    if len(code) != CODE_LENGTH or any(c not in "012" for c in code):
        raise InvalidVersionCode(f"{code!r} is not five digits in 0-2")
    return code


def code_from_index(i: int) -> str:
    if not 0 <= i < N_CODES:
        raise InvalidVersionCode(f"index {i} outside 0..{N_CODES - 1}")
    return "".join(str((i // 3**p) % 3) for p in PLACES)


def index_from_code(code: str) -> int:
    validate_code(code)
    return sum(int(d) * 3**p for d, p in zip(code, PLACES, strict=True))


def digit_sum(code: str) -> int:
    """The Fairwork score, 0–10. `ARCHITECTURE.md` §5."""
    validate_code(code)
    return sum(int(d) for d in code)


def all_codes() -> list[str]:
    return [code_from_index(i) for i in range(N_CODES)]


def dials(code: str) -> dict[str, int]:
    """``{'L1': 0, 'L2': 1, ...}`` for a code."""
    validate_code(code)
    return {lever: int(code[pos]) for pos, lever in enumerate(LEVER_BY_POSITION)}


def combine(code_a: str, code_b: str) -> str:
    """The joint cell of two codes: elementwise max of the dial vectors (`docs/02` §8.3)."""
    validate_code(code_a)
    validate_code(code_b)
    return "".join(str(max(int(a), int(b))) for a, b in zip(code_a, code_b, strict=True))


def advance(index: int, steps: int = 1) -> int:
    """Next odometer position, wrapping at 243."""
    return (index + steps) % N_CODES
