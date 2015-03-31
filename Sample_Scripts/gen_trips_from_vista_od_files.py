#!/usr/bin/env python2

import os.path
from datetime import date

from osgeo import ogr

from pyOTPA import Trip
from pyOTPA import trips_io
from pyOTPA.Trips_Generator.TimeGenerator import ZoneBlockBasedTimeGenerator
from pyOTPA.Trips_Generator.TripGenerator import OD_Based_TripGenerator
from pyOTPA.Trips_Generator import abs_zone_io
from pyOTPA.Trips_Generator.LocGenerator import WithinZoneLocGenerator
import pyOTPA.Trips_Generator.vic_planning_zones_info as pz_info
import pyOTPA.Trips_Generator.LocConstraintChecker as lc_checker
import pyOTPA.Trips_Generator.od_reader_VISTA as od_reader

def get_trip_count_totals_per_od(od_counts_by_dep_time):
    od_counts = {}
    for od_pair, dep_time_counts in od_counts_by_dep_time.iteritems():
        od_counts[od_pair] = sum(dep_time_counts.itervalues())
    return od_counts

def main():
    # This number should make sure we get all VISTA trips.
    N_TRIPS = 2
    RANDOM_TIME_SEED = 5
    RANDOM_ORIGIN_SEED = 5
    RANDOM_DEST_SEED = 10

    input_sla_fname = "/Users/Shared/GIS-Projects-General/ABS_Data/SLAs_Metro_Melb_Region.shp"
    PLANNING_ZONES_SHPFILE = '/Users/Shared/GIS-Projects-General/Vicmap_Data/AURIN/Victorian_Planning_Scheme_Zones-Vicmap_Planning-Melb/78c61513-7aea-4ba2-8ac6-b1578fdf999b.shp'
    STREETS_LANES_BUFFER_SHPFILE = '/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_Common_LargeFile_Archives/OSM/melbourne.osm2pgsql-shapefiles/melbourne.osm-line-streets_subset2.shp'
    # Value below in decimal degrees based on above, ~= 150m.
    BUFFER_DIST = 0.0015
    od_csv_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/WorkPackage_Notes/WPPTUA4-Integrating_upgrades_generate_analysis/ABS-Vista-Data/OD-all-morn.csv"
    VISTA_SLAS_TO_IGNORE = ['Yarra Ranges (S) - Pt B']

    sla_fname = os.path.expanduser(input_sla_fname)
    sla_shp = ogr.Open(sla_fname, 0)
    if sla_shp is None:
        print "Error, input SLA shape file given, %s , failed to open." \
            % (input_sla_fname)
        sys.exit(1)
    sla_lyr = sla_shp.GetLayer(0)  

    trips_output_shpfilename = "./generated_trips/trips-vista_09-OD-%d.shp" \
        % N_TRIPS

    sla_feats_dict = abs_zone_io.create_sla_name_map(sla_lyr)

    origin_constraint_checker_zone = \
        lc_checker.PlanningZoneLocConstraintChecker(
            PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_ZONES)
    dest_constraint_checker_zone = \
        lc_checker.PlanningZoneLocConstraintChecker(
            PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_AND_EMPLOYMENT_ZONES)
    origin_rd_dist_checker = \
        lc_checker.WithinBufferOfShapeLocConstraintChecker(
            STREETS_LANES_BUFFER_SHPFILE, BUFFER_DIST)
    dest_rd_dist_checker = \
        lc_checker.WithinBufferOfShapeLocConstraintChecker(
            STREETS_LANES_BUFFER_SHPFILE, BUFFER_DIST)

    origin_loc_gen = WithinZoneLocGenerator(RANDOM_ORIGIN_SEED,
        sla_feats_dict, 
        [origin_rd_dist_checker, origin_constraint_checker_zone])
    dest_loc_gen = WithinZoneLocGenerator(RANDOM_DEST_SEED,
        sla_feats_dict, 
        [dest_rd_dist_checker, dest_constraint_checker_zone])

    od_counts_by_dep_time, origin_slas, dest_slas = \
        od_reader.read_od_trip_cnts_by_dep_hour(od_csv_fname,
            slas_to_ignore = VISTA_SLAS_TO_IGNORE)
    od_counts = get_trip_count_totals_per_od(od_counts_by_dep_time)
    time_gen = ZoneBlockBasedTimeGenerator(RANDOM_TIME_SEED,
        od_counts_by_dep_time)

    trip_generator = OD_Based_TripGenerator(
        time_gen, od_counts, origin_loc_gen, dest_loc_gen, 
        N_TRIPS)

    trip_generator.initialise()

    trips = []
    for trip_i in range(N_TRIPS):
        trip = trip_generator.gen_next()
        if not trip: break
        trips.append(trip)
        Trip.print_trip(trip)

    print "Generated %d trips." % len(trips)
    #print "Origin SLAs were as follows:"
    #for sla in origin_slas: print sla
    #print "Dest SLAs were as follows:"
    #for sla in dest_slas: print sla

    trip_generator.cleanup()

    trips_io.save_trips_to_shp_file(trips_output_shpfilename, trips)
    print "... and saved to file %s." % trips_output_shpfilename

    sla_shp.Destroy()
    return

if __name__ == "__main__":
    main()
