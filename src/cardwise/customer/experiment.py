"""Campaign experiments: test vs control lift, significance and sample size.

Uses the two-proportion z-test (normal approximation), which is what most
card activation and spend-stimulation campaigns are read with.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative, require_positive

_N = NormalDist()


@dataclass(frozen=True)
class ExperimentResult(Result):
    test_rate: float
    control_rate: float
    absolute_lift: float
    relative_lift: float | None
    z: float
    p_value: float  # two-sided
    significant: bool
    ci_low: float  # confidence interval for the absolute lift
    ci_high: float
    incremental_responders: float  # absolute lift x test group size
    incremental_value: float  # incremental responders x value per responder


def two_proportion_test(
    test_size: float,
    test_conversions: float,
    control_size: float,
    control_conversions: float,
    confidence: float = 0.95,
    value_per_conversion: float = 0.0,
) -> ExperimentResult:
    nt = require_positive("test_size", test_size)
    nc = require_positive("control_size", control_size)
    xt = require_non_negative("test_conversions", test_conversions)
    xc = require_non_negative("control_conversions", control_conversions)
    if xt > nt or xc > nc:
        raise ValidationError("conversions cannot exceed group size")
    conf = require_fraction("confidence", confidence)
    if not 0 < conf < 1:
        raise ValidationError("confidence must be between 0 and 1 (exclusive)")
    value = require_non_negative("value_per_conversion", value_per_conversion)
    pt, pc = xt / nt, xc / nc
    pooled = (xt + xc) / (nt + nc)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / nt + 1 / nc))
    lift = pt - pc
    z = lift / se_pooled if se_pooled > 0 else 0.0
    p = 2 * (1 - _N.cdf(abs(z)))
    se = math.sqrt(pt * (1 - pt) / nt + pc * (1 - pc) / nc)
    zcrit = _N.inv_cdf(0.5 + conf / 2)
    return ExperimentResult(
        test_rate=pt,
        control_rate=pc,
        absolute_lift=lift,
        relative_lift=lift / pc if pc else None,
        z=z,
        p_value=p,
        significant=p < 1 - conf,
        ci_low=lift - zcrit * se,
        ci_high=lift + zcrit * se,
        incremental_responders=lift * nt,
        incremental_value=lift * nt * value,
    )


def sample_size(
    baseline_rate: float, minimum_lift: float, confidence: float = 0.95, power: float = 0.8
) -> int:
    """Customers needed per group to detect an absolute lift with the given power."""
    p1 = require_fraction("baseline_rate", baseline_rate)
    delta = require_positive("minimum_lift", minimum_lift)
    p2 = p1 + delta
    if p2 > 1:
        raise ValidationError("baseline_rate + minimum_lift must not exceed 1")
    for name, v in (("confidence", confidence), ("power", power)):
        if not 0 < v < 1:
            raise ValidationError(f"{name} must be between 0 and 1 (exclusive)")
    za = _N.inv_cdf(0.5 + confidence / 2)
    zb = _N.inv_cdf(power)
    p_bar = (p1 + p2) / 2
    n = (za * math.sqrt(2 * p_bar * (1 - p_bar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(n / delta**2)
