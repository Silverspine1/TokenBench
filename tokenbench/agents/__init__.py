"""Agent adapter configs. Provider-agnostic: a CLI agent is just a command
template plus a few execution flags. The scorer never sees any of this."""

from .loader import AgentConfigError, load_agent, load_agent_config
from .schema import AgentConfig

__all__ = ["AgentConfig", "AgentConfigError", "load_agent", "load_agent_config"]
