"""The Main menu's map and the Agents tab's five cards. `docs/06` §1.1, §1.2 and §3.1.

The seven workflow groups and their card order are **mandatory content** (`docs/06`, preamble):
styling may degrade, this may not. They live here rather than in `ui/` so the ordering is testable
without building a Gradio app, and so `ui/` stays a formatter (`docs/05` §8.4 rule 1).

**Google Sheet is removed** (`docs/06` §0). It was the prototype's database interface and Supabase
replaces it: there is no route, no card, no link and no user-facing text naming a sheet. A test
asserts that over this module's rendered text.
"""

from __future__ import annotations

from twinlab.db.client import DbBackend, get_backend
from twinlab.models.view import AgentCardView, CardGroup, LinkCard

#: Twin Lab's eight sub-tabs, in the mandatory order of `docs/06` §0.
LAB_TABS: tuple[str, ...] = (
    "Agents",
    "Dial board",
    "Twins",
    "Validation",
    "Validity tests",
    "Fieldwork",
    "Results",
    "Settings",
)

#: `docs/06` §1.1. Seven groups, each a `section_card` of link cards, in this order.
WORKFLOW_GROUPS: tuple[CardGroup, ...] = (
    CardGroup(
        title="Collect answers",
        cards=[
            LinkCard(
                title="Send the survey to a driver",
                description="The 17-part instrument, in three languages.",
                route="/survey",
            ),
            LinkCard(
                title="Make synthetic surveys for testing",
                description="Fake respondents for exercising the machinery.",
                route="/generator",
            ),
            LinkCard(
                title="Watch fieldwork",
                description="How real collection is going, by city and service.",
                route="/lab",
                tab="Fieldwork",
            ),
        ],
    ),
    CardGroup(
        title="Build and test the twins",
        cards=[
            LinkCard(
                title="Import twins from the survey",
                description="Eligible, consented respondents become twins.",
                route="/lab",
                tab="Settings",
            ),
            LinkCard(
                title="Run the twin quality test",
                description="The H3 holdout gate: who is kept and who is dropped.",
                route="/lab",
                tab="Agents",
            ),
            LinkCard(
                title="Look inside one twin",
                description="Persona, quality and answers beside its own driver's.",
                route="/lab",
                tab="Twins",
            ),
            LinkCard(
                title="Interview one twin in your own words",
                description="A sandbox conversation; never part of an analysis.",
                route="/studio",
            ),
        ],
    ),
    CardGroup(
        title="Check the twins can be trusted",
        cards=[
            LinkCard(
                title="Validation against each driver",
                description="Parts 16 and 17, twin against its own driver.",
                route="/lab",
                tab="Validation",
            ),
            LinkCard(
                title="The eight validity tests",
                description="Wrong person, placebo, simple guesses and five more.",
                route="/lab",
                tab="Validity tests",
            ),
        ],
    ),
    CardGroup(
        title="Explore the 243 versions",
        cards=[
            LinkCard(
                title="Turn the dials and ask the twins",
                description="Five levers, three steps each, one version code.",
                route="/lab",
                tab="Dial board",
            ),
            LinkCard(
                title="Let the agents choose what to test",
                description="Six versions picked by the run manager.",
                route="/lab",
                tab="Agents",
            ),
            LinkCard(
                title="Read the results",
                description="The grid, the shifts, the index and the interactions.",
                route="/lab",
                tab="Results",
            ),
        ],
    ),
    CardGroup(
        title="Analyse and export",
        cards=[
            LinkCard(
                title="Reliability and correlations",
                description="Alpha, rho_A, AVE and the correlation matrix.",
                route="/statistics",
            ),
            LinkCard(
                title="The PLS-SEM path model",
                description="Paths, R squared and the bootstrap.",
                route="/statistics",
            ),
            LinkCard(
                title="Export for SmartPLS, R or Python",
                description="A scale-annotated matrix of the human rows.",
                route="/statistics",
                tab="Export",
            ),
        ],
    ),
    CardGroup(
        title="Write the paper",
        cards=[
            LinkCard(
                title="Research model, constructs and hypotheses",
                description="The nine constructs and what each one measures.",
                route="/research",
            ),
            LinkCard(
                title="Write it all to a document",
                description="Model, methods and results as one export.",
                route="/research",
            ),
        ],
    ),
    CardGroup(
        title="Set up and manage",
        cards=[
            LinkCard(
                title="Model, speed and sample settings",
                description="Provider, temperature, panel size and pacing.",
                route="/lab",
                tab="Settings",
            ),
            LinkCard(
                title="Agent instructions and the freeze",
                description="The five agents' prompts and their version history.",
                route="/agents",
            ),
        ],
    ),
)

#: `docs/06` §1.2. One card per route **except** Main menu — seven, each with an audience line.
DIRECT_CARDS: tuple[LinkCard, ...] = (
    LinkCard(
        title="Driver survey",
        description="For drivers and field staff: the instrument and its intake status.",
        route="/survey",
    ),
    LinkCard(
        title="Twin Lab",
        description="For the researcher: the whole experiment, in eight tabs.",
        route="/lab",
    ),
    LinkCard(
        title="Generator",
        description="For testing: synthetic respondents that exercise the pipeline.",
        route="/generator",
    ),
    LinkCard(
        title="Twin Studio",
        description="For inspection: one twin, one question, in your own words.",
        route="/studio",
    ),
    LinkCard(
        title="Agent Studio",
        description="For the operator: agent instructions, models and the freeze.",
        route="/agents",
    ),
    LinkCard(
        title="Statistics",
        description="For analysis: reliability, correlations, PLS-SEM and export.",
        route="/statistics",
    ),
    LinkCard(
        title="Research model",
        description="For writing: constructs, hypotheses and the model diagram.",
        route="/research",
    ),
)

#: `docs/06` §1.4's help accordion, retained from the prototype.
HELP_TOPICS: tuple[tuple[str, str], ...] = (
    (
        "Turning on a live model",
        "Set OLLAMA_API_KEY and switch the twin model off mock in Twin Lab → Settings. The header "
        "badge reads Live: <model name> once a live provider is configured.",
    ),
    (
        "A live run is slow, or the provider refuses calls",
        "The free provider tier permits one concurrent request, so a sweep is serial by design. "
        "If calls are refused, lower the pace in Settings and check the budget before restarting.",
    ),
    (
        "A twin answer was refused",
        "A twin that cannot produce 37 valid integers after one targeted repair fails for that "
        "cell. That is the correct outcome: the answer is not padded, clamped or inferred.",
    ),
    (
        "Something is missing after an update",
        "Reference data is frozen and verified at boot. If the application refuses to start, the "
        "seeded reference digest does not match the files on disk and nothing downstream is "
        "trustworthy until that is resolved.",
    ),
    (
        "Before real fieldwork",
        "Run the quality gate and validation on synthetic twins first. Synthetic validation tests "
        "the machinery, not the twins, so it is a smoke test and never a result.",
    ),
)

#: `docs/06` §3.1's five cards, in the order they are listed there.
AGENT_CARDS: tuple[tuple[str, str, str], ...] = (
    ("manager", "Run Manager", "Owns the session. Routes, schedules and checkpoints."),
    ("design", "Policy Designer", "Renders a decided commitment set into one paragraph."),
    ("twin", "Twin Interviewer", "Answers the battery as one driver."),
    ("checker", "Quality Checker", "Decides whether a paragraph entails a commitment."),
    ("analyst", "Results Analyst", "Writes prose about numbers Python computed."),
)


async def agent_cards(backend: DbBackend | None = None) -> list[AgentCardView]:
    """The five agent cards with their live enabled state and latest operational line.

    The Manager is seeded ``enabled: false`` and nothing calls it yet; the card says so rather
    than showing a green dot for an agent that has never run (`HANDOFF.md` §2.2).
    """
    db = backend or get_backend()
    rows = {r["agent_id"]: r for r in await db.select("agent_configs", None)}
    out: list[AgentCardView] = []
    for agent_id, name, description in AGENT_CARDS:
        row = rows.get(agent_id, {})
        enabled = bool(row.get("enabled", agent_id != "manager"))
        events = await db.select(
            "run_events",
            [("eq", "agent", agent_id)],
            order=("event_id", True),
            limit=1,
        )
        latest = str(events[0].get("label")) if events else "No activity yet."
        state = "pending"
        if events:
            status = str(events[0].get("status"))
            state = (
                "complete"
                if status == "ok"
                else "failed"
                if status == "error"
                else "running"
                if status == "running"
                else "pending"
            )
        out.append(
            AgentCardView(
                agent_id=agent_id,
                name=name,
                description=description,
                state=state,
                latest=latest if enabled else "Not enabled; nothing calls it yet.",
                enabled=enabled,
            )
        )
    return out
