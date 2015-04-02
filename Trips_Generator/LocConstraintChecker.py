
import os.path

from osgeo import ogr, osr

from pyOTPA import geom_utils

DEFAULT_ZONE_CODE_FIELD = "ZONE_CODE"

class LocConstraintChecker:
    def initialise(self):
        return

    def update_region(self, region_key, region_geom, total_trip_cnt_zone):
        return
    
    def is_valid(self, loc_geom):
        return NotImplementedError("Base class, need to implement.")

    def cleanup(self):
        return

class PlanningZoneLocConstraintChecker(LocConstraintChecker):
    def __init__(self, pz_spatial_index, pz_srs, allowed_zone_codes,
            zone_code_field=DEFAULT_ZONE_CODE_FIELD):
        self._pz_spatial_index = pz_spatial_index
        self._pz_srs = pz_srs
        self.allowed_zone_codes = allowed_zone_codes
        self.zone_code_field = zone_code_field
        self._tform_to_pz_srs = None
        self._locations_srs = None
    
    def initialise(self, locations_srs):
        self._locations_srs = locations_srs
        self._tform_to_pz_srs = osr.CoordinateTransformation(
            self._locations_srs, self._pz_srs)

    def update_region(self, region_key, region_geom, total_trip_cnt_zone):
        return
    
    def is_valid(self, loc_geom):
        zone = self.get_zone_at_location(loc_geom)
        if zone and zone in self.allowed_zone_codes:
            return True
        else:
            return False

    def get_zone_at_location(self, loc_geom):
        # Do a naive linear search for now, since we already use spatial
        # filter
        zone_code = None
        loc_geom_local = loc_geom.Clone()
        loc_geom_local.Transform(self._tform_to_pz_srs)
        pz_shp = geom_utils.get_shp_geom_is_within_using_index(
            self._pz_spatial_index, loc_geom_local)
        if pz_shp:
            zone_code = pz_shp.GetField(self.zone_code_field)
        loc_geom_local.Destroy()
        return zone_code

    def cleanup(self):
        return

######################

def within_dist_any_shape(test_geoms, loc_geom, buffer_dist):
    within_dist = False
    found_geom = None
    for test_geom in test_geoms:
        if loc_geom.Distance(test_geom) <= buffer_dist:
            within_dist = True
            found_geom = test_geom
            break
    return within_dist, found_geom

def get_geoms_in_buffer_range_of_region(test_layer, region_geom, buffer_dist):
    region_geom_plus_buffer = region_geom.Buffer(buffer_dist)
    test_layer.SetSpatialFilter(region_geom_plus_buffer)
    print "Calculating geoms in buffer range of sub-region of the "\
        "%d test shapes that pass within it..." \
        % (test_layer.GetFeatureCount())
    geoms_in_range = []
    for feat in test_layer:
        geoms_in_range.append(feat.GetGeometryRef().Clone())
    test_layer.SetSpatialFilter(None)
    region_geom_plus_buffer.Destroy()
    print "...done."
    return geoms_in_range

def get_isect_geoms_in_region(test_layer, region_geom, buffer_dist):
    region_geom_plus_buffer = region_geom.Buffer(buffer_dist)
    test_layer.SetSpatialFilter(region_geom_plus_buffer)
    print "Calculating intersect geoms in sub-region of the "\
        "%d test shapes that pass within it..." \
        % (test_layer.GetFeatureCount())
    isect_geoms = []
    for feat in test_layer:
        isect_geom = feat.GetGeometryRef().Intersection(region_geom)
        isect_geoms.append(isect_geom)
    test_layer.SetSpatialFilter(None)
    region_geom_plus_buffer.Destroy()
    print "...done."
    return isect_geoms

def create_union_buffered_geom_in_region(test_layer, buffer_dist,
        region_geom):
    print "Calculating buffered shape in sub-region:..."
    isect_geoms = get_isect_geoms_in_region(test_layer, region_geom,
        buffer_dist)
    print "...now calculating the buffer and union..."
    buffered_geoms = []
    for isect_geom in isect_geoms:
        buffer_geom = isect_geom.Buffer(buffer_dist)
        buffered_geoms.append(buffer_geom)
        isect_geom.Destroy()
    union_geom = None
    if len(buffered_geoms) > 0:
        union_geom = buffered_geoms[0]
        for bgeom in buffered_geoms[1:]:
            new_union_geom = union_geom.Union(bgeom)
            union_geom.Destroy()
            bgeom.Destroy()
            union_geom = new_union_geom
    print "...done."
    return union_geom

#FULL_BUFFER_CALC_LEVEL = 200
FULL_BUFFER_CALC_LEVEL = 1000

class WithinBufferOfShapeLocConstraintChecker(LocConstraintChecker):
    def __init__(self, test_shpfilename, buffer_dist,
            zonal_buffered_geoms_cache, grid_index):
        self.test_shpfilename = test_shpfilename
        self._buffer_dist = buffer_dist
        self._tform_to_test_srs = None
        self._locations_srs = None
        self._test_geom_buffer_in_region = None
        self._test_geoms_in_region = None
        self._test_shp = None
        self._region_buffered_geoms_cache = zonal_buffered_geoms_cache
        self._region_geom_refs = None
        self._test_geom_index_grid = grid_index
    
    def initialise(self, locations_srs):
        self._locations_srs = locations_srs
        test_fname = os.path.expanduser(self.test_shpfilename)
        self._test_shp = ogr.Open(test_fname, 0)
        if self._test_shp is None:
            print "Error, input within boundary shape file given, %s , "\
                "failed to open." % (self.test_shpfilename)
            sys.exit(1)
        self._test_lyr = self._test_shp.GetLayer(0)  
        #assert self._test_lyr.GetFeatureCount() == 1
        test_srs = self._test_lyr.GetSpatialRef()
        self._tform_to_test_srs = osr.CoordinateTransformation(
            self._locations_srs, test_srs)
        self._test_geom_buffer_in_region = None
        self._test_geoms_in_region = None
        #self._region_buffered_geoms_cache = {}
        self._region_geom_refs = {}

    def update_region(self, region_key, region_geom, total_trip_cnt_zone):
        self._test_geom_buffer_in_region = None
        self._test_geoms_in_region = None

        return
        # TODO: remove the rest if safe.
        if region_key in self._region_buffered_geoms_cache.iterkeys():
            self._test_geom_buffer_in_region = \
                self._region_buffered_geoms_cache[region_key]
            return
        elif region_key in self._region_geom_refs.iterkeys():
            self._test_geoms_in_region = \
                self._region_geom_refs[region_key]
            return

        region_geom_local = region_geom.Clone()
        region_geom_local.Transform(self._tform_to_test_srs)
        if not self._test_geom_buffer_in_region \
                and total_trip_cnt_zone >= FULL_BUFFER_CALC_LEVEL:
            bgeom = create_union_buffered_geom_in_region(
                self._test_lyr, self._buffer_dist, region_geom_local)
            self._test_geom_buffer_in_region = bgeom
            self._region_buffered_geoms_cache[region_key] = bgeom
        elif not self._test_geoms_in_region:
            test_geoms_in_region = get_geoms_in_buffer_range_of_region(
                self._test_lyr, region_geom_local, self._buffer_dist)
            self._test_geoms_in_region = test_geoms_in_region
            self._region_geom_refs[region_key] = test_geoms_in_region
        region_geom_local.Destroy()
        return
 
    def is_valid(self, loc_geom):
        loc_geom2 = loc_geom.Clone()
        loc_geom2.Transform(self._tform_to_test_srs)
        if self._test_geom_buffer_in_region:
            if self._test_geom_buffer_in_region.Contains(loc_geom2):
                within = True
            else:
                within = False
        elif self._test_geoms_in_region:
            within_1, shp_near_a = within_dist_any_shape(
                self._test_geoms_in_region, loc_geom2,
                self._buffer_dist)
            if within_1:
                within = True
            else:
                within = False
        elif self._test_geom_index_grid:
            within, shp_near = geom_utils.check_any_shps_near_point(
                self._test_geom_index_grid, loc_geom2, self._buffer_dist)
            #within_old, shp_near_a = within_dist_any_shape(
            #    self._test_geoms_in_region, loc_geom2,
            #    self._buffer_dist)
            #assert within == within_old    
        else:
            within = True
        loc_geom2.Destroy()
        return within

    def cleanup(self):
        if self._test_shp:
            self._test_shp.Destroy()
        self._test_lyr = None
        self._test_shp = None
        if self._region_buffered_geoms_cache:
            for region_code, buffered_geom in \
                    self._region_buffered_geoms_cache.items():
                if buffered_geom:
                    buffered_geom.Destroy()
                del(self._region_buffered_geoms_cache[region_code])
            self._test_geom_buffer_in_region = None
        if self._region_geom_refs:
            for region_code, geom_list in self._region_geom_refs.items():
                for geom in geom_list:
                    geom.Destroy()
                del(self._region_geom_refs[region_code])    
