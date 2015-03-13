import os, os.path
from datetime import datetime, timedelta, time
import itertools
import json
import copy

import geom_utils
import time_utils

DEFAULT_LONGEST_WALK_LEN_KM = 1.2
ALL_MODES_OTP = ['WALK', 'BUS', 'TRAM', 'SUBWAY']

########################
## Analysis and Printing

def get_trip_speed_direct(origin_lon_lat, dest_lon_lat, trip_req_start_dt,
        trip_itin):
    dist_direct = geom_utils.haversine(origin_lon_lat[0], origin_lon_lat[1],
        dest_lon_lat[0], dest_lon_lat[1])
    total_trip_sec = trip_itin.get_total_trip_sec(trip_req_start_dt)
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))
    return trip_speed_direct

def print_single_trip_stats(origin_lon_lat, dest_lon_lat, trip_req_start_dt,
        trip_itin):
    ti = trip_itin
    itin_start_dt = ti.get_start_dt()
    itin_end_dt = ti.get_end_dt()
    total_trip_td = ti.get_total_trip_td(trip_req_start_dt)
    total_trip_sec = ti.get_total_trip_sec(trip_req_start_dt)

    init_wait_td = ti.get_init_wait_td(trip_req_start_dt)
    tfer_wait_td = ti.get_tfer_wait_td()
    total_wait_td = ti.get_total_wait_td(trip_req_start_dt)
    walk_td = ti.get_walk_td()
    transit_td = ti.get_transit_td()

    wait_pct = time_utils.get_td_pct(total_wait_td, total_trip_td)
    walk_pct = time_utils.get_td_pct(walk_td, total_trip_td)
    transit_pct = time_utils.get_td_pct(transit_td, total_trip_td)

    dist_travelled = ti.get_dist_travelled()
    trip_speed_along_route = ti.get_trip_speed_along_route(trip_req_start_dt)

    dist_direct = geom_utils.haversine(origin_lon_lat[0], origin_lon_lat[1],
        dest_lon_lat[0], dest_lon_lat[1])
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))

    print "Trip departs at %s" % itin_start_dt 
    print "Trip arrives at %s" % itin_end_dt 
    print "%s total time (inc initial wait)" % total_trip_td
    print "  %s (%.2f%%) waiting (%s initial, %s transfers)" \
        % (total_wait_td, wait_pct, init_wait_td, tfer_wait_td)
    print "  %s (%.2f%%) walking (for %.2fm)" \
        % (walk_td, walk_pct, ti.json['walkDistance'])
    print "  %s (%.2f%%) on transit vehicles (%d transfers)" \
        % (transit_td, transit_pct, ti.json['transfers'])
    print "Total trip distance (as crow flies): %.2fm." % dist_direct
    print "Total trip distance (travelled): %.2fm." % dist_travelled
    print "(Trip directness ratio:- %.2f)" % (dist_direct / dist_travelled)
    print "Trip speed (along route, inc. init wait): %.2fkm/h." \
        % trip_speed_along_route
    print "Trip speed (as crow flies, inc. init wait): %.2fkm/h." \
        % trip_speed_direct
    return

def calc_mean_total_time(trip_itins, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: trip_itins[trip_id].get_total_trip_sec(
            trip_req_start_dts[trip_id]), trip_itins.iterkeys()))
    mean_sec = sum_val / float(len(trip_itins))
    return timedelta(seconds=mean_sec)

def calc_mean_basic_itin_attr(trip_itins, itin_attr):
    """Convenience function."""
    sum_val = sum(itertools.imap(
        lambda ti: ti.json[itin_attr], trip_itins.itervalues()))
    mean = sum_val / float(len(trip_itins))
    return mean

def calc_mean_init_waits(trip_itins, trip_req_start_dts):
    sum_val = timedelta(0)
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_init_wait = trip_itin.get_init_wait_td(
            trip_req_start_dts[trip_id])
        sum_val += trip_init_wait    
    total_sec = time_utils.get_total_sec(sum_val)
    mean_sec = total_sec / float(len(trip_itins))
    return timedelta(seconds=mean_sec)

def calc_mean_tfer_waits(trip_itins):
    sum_val = timedelta(0)
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_tfer_wait = trip_itin.get_tfer_wait_td()
        sum_val += trip_tfer_wait    
    total_sec = time_utils.get_total_sec(sum_val)
    mean_sec = total_sec / float(len(trip_itins))
    return timedelta(seconds=mean_sec)

def calc_mean_init_waits_by_mode(trip_itins, trip_req_start_dts):
    sum_modal_init_waits = {}
    cnt_modal_init_waits = {}
    for mode in ALL_MODES_OTP:
        if mode == 'WALK': continue
        sum_modal_init_waits[mode] = timedelta(0)
        cnt_modal_init_waits[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        # Skip legs that are pure walking
        if len(trip_itin.json['legs']) > 1 \
                or trip_itin.json['legs'][0]['mode'] != 'WALK':
            trip_init_wait = trip_itin.get_init_wait_td(
                trip_req_start_dts[trip_id])
            first_non_walk_mode = None
            for leg in trip_itin.json['legs']:
                if leg['mode'] != 'WALK':
                    first_non_walk_mode = leg['mode']
                    break
            assert first_non_walk_mode
            sum_modal_init_waits[first_non_walk_mode] += trip_init_wait
            cnt_modal_init_waits[first_non_walk_mode] += 1
    mean_modal_init_waits = {}
    for mode in ALL_MODES_OTP:
        if mode == 'WALK': continue
        total_sec = time_utils.get_total_sec(sum_modal_init_waits[mode])
        mean_sec = total_sec / float(cnt_modal_init_waits[mode])
        mean_modal_init_waits[mode] = timedelta(seconds=mean_sec)
    return mean_modal_init_waits, cnt_modal_init_waits

def calc_mean_walk_dist(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'walkDistance')

def calc_mean_transfers(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'transfers')

def calc_mean_direct_speed(trip_itins, trips_by_id, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: get_trip_speed_direct(trips_by_id[trip_id][0],
            trips_by_id[trip_id][1], trip_req_start_dts[trip_id],
            trip_itins[trip_id]), trip_itins.iterkeys()))
    mean_spd = sum_val / float(len(trip_itins))
    return mean_spd

def calc_mean_modal_distances(trip_itins):
    sums_modal_distances = {}
    for mode in ALL_MODES_OTP:
        sums_modal_distances[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_modal_dists = trip_itin.get_dist_m_by_mode()
        for mode, dist in trip_modal_dists.iteritems():
            sums_modal_distances[mode] += dist
    means_modal_distances = {}
    for mode in ALL_MODES_OTP:
        means_modal_distances[mode] = sums_modal_distances[mode] / \
            float(len(trip_itins))
    return means_modal_distances

def calc_mean_modal_times(trip_itins):
    sums_modal_times = {}
    for mode in ALL_MODES_OTP:
        sums_modal_times[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_modal_times = trip_itin.get_time_sec_by_mode()
        for mode, time_sec in trip_modal_times.iteritems():
            sums_modal_times[mode] += time_sec
    means_modal_times = {}
    for mode in ALL_MODES_OTP:
        mean_time_s = sums_modal_times[mode] / \
            float(len(trip_itins))
        means_modal_times[mode] = timedelta(seconds=mean_time_s)
    return means_modal_times

def calc_mean_modal_speeds(trip_itins):
    sums_modal_speeds = {}
    n_modal_speeds = {}
    for mode in ALL_MODES_OTP:
        sums_modal_speeds[mode] = 0
        n_modal_speeds[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_modal_times = trip_itin.get_time_sec_by_mode()
        trip_modal_dists = trip_itin.get_dist_m_by_mode()
        for mode in trip_modal_times.iterkeys():
            dist = trip_modal_dists[mode] 
            time_s = trip_modal_times[mode]
            if time_s > 0:
                speed_km_h = (dist / 1000.0) / (time_s / (60.0 * 60.0))
                sums_modal_speeds[mode] += speed_km_h
                n_modal_speeds[mode] += 1
            else:
                print "Warning for trip %s: for mode %s: dist = %.2fm, "\
                    "time = %.2fs (inf speed)" % (trip_id, mode, dist, time_s)
                print "Not including this in the average."
    means_modal_speeds = {}
    for mode in ALL_MODES_OTP:
        mean_spd_km_h = sums_modal_speeds[mode] / \
            float(n_modal_speeds[mode])
        means_modal_speeds[mode] = mean_spd_km_h
    return means_modal_speeds

def calc_means_of_tripset(trip_results, trips_by_id, trip_req_start_dts):
    means = {}
    means['n_trips'] = len(trip_results)
    means['total_time'] = \
        calc_mean_total_time(trip_results, trip_req_start_dts)
    means['direct_speed'] = \
        calc_mean_direct_speed(trip_results, trips_by_id,
            trip_req_start_dts)
    means['walk_dist'] = calc_mean_walk_dist(trip_results)
    means['transfers'] = calc_mean_transfers(trip_results)
    return means

def get_trip_ids_with_walk_leg_gr_than_dist_km(trip_results, dist_km):
    trip_ids_match_criteria = []
    for trip_id, trip_result in trip_results.iteritems():
        longest_walk_m = trip_result.get_longest_walk_leg_dist_m()
        if longest_walk_m / 1000.0 > dist_km:
            trip_ids_match_criteria.append(trip_id)
            #print "(trip %s matches since it's longest walk leg "\
            #    "was %fm.)" % (trip_id, longest_walk_m)
    return trip_ids_match_criteria

def print_mean_results(mean_results_by_category, key_print_order=None):
    if key_print_order:
        keys = key_print_order
    else:
        keys = mean_results_by_category.keys()
        
    for key in keys:
        means = mean_results_by_category[key]
        print "  '%s': %d trips, mean trip time %s, direct speed %.2f km/h, "\
            "walk dist %.2fm, # of transfers %.1f" % \
             (key,
              means['n_trips'],
              means['total_time'],
              means['direct_speed'],
              means['walk_dist'],
              means['transfers'])
    return

def get_trip_req_start_dts(trips_by_id, trip_req_start_date):
    trip_req_start_dts = {}
    for trip_id, trip in trips_by_id.iteritems():
        if isinstance(trip[2], datetime):
            trip_req_start_dts[trip_id] = trip[2]
        else:
            trip_req_start_dts[trip_id] = datetime.combine(trip_req_start_date,
                trip[2])
    return trip_req_start_dts

def calc_print_mean_results(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_date, 
        longest_walk_len_km=DEFAULT_LONGEST_WALK_LEN_KM):
    trip_req_start_dts = get_trip_req_start_dts(trips_by_id,
        trip_req_start_date)
    means = {}
    means_filtered = {}
    means_filtered_modal_times = {}
    means_filtered_modal_distances = {}
    means_filtered_modal_speeds = {}
    means_filtered_init_waits = {}
    means_filtered_init_waits_by_mode = {}
    counts_filtered_init_waits_by_mode = {}
    means_filtered_tfer_waits = {}
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        trip_ids_long_walk = get_trip_ids_with_walk_leg_gr_than_dist_km(
            trip_results, longest_walk_len_km)
        trip_results_filtered = {}
        trip_results_filtered = copy.copy(trip_results)
        for trip_id in trip_ids_long_walk:
            del(trip_results_filtered[trip_id])
        means[graph_name] = calc_means_of_tripset(
            trip_results, trips_by_id, trip_req_start_dts)
        means_filtered[graph_name] = calc_means_of_tripset(
            trip_results_filtered, trips_by_id, trip_req_start_dts)
        means_filtered_modal_times[graph_name] = \
            calc_mean_modal_times(trip_results_filtered)
        means_filtered_modal_distances[graph_name] = \
            calc_mean_modal_distances(trip_results_filtered)
        means_filtered_modal_speeds[graph_name] = \
            calc_mean_modal_speeds(trip_results_filtered)
        means_filtered_init_waits[graph_name] = \
            calc_mean_init_waits(trip_results_filtered, trip_req_start_dts)
        miw_by_mode, ciw_by_mode = \
            calc_mean_init_waits_by_mode(trip_results_filtered,
                trip_req_start_dts)
        means_filtered_init_waits_by_mode[graph_name] = miw_by_mode
        counts_filtered_init_waits_by_mode[graph_name] = ciw_by_mode
        means_filtered_tfer_waits[graph_name] = \
            calc_mean_tfer_waits(trip_results_filtered)

    print "Overall (unfiltered) mean results for the %d trips were:" \
        % (max(map(len, trip_results_by_graph.itervalues())))
    print_mean_results(means)
    print "\nOverall (filtered to remove long walk legs) mean results "\
        "for the %d trips were:" \
        % (max(map(len, trip_results_by_graph.itervalues())))
    print_mean_results(means_filtered)
    print "\n trip results (filtered) broken down by mode:"
    for graph_name in graph_names:
        print "For graph %s, mean distances, times, speeds by mode "\
            "were:" % graph_name
        for mode in ALL_MODES_OTP:
            mode_dist = means_filtered_modal_distances[graph_name][mode]
            mode_time = means_filtered_modal_times[graph_name][mode]
            mode_speed = means_filtered_modal_speeds[graph_name][mode]
            print "  %s: %.1f m, %s, %.2f km/h " \
                % (mode, mode_dist, mode_time, mode_speed)
        print "  initial wait: %s " % means_filtered_init_waits[graph_name]
        print "  transfer wait: %s " % means_filtered_tfer_waits[graph_name]
        print "\n  mean init waits by mode:"
        for mode in ALL_MODES_OTP:
            if mode == 'WALK': continue
            print "    %s: %s (%d trips)" % (mode, \
                means_filtered_init_waits_by_mode[graph_name][mode],
                counts_filtered_init_waits_by_mode[graph_name][mode])
        print ""
    return

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

def calc_print_mean_results_by_dep_times(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_date,
        longest_walk_len_km=DEFAULT_LONGEST_WALK_LEN_KM):
    dep_time_cats = {}
    dep_time_cats['weekday_morning_early'] = ([0,1,2,3,4],
        time(4,00), time(7,00))
    dep_time_cats['weekday_morning_peak'] = ([0,1,2,3,4],
        time(7,00), time(10,00))
    dep_time_cats['weekday_interpeak'] = ([0,1,2,3,4],
        time(10,00), time(16,00))
    dep_time_cats['weekday_arvo_peak'] = ([0,1,2,3,4],
        time(16,00), time(18,30))
    dep_time_cats['weekday_evening'] = ([0,1,2,3,4],
        time(18,30), time(23,59,59))
    dep_time_cats['saturday'] = ([5],
        time(0,00), time(23,59,59))
    dep_time_cats['sunday'] = ([6],
        time(0,00), time(23,59,59))
    dep_time_print_order = [
        'weekday_morning_early', 'weekday_morning_peak',
        'weekday_interpeak', 'weekday_arvo_peak', 'weekday_evening',
        'saturday', 'sunday']

    trip_req_start_dts = get_trip_req_start_dts(trips_by_id,
        trip_req_start_date)

    means = {}
    means_filtered = {}
    for graph_name in graph_names:
        means[graph_name] = {}
        means_filtered[graph_name] = {}
        trip_results_graph = trip_results_by_graph[graph_name]
        for dep_time_cat, dt_info in dep_time_cats.iteritems():
            trip_results_for_dep_time_cat = get_results_in_dep_time_range(
                trip_results_graph, trip_req_start_dts, dt_info)
            trip_ids_long_walk = get_trip_ids_with_walk_leg_gr_than_dist_km(
                trip_results_for_dep_time_cat, longest_walk_len_km)
            trip_results_filtered = copy.copy(trip_results_for_dep_time_cat)
            for trip_id in trip_ids_long_walk:
                del(trip_results_filtered[trip_id])
            means[graph_name][dep_time_cat] = calc_means_of_tripset(
                trip_results_for_dep_time_cat, trips_by_id,
                trip_req_start_dts)
            means_filtered[graph_name][dep_time_cat] = calc_means_of_tripset(
                trip_results_filtered, trips_by_id,
                trip_req_start_dts)

    print "\nMean results for the %d trips, by time period, were:" \
        % (max(map(len, trip_results_by_graph.itervalues())))
    for graph_name in graph_names:
        print "For graph name '%s':" % graph_name
        print_mean_results(means[graph_name], dep_time_print_order)    
    print "\nMean results for the %d trips, by time period (filtered for max "\
        "walk dist), were:" \
        % (max(map(len, trip_results_by_graph.itervalues())))
    for graph_name in graph_names:
        print "For graph name '%s':" % graph_name
        print_mean_results(means_filtered[graph_name], dep_time_print_order)    
    return        

def createTripsCompShapefile(trips_by_id, graph_names, trip_req_start_date,
        trip_results_1, trip_results_2, shapefilename):
    """Creates a Shape file stating the difference between times in two
    sets of results for the same set of trips.
    Saves results to a shapefile determined by shapefilename.
    
    N.B. :- thanks for overall strategy here are due to author of
    https://github.com/glennon/FlowpyGIS"""

    import osgeo.ogr
    from osgeo import ogr

    print "Creating shapefile of trip lines with time attributes to file"\
        " %s ..." % (shapefilename)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    # create a new data source and layer
    if os.path.exists(shapefilename):
        driver.DeleteDataSource(shapefilename)
    ds = driver.CreateDataSource(shapefilename)
    if ds is None:
        print 'Could not create file'
        sys.exit(1)

    c1TimeFieldName = 't%s' % graph_names[0]
    c2TimeFieldName = 't%s' % graph_names[1]
    #Abbreviate due to Shpfile limits.
    c1TimeFieldName = c1TimeFieldName[:8]
    c2TimeFieldName = c2TimeFieldName[:8]

    layer = ds.CreateLayer('trip_comps', geom_type=ogr.wkbLineString)
    fieldDefn = ogr.FieldDefn('TripID', ogr.OFTString)
    fieldDefn.SetWidth(20)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('DepTime', ogr.OFTString)
    fieldDefn.SetWidth(8)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('OriginZ', ogr.OFTString)
    fieldDefn.SetWidth(254)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('DestZ', ogr.OFTString)
    fieldDefn.SetWidth(254)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c1TimeFieldName, ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c2TimeFieldName, ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('Diff', ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    # END setup creation of shapefile

    for trip_id in sorted(trips_by_id.iterkeys()):
        trip = trips_by_id[trip_id]
        if isinstance(trip[2], datetime):
            trip_req_start_dt = trip[2]
        else:
            trip_req_start_dt = datetime.combine(trip_req_start_date, 
                trip[2])
        try:
            trip_res_1 = trip_results_1[trip_id]
            trip_res_2 = trip_results_2[trip_id]
        except KeyError:
            # For now - just skip trips not valid in both graphs.
            continue
        case1time = trip_res_1.get_total_trip_sec(trip_req_start_dt)
        case2time = trip_res_2.get_total_trip_sec(trip_req_start_dt)
        linester = ogr.Geometry(ogr.wkbLineString)
        linester.AddPoint(*trip[0])
        linester.AddPoint(*trip[1])

        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(linester)
        feature.SetField('TripId', str(trip_id))
        feature.SetField('DepTime', trip[2].strftime('%H:%M:%S'))
        feature.SetField('OriginZ', trip[3])
        feature.SetField('DestZ', trip[4])
        feature.SetField(c1TimeFieldName, case1time)
        feature.SetField(c2TimeFieldName, case2time)
        diff = case1time - case2time
        feature.SetField('Diff', diff)
        layer.CreateFeature(feature)

    # shapefile cleanup
    # destroy the geometry and feature and close the data source
    linester.Destroy()
    feature.Destroy()
    ds.Destroy()
    print "Done."
    return

