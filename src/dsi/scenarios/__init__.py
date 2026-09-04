"""The three mandatory challenge scenarios (automated & reproducible)."""

from dsi.scenarios.a_evidence_update import (
    ScenarioAResult,
    corrected_version_record,
    run_scenario_a,
)
from dsi.scenarios.b_conflict import ScenarioBResult, run_scenario_b
from dsi.scenarios.c_constrained import ScenarioCResult, run_scenario_c

__all__ = [
    "run_scenario_a", "ScenarioAResult", "corrected_version_record",
    "run_scenario_b", "ScenarioBResult",
    "run_scenario_c", "ScenarioCResult",
]
