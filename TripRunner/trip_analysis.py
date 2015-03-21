import os, os.path
from datetime import datetime, timedelta, time
import itertools
import json
import copy

import geom_utils
import time_utils

DEFAULT_LONGEST_WALK_LEN_KM = 1.2
OTP_MODES = ['WALK', 'BUS', 'TRAM', 'SUBWAY']
OTP_WALK_MODE = 'WALK'
OTP_NON_WALK_MODES = filter(lambda x: x != OTP_WALK_MODE, OTP_MODES)

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
    for mode in OTP_NON_WALK_MODES:
        sum_modal_init_waits[mode] = timedelta(0)
        cnt_modal_init_waits[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        # Skip legs that are pure walking
        first_non_walk_mode = trip_itin.get_first_non_walk_mode()
        if first_non_walk_mode:
            trip_init_wait = trip_itin.get_init_wait_td(
                trip_req_start_dts[trip_id])
            sum_modal_init_waits[first_non_walk_mode] += trip_init_wait
            cnt_modal_init_waits[first_non_walk_mode] += 1
    mean_modal_init_waits = {}
    for mode in OTP_NON_WALK_MODES:
        total_sec = time_utils.get_total_sec(sum_modal_init_waits[mode])
        mean_sec = total_sec / float(cnt_modal_init_waits[mode])
        mean_modal_init_waits[mode] = timedelta(seconds=mean_sec)
    return mean_modal_init_waits, cnt_modal_init_waits

def calc_mean_walk_dist(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'walkDistance')

def calc_mean_dist_travelled(trip_itins):
    sum_iter = itertools.imap(
        lambda ti: ti.get_dist_travelled(), trip_itins.itervalues())
    sum_dist = sum(sum_iter)
    mean_dist_travelled = sum_dist / float(len(trip_itins))
    return mean_dist_travelled

def calc_mean_transfers(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'transfers')

def calc_mean_direct_speed(trip_itins, trips_by_id, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: get_trip_speed_direct(trips_by_id[trip_id][0],
            trips_by_id[trip_id][1], trip_req_start_dts[trip_id],
            trip_itins[trip_id]), trip_itins.iterkeys()))
    mean_spd = sum_val / float(len(trip_itins))
    return mean_spd

def calc_num_trips_using_modes(trip_itins):
    modes_used_in_trip_counts = {}
    for mode in OTP_MODES:
        modes_used_in_trip_counts[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        modes_used = trip_itin.get_set_of_modes_used()
        for mode in modes_used:
            modes_used_in_trip_counts[mode] += 1
    return modes_used_in_trip_counts

def calc_total_legs_by_mode(trip_itins):
    num_legs_of_modes = {}
    for mode in OTP_MODES:
        num_legs_of_modes[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        mode_legs = trip_itin.get_mode_sequence()
        for mode in mode_legs:
            num_legs_of_modes[mode] += 1
    return num_legs_of_modes

def calc_sum_modal_distances(trip_itins):
    """Calculate the sum of OTP's reported in-vehicle travel distances,
    per-mode, over all trips."""
    sum_modal_distances = {}
    for mode in OTP_MODES:
        sum_modal_distances[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_modal_dists = trip_itin.get_dist_m_by_mode()
        for mode, dist in trip_modal_dists.iteritems():
            sum_modal_distances[mode] += dist
    return sum_modal_distances

def calc_mean_modal_distances_per_all_trips(sum_modal_distances, n_trips_total):
    """Calculate the mean time, per-mode, over _all_ trips:- not just
    the ones where that mode was used."""
    means_modal_distances = {}
    for mode in OTP_MODES:
        means_modal_distances[mode] = sum_modal_distances[mode] / \
            n_trips_total
    return means_modal_distances

def calc_mean_modal_distances_per_leg_used(sum_modal_distances,
        n_legs_per_mode):
    """Calculate the mean distance travelled, per-mode, over legs travelled on
    each mode."""
    means_modal_distances = {}
    for mode in OTP_MODES:
        means_modal_distances[mode] = sum_modal_distances[mode] / \
            n_legs_per_mode[mode]
    return means_modal_distances

def calc_sum_modal_times(trip_itins):
    """Calculate the sum of in-vehicle travel time, per-mode, over all
    trips."""
    sums_modal_times = {}
    for mode in OTP_MODES:
        sums_modal_times[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        trip_modal_times = trip_itin.get_time_sec_by_mode()
        for mode, time_sec in trip_modal_times.iteritems():
            sums_modal_times[mode] += time_sec
    return sums_modal_times

def calc_mean_modal_times_per_all_trips(sums_modal_times, n_trips_total):
    """Calculate the mean time spent, per-mode, over _all_ trips:- not just the ones
    where that mode was used."""
    means_modal_times = {}
    for mode in OTP_MODES:
        mean_time_s = sums_modal_times[mode] / \
            n_trips_total
        means_modal_times[mode] = timedelta(seconds=mean_time_s)
    return means_modal_times

def calc_mean_modal_times_per_leg_used(sums_modal_times, n_legs_per_mode):
    """Calculate the mean time spent, per-mode, over legs using that mode."""
    means_modal_times = {}
    for mode in OTP_MODES:
        mean_time_s = sums_modal_times[mode] / \
            n_trips_total
        means_modal_times[mode] = timedelta(seconds=mean_time_s)
    return means_modal_times

def calc_mean_modal_speeds(trip_itins):
    sums_modal_speeds = {}
    n_modal_speeds = {}
    for mode in OTP_MODES:
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
    for mode in OTP_MODES:
        mean_spd_km_h = sums_modal_speeds[mode] / \
            float(n_modal_speeds[mode])
        means_modal_speeds[mode] = mean_spd_km_h
    return means_modal_speeds

def calc_means_of_tripset(trip_results, trips_by_id, trip_req_start_dts):
    means = {}
    means['n_trips'] = len(trip_results)
    means['total_time'] = \
        calc_mean_total_time(trip_results, trip_req_start_dts)
    means['init_wait'] = \
        calc_mean_init_waits(trip_results, trip_req_start_dts)
    means['direct_speed'] = \
        calc_mean_direct_speed(trip_results, trips_by_id,
            trip_req_start_dts)
    means['dist_travelled'] = calc_mean_dist_travelled(trip_results)
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

def categorise_trip_ids_by_first_non_walk_mode(trip_itins):
    trips_by_first_mode = {}
    for mode in OTP_NON_WALK_MODES:
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

def categorise_trip_ids_by_mode_agency_route(trip_itins):
    trips_by_mar = {}
    trips_by_mar_legs = {}
    for mode in OTP_NON_WALK_MODES:
        trips_by_mar[mode] = {}
        trips_by_mar_legs[mode] = {}
    for trip_id, trip_itin in trip_itins.iteritems():
        legs = trip_itin.json['legs']
        for leg_i, leg in enumerate(legs):
            mode = leg['mode']
            if mode == OTP_WALK_MODE: continue
            a_name = leg['agencyName']
            r_s_name = leg['routeShortName']
            r_l_name = leg['routeLongName']
            r_tup = (r_s_name, r_l_name)
            if a_name not in trips_by_mar[mode]:
                trips_by_mar[mode][a_name] = {}
                trips_by_mar_legs[mode][a_name] = {}
            if (r_s_name, r_l_name) not in trips_by_mar[mode][a_name]:
                trips_by_mar[mode][a_name][r_tup] = {}
                trips_by_mar_legs[mode][a_name][r_tup] = {}

            trips_by_mar[mode][a_name][r_tup][trip_id] = \
                trip_itin
            if trip_id in trips_by_mar_legs[mode][a_name][r_tup]:
                trips_by_mar_legs[mode][a_name][r_tup][trip_id].append(leg_i)
            else:
                trips_by_mar_legs[mode][a_name][r_tup][trip_id] = [leg_i]
    return trips_by_mar, trips_by_mar_legs

def calc_print_trip_info_by_mode_agency_route(trip_itins):
    trips_by_mar, trips_by_mar_legs = categorise_trip_ids_by_mode_agency_route(
        trip_itins)
    for mode, trips_by_ar in trips_by_mar.iteritems():
        print "For mode %s:" % mode
        for agency, trips_by_r in trips_by_ar.iteritems():
            print "  for agency %s:" % agency
            for route, trip_itins in trips_by_r.iteritems():
                r_short_name, r_l_name = route
                print "    for route %s, %s:" % (r_short_name, r_l_name)
                sum_trips = len(trip_itins)
                sum_legs = 0
                sum_dist = 0
                sum_duration = 0
                sum_speeds_km_h = 0
                valid_speeds_cnt = 0
                for trip_id, trip_itin in trip_itins.iteritems():
                    leg_is = trips_by_mar_legs[mode][agency][route][trip_id] 
                    sum_legs += len(leg_is)
                    for leg_i in leg_is:
                        leg_dist_m = trip_itin.json['legs'][leg_i]['distance'] 
                        leg_time_s = trip_itin.json['legs'][leg_i]['duration'] \
                            / 1000.0
                        sum_dist += leg_dist_m
                        sum_duration += leg_time_s
                        if leg_time_s > 0:
                            leg_speed_km_h = (leg_dist_m / 1000.0) \
                                / (leg_time_s / (60 * 60))
                            sum_speeds_km_h += leg_speed_km_h
                            valid_speeds_cnt += 1
                avg_dist_km = sum_dist / float(sum_legs) / 1000.0    
                mean_speed_km_h = sum_speeds_km_h / float(valid_speeds_cnt)
                print "      Used in %d legs, %d trips, for %.2f km " \
                    "(avg %.2f km/leg), at avg speed of %.2f km/hr" \
                    % (sum_legs, sum_trips, sum_dist / 1000.0, \
                       avg_dist_km, mean_speed_km_h)
            print ""
    return

def print_mean_results(mean_results_by_category, key_print_order=None):
    if key_print_order:
        keys = key_print_order
    else:
        keys = mean_results_by_category.keys()
        
    for key in keys:
        means = mean_results_by_category[key]
        print "  '%s': %d trips, mean trip time %s, mean dist travelled "\
            "%.2fkm, direct speed %.2f km/h, "\
            "walk dist %.2fm, # of transfers %.1f" % \
             (key,
              means['n_trips'],
              means['total_time'],
              means['dist_travelled'] / 1000.0,
              means['direct_speed'],
              means['walk_dist'],
              means['transfers'])
    print ""
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

def get_trips_subset_by_ids(trip_results_dict, trip_ids_to_select):
    trip_results_filtered = {}
    for trip_id in trip_ids_to_select:
        try:
            trip_results_filtered[trip_id] = trip_results_dict[trip_id]
        except KeyError:
            raise ValueError("Input trip_results_dict didn't contain at "\
                "least one of the trip IDs ('%s') you requested in "\
                "trip_ids_to_select." % trip_id)
    return trip_results_filtered

def get_trips_subset_by_ids_to_exclude(trip_results_dict, trip_ids_to_exclude):
    # In the excluding IDs case:- start by creating a copy of the entire 
    # first dict:- since it will be faster to just delete dictionary entries
    # that are excluded. copy.copy just creates a new dictionary pointing to
    # the same actual entries in memory, so this won't waste lots of space.
    trip_results_filtered = copy.copy(trip_results_dict)
    for trip_id in trip_ids_to_exclude:
        try:
            del(trip_results_filtered[trip_id])
        except KeyError:
            print "Warning: Input trip_results_dict didn't contain at "\
                "least one of the trip IDs ('%s') you requested to exclude "\
                "in trip_ids_to_exclude." % trip_id
    return trip_results_filtered

def calc_means_of_tripset_by_first_non_walk_mode(trip_results_by_graph,
    trips_by_id, trip_req_start_dts):

    trips_by_first_non_walk_mode = {}
    means_by_first_non_walk_mode = {}
    for graph_name, trip_results in trip_results_by_graph.iteritems():
        # Further classify by first non-walk mode
        trips_by_first_non_walk_mode[graph_name] = \
            categorise_trip_ids_by_first_non_walk_mode(trip_results)
        means_by_first_non_walk_mode[graph_name] = {}
        for mode in OTP_NON_WALK_MODES:
            means_by_first_non_walk_mode[graph_name][mode] = \
                calc_means_of_tripset(
                    trips_by_first_non_walk_mode[graph_name][mode],
                    trips_by_id, trip_req_start_dts)
    return means_by_first_non_walk_mode

def calc_print_mean_results_overall_summaries(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts, 
        description=None):

    means = {}
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        means[graph_name] = calc_means_of_tripset(
            trip_results, trips_by_id, trip_req_start_dts)

    if description:
        extra_string = "(%s)" % description
    else:
        extra_string = ""

    print "Overall %s mean results for the %d trips were:" \
        % (extra_string, max(map(len, trip_results_by_graph.itervalues())))
    print_mean_results(means)
    return

def calc_print_mean_results_agg_by_mode_agency(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts, 
        description=None):

    sum_modes_in_trips = {}
    sum_legs_by_mode = {}
    sum_modal_dists = {}
    sum_modal_times = {}
    means_modal_times = {}
    means_modal_dists = {}
    means_modal_dist_leg = {}
    means_modal_speeds = {}
    means_init_waits_by_mode = {}
    counts_init_waits_by_mode = {}
    means_init_waits = {}
    means_tfer_waits = {}
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        sum_modes_in_trips[graph_name] = \
            calc_num_trips_using_modes(trip_results)
        sum_legs_by_mode[graph_name] = \
            calc_total_legs_by_mode(trip_results)
        sum_modal_dists[graph_name] = \
            calc_sum_modal_distances(trip_results)
        sum_modal_times[graph_name] = \
            calc_sum_modal_times(trip_results)
        means_modal_times[graph_name] = \
            calc_mean_modal_times_per_all_trips(
                sum_modal_times[graph_name], len(trip_results))
        means_modal_dists[graph_name] = \
            calc_mean_modal_distances_per_all_trips(
                sum_modal_dists[graph_name], len(trip_results))
        means_modal_dist_leg[graph_name] = \
            calc_mean_modal_distances_per_leg_used(
                sum_modal_dists[graph_name], sum_legs_by_mode[graph_name])
        means_modal_speeds[graph_name] = \
            calc_mean_modal_speeds(trip_results)
        means_init_waits[graph_name] = \
            calc_mean_init_waits(trip_results, trip_req_start_dts)
        means_tfer_waits[graph_name] = \
            calc_mean_tfer_waits(trip_results)
    
    for graph_name, trip_results in trip_results_by_graph.iteritems():
        miw_by_mode, ciw_by_mode = \
            calc_mean_init_waits_by_mode(trip_results,
                trip_req_start_dts)
        means_init_waits_by_mode[graph_name] = miw_by_mode
        counts_init_waits_by_mode[graph_name] = ciw_by_mode

    means_by_first_non_walk_mode = \
        calc_means_of_tripset_by_first_non_walk_mode(
            trip_results_by_graph, trips_by_id, trip_req_start_dts)

    trips_by_agencies_used = {}
    means_by_agencies_used = {}
    for graph_name in graph_names:
        # Further classify by agencies used
        trip_results = trip_results_by_graph[graph_name]
        trips_by_agencies_used[graph_name] = \
            categorise_trips_by_agencies_used(trip_results)
        means_by_agencies_used[graph_name] = {}
        for agency_tuple, trip_itins in \
                trips_by_agencies_used[graph_name].iteritems():
            means_by_agencies_used[graph_name][agency_tuple] = \
                calc_means_of_tripset(trip_itins, trips_by_id,
                    trip_req_start_dts)

    if description:
        extra_string = " (%s)" % description
    else:
        extra_string = ""
    print "\nTrip results%s: aggregated by mode were:" % extra_string
    for graph_name in graph_names:
        print "For graph %s, aggregated results for mode use were:" \
            % graph_name
        print "  mode, mean time (all trips), mean dist (all trips), "\
            "# trips used in, # legs, total dist (km), "\
            "mean dist/leg (m), mean in-vehicle speed (km/h)"
        for mode in OTP_MODES:
            mode_time = means_modal_times[graph_name][mode]
            mode_dist = means_modal_dists[graph_name][mode]
            mode_in_trip_cnt = sum_modes_in_trips[graph_name][mode]
            mode_legs_cnt = sum_legs_by_mode[graph_name][mode]
            mode_sum_dist = sum_modal_dists[graph_name][mode]
            mode_dist_leg = means_modal_dist_leg[graph_name][mode]
            mode_speed = means_modal_speeds[graph_name][mode]
            print "  %s, %s, %.1f m, %d, %d, %.2f km, %.1f m, %.2f," \
                % (mode, mode_time, mode_dist, mode_in_trip_cnt, \
                   mode_legs_cnt, mode_sum_dist, mode_dist_leg, mode_speed)
        print "  initial wait, %s, " % means_init_waits[graph_name]
        print "  transfer wait, %s, " % means_tfer_waits[graph_name]

        print "\n  mean init waits, total trip times, trip overall speeds, "\
            "by first non-walk mode:"
        for mode in OTP_NON_WALK_MODES:
            print "    %s: %s, %s, %.2f km/h (%d trips)" % (mode, \
                means_init_waits_by_mode[graph_name][mode],
                means_by_first_non_walk_mode[graph_name][mode]['total_time'],
                means_by_first_non_walk_mode[graph_name][mode]['direct_speed'],
                counts_init_waits_by_mode[graph_name][mode])
        print ""

        print "  mean init waits, total trip times, trip overall speeds, "\
            "by agencies used (sorted by speed):"
        agency_tups_and_means_sorted_by_spd = sorted(
            means_by_agencies_used[graph_name].iteritems(), 
            key = lambda x: x[1]['direct_speed'])
        for agency_tuple, means in \
                reversed(agency_tups_and_means_sorted_by_spd):
            print "    %s: %s, %s, %.2f km/h (%d trips)" \
                % (agency_tuple, \
                   means['init_wait'],
                   means['total_time'],
                   means['direct_speed'],
                   means['n_trips'])
        print ""
    #import pdb
    #pdb.set_trace()

    #print "Further info by mode, agency, route:"
    #for graph_name in graph_names:
    #    print "*For graph %s:*" % graph_name
    #    calc_print_trip_info_by_mode_agency_route(
    #        trip_results_by_graph[graph_name])
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
        trips_by_id, trip_req_start_dts,
        dep_time_cats, description=None,
        dep_time_print_order=None ):
    """Similar to the normal mean-printing function:- but this time breaks
    down results into categories based on departure times.
    These are given by input dictionary 'dep_time_cats': with each entry
    being key being a time category string (e.g. 'weekday_morning_early')
    mapped to a tuple of the form:
    (dow_list, time_start, time_end)
    * dow_list is a list of days-of-the-week matching the Python datetime
      class's weekday() function :- where 0 is Monday, etc.
    * time_start and time_end are both Python time instances listing when that
      time category begins and ends.
    * E.g. here is a tuple for weekday evenings between 6:30PM and midnight:
    ([0,1,2,3,4], time(18,30), time(23,59,59))   
    """

    means_by_deptime = {}
    for graph_name in graph_names:
        means_by_deptime[graph_name] = {}
        trip_results_graph = trip_results_by_graph[graph_name]
        for dep_time_cat, dt_info in dep_time_cats.iteritems():
            trip_results_for_dep_time_cat = get_results_in_dep_time_range(
                trip_results_graph, trip_req_start_dts, dt_info)
            means_by_deptime[graph_name][dep_time_cat] = calc_means_of_tripset(
                trip_results_for_dep_time_cat, trips_by_id,
                trip_req_start_dts)

    if description:
        extra_string = " (%s)" % description
    else:
        extra_string = ""
    print "\nMean results for the %d trips%s, by departure time period, were:" \
        % (max(map(len, trip_results_by_graph.itervalues())), extra_string)
    for graph_name in graph_names:
        print "For graph name '%s':" % graph_name
        print_mean_results(means_by_deptime[graph_name], dep_time_print_order)
    return        

def createTripsCompShapefile(trips_by_id, graph_names, trip_req_start_dts,
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
        trip_req_start_dt = trip_req_start_dts[trip_id]

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

