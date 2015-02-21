#!/usr/bin/env python2

import os.path
from datetime import date, datetime
from osgeo import osr
from optparse import OptionParser

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
    if not options.trips_date:
        parser.print_help()
        parser.error("No trip departure date provided.")
    trips_date_str = options.trips_date
    try:
        trip_req_start_date = datetime.strptime(trips_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        parser.print_help()
        parser.error("Couldn't parse the trip start date you supplied, "
            "'%s'. Exception message was: %s" % (trips_date_str, e))

    graph_names = None # Means graphs will be inferred from subdirectiries.

    otp_router_srs = osr.SpatialReference()
    otp_router_srs.ImportFromEPSG(otp_config.OTP_ROUTER_EPSG)
    trips_by_id, trips = Trips_Generator.trips_io.read_trips_from_shp_file(
        trips_shpfilename, otp_router_srs)

    trip_results_by_graph = trip_itins_io.load_trip_itineraries(output_base_dir,
        graph_names)
    trip_analysis.calc_print_mean_results(trip_results_by_graph.keys(),
        trip_results_by_graph, trips_by_id, trip_req_start_date)
    return

if __name__ == "__main__":
    main()
