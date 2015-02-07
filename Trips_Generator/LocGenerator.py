import random
from osgeo import ogr, osr

class BasicRandomLocGenerator:
    def __init__(self, seed, bbox):
        self._random_seed = seed
        self._randomiser = random.Random(seed)
        self.bbox = bbox
    
    def gen_loc_within_zone(self, zone_code):
        # Ignore the zone code in this case.
        loc_x = self._randomiser.uniform(self.bbox[0][0], self.bbox[1][0])
        loc_y = self._randomiser.uniform(self.bbox[0][1], self.bbox[1][1])
        return (loc_x, loc_y)

class WithinZoneLocGenerator:
    def __init__(self, seed, zone_polys_dict, constraint_checker=None):
        self._random_seed = seed
        self._randomiser = random.Random(seed)
        self._zone_polys_dict = zone_polys_dict
        self._constraint_checker = constraint_checker
    
    def gen_loc_within_zone(self, zone_name):
        zone_shp = self._zone_polys_dict[zone_name]
        zone_poly = zone_shp.GetGeometryRef()
        zone_env = zone_poly.GetEnvelope()
        while True:
            # First generate a random point within the extents
            loc_x = self._randomiser.uniform(zone_env[0], zone_env[1])
            loc_y = self._randomiser.uniform(zone_env[2], zone_env[3])
            loc_pt = ogr.Geometry(ogr.wkbPoint)
            loc_pt.AddPoint(loc_x, loc_y)
            if zone_poly.Contains(loc_pt):
                if not self._constraint_checker:
                    break
                else:
                    # Also check the location passes any constraints.
                    if self._constraint_checker.is_valid(loc_pt):
                        break
            loc_pt.Destroy()
        return loc_pt


