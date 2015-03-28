#!/usr/bin/env python2

import os.path
from datetime import date, datetime, time, timedelta
from optparse import OptionParser
from osgeo import ogr

import Trips_Generator.trips_io
import trip_itins_io
import otp_config
import trip_analysis
import trip_filters

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
    longest_walk_len_km = trip_filters.DEFAULT_LONGEST_WALK_LEN_KM
    longest_trip_time = timedelta(hours=4)
    filtered_desc = "filtered to remove trips with > %.1fkm walk legs and " \
        "those with calc time > %s" \
        % (longest_walk_len_km, longest_trip_time)
    trip_results_by_graph_filtered = {}
    for graph_name in trip_results_by_graph.keys():
        trip_results = trip_results_by_graph[graph_name]
        trip_ids_to_exclude = set()
        # Filter out trips that involved a very long walk:-
        # OTP still sometimes returns these where there is no alternative 
        # option, even if well above your specified max walk distance.
        trip_ids_long_walk = \
            trip_filters.get_trip_ids_with_walk_leg_gr_than_dist_km(
                trip_results, longest_walk_len_km)
        trip_ids_to_exclude.update(trip_ids_long_walk)
        # Filter out trips that took a very long time - e.g. trips starting
        # on a Sunday where there is no service till the next day.
        trip_ids_long_time = \
            trip_filters.get_trip_ids_with_total_time_gr_than(
                trip_results, trip_req_start_dts, longest_trip_time)
        trip_ids_to_exclude.update(trip_ids_long_time)
        trip_results_by_graph_filtered[graph_name] = \
            trip_analysis.get_trips_subset_by_ids_to_exclude(trip_results, 
                trip_ids_to_exclude)

    # Also create a separate filtered list of trips within a target distance
    # from the routes.
    print "Loading improved network shapefiles for creating "\
        "subset of trip results near these networks' stops and "\
        "calculating trips subset near these..."
    buff_dist_m = 500
    near_upgraded_routes_desc = "Trips starting and finishing within %dm "\
        "of the upgraded networks' stops (Trains, trams, smartbuses, and selected "\
        "regular buses)" % buff_dist_m
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
    trip_results_by_graph_near_imp_network_stops = {}
    for graph_name in trip_results_by_graph.keys():
        trip_results = trip_results_by_graph[graph_name] 
        trip_result_ids_iter = trip_results.iterkeys()
        trip_ids_near_imp_route_stops = \
            trip_filters.get_trip_ids_near_network_stops(trips_by_id,
                imp_network_stop_lyrs, buff_dist_m, trip_result_ids_iter)
        trip_results_by_graph_near_imp_network_stops[graph_name] = \
            trip_analysis.get_trips_subset_by_ids(trip_results, 
                trip_ids_near_imp_route_stops)
    print "...done."

    # Initially print high-level summaries
    trip_analysis.calc_print_mean_results_overall_summaries(
        trip_results_by_graph.keys(), trip_results_by_graph, 
        trips_by_id, trip_req_start_dts, description=def_desc)

    trip_analysis.calc_print_mean_results_overall_summaries(
        trip_results_by_graph.keys(), trip_results_by_graph_filtered, 
        trips_by_id, trip_req_start_dts, description=filtered_desc)

    trip_analysis.calc_print_mean_results_overall_summaries(
        trip_results_by_graph.keys(),
        trip_results_by_graph_near_imp_network_stops,
        trips_by_id, trip_req_start_dts,
        description=near_upgraded_routes_desc)

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
        trip_analysis.calc_save_trip_info_by_mode_agency_route(
            trip_results_by_graph_filtered[graph_name],
            trip_req_start_dts, output_fname)

    print "Saving info by trip O-D SLA to files:"
    for graph_name in trip_results_by_graph.keys():
        output_fname = os.path.join(output_base_dir, 
            "totals-by-SLAs-%s.csv" % graph_name)
        print "For graph %s: to %s" % (graph_name, output_fname)
        trip_analysis.calc_save_trip_info_by_OD_SLA(
            trip_results_by_graph_filtered[graph_name], trips_by_id,
            trip_req_start_dts, output_fname)

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

    # cleanup
    train_stops_shp.Destroy()
    tram_stops_shp.Destroy()
    smartbus_stops_shp.Destroy()
    upg_bus_stops_shp.Destroy()
    return

if __name__ == "__main__":
    main()
