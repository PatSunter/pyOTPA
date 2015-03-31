"""Useful configuration info/parameters about OTP."""

OTP_DATE_FMT = "%Y-%m-%d"
OTP_TIME_FMT = "%H:%M:%S"
OTP_DATE_FMT_WEB_PLANNER = "%m/%d/%Y"
OTP_TIME_FMT_WEB_PLANNER = "%I:%M%p"

OTP_ROUTER_EPSG = 4326

OTP_MODES = ['WALK', 'BUS', 'TRAM', 'SUBWAY']
OTP_WALK_MODE = 'WALK'
OTP_NON_WALK_MODES = filter(lambda x: x != OTP_WALK_MODE, OTP_MODES)

