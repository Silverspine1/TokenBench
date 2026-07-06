"""Deterministic, approximate token estimator.

This is NOT real tokenizer accounting. It is a coarse char-based estimate used
only for calibration telemetry. Every field it produces is explicitly an
estimate. A canonical tokenizer can replace or supplement it later.
"""

from __future__ import annotations

import math

# Identifier recorded in telemetry so a later run can tell which estimator
# produced a number. Bump the suffix when the formula changes.
ESTIMATOR_NAME = "chars_div_4_v1"


def estimate_tokens(char_count: int) -> int:
    """Estimate token count as ``ceil(char_count / 4)``.

    Negative or zero counts estimate to 0. Byte counts may be passed in place of
    character counts for ASCII-dominant text (logs); the result is still only an
    estimate.
    """
    if char_count <= 0:
        return 0
    return math.ceil(char_count / 4)
