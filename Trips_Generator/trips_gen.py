#!/usr/bin/env python2

import os.path
from datetime import time
from osgeo import ogr, osr

import TimeGenerator
import LocGenerator
import LocConstraintChecker
import TripGenerator
import trips_io
import sla_io
import vic_planning_zones_info as pz_info
import test_data

def main():
    N_TRIPS = 50
    RANDOM_TIME_SEED = 5
    RANDOM_ORIGIN_SEED = 5
    RANDOM_DEST_SEED = 10
    OUTPUT_EPSG=4326

    #MELB_BBOX = ((144.765, -37.9), (145.36, -37.645))
    #origin_loc_gen = BasicRandomLocGenerator(RANDOM_ORIGIN_SEED, MELB_BBOX)
    #dest_loc_gen = BasicRandomLocGenerator(RANDOM_DEST_SEED, MELB_BBOX)

    #zone_polys_dict = TEST_ZONE_POLYS_DICT
    input_sla_fname = "/Users/Shared/GIS-Projects-General/ABS_Data/SLAs_Metro_Melb_Region.shp"
    PLANNING_ZONES_SHPFILE = '/Users/Shared/GIS-Projects-General/Vicmap_Data/AURIN/Victorian_Planning_Scheme_Zones-Vicmap_Planning-Melb/78c61513-7aea-4ba2-8ac6-b1578fdf999b.shp'

    sla_fname = os.path.expanduser(input_sla_fname)
    sla_shp = ogr.Open(sla_fname, 0)
    if sla_shp is None:
        print "Error, input SLA shape file given, %s , failed to open." \
            % (input_sla_fname)
        sys.exit(1)
    sla_lyr = sla_shp.GetLayer(0)  

    trips_output_shpfilename = "./output/trips.shp"

    zone_polys_dict = sla_io.populate_zone_polys_dict_from_layer(sla_lyr)

    # This determines if we're happy for locations to be generated in the same
    # SRS as the SLAs. If not, we can use something different.
    loc_srs = sla_lyr.GetSpatialRef()

    origin_constraint_checker = \
        LocConstraintChecker.PlanningZoneLocConstraintChecker(
            PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_ZONES, loc_srs)
    dest_constraint_checker = \
        LocConstraintChecker.PlanningZoneLocConstraintChecker(
            PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_AND_EMPLOYMENT_ZONES,
            loc_srs)

    origin_loc_gen = LocGenerator.WithinZoneLocGenerator(RANDOM_ORIGIN_SEED,
        zone_polys_dict, origin_constraint_checker)
    dest_loc_gen = LocGenerator.WithinZoneLocGenerator(RANDOM_DEST_SEED,
        zone_polys_dict, dest_constraint_checker)

    od_counts = {}
    for od_pair, dep_time_counts in \
            test_data.TEST_OD_COUNTS_SLAS_TIMES.iteritems():
        od_counts[od_pair] = sum(dep_time_counts.itervalues())
    time_gen = TimeGenerator.ZoneBlockBasedTimeGenerator(RANDOM_TIME_SEED,
        test_data.TEST_OD_COUNTS_SLAS_TIMES)

    trip_generator = TripGenerator.OD_Based_TripGenerator(time_gen, od_counts,
        origin_loc_gen, dest_loc_gen, N_TRIPS)

    trip_generator.initialise()

    trips = []
    trip = trip_generator.gen_next()
    for trip_i in range(N_TRIPS):
        trip = trip_generator.gen_next()
        if not trip: break
        trips.append(trip)
        print "%f,%f to %f,%f at %s ('%s'->'%s')" \
            % (trip[0].GetX(), trip[0].GetY(), \
               trip[1].GetX(), trip[1].GetY(), trip[2], trip[3], trip[4])
    print "Generated %d trips." % len(trips)

    trip_generator.cleanup()

    trips_srs = sla_lyr.GetSpatialRef()
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(OUTPUT_EPSG)
    trips_io.save_trips_to_shp_file(trips_output_shpfilename,
        trips, trips_srs, output_srs)

    sla_shp.Destroy()
    return

if __name__ == "__main__":
    main()
