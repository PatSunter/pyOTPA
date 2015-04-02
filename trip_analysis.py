import sys
import csv
import os, os.path
from datetime import timedelta
import itertools
import operator
import json
import copy

from pyOTPA import Trip
from pyOTPA import geom_utils
from pyOTPA import time_utils
from pyOTPA import misc_utils
from pyOTPA import otp_config
from pyOTPA import trip_itin_filters

# Numbers of decimal places to round various outputs to.
OUTPUT_ROUND_DIST_KM = 3
OUTPUT_ROUND_SPEED_KPH = 2
OUTPUT_ROUND_TRANSFERS = 1
OUTPUT_ROUND_TIME_MIN = 2

########################
## Analysis and Printing

def calc_trip_direct_dist_km(trip):
    dist_direct = geom_utils.haversine(
        trip[Trip.ORIGIN][0], trip[Trip.ORIGIN][1],
        trip[Trip.DEST][0], trip[Trip.DEST][1])
    return dist_direct

def calc_mean_dist_direct_km(trip_itins, trips_by_id):
    dist_iter = itertools.imap(
        lambda trip_id: calc_trip_direct_dist_km(trips_by_id[trip_id]),
        trip_itins.iterkeys())
    sum_dist_km = sum(dist_iter) / 1000.0
    mean_dist_direct = sum_dist_km / float(len(trip_itins))
    return mean_dist_direct

def calc_trip_speed_direct(trip, trip_req_start_dt, trip_itin):
    dist_direct = calc_trip_direct_dist_km(trip)
    total_trip_sec = trip_itin.get_total_trip_sec(trip_req_start_dt)
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))
    return trip_speed_direct

def calc_mean_dist_travelled_km(trip_itins):
    sum_iter = itertools.imap(
        lambda ti: ti.get_dist_travelled(), trip_itins.itervalues())
    sum_dist_km = sum(sum_iter) / 1000.0
    mean_dist_travelled = sum_dist_km / float(len(trip_itins))
    return mean_dist_travelled

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

def calc_mean_walk_dist_km(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'walkDistance') / 1000.0

def calc_mean_transfers(trip_itins):
    # Can't use the standard mean-calculating algorithm here :- since OTP
    # returns a '-1' to distinguish pure-walking trips, from trips that have
    # only one transfer. We want to use zero for pure-walk trips for this mean
    # calculation, so adjust.
    tfer_vals = itertools.imap(
        lambda ti: ti.json['transfers'], trip_itins.itervalues())
    tfer_vals_adjust = itertools.imap(
        lambda tval: tval if tval >= 0 else 0, tfer_vals)
    mean = sum(tfer_vals_adjust) / float(len(trip_itins))
    return mean

def calc_mean_direct_speed(trip_itins, trips_by_id, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: calc_trip_speed_direct(
            trips_by_id[trip_id],
            trip_req_start_dts[trip_id],
            trip_itins[trip_id]),
        trip_itins.iterkeys()))
    mean_spd = sum_val / float(len(trip_itins))
    return mean_spd

def calc_num_trips_using_modes(trip_itins):
    modes_used_in_trip_counts = {}
    for mode in otp_config.OTP_MODES:
        modes_used_in_trip_counts[mode] = 0
    for trip_id, trip_itin in trip_itins.iteritems():
        modes_used = trip_itin.get_set_of_modes_used()
        for mode in modes_used:
            modes_used_in_trip_counts[mode] += 1
    return modes_used_in_trip_counts

def calc_total_legs_by_mode(trip_itins):
    num_legs_of_modes = {}
    for mode in otp_config.OTP_MODES:
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
    for mode in otp_config.OTP_MODES:
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
    for mode in otp_config.OTP_MODES:
        means_modal_distances[mode] = sum_modal_distances[mode] / \
            n_trips_total
    return means_modal_distances

def calc_mean_modal_distances_per_leg_used(sum_modal_distances,
        n_legs_per_mode):
    """Calculate the mean distance travelled, per-mode, over legs travelled on
    each mode."""
    means_modal_distances = {}
    for mode in otp_config.OTP_MODES:
        if n_legs_per_mode[mode]:
            means_modal_distances[mode] = sum_modal_distances[mode] / \
                n_legs_per_mode[mode]
        else:
            means_modal_distances[mode] = None
    return means_modal_distances

def calc_sum_modal_times(trip_itins):
    """Calculate the sum of in-vehicle travel time, per-mode, over all
    trips."""
    sums_modal_times = {}
    for mode in otp_config.OTP_MODES:
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
    for mode in otp_config.OTP_MODES:
        mean_time_s = sums_modal_times[mode] / \
            n_trips_total
        means_modal_times[mode] = timedelta(seconds=mean_time_s)
    return means_modal_times

def calc_mean_modal_times_per_leg_used(sums_modal_times, n_legs_per_mode):
    """Calculate the mean time spent, per-mode, over legs using that mode."""
    means_modal_times = {}
    for mode in otp_config.OTP_MODES:
        mean_time_s = sums_modal_times[mode] / \
            n_trips_total
        means_modal_times[mode] = timedelta(seconds=mean_time_s)
    return means_modal_times

def calc_mean_modal_speeds(trip_itins):
    sums_modal_speeds = {}
    n_modal_speeds = {}
    for mode in otp_config.OTP_MODES:
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
                #print "Warning for trip %s: for mode %s: dist = %.2fm, "\
                #    "time = %.2fs (inf speed)" % (trip_id, mode, dist, time_s)
                #print "Not including this in the average."
                pass
    means_modal_speeds = {}
    for mode in otp_config.OTP_MODES:
        if n_modal_speeds[mode]:
            mean_spd_km_h = sums_modal_speeds[mode] / \
                float(n_modal_speeds[mode])
            means_modal_speeds[mode] = mean_spd_km_h
        else:
            means_modal_speeds[mode] = None
    return means_modal_speeds

def calc_means(trip_results, trips_by_id, trip_req_start_dts):
    assert len(trip_results) > 0
    means = {}
    means['n trips'] = len(trip_results)
    means['total time'] = \
        calc_mean_total_time(trip_results, trip_req_start_dts)
    means['init wait'] = \
        calc_mean_init_waits(trip_results, trip_req_start_dts)
    means['tfer wait'] = \
        calc_mean_tfer_waits(trip_results)
    means['direct speed (kph)'] = \
        calc_mean_direct_speed(trip_results, trips_by_id,
            trip_req_start_dts)
    means['dist direct (km)'] = calc_mean_dist_direct_km(trip_results,
        trips_by_id)
    means['dist travelled (km)'] = calc_mean_dist_travelled_km(trip_results)
    means['walk dist (km)'] = calc_mean_walk_dist_km(trip_results) 
    means['transfers'] = calc_mean_transfers(trip_results)
    return means

def calc_save_trip_info_by_mode_agency_route(trip_itins, trip_req_start_dts, output_fname):

    trips_by_mar, trips_by_mar_legs = \
        trip_itin_filters.categorise_trip_ids_by_mode_agency_route(trip_itins)
    
    TRIP_INFO_BY_ROUTE_HEADERS = ['Mode', 'Agency', 'R ID', 'R S name', 
        'R L name', 'n trips', 'n legs', 'tot dist (km)', 'tot wait (min)',
        'mean dist/leg (km)', 'mean speed (km/h)', 'mean wait (min)']

    if sys.version_info >= (3,0,0):
        csv_file = open(output_fname, 'w', newline='')
    else:
        csv_file = open(output_fname, 'wb')

    writer = csv.writer(csv_file, delimiter=',')

    writer.writerow(TRIP_INFO_BY_ROUTE_HEADERS)

    for mode, trips_by_ar in trips_by_mar.iteritems():
        #print "For mode %s:" % mode
        for agency, trips_by_r in trips_by_ar.iteritems():
            #print "  for agency %s:" % agency
            out_row_base = [mode, agency]
            for route, trip_itins in trips_by_r.iteritems():
                r_id, r_short_name, r_l_name = route
                #print "    for route %s, %s:" % (r_short_name, r_l_name)
                sum_trips = len(trip_itins)
                sum_legs = 0
                sum_dist = 0
                sum_duration = 0
                sum_speeds_km_h = 0
                valid_speeds_cnt = 0
                mean_wait_min = 0
                sum_wait = timedelta(seconds=0)
                for trip_id, trip_itin in trip_itins.iteritems():
                    trip_req_start_dt = trip_req_start_dts[trip_id]
                    leg_is = trips_by_mar_legs[mode][agency][route][trip_id] 
                    sum_legs += len(leg_is)
                    for leg_i in leg_is:
                        leg_dist_m = trip_itin.json['legs'][leg_i]['distance'] 
                        leg_time_s = trip_itin.json['legs'][leg_i]['duration'] \
                            / 1000.0
                        wait = trip_itin.get_transfer_wait_before_leg(leg_i, 
                            trip_req_start_dt)
                        sum_wait += wait
                        sum_dist += leg_dist_m
                        sum_duration += leg_time_s
                        if leg_time_s > 0:
                            leg_speed_km_h = (leg_dist_m / 1000.0) \
                                / (leg_time_s / (60 * 60))
                            sum_speeds_km_h += leg_speed_km_h
                            valid_speeds_cnt += 1
                sum_dist_km = sum_dist / 1000.0            
                avg_dist_km = sum_dist / float(sum_legs) / 1000.0    
                mean_speed_km_h = sum_speeds_km_h / float(valid_speeds_cnt)
                sum_wait_min = time_utils.get_total_mins(sum_wait)
                mean_wait_min = sum_wait_min / float(sum_legs)
                #print "      Used in %d legs, %d trips, for %.2f km " \
                #    "(avg %.2f km/leg), at avg speed of %.2f km/hr" \
                #    % (sum_legs, sum_trips, sum_dist / 1000.0, \
                #       avg_dist_km, mean_speed_km_h)
                out_row = out_row_base + [r_id, r_short_name, r_l_name, \
                    sum_trips, sum_legs, 
                    round(sum_dist_km, OUTPUT_ROUND_DIST_KM), 
                    round(sum_wait_min, OUTPUT_ROUND_TIME_MIN), 
                    round(avg_dist_km, OUTPUT_ROUND_DIST_KM),
                    round(mean_speed_km_h, OUTPUT_ROUND_DIST_KM),
                    round(mean_wait_min, OUTPUT_ROUND_TIME_MIN)]
                writer.writerow(out_row)
            #print ""
    csv_file.close()
    return

def calc_means_by_first_non_walk_mode(trip_results,
        trips_by_id, trip_req_start_dts):
    trips_by_first_non_walk_mode = \
        trip_itin_filters.categorise_trip_ids_by_first_non_walk_mode(
            trip_results)
    means_by_first_non_walk_mode = {}
    for mode in otp_config.OTP_NON_WALK_MODES:
        if trips_by_first_non_walk_mode[mode]: 
            means_by_first_non_walk_mode[mode] = \
                calc_means(
                    trips_by_first_non_walk_mode[mode],
                    trips_by_id, trip_req_start_dts)
        else:
            means_by_first_non_walk_mode[mode] = None
    return means_by_first_non_walk_mode

def calc_means_by_first_non_walk_mode_multi(trip_results_by_graph,
        trips_by_id, trip_req_start_dts):

    trips_by_first_non_walk_mode = {}
    means_by_first_non_walk_mode = {}
    for graph_name, trip_results in trip_results_by_graph.iteritems():
        if not trip_results:
            trips_by_first_non_walk_mode[graph_name] = None
            means_by_first_non_walk_mode[graph_name] = None
            continue
        means_by_first_non_walk_mode[graph_name] = \
            calc_means_by_first_non_walk_mode(trip_results,
                trips_by_id, trip_req_start_dts)
    return means_by_first_non_walk_mode

def calc_print_mean_results_overall_summaries(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts, 
        description=None):

    means = {}
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        if trip_results:
            means[graph_name] = calc_means(
                trip_results, trips_by_id, trip_req_start_dts)
        else:
            means[graph_name] = None

    if description:
        extra_string = "(%s)" % description
    else:
        extra_string = ""

    print "Overall %s mean results for the %d trips were:" \
        % (extra_string, max(map(len, trip_results_by_graph.itervalues())))
    print_mean_results(means)
    return

def calc_print_mean_usage_by_mode(
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
    means_init_waits = {}
    means_tfer_waits = {}

    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        if not trip_results: continue
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
    
    if description:
        extra_string = " (on trips %s)" % description
    else:
        extra_string = ""
    print "\nVehicle usage totals by mode%s were:" % extra_string
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        if not trip_results: 
            print "(Graph %s had no results - skipping.)" % graph_name
            continue
        print "For graph %s:" % graph_name

        print "  mode, mean time (all trips), mean dist (all trips), "\
            "# trips used in, # legs, total dist (km), "\
            "mean dist/leg (m), mean in-vehicle speed (km/h)"
        for mode in otp_config.OTP_MODES:
            mode_legs_cnt = sum_legs_by_mode[graph_name][mode]
            if mode_legs_cnt:
                mode_time = means_modal_times[graph_name][mode]
                mode_dist = means_modal_dists[graph_name][mode]
                mode_in_trip_cnt = sum_modes_in_trips[graph_name][mode]
                mode_sum_dist = sum_modal_dists[graph_name][mode]
                mode_dist_leg = means_modal_dist_leg[graph_name][mode]
                mode_speed = means_modal_speeds[graph_name][mode]
                print "  %s, %s, %.1f m, %d, %d, %.2f km, %.1f m, %.2f," \
                    % (mode, mode_time, mode_dist, mode_in_trip_cnt, \
                       mode_legs_cnt, mode_sum_dist, mode_dist_leg, mode_speed)
            else:
                print "  %s, None, None, 0, 0, 0 km, None, None," % mode
        print "  initial wait, %s, " % means_init_waits[graph_name]
        print "  transfer wait, %s, " % means_tfer_waits[graph_name]
    print ""
    return

def calc_print_mean_results_by_first_non_walk_mode(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts,
        description=None):

    means_by_first_non_walk_mode = \
        calc_means_by_first_non_walk_mode_multi(
            trip_results_by_graph, trips_by_id, trip_req_start_dts)

    if description:
        extra_string = " (%s)" % description
    else:
        extra_string = ""
    print "\nTrip results%s: aggregated by first non-walk mode were:" % extra_string
    for graph_name in graph_names:
        print "For graph %s:" % graph_name
        trip_results = means_by_first_non_walk_mode[graph_name]
        if not trip_results: 
            print "(Graph %s had no results - skipping.)" % graph_name
            continue
        # TODO: Should be compact version ...    
        print_mean_results(means_by_first_non_walk_mode[graph_name],
            otp_config.OTP_NON_WALK_MODES)
        continue    
    return

def calc_save_mean_results_by_first_non_walk_mode(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts,
        description, output_file_base):

    means_by_first_non_walk_mode = \
        calc_means_by_first_non_walk_mode_multi(
            trip_results_by_graph, trips_by_id, trip_req_start_dts)

    for graph_name in graph_names:
        output_fname = output_file_base + "-%s.csv" % graph_name
        print "Saving mean results by first non-walk mode (%s) for graph "\
            "%s to file %s" \
            % (description, graph_name, output_fname)
        if not trip_results_by_graph[graph_name]:
            continue
        
        save_trip_result_means_to_csv(means_by_first_non_walk_mode[graph_name],
            ['mode'], output_fname,
            save_order=otp_config.OTP_NON_WALK_MODES)
    print ""
    return

def calc_means_by_agencies_used(trip_results, trips_by_id,
        trip_req_start_dts):
    trips_by_agencies_used = \
        trip_itin_filters.categorise_trips_by_agencies_used(trip_results)
    means_by_agencies_used = {}
    for agency_tuple, trip_itins in \
            trips_by_agencies_used.iteritems():
        means_by_agencies_used[agency_tuple] = \
            calc_means(trip_itins, trips_by_id, trip_req_start_dts)
    return means_by_agencies_used

def calc_means_by_agencies_used_multi(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_dts):
    trips_by_agencies_used = {}
    means_by_agencies_used = {}
    for graph_name in graph_names:
        # Further classify by agencies used
        trip_results = trip_results_by_graph[graph_name]
        if not trip_results: continue
        trips_by_agencies_used[graph_name] = \
            trip_itin_filters.categorise_trips_by_agencies_used(trip_results)
        means_by_agencies_used[graph_name] = {}
        for agency_tuple, trip_itins in \
                trips_by_agencies_used[graph_name].iteritems():
            means_by_agencies_used[graph_name][agency_tuple] = \
                calc_means(trip_itins, trips_by_id,
                    trip_req_start_dts)
    return means_by_agencies_used

def calc_print_mean_results_by_agencies_used(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts, 
        description=None):
    means_by_agencies_used = \
        calc_means_by_agencies_used(graph_names,
            trip_results_by_graph, trips_by_id, trip_req_start_dts)

    if description:
        extra_string = " (%s)" % description
    else:
        extra_string = ""
    print "\nTrip results%s: aggregated by agencies used in trips were:" \
        % extra_string
    for graph_name in graph_names:
        print "For graph %s:" % graph_name
        trip_results = trip_results_by_graph[graph_name]
        if not trip_results: 
            print "(Graph %s had no results - skipping.)" % graph_name
            continue
            
        agency_tups_and_means_sorted_by_spd = sorted(
            means_by_agencies_used[graph_name].iteritems(), 
            key = lambda x: x[1]['direct speed (kph)'])
        agency_tups_sorted_by_rev_spd = reversed(
            map(operator.itemgetter(0), agency_tups_and_means_sorted_by_spd))
            
        print_mean_results(means_by_agencies_used[graph_name],
            agency_tups_sorted_by_rev_spd)
        print ""
    return 

def save_mean_results_by_agencies_used(means_by_agencies_used, output_fname):
    means_by_agencies_used_strkeys = {}
    for ag_tup, vals in means_by_agencies_used.iteritems():
        strkey = ", ".join(ag_tup)
        means_by_agencies_used_strkeys[strkey] = vals

    # We want to stringify the agencies tuple, and 
    # sort these by speed (reversed)
    agency_strs_and_means_sorted_by_spd = sorted(
        means_by_agencies_used_strkeys.iteritems(), 
        key = lambda x: x[1]['direct speed (kph)'])
    agency_strs_sorted_by_rev_spd = reversed(
        map(operator.itemgetter(0), agency_strs_and_means_sorted_by_spd))
    save_trip_result_means_to_csv(means_by_agencies_used_strkeys,
        ['agencies used'], output_fname,
        save_order=agency_strs_sorted_by_rev_spd)
    return

def calc_save_mean_results_by_agencies_used(
        graph_names, trip_results_by_graph, trips_by_id, trip_req_start_dts, 
        description, output_file_base):
    means_by_agencies_used = \
        calc_means_by_agencies_used(graph_names,
            trip_results_by_graph, trips_by_id, trip_req_start_dts)
        
    for graph_name in graph_names:
        output_fname = output_file_base + "-%s.csv" % graph_name
        print "Saving mean results by agencies (%s) for graph %s: to file %s" \
            % (description, graph_name, output_fname)
        if not trip_results_by_graph[graph_name]:
            continue
        save_mean_results_by_agencies_used(means_by_agencies_used,
            output_fname)
    print ""
         
    return 
 
def calc_trip_info_by_OD_SLA(trip_itins, trips_by_id, trip_req_start_dts):
    tripsets_by_od_sla = trip_itin_filters.categorise_trip_results_by_od_sla(
        trip_itins, trips_by_id)
    means_by_od_sla = {}
    for o_sla, tripsets_by_dest_sla in tripsets_by_od_sla.iteritems():
        means_by_od_sla[o_sla] = {}
        for d_sla, trip_itins in tripsets_by_dest_sla.iteritems():
            means_by_od_sla[o_sla][d_sla] = calc_means(
                trip_itins, trips_by_id, trip_req_start_dts)
    return means_by_od_sla

def calc_save_trip_info_by_OD_SLA(trip_itins, trips_by_id, trip_req_start_dts,
        output_fname):
    means_by_od_sla = calc_trip_info_by_OD_SLA(trip_itins, trips_by_id, 
        trip_req_start_dts)
    save_trip_result_means_to_csv(means_by_od_sla,
        ['Origin SLA', 'Dest SLA'], output_fname)
    return means_by_od_sla

def calc_means_by_dep_times(trip_results, trips_by_id,
        trip_req_start_dts, dep_time_cats):
    means_by_deptime = {}
    for dep_time_cat, dt_info in dep_time_cats.iteritems():
        trip_results_for_dep_time_cat = \
            trip_itin_filters.get_results_in_dep_time_range(
                trip_results, trip_req_start_dts, dt_info)
        if trip_results_for_dep_time_cat:
            means_by_deptime[dep_time_cat] = \
                calc_means(trip_results_for_dep_time_cat, trips_by_id,
                    trip_req_start_dts)
        else:
            # In case there's no results in that time period
            means_by_deptime[dep_time_cat] = None
    return means_by_deptime

def calc_means_by_dep_times_multi(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_dts, dep_time_cats):
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
        trip_results = trip_results_by_graph[graph_name]
        if not trip_results:
            means_by_deptime[graph_name] = None
            continue
        means_by_deptime[graph_name] = calc_means_by_dep_times(
            trip_results, trips_by_id, trip_req_start_dts, dep_time_cats)
    return means_by_deptime

def calc_print_mean_results_by_dep_times(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_dts,
        dep_time_cats, description=None,
        dep_time_print_order=None ):

    means_by_deptime = calc_means_by_dep_times_multi(graph_names,
        trip_results_by_graph, trips_by_id, trip_req_start_dts, dep_time_cats)

    if description:
        extra_string = " (%s)" % description
    else:
        extra_string = ""

    print "\nMean results for the %d trips%s, by departure time period, were:" \
        % (max(map(len, trip_results_by_graph.itervalues())), extra_string)
    for graph_name in graph_names:
        print "For graph name '%s':" % graph_name
        if not trip_results_by_graph[graph_name]:
            print "(No results)."
            continue
        print_mean_results(means_by_deptime[graph_name], dep_time_print_order)
    return        

def calc_save_mean_results_by_dep_times(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_dts, dep_time_cats,
        description, output_file_base, dep_time_print_order=None ):

    means_by_deptime = calc_means_by_dep_times(graph_names,
        trip_results_by_graph, trips_by_id, trip_req_start_dts, dep_time_cats)

    for graph_name in graph_names:
        output_fname = output_file_base + "-%s.csv" % graph_name
        print "Saving mean results (%s) for graph %s: to file %s" \
            % (description, graph_name, output_fname)
        if not trip_results_by_graph[graph_name]:
            continue
        save_trip_result_means_to_csv(means_by_deptime[graph_name],
            ['Dep time cat.'], output_fname, save_order=dep_time_print_order)
    print ""
    return

########################

# Output header, input dict key, round func.
TRIP_MEAN_HDRS_OUTPUT = [
    ('n trips', 'n trips',
        lambda x: x),
    ('mean time (min)', 'total time', 
        lambda x: round(time_utils.get_total_mins(x), OUTPUT_ROUND_TIME_MIN)),
    ('mean init wait (min)', 'init wait',
        lambda x: round(time_utils.get_total_mins(x), OUTPUT_ROUND_TIME_MIN)),
    ('mean tfer wait (min)', 'tfer wait',
        lambda x: round(time_utils.get_total_mins(x), OUTPUT_ROUND_TIME_MIN)),
    ('mean direct spd (kph)', 'direct speed (kph)',
        lambda x: round(x, OUTPUT_ROUND_SPEED_KPH)),
    ('mean dist direct (km)', 'dist direct (km)',
        lambda x: round(x, OUTPUT_ROUND_DIST_KM)),
    ('mean dist trav (km)', 'dist travelled (km)',
        lambda x: round(x, OUTPUT_ROUND_DIST_KM)),
    ('mean walk dist (km)', 'walk dist (km)',
        lambda x: round(x, OUTPUT_ROUND_DIST_KM)),
    ('mean transfers', 'transfers',
        lambda x: round(x, OUTPUT_ROUND_TRANSFERS)),
    ]

def order_and_format_means_for_output(means_dict):
    means_ordered = [0] * len(TRIP_MEAN_HDRS_OUTPUT)
    for ii, mean_hdr_tuple in enumerate(TRIP_MEAN_HDRS_OUTPUT):
        val = means_dict[mean_hdr_tuple[1]]
        # Apply the rounding function.
        means_ordered[ii] = mean_hdr_tuple[2](val)
    return means_ordered

#def print_mean_results_short(mean_results_by_category, key_print_order=None):
        #print "  mean init waits, total trip times, trip overall speeds, "\
        #    "by agencies used (sorted by speed):"
        #for agency_tuple, means in \
        #        reversed(agency_tups_and_means_sorted_by_spd):
        #    if means:
        #        print "    %s: %s, %s, %.2f km/h (%d trips)" \
        #            % (agency_tuple, \
        #               means['init wait'],
        #               means['total time'],
        #               means['direct speed (kph)'],
        #               means['n trips'])
        #    else:
        #        print "    %s: None, None, None (0 trips)" % agency_tuple

# From the by first non-walk mode.
        #print "  mean init waits, total trip times, trip overall speeds:"
        #for mode in otp_config.OTP_NON_WALK_MODES:
        #    if counts_init_waits_by_mode[graph_name][mode]: 
        #        print "    %s: %s, %s, %.2f km/h (%d trips)" % (mode, \
        #            means_init_waits_by_mode[graph_name][mode],
        #            means_by_first_non_walk_mode[graph_name][mode]['total time'],
        #            means_by_first_non_walk_mode[graph_name][mode]['direct speed (kph)'],
        #            counts_init_waits_by_mode[graph_name][mode])
        #    else:
        #        print "    %s: None, None, None (0 trips)" % (mode)
        #print ""
  
def print_mean_results(mean_results_by_category, key_print_order=None):
    if key_print_order:
        keys = key_print_order
    else:
        keys = mean_results_by_category.keys()
        
    for key in keys:
        means = mean_results_by_category[key]
        if not means:
            print "  '%s': no results." % key
            continue     
        print "  '%s': %d trips, mean trip time %s, mean init wait %s, mean dist travelled "\
            "%.2fkm, direct speed %.2f km/h, "\
            "walk dist %.2fm, # of transfers %.1f" % \
             (key,
              means['n trips'],
              means['total time'],
              means['init wait'],
              means['dist travelled (km)'],
              means['direct speed (kph)'],
              means['walk dist (km)'] * 1000.0,
              means['transfers'])
    print ""
    return

def save_trip_result_means_to_csv(means_by_categories, cat_names,
        output_fname, save_order=None):
    """Save a group of mean value dicts to a CSV file.
    means_by_categories should be the headings you want for the categories
    in the dict."""
    if save_order:
        if len(cat_names) > 1:
            raise ValueError("Can't specify a save order if more than one "
                "depth of category in the output.")

    if sys.version_info >= (3,0,0):
        csv_file = open(output_fname, 'w', newline='', delimiter=';')
    else:
        csv_file = open(output_fname, 'wb')
    writer = csv.writer(csv_file, delimiter=';')

    hdrs_row = cat_names + map(operator.itemgetter(0), TRIP_MEAN_HDRS_OUTPUT)
    writer.writerow(hdrs_row)

    if len(cat_names) > 1:
        flattened_dict = misc_utils.flatten_dict(means_by_categories,
            max_levels=len(cat_names))
        output_dict = flattened_dict
        output_keys = output_dict.iterkeys()
    else:    
        output_dict = means_by_categories
        if not save_order:
            output_keys = output_dict.iterkeys()
        else:
            output_keys = save_order

    for key in output_keys:
        means=output_dict[key]
        if len(cat_names) > 1:
            cats_tuple = key
            out_row_base = list(cats_tuple)
        else:
            out_row_base = [key]
        means_ordered = order_and_format_means_for_output(means)
        out_row = out_row_base + means_ordered
        writer.writerow(out_row)
    csv_file.close()
    return 

#####################

def extract_trip_times_otp_format(trips_by_id, trip_req_start_dts,
        trip_itins_1, trip_itins_2):
    """A conversion function from a dict of TripItinerary's to just extract
    trip times, for use in compute_trip_result_comparison_stats."""
    trip_itins = [trip_itins_1, trip_itins_2]
    trip_times = [[], []]
    for trip_id, trip in trips_by_id.iteritems():
        for ii in range(2):
            if trip_id not in trip_itins[ii]:
                # This is OTP format for "trip didn't return valid result".
                trip_times[ii].append(-1)
            else:
                trip_start_dt = trip_req_start_dts[trip_id]
                ti = trip_itins[ii][trip_id]
                trip_time_s = ti.get_total_trip_sec(trip_start_dt)
                trip_times[ii].append(trip_time_s)
    return trip_times[0], trip_times[1]

MINUTE_BREAKS = [1, 10, 20, 30, 60, 180]

def compute_trip_result_comparison_stats(otp_curr_times, otp_new_times):
    otp_diffs = [curr - new for new, curr \
        in zip(otp_new_times, otp_curr_times)]
    st = {
        'total_trips' : len(otp_curr_times),
        'lost_trips' : 0,
        'added_trips' : 0,
        'valid_trips_both' : 0,
        'faster_trips' : 0,
        'slower_trips' : 0,
        'same_trips' : 0,
        'slower_total_change' : 0,
        'faster_total_change' : 0,
        'valid_total_curr' : 0,
        'valid_total_new' : 0,
        'valid_total_diff' : 0,
        'trips_in_range' : {}
        }
    for min_break in MINUTE_BREAKS:
        st['trips_in_range'][-min_break] = 0
        st['trips_in_range'][min_break] = 0
    st['trips_in_range']['-inf'] = 0
    st['trips_in_range']['inf'] = 0
        
    for ii, (otp_curr_t, otp_new_t, otp_diff) in enumerate(zip(otp_curr_times,
            otp_new_times, otp_diffs)):
        if otp_curr_t <= 0 and otp_new_t <= 0:
            # Trip is invalid in both.
            continue
        if otp_curr_t > 0 and otp_new_t <= 0:
            st['lost_trips'] += 1
        elif otp_curr_t <= 0 and otp_new_t > 0:
            st['added_trips'] += 1
        else:
            st['valid_trips_both'] += 1
            st['valid_total_curr'] += otp_curr_t 
            st['valid_total_new'] += otp_new_t
            st['valid_total_diff'] += otp_diff
            abs_diff_min = abs(otp_diff / 60.0)
            if otp_diff == 0:
                st['same_trips'] += 1
            elif otp_curr_t < otp_new_t: 
                st['slower_trips'] += 1
                st['slower_total_change'] += otp_diff
                range_found = False
                for min_break in MINUTE_BREAKS:
                    if abs_diff_min <= abs(min_break):
                        st['trips_in_range'][-min_break] += 1
                        range_found = True
                        break
                if range_found == False:
                    st['trips_in_range']["-inf"] += 1
            elif otp_new_t < otp_curr_t:
                st['faster_trips'] += 1
                st['faster_total_change'] += otp_diff
                range_found = False
                for min_break in MINUTE_BREAKS:
                    if abs_diff_min <= abs(min_break):
                        st['trips_in_range'][min_break] += 1
                        range_found = True
                        break
                if range_found == False:
                    st['trips_in_range']["inf"] += 1
    # Compute averages.
    if st['valid_trips_both'] > 0:
        st['avg_curr_min'] = \
            (st['valid_total_curr'] / float(st['valid_trips_both'])) / 60.0
        st['avg_new_min'] = \
            (st['valid_total_new'] / float(st['valid_trips_both'])) / 60.0
        st['avg_diff_min'] = \
            (st['valid_total_diff'] / float(st['valid_trips_both'])) / 60.0
        st['same_trips_pct'] = \
            st['same_trips'] / float(st['valid_trips_both']) * 100.0
        st['slower_trips_pct'] = \
            st['slower_trips'] / float(st['valid_trips_both']) * 100.0
        st['faster_trips_pct'] = \
            st['faster_trips'] / float(st['valid_trips_both']) * 100.0
    else:
        st['avg_curr_min'] = 0
        st['avg_new_min'] = 0
        st['avg_diff_min'] = 0
        st['same_trips_pct'] = 0
        st['slower_trips_pct'] = 0
        st['faster_trips_pct'] = 0
    if st['valid_total_curr']:
        st['avg_diff_perc'] = \
            st['valid_total_diff'] / float(st['valid_total_curr']) * 100.0
    else:        
        st['avg_diff_perc'] = 0
    if st['slower_trips']:
        st['avg_slower'] = st['slower_total_change'] / float(st['slower_trips'])
    else:
        st['avg_slower'] = 0
    if st['faster_trips']:          
        st['avg_faster'] = st['faster_total_change'] / float(st['faster_trips'])
    else:
        st['avg_faster'] = 0
    return st

def print_trip_result_comparison_stats(stats_dict):
    st = stats_dict
    print "Total trips:-"
    print " %d total, %d valid in both, %d only in first, %d only in second." % \
        (st['total_trips'], st['valid_trips_both'], \
         st['lost_trips'], st['added_trips'])
    print "Aggregate change:-"
    print " For trips valid in both, avg trip time changed from %.1f "\
        "minutes to %.1f minutes.\n" \
        " A change of %.1f min (%.2f%%)." \
        % (st['avg_curr_min'], st['avg_new_min'], \
           st['avg_diff_min'], st['avg_diff_perc'])
    print "Trip breakdown:"
    print "%5d trips (%.2f%%) of unchanged duration.\n"\
        "%5d trips (%.2f%%) were slower (avg change of %.1f sec (%.1f min)).\n"\
        "%5d trips (%.2f%%) were faster (avg change of %.1f sec (%.1f min))."\
        % (st['same_trips'], st['same_trips_pct'], \
           st['slower_trips'], st['slower_trips_pct'], \
           st['avg_slower'], st['avg_slower'] / 60.0, \
           st['faster_trips'], st['faster_trips_pct'], \
           st['avg_faster'], st['avg_faster'] / 60.0 )
    print "Detailed trip breakdown:"
    sign_word_pairs = [(-1, "slower"), (1, "faster")]
    for sign, speed_word in sign_word_pairs:
        prev_tval = 0
        for tval in MINUTE_BREAKS:
            trips_in_range = st['trips_in_range'][sign * tval]
            perc_in_range = trips_in_range / float(st['valid_trips_both']) * 100
            print "%5d trips (%5.2f%%) in range (%d,%d] mins %s." % \
                (trips_in_range, perc_in_range, prev_tval, tval, speed_word)
            prev_tval = tval
        inf_word = "-inf" if sign < 0 else "inf"
        trips_in_last_range = st['trips_in_range'][inf_word]
        print "%5d trips > %d mins %s." % \
            (trips_in_last_range, prev_tval, speed_word)
    print ""

#####################

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
        linester.AddPoint(*trip[Trip.ORIGIN])
        linester.AddPoint(*trip[Trip.DEST])

        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(linester)
        feature.SetField('TripId', str(trip_id))
        feature.SetField('DepTime', trip[Trip.START_DTIME].strftime('%H:%M:%S'))
        feature.SetField('OriginZ', trip[Trip.O_ZONE])
        feature.SetField('DestZ', trip[Trip.D_ZONE])
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

