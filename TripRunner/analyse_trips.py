#!/usr/bin/env python2

import os.path
from datetime import date, datetime
from optparse import OptionParser
from datetime import time

import Trips_Generator.trips_io
import trip_itins_io
import otp_config
import trip_analysis

def main():
    parser = OptionParser()
    parser.add_option('--results_base_dir', dest='results_base_dir',
        help='Base dir of trip results to analyse.')
    parser.add_option('--trips_shpfile', dest='trips_shpfile',
        help='Name of shapefile containing specified trips.')
    parser.add_option('--trips_date', dest='trips_date',
        help='Departure date of trips. Must be in a format of YYYY-MM-DD.')
    parser.add_option('--analyse_graphs', dest='analyse_graphs',
        help="(optional) if specified, only these graphs' results will be "
            "loaded and analysed.")
    parser.add_option('--create_comparison_shpfile',
        dest='create_comparison_shpfile', help='a pair of graph names you '\
            'want to create a comparison shapefile, visualising travel '\
            'times - separated by a , .')
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
    graph_names = None # Means graphs will be inferred from subdirectiries.
    if options.analyse_graphs:
        graph_names = options.analyse_graphs.split(',')

    trips_by_id, trips = \
        Trips_Generator.trips_io.read_trips_from_shp_file_otp_srs(
            trips_shpfilename)
    trip_req_start_dts = trip_analysis.get_trip_req_start_dts(
        trips_by_id, trip_req_start_date)

    trip_results_by_graph = trip_itins_io.load_trip_itineraries(
        output_base_dir, graph_names)

    # Now apply various filters to the trip-set ...
    def_desc = "all trips"
    filtered_desc = "filtered to remove long walk legs"
    longest_walk_len_km = trip_analysis.DEFAULT_LONGEST_WALK_LEN_KM
    trip_results_by_graph_filtered = {}
    for graph_name in trip_results_by_graph.keys():
        trip_results = trip_results_by_graph[graph_name]
        trip_ids_long_walk = \
            trip_analysis.get_trip_ids_with_walk_leg_gr_than_dist_km(
                trip_results, longest_walk_len_km)
        trip_results_by_graph_filtered[graph_name] = \
            trip_analysis.get_trips_subset_by_ids_to_exclude(trip_results, 
                trip_ids_long_walk)

    # Initially print high-level summaries
    trip_analysis.calc_print_mean_results_overall_summaries(
        trip_results_by_graph.keys(), trip_results_by_graph, 
        trips_by_id, trip_req_start_dts, description=def_desc)

    trip_analysis.calc_print_mean_results_overall_summaries(
        trip_results_by_graph.keys(), trip_results_by_graph_filtered, 
        trips_by_id, trip_req_start_dts, description=filtered_desc)

    # Print further, more advanced analysis just on the filtered trips for the
    # moment.
    trip_analysis.calc_print_mean_results_agg_by_mode_agency(
        trip_results_by_graph.keys(), trip_results_by_graph_filtered, 
        trips_by_id, trip_req_start_dts, 
        description=filtered_desc)

    # TODO:- really should be reading these in from CSV - and saving results
    # likewise.
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

    trip_analysis.calc_print_mean_results_by_dep_times(
        trip_results_by_graph.keys(), trip_results_by_graph, 
        trips_by_id, trip_req_start_dts, dep_time_cats, 
        description=def_desc,
        dep_time_print_order=dep_time_print_order)

    trip_analysis.calc_print_mean_results_by_dep_times(
        trip_results_by_graph.keys(), trip_results_by_graph_filtered, 
        trips_by_id, trip_req_start_dts, dep_time_cats, 
        description=filtered_desc,
        dep_time_print_order=dep_time_print_order)

    print "Saving info for individual routes (on filtered trips) to files:"
    for graph_name in trip_results_by_graph.keys():
        output_fname = os.path.join(output_base_dir, 
            "route_totals-%s.csv" % graph_name)
        print "For graph %s: to %s" % (graph_name, output_fname)
        trip_analysis.calc_print_trip_info_by_mode_agency_route(
            trip_results_by_graph_filtered[graph_name], output_fname)

    if comp_shp_graphs:
        graph_name_1, graph_name_2 = comp_shp_graphs
        comp_shpfilename = os.path.join(output_base_dir, 
            "%s-vs-%s.shp" % (graph_name_1, graph_name_2))
        trip_analysis.createTripsCompShapefile(trips_by_id, 
            (graph_name_1, graph_name_2),
            trip_req_start_dts,
            trip_results_by_graph[graph_name_1], 
            trip_results_by_graph[graph_name_2],
            comp_shpfilename)
    return

if __name__ == "__main__":
    main()
