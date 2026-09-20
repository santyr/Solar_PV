from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from earthship_energy.power_intervals import PowerInterval, account_common_power

START = datetime(2026,9,20,tzinfo=timezone.utc)


def interval(left, right, watts):
    return PowerInterval(START+timedelta(hours=left),START+timedelta(hours=right),watts)


def test_different_coverage_does_not_distort_efficiency():
    a, b = account_common_power([interval(0,2,1000)], [interval(1,2,900)],
                                window_start=START,window_end=START+timedelta(hours=4))
    assert a.positive_kwh == 1
    assert b.positive_kwh == .9
    assert a.covered_seconds == b.covered_seconds == 3600
    assert a.coverage == b.coverage == .25


def test_gaps_and_multiple_boundaries_are_preserved():
    a, b = account_common_power([interval(0,1,1000),interval(2,4,2000)],
                               [interval(.5,2.5,900),interval(3,5,1800)],
                               window_start=START,window_end=START+timedelta(hours=4))
    assert a.positive_kwh == 3.5
    assert b.positive_kwh == pytest.approx(2.7)
    assert a.covered_seconds == b.covered_seconds == 7200


@pytest.mark.parametrize('left,right', [([],[]),([interval(0,1,1000)],[interval(1,2,900)])])
def test_no_overlap_is_no_coverage(left,right):
    a,b=account_common_power(left,right,window_start=START,window_end=START+timedelta(hours=4))
    assert a.coverage == b.coverage == 0
    assert a.positive_kwh == b.positive_kwh == 0


def test_invalid_input_is_rejected_even_with_empty_other_stream():
    with pytest.raises(ValueError,match='nonoverlapping'):
        account_common_power([interval(0,2,1),interval(1,2,1)],[],
                             window_start=START,window_end=START+timedelta(hours=4))


@pytest.mark.parametrize('month,day,hours',[(3,8,23),(11,1,25)])
def test_dst_uses_elapsed_common_support(month,day,hours):
    start=datetime(2026,month,day,tzinfo=ZoneInfo('America/Denver'))
    end=start+timedelta(days=1)
    a,b=account_common_power([PowerInterval(start,end,1000)],[PowerInterval(start,end,900)],
                             window_start=start,window_end=end)
    assert a.positive_kwh == hours
    assert b.positive_kwh == pytest.approx(hours*.9)
    assert a.coverage == b.coverage == 1
