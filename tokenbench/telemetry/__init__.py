"""Raw telemetry capture for TokenBench runs (V0.4.2).

Telemetry is raw evidence: the measurable facts of a run (timing, log volume,
file/line churn, prompt and patch size, estimated tokens, provider usage when
available). It is deliberately separate from scoring, which is interpretation.
Do not derive a final token-efficiency formula from these fields yet.
"""

from .collector import build_telemetry, write_telemetry
from .schema import Telemetry
from .token_estimator import ESTIMATOR_NAME, estimate_tokens

__all__ = [
    "build_telemetry",
    "write_telemetry",
    "Telemetry",
    "ESTIMATOR_NAME",
    "estimate_tokens",
]
