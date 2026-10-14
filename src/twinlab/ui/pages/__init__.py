"""One module per top-level route. `docs/06_SCREENS.md`."""

from .agent_studio import render_agent_studio
from .driver_survey import render_driver_survey
from .generator import render_generator
from .lab import render_lab
from .main_menu import render_main_menu
from .research_model import render_research_model
from .statistics import render_statistics
from .studio import render_studio
from .survey_take import render_survey_take

__all__ = [
    "render_agent_studio",
    "render_driver_survey",
    "render_generator",
    "render_lab",
    "render_main_menu",
    "render_research_model",
    "render_statistics",
    "render_studio",
    "render_survey_take",
]
