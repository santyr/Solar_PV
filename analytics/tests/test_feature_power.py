from datetime import timedelta
import pytest
from earthship_energy import feature_reader
from earthship_energy.power_intervals import PowerInterval
from test_feature_reader import Connection, START, END

TABLES = {'battery.soc_pct': 'item0001', 'weather.outdoor_temperature_c': 'item0004',
          'weather.irradiance_w_m2': 'item0005'}


def run(connection, **kwargs):
    return feature_reader.fetch_feature_rows(connection, TABLES, START, END,
        cadence_minutes=15, timezone_name='America/Denver', **kwargs)


@pytest.mark.parametrize('intervals,current,lag', [
    ([], None, None),
    ([PowerInterval(START, START + timedelta(seconds=120), 0)], 0, None),
    ([PowerInterval(START - timedelta(hours=1), START, 120)], None, 120),
    ([PowerInterval(START - timedelta(seconds=1), START + timedelta(seconds=1), 50)], 50, None),
])
def test_qualified_gaps_zero_exclusive_end_and_lag(monkeypatch, intervals, current, lag):
    calls = []
    def read(*args, **kwargs):
        calls.append((args, kwargs))
        return {'pv.input_power_w': intervals}
    monkeypatch.setattr(feature_reader, 'read_power_history', read)
    connection = Connection()
    row = run(connection, power_settings=object(), power_table='item0647',
              power_cutover=START - timedelta(days=1))[0]
    assert row['pv_power_w'] == current
    assert row['pv_power_w_lag_1h'] == lag
    assert row['load_power_w'] is row['load_power_w_lag_1h'] is None
    sql = connection.cursor_instance.executed[0]
    assert 'NULL::double precision AS pv_power_w' in sql
    assert 'NULL::double precision AS load_power_w' in sql
    assert calls[0][0][2:] == (START - timedelta(hours=1), END)


def test_partial_configuration_fails_before_query():
    connection = Connection()
    with pytest.raises(ValueError, match='settings, table and cutover'):
        run(connection, power_table='item0647')
    assert connection.cursor_instance.executed is None


def test_reader_failure_never_falls_back(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError('ambiguous evidence')
    monkeypatch.setattr(feature_reader, 'read_power_history', fail)
    connection = Connection()
    with pytest.raises(ValueError, match='ambiguous'):
        run(connection, power_settings=object(), power_table='item0647', power_cutover=START)
    assert connection.cursor_instance.executed is None


def test_overlap_is_not_repaired(monkeypatch):
    monkeypatch.setattr(feature_reader, 'read_power_history', lambda *a, **k: {
        'pv.input_power_w': [PowerInterval(START, END, 1), PowerInterval(START, END, 2)]})
    with pytest.raises(ValueError, match='nonoverlapping'):
        run(Connection(), power_settings=object(), power_table='item0647', power_cutover=START)
