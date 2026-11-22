import pytest

from cardwise.benchmark.peers import peer_position, percentile, scorecard
from cardwise.core.errors import ValidationError


def test_percentile_matches_excel() -> None:
    data = [1, 2, 3, 4, 5]
    assert percentile(data, 0.5) == 3
    assert percentile(data, 0.25) == 2
    assert percentile([10, 20], 0.5) == 15
    assert percentile([7], 0.9) == 7
    with pytest.raises(ValidationError, match="q must"):
        percentile(data, 2)


def test_higher_is_better() -> None:
    p = peer_position("active_rate", 0.70, [0.5, 0.55, 0.6, 0.65, 0.8])
    assert p.median == pytest.approx(0.6)
    assert p.percentile_rank == pytest.approx(0.8)
    assert p.quartile == 1
    assert p.gap_to_median == pytest.approx(0.1)
    assert p.gap_to_top_quartile == pytest.approx(0.05)


def test_lower_is_better() -> None:
    p = peer_position("loss_rate", 0.05, [0.02, 0.03, 0.04, 0.05], higher_is_better=False)
    assert p.top_quartile == pytest.approx(0.0275)
    assert p.percentile_rank == pytest.approx(0.125)
    assert p.quartile == 4
    assert p.gap_to_median < 0


def test_scorecard_sorts_worst_first() -> None:
    rows = scorecard(
        {"active_rate": 0.7, "loss_rate": 0.05, "unknown": 1},
        {"active_rate": [0.5, 0.6, 0.65, 0.8], "loss_rate": [0.02, 0.03, 0.04, 0.06]},
        {"loss_rate": False},
    )
    assert [r.metric for r in rows] == ["loss_rate", "active_rate"]
    with pytest.raises(ValidationError, match="share no metrics"):
        scorecard({"a": 1}, {"b": [1]}, {})
