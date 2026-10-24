VERSION = '1.0'
CHANNELS = ('temp_c', 'rh_pct', 'pressure_hpa', 'wind_kmh', 'wind_dir_deg', 'rain_mm', 'ghi_wm2')
FIELDS = ('station_id', 'channel', 'start_utc', 'end_utc', 'issue', 'action', 'note')
FLOORS = {'temp_c': .3, 'pressure_hpa': .5, 'rh_pct': 2.0, 'wind_kmh': .5}
BIAS_FLOORS = {'temp_c': 2., 'pressure_hpa': 3., 'rh_pct': 10.}
