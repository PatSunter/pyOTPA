import random
from osgeo import ogr, osr

class LocGenerator:
    def initialise(self):
        return

    def cleanup(self):
        return

class BasicRandomLocGenerator(LocGenerator):
    def __init__(self, seed, bbox):
        self._random_seed = seed
        self._randomiser = random.Random(seed)
        self.bbox = bbox
    
    def update_zone(self, zone_name):
        # Nothing to do.
        return

    def gen_loc_within_zone(self, zone_name):
        return self.gen_loc_within_curr_zone()

    def gen_loc_within_curr_zone(self):
        loc_x = self._randomiser.uniform(self.bbox[0][0], self.bbox[1][0])
        loc_y = self._randomiser.uniform(self.bbox[0][1], self.bbox[1][1])
        return (loc_x, loc_y)

class WithinZoneLocGenerator:
    def __init__(self, seed, zone_polys_dict, constraint_checkers=None):
        self._random_seed = seed
        self._zone_polys_dict = zone_polys_dict
        self.constraint_checkers = constraint_checkers

    def initialise(self):
        self._randomiser = random.Random(self._random_seed)
        if self.constraint_checkers:
            for cc in self.constraint_checkers:
                cc.initialise()
    
    def update_zone(self, zone_name):
        self._curr_zone = zone_name
        zone_shp = self._zone_polys_dict[zone_name]
        self._curr_zone_poly = zone_shp.GetGeometryRef()
        self._curr_zone_env = self._curr_zone_poly.GetEnvelope()
        if self.constraint_checkers:
            for cc in self.constraint_checkers:
                cc.update_region(self._curr_zone_poly)
        
    def gen_loc_within_zone(self, zone_name):
        self.update_zone(zone_name)
        return self.gen_loc_within_curr_zone()

    def gen_loc_within_curr_zone(self):
        valid_loc_found = False
        loc_pt = None
        while True:
            # First generate a random point within the extents
            loc_x = self._randomiser.uniform(self._curr_zone_env[0],
                self._curr_zone_env[1])
            loc_y = self._randomiser.uniform(self._curr_zone_env[2],
                self._curr_zone_env[3])
            loc_pt = ogr.Geometry(ogr.wkbPoint)
            loc_pt.AddPoint(loc_x, loc_y)
            if self._curr_zone_poly.Contains(loc_pt):
                if not self.constraint_checkers:
                    valid_loc_found = True
                else:
                    # Also check the location passes any constraints.
                    all_cc_pass = True
                    for cc in self.constraint_checkers:
                        if not cc.is_valid(loc_pt):
                            all_cc_pass = False
                            break
                    if all_cc_pass:
                        valid_loc_found = True
            if valid_loc_found:        
                break
            else:
                # Keep searching for a valid location ...
                loc_pt.Destroy()
        return loc_pt

    def cleanup(self):
        if self.constraint_checkers:
            for cc in self.constraint_checkers:
                cc.cleanup()
        return        
