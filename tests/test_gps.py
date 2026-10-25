import numpy as np
import pandas as pd
from tests.helpers import make_pack, save, sentence, add_gps
from ridgeline.io import load_pack
from ridgeline.gps import parse_nmea, audit_gps, apply_supported_time_map


def test_nmea_validation_position_and_gga_date():
    record = parse_nmea(sentence('GPRMC,235959.00,A,4000.0000,S,10530.0000,W,0,0,311224,,,A'))
    assert record['utc'] == pd.Timestamp('2024-12-31 23:59:59')
    assert record['lat'] == -40 and record['lon'] == -105.5
    assert parse_nmea(sentence('GPRMC,000000.00,V,4000.0,N,10500.0,W,0,0,010125,,,A')) is None
    assert parse_nmea('$GPRMC,wrong*00') is None
    gga = parse_nmea(sentence('GPGGA,000000.00,4000.0,N,10500.0,W,1,8,1.0,1500,M,-17,M,,'))
    assert gga['utc'] is None  # GGA alone cannot establish the date


def test_supported_offset_corrects_copy_only(tmp_path):
    frames = make_pack(tmp_path, days=2, ids=('A',))
    frames['A']['timestamp_utc'] = (pd.to_datetime(frames['A'].timestamp_utc) + pd.Timedelta(hours=2)).dt.strftime('%Y-%m-%d %H:%M')
    save(tmp_path, 'A', frames['A'])
    add_gps(tmp_path, 'A', pd.date_range('2024-05-01', periods=48, freq='h'), np.full(48, 7200))
    pack = load_pack(tmp_path)
    candidates = audit_gps(pack)
    clock = [c for c in candidates if c.issue == 'clock_error']
    assert len(clock) == 1 and clock[0].evidence['offset_seconds'] == 7200
    assert clock[0].evidence['supported']
    corrected = apply_supported_time_map(pack, candidates)
    assert pack.weather['A']['_time'].iloc[0] == pd.Timestamp('2024-05-01 02:00')
    assert corrected.weather['A']['_time'].iloc[0] == pd.Timestamp('2024-05-01 00:00')
    assert corrected.weather['A']['_raw_time'].equals(pack.weather['A']['_raw_time'])


def test_bad_gps_never_corrects_and_metadata_is_distinct(tmp_path):
    make_pack(tmp_path, ids=('A',))
    add_gps(tmp_path, 'A', pd.date_range('2024-05-01', periods=30, freq='h'), lat='4100.0000')
    candidates = audit_gps(load_pack(tmp_path))
    mismatch = [c for c in candidates if c.issue == 'location_mismatch']
    assert len(mismatch) == 1 and mismatch[0].channel == 'metadata'
    path = tmp_path / 'gps/A.nmea'
    path.write_text(path.read_text().replace('*', '*ZZ'))
    assert audit_gps(load_pack(tmp_path)) == []


def test_clock_drift_is_detected_without_guessed_correction(tmp_path):
    make_pack(tmp_path, days=5, ids=('A',))
    times = pd.date_range('2024-05-01', periods=120, freq='h')
    add_gps(tmp_path, 'A', times, np.arange(120) * 5.)
    candidates = audit_gps(load_pack(tmp_path))
    drift = [c for c in candidates if c.subtype == 'drift']
    assert len(drift) == 1 and drift[0].evidence['supported']
    assert not drift[0].evidence.get('correctable', False)


def test_reset_with_second_jitter_creates_no_false_gap_or_duplicates(tmp_path):
    from ridgeline.checks import check_basic
    frames=make_pack(tmp_path,days=3,ids=('A',))
    f=frames['A'];time=pd.to_datetime(f.timestamp_utc)
    shifted=time.where(f.index<144,time-pd.Timedelta(hours=6))
    f['timestamp_utc']=shifted.dt.strftime('%Y-%m-%d %H:%M');save(tmp_path,'A',f)
    utc=pd.date_range('2024-05-01',periods=72,freq='h')
    add_gps(tmp_path,'A',utc,np.where(np.arange(72)<24,1,-21599))
    pack=load_pack(tmp_path);candidates=audit_gps(pack);analysis=apply_supported_time_map(pack,candidates)
    assert analysis.weather['A'].loc[144,'_time']==pd.Timestamp('2024-05-02 00:00')
    basic=check_basic(analysis)
    assert not any(c.subtype=='records' for c in basic)
    assert not any(c.issue=='duplicate_data' for c in basic)
    assert analysis.weather['A']['_time'].iloc[-1] is pd.NaT
