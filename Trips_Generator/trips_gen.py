#!/usr/bin/env python2

import os.path

from osgeo import ogr, osr

import TimeGenerator
import LocGenerator
import TripGenerator

TRIP_LYR_NAME = "trips"
TRIP_ID_FIELD = "id"
TRIP_ORIGIN_SLA_FIELD = "orig_sla"
TRIP_DEST_SLA_FIELD = "dest_sla"
TRIP_DEP_TIME_FIELD = "dep_time"

def save_trips_to_shp_file(filename, trips, trips_srs, output_srs):
    if os.path.exists(filename):
        os.unlink(filename)    
    driver = ogr.GetDriverByName("ESRI Shapefile")
    trips_shp_file = driver.CreateDataSource(filename)
    trips_lyr = trips_shp_file.CreateLayer(TRIP_LYR_NAME, output_srs, ogr.wkbLineString)
    trips_lyr.CreateField(ogr.FieldDefn(TRIP_ID_FIELD, ogr.OFTInteger))
    field = ogr.FieldDefn(TRIP_ORIGIN_SLA_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)
    field = ogr.FieldDefn(TRIP_DEST_SLA_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)
    field = ogr.FieldDefn(TRIP_DEP_TIME_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)
    transform = osr.CoordinateTransformation(trips_srs, output_srs)

    for trip_cnt, trip in enumerate(trips):
        trip_feat = ogr.Feature(trips_lyr.GetLayerDefn())
        trip_geom = ogr.Geometry(ogr.wkbLineString) 
        trip_geom.AddPoint(*trip[0].GetPoint(0))
        trip_geom.AddPoint(*trip[1].GetPoint(0))
        trip_geom.Transform(transform)
        trip_feat.SetGeometry(trip_geom)
        trip_feat.SetField(TRIP_ID_FIELD, trip_cnt)
        trip_feat.SetField(TRIP_ORIGIN_SLA_FIELD, trip[3])
        trip_feat.SetField(TRIP_DEST_SLA_FIELD, trip[4])
        trip_feat.SetField(TRIP_DEP_TIME_FIELD, trip[2].strftime("%H:%M"))
        trips_lyr.CreateFeature(trip_feat)
        trip_feat.Destroy()
    trips_shp_file.Destroy()
    return

SLA_NAME_FIELD = "SLA_NAME06"

def populate_zone_polys_dict_from_layer(sla_lyr):
    polys_dict = {}
    for sla_shp in sla_lyr:
        sla_name = sla_shp.GetField(SLA_NAME_FIELD)       
        sla_geom = sla_shp.GetGeometryRef()
        polys_dict[sla_name] = sla_shp
    return polys_dict

TEST_OD_COUNTS = {
    ("A", "A"): 254,
    ("A", "B"): 2345,
    ("A", "C"): 0,
    ("B", "A"): 43,
    ("B", "B"): 4356,
    ("B", "C"): 500,
    ("C", "A"): 23,
    ("C", "B"): 1231,
    ("C", "C"): 581,
    }

a_geom = ogr.Geometry(ogr.wkbLinearRing)
a_geom.AddPoint(144.765, -37.9)
a_geom.AddPoint(144.865, -37.9)
a_geom.AddPoint(144.865, -37.8)
a_geom.AddPoint(144.825, -37.85)
a_geom.AddPoint(144.8, -37.9)
a_geom.AddPoint(144.765, -37.9)
a_poly = ogr.Geometry(ogr.wkbPolygon)
a_poly.AddGeometry(a_geom)

b_geom = ogr.Geometry(ogr.wkbLinearRing)
b_geom.AddPoint(145.0, -37.70)
b_geom.AddPoint(145.05, -37.70)
b_geom.AddPoint(145.05, -37.60)
b_geom.AddPoint(145.0, -37.60)
b_geom.AddPoint(145.0, -37.70)
b_poly = ogr.Geometry(ogr.wkbPolygon)
b_poly.AddGeometry(b_geom)

c_geom = ogr.Geometry(ogr.wkbLinearRing)
c_geom.AddPoint(145.2, -37.65)
c_geom.AddPoint(145.3, -37.65)
c_geom.AddPoint(145.25, -37.68)
c_geom.AddPoint(145.2, -37.65)
c_poly = ogr.Geometry(ogr.wkbPolygon)
c_poly.AddGeometry(c_geom)

TEST_ZONE_POLYS_DICT = {
    "A": a_poly,
    "B": b_poly,
    "C": c_poly,
    }

TEST_OD_COUNTS_SLAS = {
    ("Melton (S) - East", "Melton (S) - East"): 254,
    ("Melton (S) - East", "Melbourne (C) - Inner"): 2345,
    ("Melton (S) - East", "Nillumbik (S) - South-West"): 0,
    ("Melbourne (C) - Inner", "Melton (S) - East"): 43,
    ("Melbourne (C) - Inner", "Melbourne (C) - Inner"): 4356,
    ("Melbourne (C) - Inner", "Nillumbik (S) - South-West"): 500,
    ("Nillumbik (S) - South-West", "Melton (S) - East"): 233,
    ("Nillumbik (S) - South-West", "Melbourne (C) - Inner"): 1231,
    ("Nillumbik (S) - South-West", "Nillumbik (S) - South-West"): 581,
    }

def main():
    N_TRIPS = 100
    RANDOM_TIME_SEED = 5
    RANDOM_ORIGIN_SEED = 5
    RANDOM_DEST_SEED = 10
    OUTPUT_EPSG=4326

    #MELB_BBOX = ((144.765, -37.9), (145.36, -37.645))
    #origin_loc_gen = BasicRandomLocGenerator(RANDOM_ORIGIN_SEED, MELB_BBOX)
    #dest_loc_gen = BasicRandomLocGenerator(RANDOM_DEST_SEED, MELB_BBOX)

    #zone_polys_dict = TEST_ZONE_POLYS_DICT
    input_sla_fname = "/Users/Shared/GIS-Projects-General/ABS_Data/SLAs_Metro_Melb_Region.shp"
    sla_fname = os.path.expanduser(input_sla_fname)
    sla_shp = ogr.Open(sla_fname, 0)
    if sla_shp is None:
        print "Error, input SLA shape file given, %s , failed to open." \
            % (input_sla_fname)
        sys.exit(1)
    sla_lyr = sla_shp.GetLayer(0)  
    zone_polys_dict = populate_zone_polys_dict_from_layer(sla_lyr)

    origin_loc_gen = LocGenerator.WithinZoneLocGenerator(RANDOM_ORIGIN_SEED,
        zone_polys_dict, None)
    dest_loc_gen = LocGenerator.WithinZoneLocGenerator(RANDOM_DEST_SEED,
        zone_polys_dict, None)

    random_time_gen = TimeGenerator.RandomTimeGenerator(RANDOM_TIME_SEED)

    od_counts = TEST_OD_COUNTS_SLAS

    trip_generator = TripGenerator.OD_Based_TripGenerator(random_time_gen, od_counts,
        origin_loc_gen, dest_loc_gen, N_TRIPS)

    trips = []
    trip = trip_generator.gen_next()
    for trip_i in range(N_TRIPS):
        trip = trip_generator.gen_next()
        if not trip: break
        trips.append(trip)
        print "%f,%f to %f,%f at %s ('%s'->'%s')" % (trip[0].GetX(), trip[0].GetY(), \
            trip[1].GetX(), trip[1].GetY(), trip[2], trip[3], trip[4])
    print "Generated %d trips." % len(trips)

    trips_srs = sla_lyr.GetSpatialRef()
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(OUTPUT_EPSG)
    save_trips_to_shp_file("./output/trips.shp", trips, trips_srs, output_srs)

    sla_shp.Destroy()
    return

if __name__ == "__main__":
    main()
