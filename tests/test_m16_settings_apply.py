"""M16 — a Settings save actually changes behaviour. `HANDOFF_M15_LIVE_PATH.md` §5.2.

The read path was built in M15 and **never observed changing anything**. The failure it was built
to fix is the quiet one: before it, the Settings tab wrote a new `app_config` version and nothing
read it back, so a researcher who changed a quality threshold saw a success message and changed
nothing — the gate went on running the YAML seed.

These tests follow one value from the save to the thing it is supposed to move:

    save_settings -> app_config -> refresh_twin_config -> load_twin_config -> the budget card

and the same for `app_config['rules'].weights` reaching the computed index. No live LLM, no live
DB; `_override` is process state, so every test restores it.
"""

from __future__ import annotations

import inspect

import pytest

from twinlab.orchestrator.budget import quality_budget
from twinlab.services.config import (
    load_twin_config,
    refresh_twin_config,
    seed_twin_config,
    twin_config_version,
)
from twinlab.services.lab import save_settings


@pytest.fixture(autouse=True)
def _restore_override():
    """`_override` is process-wide module state, so it must not leak between tests."""
    import twinlab.services.config as cfg

    before, before_version = dict(cfg._override), cfg._override_version
    yield
    cfg._override, cfg._override_version = before, before_version


# ------------------------------------------------------------------ the quality gate's repeats


async def test_the_seed_is_what_runs_when_nothing_is_stored(backend):
    """The defined fallback. `docs/09` §4 makes the YAML the seed, `app_config` the live values."""
    await refresh_twin_config(backend)

    assert load_twin_config().quality_runs_per_twin == seed_twin_config().quality_runs_per_twin
    assert twin_config_version() == 1, "nothing stored is version 1, not None"


async def test_saving_quality_runs_per_twin_changes_the_budget_card(backend):
    """§5.2's own test, as a test. 3 calls per twin at 3 repeats, 1 at 1.

    This is the number on the confirm card a researcher presses OK on, so if the save does not
    reach it they authorise one budget and spend another. The per-twin cost fell from 18 to 3 in
    M19 WP-3 (one call per repeat, all six Part-17 versions in it); what this test is about is
    that **the saved value reaches the card**, which is unchanged.
    """
    await refresh_twin_config(backend)
    seeded = load_twin_config().quality_runs_per_twin
    assert seeded == 3, "the seed is 3; this test's arithmetic below assumes it"
    # Three H3 repeats plus the two control answers (RESEARCHER 2026-10-05).
    assert quality_budget(twins=1, repeats=seeded).calls == 3 + 2

    version = await save_settings("twin", {"quality_runs_per_twin": 1}, backend=backend)
    live = await refresh_twin_config(backend)

    assert live.quality_runs_per_twin == 1, "the save did not reach the live config"
    assert quality_budget(twins=1, repeats=live.quality_runs_per_twin).calls == 1 + 2
    assert twin_config_version() == version, (
        "the version the config came from must be recordable on the evidence row"
    )


async def test_a_save_only_changes_the_key_it_names(backend):
    """`save_settings` merges over the stored row; a partial dict must not delete a threshold.

    `app_config['twin']` is a whole configuration — every quality-gate threshold `seed_db` wrote —
    and an upsert on `key` replaces the entire value object.
    """
    await save_settings("twin", {"mae_max": 0.5, "pct_within_1_min": 0.9}, backend=backend)
    await save_settings("twin", {"quality_runs_per_twin": 2}, backend=backend)
    live = await refresh_twin_config(backend)

    assert live.quality_runs_per_twin == 2
    assert live.mae_max == 0.5, "the second save deleted a threshold the first one set"
    assert live.pct_within_1_min == 0.9


async def test_the_settings_screen_cannot_write_show_baseline(backend):
    """`docs/03` §321 — a researcher-set default held in `app_config`, **not a UI control**.

    The Settings tab builds a full `TwinConfig` to validate what the researcher typed, and that
    model necessarily carries a `show_baseline`. It must not reach the database: before this, the
    value came from a `load_twin_config()` evaluated when the Blocks were **built**, which is
    before anything has read `app_config`, so it was the YAML seed. Any Save therefore wrote the
    seed's `show_baseline` over the stored one — which is how `false` could sit in the YAML while
    `app_config` went on running `true`.

    The guarantee is structural rather than careful: `save_settings` merges, so a key the screen
    never sends is a key it can never clobber. This test pins the key list the screen sends.
    """
    from twinlab.ui.pages import lab as lab_page

    source = inspect.getsource(lab_page._settings_tab)
    assert '"show_baseline"' not in source.split("EDITABLE = (")[1].split(")")[0], (
        "the Settings screen listed show_baseline as editable; it is set in app_config only"
    )

    # The database holds False; a save of an unrelated field must leave it there.
    await backend.upsert(
        "app_config",
        [{"key": "twin", "value": {"show_baseline": False}, "version": 3}],
        on_conflict="key",
    )
    assert (await refresh_twin_config(backend)).show_baseline is False

    await save_settings("twin", {"temperature": 0.7}, backend=backend)
    live = await refresh_twin_config(backend)

    assert live.temperature == 0.7, "the save did not reach the live config"
    assert live.show_baseline is False, (
        "a Settings save flipped show_baseline; the twin would see its own numbers again and the "
        "00000 control would go back to echoing them (docs/DECISIONS.md 2026-10-07)"
    )


async def test_the_settings_screen_repaints_every_control_from_app_config(backend):
    """The screen must show what is in force, not the seed it was built with.

    A settings screen displaying `config/twin.default.yaml` while the database holds something
    else is the same lie as a read-only control that looks editable, and it is what sent a
    researcher to hand-edit the YAML — unversioned, unaudited, and outside the `config_version`
    that `twin_quality_runs` records.
    """
    from twinlab.ui.pages import lab as lab_page

    source = inspect.getsource(lab_page._settings_tab)
    assert "load_once(" in source and "_refresh" in source, (
        "the Settings tab paints its controls once at build time and never re-reads app_config"
    )
    # Every editable control, plus the read-only show_baseline display, is repainted by it.
    wired = source[source.index("load_once("):]
    for control in (
        "temperature", "wording", "quality_runs", "mae_max", "pct_min", "panel_size",
        "baseline_shown",
    ):
        assert control in wired, f"{control} is not repainted from the live config"


async def test_a_stored_config_that_cannot_run_raises_rather_than_falling_back(backend):
    """Running the seed as though it were the researcher's choice is the failure to avoid.

    `quality_runs_per_twin = 0` is rejected by `TwinConfig` itself (it counts the first run), so a
    row carrying it must fail loudly at the read, not silently revert to 3.
    """
    await backend.upsert(
        "app_config",
        [{"key": "twin", "value": {"quality_runs_per_twin": 0}, "version": 7}],
        on_conflict="key",
    )
    with pytest.raises(ValueError, match="at least 1"):
        await refresh_twin_config(backend)


async def test_an_unknown_stored_key_is_dropped_not_fatal(backend):
    """`seed_db` writes `max_concurrency` into this row and `TwinConfig` forbids extras."""
    await backend.upsert(
        "app_config",
        [{
            "key": "twin",
            "value": {"quality_runs_per_twin": 2, "max_concurrency": 1},
            "version": 3,
        }],
        on_conflict="key",
    )
    live = await refresh_twin_config(backend)
    assert live.quality_runs_per_twin == 2


async def test_an_unreachable_database_falls_back_instead_of_blocking_a_tick(backend):
    """A config read must never stop the UI, and the seed is a defined state."""

    class _Broken:
        name = "broken"

        async def select(self, *_a, **_k):
            raise RuntimeError("no database")

    live = await refresh_twin_config(_Broken())
    assert live.quality_runs_per_twin == seed_twin_config().quality_runs_per_twin


# ------------------------------------------------------------------ the index weights


async def test_the_default_index_is_unweighted(backend):
    """`docs/07` §4.1 — **the unweighted index is what the paper reports.**"""
    from twinlab.services.twin_runtime import _index_weights

    assert await _index_weights(backend) == {}


async def test_saved_rule_weights_reach_the_index(backend):
    """§5.2's second unverified claim: Agent Studio's weights reaching a computed index."""
    from twinlab.services.twin_runtime import _index_weights

    await save_settings("rules", {"weights": {"FAIR": 2.0, "TRANS": 0.5}}, backend=backend)

    assert await _index_weights(backend) == {"FAIR": 2.0, "TRANS": 0.5}


async def test_a_malformed_weight_block_falls_back_to_unweighted(backend):
    """Not to a partial weighting: a half-read weight set is a different index, silently."""
    from twinlab.services.twin_runtime import _index_weights

    await save_settings("rules", {"weights": "all of them"}, backend=backend)

    assert await _index_weights(backend) == {}


async def test_weights_actually_move_the_computed_index(backend):
    """The whole point of the chain: a saved weight changes a number, not just a dict.

    Proven on `compute_shifts` rather than on the stored dict, because a weight that is read and
    then not passed to the statistics is exactly the M15 defect one level down.
    """
    from twinlab.analysis.metrics import compute_shifts
    from twinlab.ingest.reference_store import reference
    from twinlab.services.twin_runtime import _index_weights

    ref = reference()
    battery = ref.battery_item_ids
    baseline = {"T1": dict.fromkeys(battery, 3)}
    variant = {"T1": dict.fromkeys(battery, 5)}

    unweighted = compute_shifts(
        baseline_vectors=baseline, variant_vectors=variant,
        version_code="01000", weights=None, ref=ref,
    )

    # ASYMMETRIC on purpose. `compute_index` is a normalised weighted mean, so weighting every
    # metric by 3.0 gives back exactly the unweighted index — a test built on uniform weights
    # would pass against an implementation that read the weights and then ignored them.
    metrics = sorted(unweighted.shifts)
    assert len(metrics) >= 2, "the index needs at least two metrics for weighting to mean anything"
    skewed = {metrics[0]: 9.0} | {m: 1.0 for m in metrics[1:]}
    await save_settings("rules", {"weights": skewed}, backend=backend)

    weights = await _index_weights(backend)
    assert weights == skewed, "the saved weights never reached the read path"

    weighted = compute_shifts(
        baseline_vectors=baseline, variant_vectors=variant,
        version_code="01000", weights=weights or None, ref=ref,
    )

    assert unweighted.index_value is not None and weighted.index_value is not None
    assert weighted.index_value != unweighted.index_value, (
        f"the weights were read but did not move the index: both {weighted.index_value}. "
        "A weight that reaches the config and not the statistics is the M15 defect one level down."
    )
    # And the unweighted default is untouched by the save, because it is what the paper reports.
    again = compute_shifts(
        baseline_vectors=baseline, variant_vectors=variant,
        version_code="01000", weights=None, ref=ref,
    )
    assert again.index_value == unweighted.index_value
