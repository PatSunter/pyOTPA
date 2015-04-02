#!/usr/bin/env python2

import os.path
from datetime import datetime, time, timedelta
from optparse import OptionParser
from osgeo import ogr

from pyOTPA import otp_config
from pyOTPA import Trip
from pyOTPA import trips_io
from pyOTPA import trip_itins_io
from pyOTPA import trip_analysis
from pyOTPA import trip_filters
from pyOTPA import trip_itin_filters

ALL_TRIPS_DESC = "all_trips"

def exclude_slow_trips_long_walks(
        trips_by_id, trip_req_start_dts, trip_results):
    trip_ids_to_exclude = set()
    longest_walk_len_km = trip_itin_filters.DEFAULT_LONGEST_WALK_LEN_KM
    longest_trip_time = timedelta(hours=4)
    filter_desc_long = "filtered to remove trips with > %.1fkm walk legs "\
        "and those with calc time > %s" \
        % (longest_walk_len_km, longest_trip_time)
    filter_desc_short = "filtered"

    # Filter out trips that involved a very long walk:-
    # OTP still sometimes returns these where there is no alternative 
    # option, even if well above your specified max walk distance.
    trip_ids_long_walk = \
        trip_itin_filters.get_trip_ids_with_walk_leg_gr_than_dist_km(
            trip_results, longest_walk_len_km)
    trip_ids_to_exclude.update(trip_ids_long_walk)
    # Filter out trips that took a very long time - e.g. trips starting
    # on a Sunday where there is no service till the next day.
    trip_ids_long_time = \
        trip_itin_filters.get_trip_ids_with_total_time_gr_than(
            trip_results, trip_req_start_dts, longest_trip_time)
    trip_ids_to_exclude.update(trip_ids_long_time)

    trip_results_filtered = \
        Trip.get_trips_subset_by_ids_to_exclude(trip_results, 
            trip_ids_to_exclude)
    return trip_results_filtered, filter_desc_short, filter_desc_long

def trips_near_upgraded_networks(
        trips_by_id, trip_req_start_dts, trip_results, imp_network_stop_lyrs):

    buff_dist_m = 500
    filter_desc_long = "Trips starting and finishing within %dm "\
        "of the upgraded networks' stops (Trains, trams, smartbuses, "\
            "and selected regular buses)" % buff_dist_m
    filter_desc_short = "near_imp_nw"
    trip_result_ids_iter = trip_results.iterkeys()
    trip_ids_near_imp_route_stops = \
        trip_filters.get_trip_ids_near_network_stops(trips_by_id,
            imp_network_stop_lyrs, buff_dist_m, trip_result_ids_iter)
    trip_results_filtered = \
        Trip.get_trips_subset_by_ids(trip_results, 
            trip_ids_near_imp_route_stops)

    return trip_results_filtered, filter_desc_short, filter_desc_long

def process_one_graph_results(trips_by_id, trip_req_start_dts,
        output_base_dir, graph_name, dep_time_cats, dep_time_order,
        imp_network_stop_lyrs):
    """Split out into a separate function to save memory by processing each
    graph's results one at a time."""

    trip_results = {}
    descs_long = {}

    trip_results[ALL_TRIPS_DESC] = trip_itins_io.load_trip_itineraries(
        output_base_dir, [graph_name])[graph_name]
    descs_long[ALL_TRIPS_DESC] = "all trips"

    print "Calculating various means and other statistics for graph %s:" \
        % graph_name

    # Now apply various filters to the trip-set ...
    trip_results_filt, base_filtered_desc, filter_desc_long = \
        exclude_slow_trips_long_walks(
            trips_by_id, trip_req_start_dts, trip_results[ALL_TRIPS_DESC])
    trip_results[base_filtered_desc] = trip_results_filt
    descs_long[base_filtered_desc] = filter_desc_long
    trip_results_filt, near_imp_nw_desc, filter_desc_long = \
        trips_near_upgraded_networks(
            trips_by_id, trip_req_start_dts, trip_results[ALL_TRIPS_DESC],
            imp_network_stop_lyrs)
    trip_results[near_imp_nw_desc] = trip_results_filt
    descs_long[near_imp_nw_desc] = filter_desc_long

    result_descs = [ALL_TRIPS_DESC, base_filtered_desc, near_imp_nw_desc]
    trip_summary_results = {}
    means = {}
    usages = {}
    for desc in result_descs:
        trip_summary_results[desc] = {}
        means[desc] = {}
        usages[desc] = {}

    for desc in result_descs:
        if not trip_results[desc]: continue

        means[desc]['overall'] = trip_analysis.calc_means(
            trip_results[desc], trips_by_id, trip_req_start_dts)

        means[desc]['by_first_nonwalk_mode'] = \
            trip_analysis.calc_means_by_first_non_walk_mode(
                trip_results[desc], trips_by_id, trip_req_start_dts)

        means[desc]['by_agencies_used'] = \
            trip_analysis.calc_means_by_agencies_used(
                trip_results[desc], trips_by_id, trip_req_start_dts)

        means[desc]['by_deptime'] = \
            trip_analysis.calc_means_by_dep_times(
                trip_results[desc], trips_by_id, trip_req_start_dts,
                dep_time_cats)

        means[desc]['by_OD_SLA'] = \
            trip_analysis.calc_trip_info_by_OD_SLA(
                trip_results[desc], trips_by_id, trip_req_start_dts)

        #usages[filtered_desc]['by_mode_agency_route'] = \
        #    trip_analysis.calc_trip_info_by_mode_agency_route(
        #        trip_results[desc], trip_req_start_dts, output_fname)
        print "Saving info for individual routes to files:"
        output_fname = os.path.join(output_base_dir, 
            "route_totals-%s-%s.csv" % (desc, graph_name))
        print "For desc %s: to %s" % (desc, output_fname)
        trip_analysis.calc_save_trip_info_by_mode_agency_route(
            trip_results[desc], trip_req_start_dts, output_fname)

    print "...done calculating."

    print "Saving larger stat sets to files:"
    for desc in result_descs:
        print "For desc %s:" % (desc)
        output_fname = os.path.join(output_base_dir, 
            "means-%s-%s-%s.csv" % ('by_first_nonwalk_mode',
                graph_name, desc))
        print "  %s" % output_fname
        trip_analysis.save_trip_result_means_to_csv(
            means[desc]['by_first_nonwalk_mode'],
                ["mode"], output_fname)

        output_fname = os.path.join(output_base_dir, 
            "means-%s-%s-%s.csv" % ('by_agencies_used',
                graph_name, desc))
        print "  %s" % output_fname
        trip_analysis.save_mean_results_by_agencies_used(
            means[desc]['by_agencies_used'], output_fname)

        output_fname = os.path.join(output_base_dir, 
            "means-%s-%s-%s.csv" % ('by_deptime',
                graph_name, desc))
        print "  %s" % output_fname
        trip_analysis.save_trip_result_means_to_csv(
            means[desc]['by_deptime'],
                ['Dep time cat.'], output_fname, save_order=dep_time_order)

        output_fname = os.path.join(output_base_dir, 
            "means-%s-%s-%s.csv" % ('by_OD_SLA',
                graph_name, desc))
        print "  %s" % output_fname
        trip_analysis.save_trip_result_means_to_csv(means[desc]['by_OD_SLA'],
            ['Origin SLA', 'Dest SLA'], output_fname)
    print "...done saving."

    return trip_summary_results, means, usages, descs_long

def main():
    parser = OptionParser()
    parser.add_option('--results_base_dir', dest='results_base_dir',
        help="Base dir of trip results to analyse.")
    parser.add_option('--trips_shpfile', dest='trips_shpfile',
        help="Name of shapefile containing specified trips.")
    parser.add_option('--dep_times_csv', dest='dep_times_csv',
        help="Path of CSV file containing departure time categories "\
            "to sort into.")
    parser.add_option('--trips_date', dest='trips_date',
        help="Departure date of trips. Must be in a format of YYYY-MM-DD.")
    parser.add_option('--analyse_graphs', dest='analyse_graphs',
        help="(optional) if specified, only these graphs' results will be "\
            "loaded and analysed.")
    parser.add_option('--create_comparison_shpfile',
        dest='create_comparison_shpfile', 
        help="a pair of graph names you want to create a comparison "
            "shapefile, visualising travel times - separated by a , .")
    (options, args) = parser.parse_args()
    
    output_base_dir = options.results_base_dir
    if not output_base_dir:
        parser.print_help()
        parser.error("no provided output base dir.")
    if not os.path.isdir(output_base_dir):
        parser.print_help()
        parser.error("provided output base dir isn't a directory.")
    # Still load trip specification :- could be useful for checking for null
    # results etc.
    trips_shpfilename = options.trips_shpfile
    if not trips_shpfilename:
        parser.print_help()
        parser.error("no provided trips shpfile path.")
    #if not options.trips_date:
    #    parser.print_help()
    #    parser.error("No trip departure date provided.")
    trip_req_start_date = None
    dep_times_csv_fname = options.dep_times_csv
    if not dep_times_csv_fname or not os.path.exists(dep_times_csv_fname):
        parser.print_help()
        parser.error("No provided departure time categories CSV file.")
    if not os.path.exists(dep_times_csv_fname):
        parser.print_help()
        parser.error("Provided departure time categories CSV file %s "
            "doesn't exist." % dep_times_csv_fname)
    if options.trips_date:
        trips_date_str = options.trips_date
        try:
            trip_req_start_date = \
                datetime.strptime(trips_date_str, "%Y-%m-%d").date()
        except ValueError as e:
            parser.print_help()
            parser.error("Couldn't parse the trip start date you supplied, "
                "'%s'. Exception message was: %s" % (trips_date_str, e))
    comp_shp_graphs = None
    if options.create_comparison_shpfile:
        comp_shp_graphs = options.create_comparison_shpfile.split(',')[:2]
        if len(comp_shp_graphs) != 2:
            parser.print_help()
            parser.error("Error, the input for create_comparison_shpfile "
                "must be a comma-separated pair of result directory names.")
    if options.analyse_graphs:
        graph_names = options.analyse_graphs.split(',')
    else:    
        graph_names = trip_itins_io.read_graph_names(output_base_dir)

    dep_time_cats, dep_time_order = \
        trip_itin_filters.read_trip_deptime_categories(dep_times_csv_fname)

    trips_by_id, trips = \
        trips_io.read_trips_from_shp_file_otp_srs(
            trips_shpfilename)
    trip_req_start_dts = Trip.get_trip_req_start_dts(
        trips_by_id, trip_req_start_date)

    # Also create a separate filtered list of trips within a target distance
    # from the routes. 
    print "Loading improved network shapefiles for creating "\
        "subset of trip results near these networks' stops and "\
        "calculating trips subset near these..."
    # TODO: read in all these parameters, rather than hard-coding.
    train_stops_shp_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/Melbourne_GIS_NetworkDataWork/train_upgrades_extensions/output/melb-train-gtfs-2014_06-topology-stops-combined.shp"
    tram_stops_shp_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/Melbourne_GIS_NetworkDataWork/tram_upgrades_extensions/output/melb-tram-gtfs-2014_06-topology-stops-combined_auto_600.shp"
    smartbus_stops_shp_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/Melbourne_GIS_NetworkDataWork/bus_upgrades/output/metro-smartbus/melb-bus-gtfs-2014_06-metro-smartbus-topology-stops.shp"
    upg_bus_stops_shp_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/Melbourne_GIS_NetworkDataWork/bus_upgrades/output/metro-upgrade_to_smartbus-v2-20141115/melb-bus-gtfs-2014_06-metro-upgrade_to_smartbus-v2-20141115-topology-stops.shp"
    train_stops_shp = ogr.Open(train_stops_shp_fname)
    tram_stops_shp = ogr.Open(tram_stops_shp_fname)
    smartbus_stops_shp = ogr.Open(smartbus_stops_shp_fname)
    upg_bus_stops_shp = ogr.Open(upg_bus_stops_shp_fname)
    imp_network_stop_lyrs = map(lambda x: x.GetLayer(0),
        [train_stops_shp])#, tram_stops_shp, smartbus_stops_shp, upg_bus_stops_shp])
    print "...done."

    # Extract results, one graph at a time.
    means_by_graph = {}
    for graph_name in graph_names:
        trip_summary_results, means, usages, descs_long = \
            process_one_graph_results(
                trips_by_id, trip_req_start_dts, output_base_dir, graph_name,
                dep_time_cats, dep_time_order, imp_network_stop_lyrs)
        #trip_times_by_graph[graph_name] = trip_summary_results['total_times']
        means_by_graph[graph_name] = means
    subset_descs = means_by_graph.values()[0].keys()

    # print high-level summaries
    
    overall_means = {}
    for gn in graph_names:
        overall_means[gn] = means_by_graph[gn][ALL_TRIPS_DESC]['overall'] 
    print "Overall trip means by graph were:"
    trip_analysis.print_mean_results(overall_means)

    for desc in subset_descs:
        if desc == ALL_TRIPS_DESC: continue
        subset_means = {}
        for gn in graph_names:
            subset_means[gn] = means_by_graph[gn][desc]['overall'] 
        print "trip means for trip subset '%s' by graph were:" \
            % (descs_long[desc])
        trip_analysis.print_mean_results(subset_means)

    # TODO: re-enable
    #trip_analysis.calc_print_mean_usage_by_mode(
    #    trip_results_by_graph.keys(), trip_results_by_graph_filtered, 
    #    trips_by_id, trip_req_start_dts, 
    #    description=FILTERED_DESC)

    # TODO: re-enable.
    if False and comp_shp_graphs:
        graph_name_1, graph_name_2 = comp_shp_graphs
        comp_shpfilename = os.path.join(output_base_dir, 
            "%s-vs-%s.shp" % (graph_name_1, graph_name_2))
        trip_analysis.createTripsCompShapefile(trips_by_id, 
            (graph_name_1, graph_name_2),
            trip_req_start_dts,
            trip_results_by_graph[graph_name_1], 
            trip_results_by_graph[graph_name_2],
            comp_shpfilename)

        times_1, times_2 = trip_analysis.extract_trip_times_otp_format(
            trips_by_id, 
            trip_req_start_dts,
            trip_results_by_graph[graph_name_1], 
            trip_results_by_graph[graph_name_2])
        stats = trip_analysis.compute_trip_result_comparison_stats(
            times_1, times_2)
        #print "Overall stats comparing between graphs '%s' and '%s' as "\
        #    "follows:" % (graph_name_1, graph_name_2)
        #trip_analysis.print_trip_result_comparison_stats(stats)

        times_1, times_2 = trip_analysis.extract_trip_times_otp_format(
            trips_by_id, 
            trip_req_start_dts,
            trip_results_by_graph_near_imp_network_stops[graph_name_1], 
            trip_results_by_graph_near_imp_network_stops[graph_name_2])
        stats = trip_analysis.compute_trip_result_comparison_stats(
            times_1, times_2)
        #print "Stats comparing between graphs '%s' and '%s' - near improved "\
        #    "network stops:- as follows:" % (graph_name_1, graph_name_2)
        #trip_analysis.print_trip_result_comparison_stats(stats)

    # cleanup
    train_stops_shp.Destroy()
    tram_stops_shp.Destroy()
    smartbus_stops_shp.Destroy()
    upg_bus_stops_shp.Destroy()
    return

if __name__ == "__main__":
    main()
