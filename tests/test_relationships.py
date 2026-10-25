import numpy as np
import pandas as pd
import pytest
from tests.helpers import make_pack, save
from ridgeline.io import load_pack
from ridgeline.checks import check_basic
from ridgeline.relationships import check_relationships, solar_elevation


@pytest.mark.parametrize('channel,amount', [('pressure_hpa', 6), ('temp_c', 4), ('rh_pct', 18)])
def test_additive_bias_respects_station_baseline(tmp_path, channel, amount):
    frames = make_pack(tmp_path, days=18)
    frames['A'].loc[10 * 144:, channel] += amount
    save(tmp_path, 'A', frames['A'])
    pack = load_pack(tmp_path)
    candidates = check_relationships(pack, check_basic(pack))
    bias = [c for c in candidates if c.station_id == 'A' and c.channel == channel and c.subtype == 'additive' and c.evidence['supported']]
    assert bias and bias[0].start <= pd.Timestamp('2024-05-11 06:00')
    assert not any(c.station_id != 'A' and c.evidence['supported'] for c in candidates)


def test_normal_elevation_front_and_local_rain_do_not_make_faults(tmp_path):
    frames = make_pack(tmp_path, days=18)
    for station, f in frames.items():
        f.loc[10 * 144:, 'pressure_hpa'] += 10
        f.loc[12 * 144:13 * 144, 'temp_c'] += 6
        if station == 'A':
            f.loc[11 * 144:11 * 144 + 6, 'rain_mm'] = .2
        save(tmp_path, station, f)
    pack = load_pack(tmp_path)
    candidates = check_relationships(pack, check_basic(pack))
    assert not any(c.evidence['supported'] and c.issue != 'corroborated_weather_event' for c in candidates)


def test_wind_scale_and_gradual_drift(tmp_path):
    frames = make_pack(tmp_path, days=25)
    n = 10 * 144
    frames['A'].loc[n:, 'wind_kmh'] *= .5
    frames['A'].loc[n:, 'temp_c'] += np.linspace(0, 5, len(frames['A']) - n)
    save(tmp_path, 'A', frames['A'])
    pack = load_pack(tmp_path)
    candidates = check_relationships(pack, check_basic(pack))
    assert any(c.station_id == 'A' and c.subtype == 'multiplicative' and c.evidence['supported'] for c in candidates)
    drift = [c for c in candidates if c.station_id == 'A' and c.subtype == 'gradual' and c.evidence['supported']]
    assert drift and abs(drift[0].start - pd.Timestamp('2024-05-11')) <= pd.Timedelta(days=1)


def test_conditional_bias_only_flags_affected_daylight(tmp_path):
    frames = make_pack(tmp_path, days=25)
    f = frames['A']
    f['wind_kmh'] = 3 + .1*np.sin(np.arange(len(f))/20)
    affected = (f.index >= 10 * 144) & f.ghi_wm2.ge(400)
    f.loc[affected, 'temp_c'] += 4
    save(tmp_path, 'A', f)
    pack = load_pack(tmp_path)
    candidates = check_relationships(pack, check_basic(pack))
    conditional = [c for c in candidates if c.station_id == 'A' and c.subtype == 'conditional' and c.evidence['supported']]
    assert conditional
    for c in conditional:
        rows = pack.weather['A'].loc[pack.weather['A']._logger_time.between(c.start, c.end)]
        assert rows.ghi_wm2.ge(400).all()


def test_repeated_rain_failure_needs_previous_response_and_no_freezing(tmp_path):
    frames = make_pack(tmp_path, days=25)
    for station, f in frames.items():
        f['temp_c'] = 12 + np.sin(np.arange(len(f))/200)
        for day in (2, 5, 11, 14, 17, 20):
            f.loc[day * 144:day * 144 + 11, 'rain_mm'] = .2 if station != 'A' or day < 10 else 0
        save(tmp_path, station, f)
    pack = load_pack(tmp_path)
    candidates = check_relationships(pack, check_basic(pack))
    rain = [c for c in candidates if c.issue == 'rainfall_underresponse' and c.evidence['supported']]
    assert len(rain) == 4 and all(c.station_id == 'A' for c in rain)


def test_insufficient_references_disclosed_and_no_auto_fault(tmp_path):
    make_pack(tmp_path, days=3, ids=('single',))
    pack = load_pack(tmp_path)
    assert check_relationships(pack, check_basic(pack)) == []
    assert any(d.get('check') == 'relationships' for d in pack.diagnostics)


def test_solar_context_independent_equatorial_equinox_sanity():
    # Broad geometric check, unrelated to the assignment's required hand calculation.
    values = solar_elevation(pd.DatetimeIndex(['2024-09-22 12:00', '2024-09-22 00:00']), 0, 0)
    assert values[0] > 85 and values[1] < -85


def test_irradiance_in_astronomical_night_needs_review(tmp_path):
    frames=make_pack(tmp_path,days=3,ids=('A',))
    frames['A']['ghi_wm2']=500
    save(tmp_path,'A',frames['A'])
    pack=load_pack(tmp_path)
    candidates=check_relationships(pack,check_basic(pack))
    assert any(c.channel=='ghi_wm2' and c.subtype=='irradiance_timing' and not c.evidence['supported'] for c in candidates)


def test_confirmed_step_survives_short_residual_threshold_crossings(tmp_path):
    frames=make_pack(tmp_path,days=25)
    onset=10*144
    frames['A'].loc[onset:,'pressure_hpa']+=6
    # Weather-dependent residual variation briefly weakens the pointwise signal,
    # but the two reference relationships show no reversal of the board offset.
    frames['A'].loc[15*144:16*144,'pressure_hpa']-=3.5
    save(tmp_path,'A',frames['A'])
    pack=load_pack(tmp_path);c=check_relationships(pack,check_basic(pack))
    bias=[p for p in c if p.station_id=='A' and p.channel=='pressure_hpa' and p.subtype=='additive' and p.evidence['supported']]
    assert len(bias)==1
    assert bias[0].end==pack.weather['A']._logger_time.max()
    assert len(bias[0].row_refs)==len(frames['A'])-onset


def test_unavailable_conditional_and_rain_checks_are_disclosed(tmp_path):
    frames=make_pack(tmp_path,days=18)
    for station,f in frames.items():f['wind_kmh']=20;save(tmp_path,station,f)
    pack=load_pack(tmp_path);check_relationships(pack,check_basic(pack))
    assert any(d.get('station_id')=='A' and d.get('check')=='conditional_bias' for d in pack.diagnostics)
    assert any(d.get('station_id')=='A' and d.get('check')=='rainfall_underresponse' for d in pack.diagnostics)
