
import os.path
from datetime import datetime, timedelta

def rasterName(loc_name, time, rel_dir=None, suffix=None):
    fname =  str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_')
    if suffix and suffix != "":
        fname += '-' + suffix
    fname += '.tiff'
    if rel_dir is not None:
        path = os.path.join(".", rel_dir, fname)
    else:
        path = fname
    return path

def vectorName(loc_name, time, iso, vec_type, rel_dir=None):
   fname = str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_') \
        + '-' + str(iso) +"min" \
        + '-' + str.lower(vec_type) \
        + '.geojson'
   if rel_dir is not None:
       path = os.path.join(".", rel_dir, fname)
   else:
       path = fname
   return path

def get_nearby_min_diffs(nearby_minutes, num_each_side):
    inc_range = range(1, num_each_side+1)
    mins_before = [-nearby_minutes * ii/float(num_each_side) \
        for ii in reversed(inc_range)]
    mins_after = [nearby_minutes * ii/float(num_each_side) \
        for ii in inc_range]
    mins_diffs = mins_before + [0] + mins_after
    return mins_diffs

def get_date_time_string_set(base_date, base_time, mins_diffs):
    y_m_d = [int(ii) for ii in base_date.split('-')]
    h_m_s = [int(ii) for ii in base_time.split(':')]
    dtime_orig = datetime(year=y_m_d[0], month=y_m_d[1],
        day=y_m_d[2], hour=h_m_s[0], minute=h_m_s[1],
        second=h_m_s[2])
    date_time_set = []
    for mins_diff in mins_diffs:
        time_diff = timedelta(minutes=mins_diff)
        mt = dtime_orig + time_diff
        date_mod = "%d-%02d-%02d" % (mt.year, mt.month, mt.day)
        time_mod = "%02d:%02d:%02d" % (mt.hour, mt.minute, mt.second)
        date_time_set.append((date_mod, time_mod))
    return date_time_set    
 
def get_raster_filenames(loc_name, date_time_str_set,
        output_subdir, suffix):
    fname_set = []
    for date_time_tuple in date_time_str_set:
        date_mod, time_mod = date_time_tuple        
        fname_set.append(rasterName(loc_name, time_mod, output_subdir,
            suffix))
    return fname_set
