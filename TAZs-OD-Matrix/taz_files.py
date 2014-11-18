
import csv
import osgeo.ogr
from osgeo import ogr, osr

EPSG_LAT_LON = 4326

def read_tazs_from_csv(csv_zone_locs_fname):
    taz_tuples = []
    tfile = open(csv_zone_locs_fname, 'rb')
    treader = csv.reader(tfile, delimiter=',', quotechar="'")
    for ii, row in enumerate(treader):
        if ii == 0: continue
        else:
            taz_tuple = (row[0], row[1], row[2])
            taz_tuples.append(taz_tuple)
    return taz_tuples

def read_tazs_from_shp(shp_zone_locs_fname):
    taz_tuples = []
    tazs_shp = osgeo.ogr.Open(shp_zone_locs_fname)
    tazs_layer = tazs_shp.GetLayer(0)
    src_srs = tazs_layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(EPSG_LAT_LON)
    transform_to_lat_lon = osr.CoordinateTransformation(src_srs,
        target_srs)
    for taz_feat in tazs_layer:
        taz_id = taz_feat.GetField("N")
        taz_geom = taz_feat.GetGeometryRef()
        taz_geom.Transform(transform_to_lat_lon)
        taz_lat = taz_geom.GetX()
        taz_lon = taz_geom.GetY()
        taz_tuples.append((taz_id, taz_lat, taz_lon))
        taz_feat.Destroy()
    tazs_shp.Destroy()
    return taz_tuples        
