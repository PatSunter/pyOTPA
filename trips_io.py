
import os, os.path
import sys
from datetime import datetime, time
from osgeo import ogr, osr

from pyOTPA import Trip
from pyOTPA import otp_config

TRIP_LYR_NAME = "trips"
TRIP_ID_FIELD = "id"
TRIP_ID_FIELD_WIDTH = 20    # Make sure can fit VISTA trip strings.
TRIP_ORIGIN_SLA_FIELD = "orig_sla"
TRIP_DEST_SLA_FIELD = "dest_sla"
TRIP_DEP_TIME_FIELD = "dep_time"
TIME_OUTPUT_STR_FORMAT = "%H:%M"
DATETIME_OUTPUT_STR_FORMAT = "%Y-%m-%d" + "-" + TIME_OUTPUT_STR_FORMAT

DEFAULT_OUTPUT_EPSG = otp_config.OTP_ROUTER_EPSG

def save_trips_to_shp_file(filename, trips, 
        trips_srs=None, output_srs=None):

    if os.path.exists(filename):
        os.unlink(filename)    

    if not trips_srs:
        trips_srs = Trip.get_trips_srs()
    if not output_srs:
        output_srs = osr.SpatialReference()
        output_srs.ImportFromEPSG(DEFAULT_OUTPUT_EPSG)
    transform = osr.CoordinateTransformation(trips_srs, output_srs)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    trips_shp_file = driver.CreateDataSource(filename)
    trips_lyr = trips_shp_file.CreateLayer(TRIP_LYR_NAME, output_srs,
        ogr.wkbLineString)
    field = ogr.FieldDefn(TRIP_ID_FIELD, ogr.OFTString)
    field.SetWidth(TRIP_ID_FIELD_WIDTH)
    trips_lyr.CreateField(field)
    field = ogr.FieldDefn(TRIP_ORIGIN_SLA_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)
    field = ogr.FieldDefn(TRIP_DEST_SLA_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)
    field = ogr.FieldDefn(TRIP_DEP_TIME_FIELD, ogr.OFTString)
    field.SetWidth(254)
    trips_lyr.CreateField(field)

    for trip_cnt, trip in enumerate(trips):
        trip_feat = ogr.Feature(trips_lyr.GetLayerDefn())
        trip_geom = ogr.Geometry(ogr.wkbLineString) 
        trip_geom.AddPoint(*trip[Trip.ORIGIN])
        trip_geom.AddPoint(*trip[Trip.DEST])
        trip_geom.Transform(transform)
        trip_feat.SetGeometry(trip_geom)
        try:
            trip_id = trip[Trip.ID]
        except IndexError:
            trip_id = str(trip_cnt)
        trip_feat.SetField(TRIP_ID_FIELD, trip_id)
        trip_feat.SetField(TRIP_ORIGIN_SLA_FIELD, trip[Trip.O_ZONE])
        trip_feat.SetField(TRIP_DEST_SLA_FIELD, trip[Trip.D_ZONE])
        dtime_str = trip[Trip.START_DTIME].strftime(DATETIME_OUTPUT_STR_FORMAT)
        trip_feat.SetField(TRIP_DEP_TIME_FIELD, dtime_str)
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
        trip_id = str(trip_feat.GetField(TRIP_ID_FIELD))
        trip_geom = trip_feat.GetGeometryRef()
        if transform:
            trip_geom.Transform(transform)
        trip_origin = trip_geom.GetPoint_2D(0)
        trip_dest = trip_geom.GetPoint_2D(1)
        try:
            dt = datetime.strptime(
                trip_feat.GetField(TRIP_DEP_TIME_FIELD),
                    DATETIME_OUTPUT_STR_FORMAT)
            trip_dep = dt
        except ValueError:            
            dt = datetime.strptime(
                trip_feat.GetField(TRIP_DEP_TIME_FIELD),
                    TIME_OUTPUT_STR_FORMAT)
            trip_dep = dt.time()
        origin_sla = trip_feat.GetField(TRIP_ORIGIN_SLA_FIELD)
        dest_sla = trip_feat.GetField(TRIP_DEST_SLA_FIELD)
        trip = Trip.new_trip(trip_origin, trip_dest, trip_dep,
            origin_sla, dest_sla, trip_id)
        trips.append(trip)
        trip_ids_map[trip_id] = trips[-1]
    trips_shp.Destroy()

    return trip_ids_map, trips

def read_trips_from_shp_file_otp_srs(filename):
    """Just a utility wrapper around above read_trips function, to ensure they
    are in the right SRS for OTP."""
    otp_router_srs = osr.SpatialReference()
    otp_router_srs.ImportFromEPSG(otp_config.OTP_ROUTER_EPSG)
    result = read_trips_from_shp_file(filename, otp_router_srs)

    return result
