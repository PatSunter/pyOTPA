#!/usr/bin/env python2

import sys
import os.path
import json
from datetime import datetime, date, time
from osgeo import osr

import otp_config
import otp_router
import trip_itins_io
import Trips_Generator.trips_io

def main():
    SERVER_URL = 'http://130.56.248.56'
    # See RoutingRequest.java in OTP for comments on each of these.
    ROUTING_PARAMS = {
        'arriveBy':'false',
        'mode':'TRANSIT,WALK',
        'maxTransfers':4,
        #'maxWalkDistance':4000,
        'maxWalkDistance':1000,
        #'maxWalkDistance':200,
        'clampInitialWait':0,
        'walkSpeed':1.38, # Default for OTP, also seems quite close to Google
        # See
        # http://www.quora.com/Google-Maps/What-is-the-assumed-walking-speed-in-Google-Mapss-time-estimates
        # for more on Google walk speed
        #parameter rep. ratio of how much worse walking is than waiting.
        # Does have an impact, closer to 1.0 will be more 'walk-like' round
        # origin, but seems to mean missing some possible places at the end.
        'waitReluctance':0.95,   # Default is 0.95
        'walkReluctance':1.01, 
        'walkBoardCost':30, # Suggsted by Albert Steiner to reduce disutility
          # of transfers. Default is 60 * 5 - ~5 minutes??
        'bikeBoardCost':30, # Default is 60 * 10 = 600.  
        'transferPenalty':0, # Default 0. Apparently can be an "extra" penalty 
          # above and beyond walkBoardCost and bikeBoardCost?
    }

    GRAPH_SPECS = {
        'PTV':'MelbTrainTramBus-2014_06-metro_bus',
        'BZE':'MelbTrainTramBus-BZE-autostops-withcongestion-WithMotorways-updated-20140724',
        'PTUA':'MelbTrainTramBus-PTUA-add_upgraded_extended_trains_upgraded_extended_auto_600_trams_upgraded_buses-v2-20141115',
        }

    trip_req_start_date = date(year=2015,month=2,day=16)

    #trip_req_start_time = time(11,45)
    #origin_lon_lat = (144.876791,-37.749236) 
    #dest_lon_lat = (145.091024,-37.897849)
    #route_single_trip_multi_graphs_print_stats(SERVER_URL, ROUTING_PARAMS,
    #    GRAPH_SPECS, trip_req_start_date, trip_req_start_time,
    #    origin_lon_lat, dest_lon_lat)

    #trips_shpfilename = "/Users/Shared/SoftwareDev/UrbanModelling-GIS/OSSTIP/OTP-Routing-Tools/Trips_Generator/output/trips-with_roads_0015-10000.shp"
    trips_shpfilename = "/Users/Shared/SoftwareDev/UrbanModelling-GIS/OSSTIP/OTP-Routing-Tools/Trips_Generator/output/trips-bad-5.shp"
    trips_set_name = "%s-walk_%s" % \
        (os.path.splitext(os.path.basename(trips_shpfilename))[0],
         ROUTING_PARAMS['maxWalkDistance'])
    output_base_dir = "./output/%s" % trips_set_name

    otp_router_srs = osr.SpatialReference()
    otp_router_srs.ImportFromEPSG(otp_config.OTP_ROUTER_EPSG)
    trips_by_id, trips = Trips_Generator.trips_io.read_trips_from_shp_file(
        trips_shpfilename, otp_router_srs)

    print "\nGoing to request OTP server at %s to route %d trips, defined in "\
        "shpfile %s, with start date %s, and routing params as follows:\n%s" \
        % (SERVER_URL, len(trips), trips_shpfilename, trip_req_start_date, 
           ROUTING_PARAMS)

    save_incrementally = True

    trip_results_by_graph = otp_router.route_trip_set_on_graphs(SERVER_URL,
        ROUTING_PARAMS,
        GRAPH_SPECS, trip_req_start_date, trips, trips_by_id,
        output_base_dir, save_incrementally, resume_existing=True)

    print "\nFinished routing all requested trips from shpfile %s ." \
        % trips_shpfilename
    if not save_incrementally:
        trip_itins_io.save_trip_itineraries(output_base_dir, trip_results_by_graph)
    else:
        print "\nResults already saved in subdirs of output directory %s ." \
            % output_base_dir
    return

if __name__ == "__main__":
    main()
