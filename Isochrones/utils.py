
import os.path
from datetime import datetime, timedelta
import json
import time

def rasterName(loc_name, time, base_path=None, suffix=None):
    fname =  str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_')
    if suffix and suffix != "":
        fname += '-' + suffix
    fname += '.tiff'
    if base_path is not None:
        path = os.path.join(os.path.expanduser(base_path), fname)
    else:
        path = fname
    return path

def vectorName(loc_name, time, iso, vec_type, base_path=None, suffix=None):
    fname = str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_') \
        + '-' + str(iso) +"min" \
        + '-' + str.lower(vec_type)
    if suffix and suffix != "":
        fname += '-' + suffix
    fname += '.geojson'
    if base_path is not None:
        path = os.path.join(os.path.expanduser(base_path), fname)
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

DATE_FORMAT_STR = "%Y-%m-%d"
TIME_FORMAT_STR = "%H:%M:%S"

def get_date_time_string_set(base_date, base_time, mins_diffs):
    dtime_orig = datetime.strptime(base_date+base_time, 
        DATE_FORMAT_STR+TIME_FORMAT_STR)
    date_time_set = []
    for mins_diff in mins_diffs:
        time_diff = timedelta(minutes=mins_diff)
        mt = dtime_orig + time_diff
        date_mod = mt.strftime(DATE_FORMAT_STR)
        time_mod = mt.strftime(TIME_FORMAT_STR)
        date_time_set.append((date_mod, time_mod))
    return date_time_set
 
def get_raster_filenames(loc_name, date_time_str_set, base_path, suffix):
    fname_set = []
    for date_time_tuple in date_time_str_set:
        date_mod, time_mod = date_time_tuple        
        fname_set.append(rasterName(loc_name, time_mod, base_path, suffix))
    return fname_set

def gen_multi_graph_iso_spec(base_path, server_url, graph_infos,
        iso_set_specifications):
    iso_spec_list = []
    if graph_infos is None or len(graph_infos) is 0:
        iso_spec_list.append((server_url, None, base_path, None,
            iso_set_specifications))
    else:    
        for otp_router_id, graph_subdir, save_suffix in graph_infos:
            out_path = os.path.join(base_path, graph_subdir) 
            iso_spec_list.append((server_url, otp_router_id, out_path,
                save_suffix, iso_set_specifications))
    return iso_spec_list        

def save_metadata(multi_graph_iso_set):
    print "Saving metadata for each run in JSON format..."
    fnames = []
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        now = datetime.now()
        d_t_str = now.strftime("%Y-%m-%d_%Hh_%Mm_%Ss")
        meta_fname = "-".join(["isos-metadata", d_t_str]) + ".json"
        meta_fname = os.path.join(os.path.abspath(save_path),
            meta_fname)
        fnames.append(meta_fname)
        print "...saving metadata of an isochrone set into %s" % \
            (meta_fname)
        meta_dict = {}
        meta_dict['run_time'] = now.isoformat()
        meta_dict['server_url'] = server_url
        meta_dict['otp_router_id'] = otp_router_id
        meta_dict['save_suffix'] = save_suffix
        meta_dict['iso_set_specification'] = isos_spec
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        meta_file = open(meta_fname, "w")
        json.dump(meta_dict, meta_file, indent=2)
        meta_file.close()
        # This is to ensure we don't overwrite files.
        time.sleep(1.01)
    print "Done."        
    return fnames
        
def load_iso_set_from_files(fnames):
    iso_spec_list = []
    for fname in fnames:
        meta_file = open(fname, "r")
        meta_dict = json.load(meta_file)
        iso_spec_list.append(
            (meta_dict['server_url'],
            meta_dict['otp_router_id'], 
            os.path.dirname(fname),
            meta_dict['save_suffix'],
            meta_dict['iso_set_specification']
            ))
    return iso_spec_list    

