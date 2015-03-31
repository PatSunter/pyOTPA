from math import radians, cos, sin, asin, sqrt

# Chose EPSG:28355 ("GDA94 / MGA zone 55") as an appropriate projected
    # spatial ref. system, in meters, for the Melbourne region.
    #  (see http://spatialreference.org/ref/epsg/gda94-mga-zone-55/)
COMPARISON_EPSG = 28355

# Note:- could possibly also use the shapely length function, or 
# geopy has a Vincenty Distance implementation
# see:- http://gis.stackexchange.com/questions/4022/looking-for-a-pythonic-way-to-calculate-the-length-of-a-wkt-linestring
def haversine(lon1, lat1, lon2, lat2):
    """
     Calculate the great circle distance between two points 
     on the earth (specified in decimal degrees) - return in metres
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    metres = km * 1000
    return metres 

def within_bbox(pt_coord, bbox):
    """Tests if geom is within the bbox envelope. Bbox of form (minx, maxx,
    miny, maxy) - IE the result of an ogr GetEnvelope() call."""
    result = False
    if pt_coord[0] >= bbox[0] and pt_coord[0] <= bbox[1] \
            and pt_coord[1] >= bbox[2] and pt_coord[1] <= bbox[3]:
        result = True      
    return result

