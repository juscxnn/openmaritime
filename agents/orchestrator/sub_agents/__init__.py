"""
Sub-agents for OpenMaritime orchestration.

These agents handle specific domains:
- fe_be_devops: Frontend, backend, DevOps
- ml_architect: ML/AI tasks
- uiux: UI/UX design
"""

from agents.orchestrator.sub_agents.fe_be_devops import fe_be_devops_agent
from agents.orchestrator.sub_agents.ml_architect import ml_architect_agent
from agents.orchestrator.sub_agents.uiux import uiux_agent

__all__ = [
    "fe_be_devops_agent",
    "ml_architect_agent",
    "uiux_agent",
]
