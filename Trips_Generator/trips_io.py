
import os, os.path
from datetime import datetime, time
from osgeo import ogr, osr

TRIP_LYR_NAME = "trips"
TRIP_ID_FIELD = "id"
TRIP_ORIGIN_SLA_FIELD = "orig_sla"
TRIP_DEST_SLA_FIELD = "dest_sla"
TRIP_DEP_TIME_FIELD = "dep_time"
TIME_OUTPUT_STR_FORMAT = "%H:%M"

def save_trips_to_shp_file(filename, trips, trips_srs, output_srs):
    if os.path.exists(filename):
        os.unlink(filename)    
    driver = ogr.GetDriverByName("ESRI Shapefile")
    trips_shp_file = driver.CreateDataSource(filename)
    trips_lyr = trips_shp_file.CreateLayer(TRIP_LYR_NAME, output_srs,
        ogr.wkbLineString)
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

def read_trips_from_shp_file(filename, output_srs):
    trip_ids_map = {}
    trips_shp = ogr.Open(filename, 0)
    if trips_shp is None:
        print "Error, input trips shape file given, %s , failed to open." \
            % (filename)
        sys.exit(1)
    trips_lyr = trips_shp.GetLayer(0)

    trips_srs = trips_lyr.GetSpatialRef()
    transform = None
    if not trips_srs.IsSame(output_srs):
        transform = osr.CoordinateTransformation(trips_srs, output_srs)
    trips = []
    for trip_feat in trips_lyr:
        trip_id = trip_feat.GetField(TRIP_ID_FIELD)
        trip_geom = trip_feat.GetGeometryRef()
        if transform:
            trip_geom.Transform(transform)
        trip_origin = trip_geom.GetPoint_2D(0)
        trip_dest = trip_geom.GetPoint_2D(1)
        dt = datetime.strptime(
            trip_feat.GetField(TRIP_DEP_TIME_FIELD), TIME_OUTPUT_STR_FORMAT)
        trip_dep_time = dt.time()
        origin_sla = trip_feat.GetField(TRIP_ORIGIN_SLA_FIELD)
        dest_sla = trip_feat.GetField(TRIP_DEST_SLA_FIELD)
        trip = (trip_origin, trip_dest, trip_dep_time,
            origin_sla, dest_sla)
        trips.append(trip)
        trip_ids_map[trip_id] = trips[-1]
    trips_shp.Destroy()

    return trip_ids_map, trips
