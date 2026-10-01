"""The eight validity tests' shapes. `docs/08` §4 and §5. Implements I15, serves I9 and I12.

`CLAUDE.md` rule 13: every Pydantic model lives in `models/`, and these are the ones the validity
layer produces. Three of them exist to make a research failure **unconstructible** rather than
merely discouraged:

* :class:`ValidityOutcome` refuses to exist with ``twins_n = 0`` and any verdict but
  ``INCONCLUSIVE`` (I15). The DDL's `validity_zero_n` says the same thing at the database, and the
  in-memory backend mirrors it — but a test that ran on nobody should not survive long enough to
  reach a write. The prototype stored live-mode `PASS` verdicts on zero twins.
* :class:`ProbeStimulus` is test 4's deliberately self-contradictory stimulus. It carries
  ``synthetic_probe`` as a `Literal[True]` that cannot be turned off, and it **has no
  `version_code` field at all**, so it cannot be filed as one of the 243 or reached from the Dial
  board. It bypassed the lookup (I1) and the Checker (I3) by construction, which is the experiment.
* :class:`AblatedPersona` is test 6's persona with the fairness items removed. It is deliberately
  **not** a :class:`~twinlab.models.twin.PersonaPassage` and deliberately carries **no
  `persona_hash`**: a passage that violates I6's losslessness by design must not be structurally
  interchangeable with one that does not, and must have nothing to write into `twins.persona_hash`.

Nothing here computes a statistic. Statistics are computed in `validity/tests.py`, in Python, from
stored integers (I12).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: `docs/08` §5. Four, and `INCONCLUSIVE` is **not a pass** — it is the verdict of a test that
#: could not run, most often because it ran on nobody.
Verdict = Literal["PASS", "FAIL", "CHECK", "INCONCLUSIVE"]

#: The label test 4's stimulus carries everywhere it is shown.
PROBE_LABEL = "synthetic probe — contradictory by construction, not one of the 243"

#: The label test 6's persona carries. It is not a persona of anybody.
ABLATION_LABEL = "ablated persona — fairness items removed on purpose, never a study persona"


class ValidityOutcome(BaseModel):
    """One completed validity test, before it is appended. `docs/08` §4 and §5.

    **A test that ran on nobody is `INCONCLUSIVE`, never `PASS`** (I15). Enforced in the validator
    below rather than only at the write, so the impossible row cannot be assembled, passed around,
    logged, or rendered on the way to being rejected by the database.
    """

    model_config = ConfigDict(extra="forbid")

    test_id: str
    twins_n: int = Field(ge=0)
    #: Test-specific numbers, all computed in Python (I12). ``None`` is a value — "not measured"
    #: is not zero.
    statistics: dict[str, float | None] = Field(default_factory=dict)
    verdict: Verdict
    #: One line for the results table.
    headline: str
    #: One line saying what the test measures, so `validity_results` reads without `docs/08`.
    detail: str
    #: Both model names on test 7; the single model elsewhere.
    models: list[str] = Field(default_factory=list)
    temperature: float | None = None

    @model_validator(mode="after")
    def _zero_twins_is_inconclusive(self) -> ValidityOutcome:
        if self.twins_n == 0 and self.verdict != "INCONCLUSIVE":
            raise ValueError(
                f"{self.test_id} claims {self.verdict} on zero twins. A test that ran on nobody "
                "concluded nothing (I15); the verdict is INCONCLUSIVE."
            )
        return self


class PairedGap(BaseModel):
    """A paired mean difference with its confidence interval. Test 1, `docs/08` §4.

    ``ci_lower``/``ci_upper`` are ``None`` when the interval is undefined — one twin, or no
    spread. ``None`` rather than ``0.0``: "the interval could not be computed" and "the interval
    touches zero" are different claims and only one of them is evidence.
    """

    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=0)
    mean: float | None = None
    sd: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None

    @property
    def excludes_zero(self) -> bool:
        """Whether the interval is entirely on one side of zero. ``False`` when undefined."""
        if self.ci_lower is None or self.ci_upper is None:
            return False
        return self.ci_lower > 0 or self.ci_upper < 0


class ProbeStimulus(BaseModel):
    """Test 4's self-contradictory stimulus. `docs/08` §4 test 4.

    **It has no `version_code`.** That absence is the enforcement: every path that files a
    stimulus — `variants`, the Dial board, the odometer, the run cache — is keyed on a version
    code, and a shape that cannot carry one cannot be filed by any of them. ``synthetic_probe`` is
    a `Literal[True]` so it cannot be unset by a caller who wants the probe to look ordinary.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    probe_id: str
    synthetic_probe: Literal[True] = True
    #: Lever → paragraph. Written by a fixture, never rendered by the design agent and never
    #: passed through the Checker, because a contradiction is exactly what the Checker rejects.
    paragraphs: dict[str, str]
    #: The two commitments that contradict each other, in the researcher's words.
    contradiction: str
    label: str = PROBE_LABEL


class AblatedPersona(BaseModel):
    """Test 6's persona with the fairness clauses removed. `docs/08` §4 test 6.

    Not a :class:`~twinlab.models.twin.PersonaPassage`, and carrying **no `persona_hash`**: there
    is nothing here that `twins.persona_hash` could be set from, so the ablation cannot be written
    onto a twin by a caller who confuses the two. It violates I6 by design, and the violation is
    the experiment rather than a defect.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    twin_id: str
    ablated: Literal[True] = True
    text: str
    #: The item ids whose clauses were removed, so the ablation is reproducible and auditable.
    removed_items: list[str]
    label: str = ABLATION_LABEL


class TemperatureRecommendation(BaseModel):
    """Test 8's output: the temperature the sweep supports. `docs/02` §7.3, `docs/08` §4 test 8.

    A **recommendation**, never an applied setting. `TwinConfig.temperature` is frozen onto every
    session's config, so changing it silently would make two sessions incomparable without anything
    in the data saying why. The researcher applies it deliberately.
    """

    model_config = ConfigDict(extra="forbid")

    recommended: float | None
    #: Temperature → between-twin SD of the index at that temperature. A zero means the twins
    #: collapsed to the same answers, which `docs/08` §4 test 8 warns about explicitly.
    between_twin_sd: dict[str, float]
    #: The largest per-metric spread across the three temperatures.
    max_metric_spread: float | None
    reason: str


class QuarantinedArtefact(ValueError):
    """An artefact built for a validity test, refused at a store it must never enter.

    Declared here beside the two flags it polices so that the guards below can be called from
    `db/` — which may import `models/` and nothing else (`ARCHITECTURE.md` §4) — and therefore
    **at the write**, which is the only place the Studio quarantine taught us a rule holds.
    """


def _flagged(value: object, flag: str) -> bool:
    if isinstance(value, dict):
        return bool(value.get(flag))
    return bool(getattr(value, flag, False))


def assert_not_a_probe(*values: object) -> None:
    """Refuse anything carrying test 4's ``synthetic_probe`` flag. `docs/11` M13.

    Called inside `VariantRepo.put`, not in a handler. The probe bypasses the lookup (I1) and the
    Checker (I3) by construction, so a `variants` row holding it would be a stimulus with no
    threshold, no reproducible delta hash and no checker verdict, filed beside 243 that have all
    three — and reachable from the Dial board like any other cell.
    """
    for value in values:
        if _flagged(value, "synthetic_probe"):
            raise QuarantinedArtefact(
                "a synthetic_probe stimulus cannot be written to `variants`. Test 4's probe is "
                "contradictory by construction: it bypassed the lookup (I1) and the Checker (I3), "
                "so it is not one of the 243 and must be unreachable from the Dial board "
                "(docs/08 §4 test 4)."
            )


def assert_not_ablated(*values: object) -> None:
    """Refuse anything carrying test 6's ``ablated`` flag. `docs/11` M13.

    Called at the two places that insert a `twins` row. An ablated persona deliberately violates
    I6's losslessness; hashing it onto a twin would make a passage missing its fairness clauses
    indistinguishable downstream from one that never had them.
    """
    for value in values:
        if _flagged(value, "ablated"):
            raise QuarantinedArtefact(
                "an ablated persona cannot be written to `twins`. Test 6 removes the fairness "
                "items on purpose, which breaks I6's losslessness; the passage is a probe and "
                "never a twin's persona (docs/08 §4 test 6)."
            )


__all__ = [
    "ABLATION_LABEL",
    "PROBE_LABEL",
    "AblatedPersona",
    "QuarantinedArtefact",
    "PairedGap",
    "ProbeStimulus",
    "TemperatureRecommendation",
    "ValidityOutcome",
    "Verdict",
    "assert_not_a_probe",
    "assert_not_ablated",
]
