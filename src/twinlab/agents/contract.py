"""THE validation ladder. `docs/02` §5. Implements I13.

Ollama Cloud accepts `response_format` with `json_schema` **without error and does not apply
grammar-constrained decoding**, so schemas are silently unenforced. Every model output is therefore
validated here, in Python, against the item register — every time, for every agent. "The schema
says so" is never a reason to skip a check.

    parse → normalise → validate → bounded targeted repair → hard fail

**Normalisation is syntactic only.** It may repair how a value was *written*. It may never change
what a value *means*. The two lists are in `docs/02` §5.3 and the split is the single most
important thing in this file:

==================================== =========================================
Allowed (syntax)                     Forbidden (meaning)
==================================== =========================================
strip markdown fences, surrounding   pad a missing item with the baseline
prose
``"6"`` → ``6``                      clamp ``6`` on a 5-point item to ``5``
``6.0`` → ``6`` (exactly integral)   round ``5.5`` to ``6``
trim whitespace, normalise key case  infer an item from a neighbour
drop a duplicate whose values agree  pick the first of two disagreeing duplicates
==================================== =========================================

Everything in the right column converts a **detectable failure** into an **undetectable
fabrication**. This module implements the left column and nothing else. There is no configuration
flag that enables the right column, and adding one is a research decision.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

#: One model call. ``None`` asks for the first attempt; a string is the targeted repair text.
#: Supplied by the caller so this module never imports a provider.
AskFn = Callable[[str | None], Any | Awaitable[Any]]

#: A fenced block, with or without a language tag.
_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\s*(.*?)\s*```", re.S)

#: The first balanced-looking JSON object or array in a blob of prose.
_FIRST_JSON = re.compile(r"[{\[].*[}\]]", re.S)


class ContractError(ValueError):
    """A model output that could not be made valid without changing its meaning.

    The correct outcome for a twin that cannot produce a valid vector after one targeted repair.
    It fails **for that cell only**; it is not dropped from the study or from the panel — only the
    quality gate drops twins (`docs/02` §5.4).
    """


@dataclass
class Defect:
    """One reason a vector is invalid, precise enough to re-ask for exactly that.

    ``kind`` is ``missing``, ``extra``, ``out_of_range``, ``not_an_integer`` or ``ambiguous``.
    """

    item_id: str
    kind: str
    detail: str = ""
    points: int | None = None

    def __str__(self) -> str:
        return f"{self.item_id}: {self.kind}{f' ({self.detail})' if self.detail else ''}"


@dataclass
class NormaliseReport:
    """What normalisation actually did, so every repair is inspectable rather than implicit."""

    value: Any
    repairs: list[str] = field(default_factory=list)

    def note(self, what: str) -> None:
        self.repairs.append(what)


# --------------------------------------------------------------------------- parsing


def strip_fences(text: str) -> str:
    """Pull the payload out of a markdown fence, and out of surrounding prose.

    Allowed: this changes how the JSON was *presented*, not what it says.
    """
    match = _FENCE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_json(raw: str | bytes | dict | list) -> Any:
    """Best-effort structural parse. Raises :class:`ContractError` if there is no JSON at all.

    Prose before or after the object is stripped (allowed, syntactic). Nothing is invented: a
    blob with no JSON in it is a failure, not an empty result.
    """
    if isinstance(raw, (dict, list)):
        return raw
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    text = strip_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _FIRST_JSON.search(text)
    if match is None:
        raise ContractError(f"no JSON object found in model output: {text[:120]!r}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ContractError(f"model output is not valid JSON: {exc}") from exc


def model_payload(raw: Any) -> Any:
    """Whatever a client returned → a plain payload :func:`normalise_answers` can read.

    ``ModelClient.run().output`` is a **model instance** when the provider was handed an output
    marker, and a dict when a stub hands back a fixture. `normalise_answers` branches on
    ``isinstance(payload, dict)`` and raises otherwise, so without this every live reply —
    including a perfectly valid one — was reported as unparseable, burned an attempt and failed
    the round. The M6 tests did not catch it because the stub returns dicts.

    ``model_dump()`` is a shape conversion, not a repair: no key is added, dropped or rewritten,
    so this stays on the allowed side of `docs/02` §5.3.
    """
    if isinstance(raw, BaseModel):
        return raw.model_dump()
    if isinstance(raw, (str, bytes)):
        return parse_json(raw)
    return raw


# --------------------------------------------------------------------------- normalisation


def _as_int(value: Any) -> int | None:
    """``"6"`` → ``6``; ``6.0`` → ``6`` when **exactly** integral. Otherwise ``None``.

    ``5.5`` returns ``None`` — rounding it would be the forbidden repair. ``True`` returns
    ``None``: `bool` is an `int` in Python and a boolean is not an answer.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            pass
        try:
            number = float(text)
        except ValueError:
            return None
        return int(number) if number.is_integer() else None
    return None


def normalise_answers(
    payload: Any, *, known_items: dict[str, str] | None = None
) -> NormaliseReport:
    """Syntactic repairs only, on an answer mapping. `docs/02` §5.3.

    ``known_items`` maps an upper-cased item id to its canonical spelling, so key case can be
    normalised against the register rather than guessed. An unrecognisable key is **kept as it
    is** and becomes an ``extra`` defect — silently dropping it would hide the fact that the
    model answered something that does not exist.

    Values that cannot be read as an integer without changing their meaning are left **exactly as
    they arrived**, so :func:`validate_answers` reports them as defects rather than inventing a
    substitute.
    """
    report = NormaliseReport(value={})
    if isinstance(payload, dict) and "answers" in payload:
        if not isinstance(payload["answers"], dict):
            raise ContractError(f"`answers` is {type(payload['answers']).__name__}, not an object")
        source = payload["answers"]
        rationale = payload.get("rationale", "")
    elif isinstance(payload, dict):
        source = payload
        rationale = ""
    else:
        raise ContractError(f"expected an object of answers, got {type(payload).__name__}")

    out: dict[str, Any] = {}
    seen_raw: dict[str, list[Any]] = {}

    for raw_key, raw_value in source.items():
        key = str(raw_key).strip()
        canonical = key
        if known_items is not None:
            canonical = known_items.get(key.upper(), key)
            if canonical != key:
                report.note(f"key case normalised: {key!r} → {canonical!r}")
        seen_raw.setdefault(canonical, []).append(raw_value)

    for key, values in seen_raw.items():
        normalised = [_as_int(v) for v in values]
        if len(values) > 1:
            distinct = {v for v in normalised if v is not None}
            if len(distinct) == 1 and None not in normalised:
                # Allowed: a duplicated key whose values agree carries no ambiguity.
                report.note(f"dropped duplicate {key} (values agreed)")
                out[key] = distinct.pop()
                continue
            # Forbidden: picking the first of two disagreeing duplicates. Keep the ambiguity
            # visible so validation fails on it.
            out[key] = _Ambiguous(values)
            continue
        value, only = normalised[0], values[0]
        if value is None:
            out[key] = only          # left untouched; validation will report it
        else:
            if not isinstance(only, int) or isinstance(only, bool):
                report.note(f"{key}: {only!r} read as {value}")
            out[key] = value

    report.value = {"answers": out, "rationale": rationale}
    return report


@dataclass(frozen=True)
class _Ambiguous:
    """Two disagreeing values for one item. Never resolved — only reported."""

    values: list[Any]


# --------------------------------------------------------------------------- validation


def validate_answers(
    answers: dict[str, Any], expected: list[str], points_for: dict[str, int]
) -> list[Defect]:
    """Every defect in one vector, against the item register. I13.

    ``points_for`` comes from `scales.points` via the register — never a constant here. A 5-point
    item rejects ``6`` and ``7``; that is the whole reason this function reads per-item ranges
    instead of assuming 1–7 the way the prototype did.

    Returns **all** defects, not the first, so a targeted repair can name every one at once and
    spend a single serial slot.
    """
    defects: list[Defect] = []
    expected_set = set(expected)
    got = set(answers)

    for item_id in sorted(expected_set - got):
        defects.append(Defect(item_id, "missing", points=points_for.get(item_id)))
    for item_id in sorted(got - expected_set):
        defects.append(Defect(item_id, "extra", "not in the expected item set"))

    for item_id in sorted(expected_set & got):
        value = answers[item_id]
        points = points_for[item_id]
        if isinstance(value, _Ambiguous):
            defects.append(Defect(
                item_id, "ambiguous",
                f"disagreeing duplicates {value.values!r}", points=points,
            ))
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            defects.append(Defect(
                item_id, "not_an_integer", f"{value!r}", points=points,
            ))
            continue
        if not 1 <= value <= points:
            defects.append(Defect(
                item_id, "out_of_range", f"{value} outside 1..{points}", points=points,
            ))
    return defects


def merge_valid(
    previous: dict[str, int], candidate: dict[str, Any], defects: list[Defect]
) -> dict[str, int]:
    """Keep attempt 1's valid answers and take only the repaired items from attempt 2.

    `docs/02` §5.4: "Valid items from attempt 1 are **kept**." This is what makes the repair
    targeted rather than a re-roll — the 35 answers that were already valid do not move, so the
    repair adds no variance to them.
    """
    defective = {d.item_id for d in defects}
    merged = {k: v for k, v in previous.items() if k not in defective}
    for item_id in defective:
        if item_id in candidate and isinstance(candidate[item_id], int):
            if not isinstance(candidate[item_id], bool):
                merged[item_id] = candidate[item_id]
    return merged


# --------------------------------------------------------------------------- repair prompt


def repair_instruction(defects: list[Defect]) -> str:
    """The targeted repair ask. `docs/02` §5.4.

    Names the defective items and **their own ranges**, and asks for only those. The example in
    the specification is exact:

        `PAC4` and `PAC7` were missing. Return only those two, as whole numbers from 1 to 5.

    Nothing about the valid items is mentioned, so the model has nothing to re-roll.
    """
    if not defects:
        raise ContractError("repair_instruction called with no defects")

    by_kind: dict[str, list[Defect]] = {}
    for defect in defects:
        by_kind.setdefault(defect.kind, []).append(defect)

    sentences: list[str] = []
    for kind in ("missing", "out_of_range", "not_an_integer", "ambiguous", "extra"):
        group = by_kind.get(kind)
        if not group:
            continue
        names = ", ".join(f"`{d.item_id}`" for d in group)
        if kind == "missing":
            sentences.append(f"{names} {_was_were(group)} missing.")
        elif kind == "out_of_range":
            detail = "; ".join(f"{d.item_id} gave {d.detail}" for d in group)
            sentences.append(f"{names} {_was_were(group)} outside the allowed range ({detail}).")
        elif kind == "not_an_integer":
            sentences.append(f"{names} {_was_were(group)} not a whole number.")
        elif kind == "ambiguous":
            sentences.append(f"{names} {_was_were(group)} given twice with different values.")
        else:
            them = "it" if len(group) == 1 else "them"
            sentences.append(
                f"{names} {_is_are(group)} not part of what was asked; drop {them}."
            )

    repairable = [d for d in defects if d.kind != "extra"]
    if repairable:
        ranges: dict[int | None, list[str]] = {}
        for defect in repairable:
            ranges.setdefault(defect.points, []).append(defect.item_id)
        parts = []
        for points, ids in sorted(ranges.items(), key=lambda kv: (kv[0] is None, kv[0])):
            names = ", ".join(f"`{i}`" for i in sorted(ids))
            if points is None:
                parts.append(f"{names} as whole numbers")
            else:
                parts.append(f"{names} as whole numbers from 1 to {points}")
        count = len(repairable)
        which = "that one" if count == 1 else f"those {count}"
        sentences.append(f"Return only {which}: {'; '.join(parts)}.")

    return " ".join(sentences)


def _was_were(group: list[Defect]) -> str:
    return "was" if len(group) == 1 else "were"


def _is_are(group: list[Defect]) -> str:
    return "is" if len(group) == 1 else "are"


# --------------------------------------------------------------------------- the ladder


@dataclass
class ContractOutcome:
    """The ladder's result: a validated model or an honest failure. Never a coerced value."""

    ok: bool
    output: BaseModel | None = None
    retries: int = 0
    defects: list[Defect] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    reason: str = ""

    def raise_if_failed(self) -> BaseModel:
        if not self.ok or self.output is None:
            raise ContractError(self.reason or "; ".join(str(d) for d in self.defects))
        return self.output


#: Every numeric token in a piece of prose. `docs/02` §6.1.
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def grounded(prose: str, allowed: set[str]) -> list[str]:
    """Numeric tokens in ``prose`` that are not in ``allowed``. Empty list = grounded. I12.

    `docs/02` §6.1. No model ever produces a metric, and a prompt instruction is necessary but not
    sufficient: a model told "never invent a number" still occasionally does, so it is checked.

    ``allowed`` comes from :meth:`AnalysisBundle.numeric_tokens`, which is generated from the
    bundle and never hand-maintained. An unmatched token fails the output, triggers one targeted
    retry quoting the offending sentence, and then falls back to the deterministic template — the
    run still completes, and the fallback rate is itself a reportable diagnostic.
    """
    return [token for token in NUM.findall(prose) if token not in allowed]


def offending_sentences(prose: str, allowed: set[str]) -> list[str]:
    """The sentences carrying ungrounded numbers, for the targeted retry. `docs/02` §6.1.

    Quoting the sentence rather than the token is what makes the retry targeted: the model is told
    which claim is unsupported, not merely that a digit was wrong somewhere.
    """
    out: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", prose.strip()):
        if sentence and grounded(sentence, allowed):
            out.append(sentence.strip())
    return out


async def run_answer_ladder(
    ask: AskFn,
    *,
    expected: list[str],
    points_for: dict[str, int],
    schema: type[BaseModel],
    attempts: int = 2,
    schema_extra: dict[str, Any] | None = None,
) -> ContractOutcome:
    """The repair ladder for an answer vector. `docs/02` §5.4.

    ``ask(instruction)`` performs one model call: ``None`` for the first attempt, and the targeted
    repair text for a retry. It is supplied by the caller, so this function never imports a
    provider and the ladder is testable with a stub (`docs/11` → Ground rules).

    ``attempts`` counts the first call, so the default of 2 is "one call plus one repair" — the
    budget `docs/02` §5.4 specifies. When the last attempt still leaves a defect, the outcome is
    ``ok=False`` and **nothing is coerced**: the unit is recorded failed, which for a twin means
    failed *for that cell only*.

    ``ContractOutcome.retries`` is the repair count that `twin_answers.retries` stores, so a model
    or prompt version that needs many repairs is visible in the data rather than hidden.
    """
    instruction: str | None = None
    answers: dict[str, Any] = {}
    defects: list[Defect] = []
    repairs: list[str] = []
    known = {item_id.upper(): item_id for item_id in expected}

    for attempt in range(attempts):
        raw = await _maybe_await(ask(instruction))
        try:
            payload = model_payload(raw)
            report = normalise_answers(payload, known_items=known)
        except ContractError as exc:
            # An unparseable attempt is a defect in the whole vector, not in one item.
            defects = [Defect("*", "unparseable", str(exc))]
            repairs.append(f"attempt {attempt + 1}: {exc}")
            instruction = (
                "The previous reply could not be read as JSON. Return a single JSON object "
                "mapping each item id to a whole number, and nothing else."
            )
            continue

        repairs.extend(report.repairs)
        candidate = report.value["answers"]
        answers = merge_valid(answers, candidate, defects) if defects else dict(candidate)
        defects = validate_answers(answers, expected, points_for)

        if not defects:
            payload_out = {"answers": answers, **(schema_extra or {})}
            rationale = report.value.get("rationale", "")
            if rationale and "rationale" not in payload_out:
                payload_out["rationale"] = rationale
            outcome = validate_output(payload_out, schema)
            outcome.retries = attempt
            outcome.repairs = repairs + outcome.repairs
            return outcome

        instruction = repair_instruction(defects)

    return ContractOutcome(
        ok=False,
        retries=max(attempts - 1, 0),
        defects=defects,
        repairs=repairs,
        reason=(
            f"{len(defects)} defect(s) survived {attempts} attempt(s): "
            + "; ".join(str(d) for d in defects)
            + ". Recorded as failed; nothing coerced (I13)."
        ),
    )


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


def validate_output(payload: Any, schema: type[BaseModel]) -> ContractOutcome:
    """Normalise then validate a non-answer output against its schema.

    Used for the Design, Checker and Analyst shapes, where there is no per-item register to read
    and the schema is the whole contract. The parse and fence-stripping repairs are the same
    syntactic ones; nothing else is attempted.
    """
    report = NormaliseReport(value=payload)
    if isinstance(payload, (str, bytes)):
        report = NormaliseReport(value=parse_json(payload))
        report.note("parsed JSON out of raw model text")
    try:
        return ContractOutcome(
            ok=True, output=schema.model_validate(report.value), repairs=report.repairs
        )
    except ValidationError as exc:
        return ContractOutcome(
            ok=False, repairs=report.repairs,
            reason=f"{schema.__name__} validation failed: {exc.error_count()} error(s): {exc}",
        )
