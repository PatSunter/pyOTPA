"""Filters on a dict of TripItinerarys :- to produce a list of trip IDs that
match the criteria."""

import csv
from datetime import time, datetime
from osgeo import ogr, osr

from pyOTPA import geom_utils
from pyOTPA import otp_config
from pyOTPA import Trip
from pyOTPA.Trips_Generator import abs_zone_io

# Filters that rely on trip itinerary results
DEFAULT_LONGEST_WALK_LEN_KM = 1.2

def get_trip_ids_with_walk_leg_gr_than_dist_km(trip_results, dist_km):
    trip_ids_match_criteria = []
    for trip_id, trip_result in trip_results.iteritems():
        longest_walk_m = trip_result.get_longest_walk_leg_dist_m()
        if longest_walk_m / 1000.0 > dist_km:
            trip_ids_match_criteria.append(trip_id)
            #print "(trip %s matches since it's longest walk leg "\
            #    "was %fm.)" % (trip_id, longest_walk_m)
    return trip_ids_match_criteria

def get_trip_ids_with_total_time_gr_than(trip_results, trip_req_start_dts,
        comp_td):
    assert len(trip_req_start_dts) >= len(trip_results)
    trip_ids_match_criteria = []
    for trip_id, trip_result in trip_results.iteritems():
        trip_req_start_dt = trip_req_start_dts[trip_id]
        trip_total_time = trip_result.get_total_trip_td(trip_req_start_dt)
        if trip_total_time > comp_td:
            trip_ids_match_criteria.append(trip_id)
            #print "(trip %s matches since it's total time "\
            #    "was %s.)" % (trip_id, trip_total_time)
    return trip_ids_match_criteria

def get_results_in_dep_time_range(trip_results, trip_req_start_dts,
        dep_time_info):
    trip_results_subset = {}
    for trip_id, trip_result in trip_results.iteritems():
        trip_start_dt = trip_req_start_dts[trip_id]
        if trip_start_dt.weekday() in dep_time_info[0] \
                and trip_start_dt.time() >= dep_time_info[1] \
                and trip_start_dt.time() < dep_time_info[2]:
            trip_results_subset[trip_id] = trip_result
    return trip_results_subset

def categorise_trip_ids_by_first_non_walk_mode(trip_itins):
    trips_by_first_mode = {}
    for mode in otp_config.OTP_NON_WALK_MODES:
        trips_by_first_mode[mode] = {}
    for trip_id, trip_itin in trip_itins.iteritems():
        first_non_walk_mode = trip_itin.get_first_non_walk_mode()
        if first_non_walk_mode:
            trips_by_first_mode[first_non_walk_mode][trip_id] = trip_itin
    return trips_by_first_mode            

def categorise_trips_by_agencies_used(trip_itins):
    trips_by_agencies = {}
    for trip_id, trip_itin in trip_itins.iteritems():
        ag_set = trip_itin.get_set_of_agencies_used()
        # Turn this into a tuple of sorted agencies, so it is usable as a
        # dictionary key for classification.
        agencies = tuple(sorted(list(ag_set)))
        if agencies not in trips_by_agencies:
            trips_by_agencies[agencies] = {}
        trips_by_agencies[agencies][trip_id] = trip_itin
    return trips_by_agencies

def categorise_trip_results_by_od_sla(trip_itins, trips_by_id):
    trips_by_od_sla = {}
    for trip_id, trip_itin in trip_itins.iteritems():
        trip = trips_by_id[trip_id]
        o_sla, d_sla = trip[Trip.O_ZONE], trip[Trip.D_ZONE]
        if o_sla not in trips_by_od_sla:
            trips_by_od_sla[o_sla] = {}
        if d_sla not in trips_by_od_sla[o_sla]:
            trips_by_od_sla[o_sla][d_sla] = {}
        trips_by_od_sla[o_sla][d_sla][trip_id] = trip_itin
    return trips_by_od_sla

def get_trip_origin_dest_ccd(trip, ccds_index, tform_trips_srs_to_ccds_srs):
    o_geom = ogr.Geometry(ogr.wkbPoint)
    d_geom = ogr.Geometry(ogr.wkbPoint)
    o_geom.AddPoint(*trip[Trip.ORIGIN])
    d_geom.AddPoint(*trip[Trip.DEST])
    o_geom.Transform(tform_trips_srs_to_ccds_srs)
    d_geom.Transform(tform_trips_srs_to_ccds_srs)
    o_ccd, d_ccd = None, None
    o_shp = geom_utils.get_shp_geom_is_within_using_index(ccds_index, o_geom)
    d_shp = geom_utils.get_shp_geom_is_within_using_index(ccds_index, d_geom)
    if o_shp:
        o_ccd = o_shp.GetField(abs_zone_io.CCD_CODE_FIELD)
    if d_shp:
        d_ccd = d_shp.GetField(abs_zone_io.CCD_CODE_FIELD)

    #o_ccd, d_ccd = None, None
    #for ccd_code, ccd_shp in ccd_code_to_shp_map.iteritems():
    #    ccd_geom = ccd_shp.GetGeometryRef()
    #    if ccd_geom.Contains(o_geom):
    #        o_ccd = ccd_code
    #    if ccd_geom.Contains(d_geom):
    #        d_ccd = ccd_code
    #    if o_ccd and d_ccd:
    #        break
    o_geom.Destroy()
    d_geom.Destroy()
    return o_ccd, d_ccd

def categorise_trip_results_by_od_ccd(trip_itins, trips_by_id, ccds_index,
        ccds_srs, saved_trip_id_ccds_map):
    print "Categorising trip results by Origin CCD and Dest CCD "\
        "(%d trips) ..." % (len(trip_itins))
    trips_by_od_ccd = {}
    cnt = 0
    ccds_spatial_index = ccds_index
    trips_srs = Trip.get_trips_srs()
    tform_trip_srs_to_ccd_srs = osr.CoordinateTransformation(
        trips_srs, ccds_srs)
    for trip_id, trip_itin in trip_itins.iteritems():
        trip = trips_by_id[trip_id]
        saved_ccd_pair = saved_trip_id_ccds_map.get(trip_id)
        if saved_ccd_pair:
            o_ccd, d_ccd = saved_ccd_pair
        else:
            o_ccd, d_ccd = get_trip_origin_dest_ccd(trip, ccds_spatial_index,
                tform_trip_srs_to_ccd_srs)
            if o_ccd == None:
                o_ccd = "unknown"
            if d_ccd == None:
                d_ccd = "unknown"
            saved_trip_id_ccds_map[trip_id] = o_ccd, d_ccd
        if o_ccd not in trips_by_od_ccd:
            trips_by_od_ccd[o_ccd] = {}
        if d_ccd not in trips_by_od_ccd[o_ccd]:
            trips_by_od_ccd[o_ccd][d_ccd] = {}
        trips_by_od_ccd[o_ccd][d_ccd][trip_id] = trip_itin
        cnt += 1
        #if cnt % 10 == 0:
        #    print "...done %d trip ids." % cnt
    print "...finished classifying."
    if geom_utils.POTENTIAL_SHP_BBOX_TESTS:
        print "(potential max bbox tests was %d, actual bbox tests was %d, "\
            "Contains tests was %d, passed Contains tests was %d)" \
            % (geom_utils.POTENTIAL_SHP_BBOX_TESTS,
               geom_utils.ACTUAL_SHP_BBOX_TESTS,
               geom_utils.ACTUAL_CONTAINS_TESTS,
               geom_utils.PASSED_CONTAINS_TESTS)

    return trips_by_od_ccd

def categorise_trip_ids_by_mode_agency_route(trip_itins):
    trips_by_mar = {}
    trips_by_mar_legs = {}
    for mode in otp_config.OTP_NON_WALK_MODES:
        trips_by_mar[mode] = {}
        trips_by_mar_legs[mode] = {}
    for trip_id, trip_itin in trip_itins.iteritems():
        legs = trip_itin.json['legs']
        for leg_i, leg in enumerate(legs):
            mode = leg['mode']
            if mode == otp_config.OTP_WALK_MODE: continue
            a_name = leg['agencyName']
            r_id = leg['routeId']
            r_s_name = leg['routeShortName']
            r_l_name = leg['routeLongName']
            r_tup = (r_id, r_s_name, r_l_name)
            if a_name not in trips_by_mar[mode]:
                trips_by_mar[mode][a_name] = {}
                trips_by_mar_legs[mode][a_name] = {}
            if r_tup not in trips_by_mar[mode][a_name]:
                trips_by_mar[mode][a_name][r_tup] = {}
                trips_by_mar_legs[mode][a_name][r_tup] = {}

            trips_by_mar[mode][a_name][r_tup][trip_id] = \
                trip_itin
            if trip_id in trips_by_mar_legs[mode][a_name][r_tup]:
                trips_by_mar_legs[mode][a_name][r_tup][trip_id].append(leg_i)
            else:
                trips_by_mar_legs[mode][a_name][r_tup][trip_id] = [leg_i]
    return trips_by_mar, trips_by_mar_legs

example_dep_time_cats = {}
example_dep_time_cats['weekday_morning_early'] = ([0,1,2,3,4],
    time(4,00), time(7,00))
example_dep_time_cats['weekday_morning_peak'] = ([0,1,2,3,4],
    time(7,00), time(10,00))
example_dep_time_cats['weekday_interpeak'] = ([0,1,2,3,4],
    time(10,00), time(16,00))
example_dep_time_cats['weekday_arvo_peak'] = ([0,1,2,3,4],
    time(16,00), time(18,30))
example_dep_time_cats['weekday_evening'] = ([0,1,2,3,4],
    time(18,30), time(23,59,59))
example_dep_time_cats['saturday'] = ([5],
    time(0,00), time(23,59,59))
example_dep_time_cats['sunday'] = ([6],
    time(0,00), time(23,59,59))
example_dep_time_print_order = [
    'weekday_morning_early', 'weekday_morning_peak',
    'weekday_interpeak', 'weekday_arvo_peak', 'weekday_evening',
    'saturday', 'sunday']

DAY_HDRS = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
START_TIME_HDR = 'Time_Start'
STOP_TIME_HDR = 'Time_Stop'
TIME_FMT = "%H:%M:%S"

def read_trip_deptime_categories(csv_fname):
    csv_file = open(csv_fname, 'r')
    reader = csv.DictReader(csv_file, delimiter=',')
    dep_time_order = []
    dep_time_cats = {}
    for row in reader:
        cat_name = row['Name']
        days = []
        for day_i, day in enumerate(DAY_HDRS):
            if row[day]:
                days.append(day_i)
        time_start_str = row[START_TIME_HDR]
        time_stop_str = row[STOP_TIME_HDR]
        if time_stop_str == "24:00:00":
            # Python doesn't like a Time of midnight - round down a second.
            time_stop_str = "23:59:59" 
        time_start = datetime.strptime(time_start_str, TIME_FMT).time()
        time_stop = datetime.strptime(time_stop_str, TIME_FMT).time()
        cat_spec_tuple = (days, time_start, time_stop)
        dep_time_cats[cat_name] = cat_spec_tuple
        dep_time_order.append(cat_name) 
    return dep_time_cats, dep_time_order
