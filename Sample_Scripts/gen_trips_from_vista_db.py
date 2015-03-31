#!/usr/bin/env python2

import os.path
from datetime import date

from osgeo import ogr, osr
import MySQLdb as mdb

from pyOTPA import Trip
from pyOTPA import trips_io
from pyOTPA.Trips_Generator.TripGenerator import VISTA_DB_TripGenerator
from pyOTPA.Trips_Generator import abs_zone_io
from pyOTPA.Trips_Generator.LocGenerator import WithinZoneLocGenerator
import pyOTPA.Trips_Generator.vic_planning_zones_info as pz_info
import pyOTPA.Trips_Generator.LocConstraintChecker as lc_checker

def main():
    # This number should make sure we get all VISTA trips.
    #N_TRIPS = 130000
    N_TRIPS = 20
    RANDOM_ORIGIN_SEED = 5
    RANDOM_DEST_SEED = 10

    #MELB_BBOX = ((144.765, -37.9), (145.36, -37.645))
    #origin_loc_gen = BasicRandomLocGenerator(RANDOM_ORIGIN_SEED, MELB_BBOX)
    #dest_loc_gen = BasicRandomLocGenerator(RANDOM_DEST_SEED, MELB_BBOX)

    #zone_polys_dict = TEST_ZONE_POLYS_DICT
    input_sla_fname = "/Users/Shared/GIS-Projects-General/ABS_Data/SLAs_Metro_Melb_Region.shp"
    input_ccd_fname = "/Users/Shared/GIS-Projects-General/ABS_Data/CCDs_Metro_Melb_Region.shp"
    PLANNING_ZONES_SHPFILE = '/Users/Shared/GIS-Projects-General/Vicmap_Data/AURIN/Victorian_Planning_Scheme_Zones-Vicmap_Planning-Melb/78c61513-7aea-4ba2-8ac6-b1578fdf999b.shp'
    STREETS_LANES_BUFFER_SHPFILE = '/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_Common_LargeFile_Archives/OSM/melbourne.osm2pgsql-shapefiles/melbourne.osm-line-streets_subset2.shp'
    # Value below in decimal degrees based on above, ~= 150m.
    BUFFER_DIST = 0.0015
    od_csv_fname = "/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_PTUA/WorkPackage_Notes/WPPTUA4-Integrating_upgrades_generate_analysis/ABS-Vista-Data/OD-all-morn.csv"

    sla_fname = os.path.expanduser(input_sla_fname)
    sla_shp = ogr.Open(sla_fname, 0)
    if sla_shp is None:
        print "Error, input SLA shape file given, %s , failed to open." \
            % (input_sla_fname)
        sys.exit(1)
    sla_lyr = sla_shp.GetLayer(0)  

    ccd_fname = os.path.expanduser(input_ccd_fname)
    ccd_shp = ogr.Open(ccd_fname, 0)
    if ccd_shp is None:
        print "Error, input CCD shape file given, %s , failed to open." \
            % (input_ccd_fname)
        sys.exit(1)
    ccd_lyr = ccd_shp.GetLayer(0)  

    trips_output_shpfilename = "./generated_trips/trips-vista_07-%d.shp" \
        % N_TRIPS

    sla_feats_dict = abs_zone_io.create_sla_name_map(sla_lyr)
    ccd_features_dict = abs_zone_io.create_ccd_code_map(ccd_lyr)

    # Try without planning zone constraint checks, for smaller CCDs,
    #  since for multiple trip purposes.
    #origin_constraint_checker_zone = \
    #    lc_checker.PlanningZoneLocConstraintChecker(
    #        PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_ZONES)
    #dest_constraint_checker_zone = \
    #    lc_checker.PlanningZoneLocConstraintChecker(
    #        PLANNING_ZONES_SHPFILE, pz_info.RESIDENTIAL_AND_EMPLOYMENT_ZONES,
    #        )
    origin_rd_dist_checker = \
        lc_checker.WithinBufferOfShapeLocConstraintChecker(
            STREETS_LANES_BUFFER_SHPFILE, BUFFER_DIST)
    dest_rd_dist_checker = \
        lc_checker.WithinBufferOfShapeLocConstraintChecker(
            STREETS_LANES_BUFFER_SHPFILE, BUFFER_DIST)

    origin_loc_gen = WithinZoneLocGenerator(RANDOM_ORIGIN_SEED,
        ccd_features_dict, 
        #[origin_constraint_checker_zone])
        #[origin_rd_dist_checker, origin_constraint_checker_zone])
        [origin_rd_dist_checker])
    dest_loc_gen = WithinZoneLocGenerator(RANDOM_DEST_SEED,
        ccd_features_dict, 
        #[dest_constraint_checker_zone])
        #[dest_rd_dist_checker, dest_constraint_checker_zone])
        [dest_rd_dist_checker])

    connection = mdb.connect('localhost', USER, PASS, 'vista07')

    trips_date_week_start = date(year=2015,month=3,day=2)

    metro_slas_of_interest = sla_feats_dict.keys()
    # Removing the metro SLAs that aren't relevant to PTUA's network
    # improvement project :- IE outer SLAs.
    outer_slas_to_remove = [
        "Greater Geelong (C) - Pt B",
        "Queenscliffe (B)",
        "Surf Coast (S) - East",
        "Surf Coast (S) - West",
        "Golden Plains (S) - South-East",
        "Greater Geelong (C) - Pt C",
        "Bellarine - Inner",
        "Corio - Inner",
        "Geelong",
        "Geelong West",
        "Newtown",
        "South Barwon - Inner",
        "Moorabool (S) - Ballan",
        "Macedon Ranges (S) - Romsey",
        "Macedon Ranges (S) Bal",
        "Mitchell (S) - South",
        "Cardinia (S) - South",
        "Yarra Ranges (S) - Central",
        "Baw Baw (S) - Pt B West",
        "Bass Coast (S) - Phillip Is.",
        "Bass Coast (S) Bal",
        "South Gippsland (S) - West",
        "French Island",
        "Cardinia (S) - North",
        ]
    for sla_name in outer_slas_to_remove:
        metro_slas_of_interest.remove(sla_name)
    trip_generator = VISTA_DB_TripGenerator(
        connection, origin_loc_gen, dest_loc_gen, N_TRIPS,
        trips_date_week_start, ccd_features_dict,
        skipped_modes = ['School Bus', 'Walking', 'Plane'],
        allowed_origin_slas = metro_slas_of_interest,
        allowed_dest_slas = metro_slas_of_interest,
        trip_min_dist_km = 0.5  # Ignore short walking trips.
        )

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
    connection.close()

    trips_io.save_trips_to_shp_file(trips_output_shpfilename, trips)
    print "... and saved to file %s." % trips_output_shpfilename

    sla_shp.Destroy()
    return

if __name__ == "__main__":
    main()
