
import os.path

from osgeo import ogr, osr

DEFAULT_ZONE_CODE_FIELD = "ZONE_CODE"

class LocConstraintChecker:
    def initialise(self):
        return

    def update_region(self, region_geom):
        return
    
    def is_valid(self, loc_geom):
        return NotImplementedError("Base class, need to implement.")

    def cleanup(self):
        return

class PlanningZoneLocConstraintChecker(LocConstraintChecker):
    def __init__(self, pz_shpfilename, allowed_zone_codes,
            trips_srs, zone_code_field=DEFAULT_ZONE_CODE_FIELD):
        self.pz_shpfilename = pz_shpfilename
        self.allowed_zone_codes = allowed_zone_codes
        self.zone_code_field = zone_code_field
        self._tform_to_pz_srs = None
        self._trips_srs = trips_srs
        self._pz_shp = None
        self._region_geom_local = None
    
    def initialise(self):
        pz_fname = os.path.expanduser(self.pz_shpfilename)
        self._pz_shp = ogr.Open(pz_fname, 0)
        if self._pz_shp is None:
            print "Error, input Planning Zones shape file given, %s , "\
                "failed to open." % (self.pz_shpfilename)
            sys.exit(1)
        self._pz_lyr = self._pz_shp.GetLayer(0)  
        pz_srs = self._pz_lyr.GetSpatialRef()
        self._tform_to_pz_srs = osr.CoordinateTransformation(
            self._trips_srs, pz_srs)

    def update_region(self, region_geom):
        self._pz_lyr.SetSpatialFilter(None)
        if self._region_geom_local:
            self._region_geom_local.Destroy()
        self._region_geom_local = region_geom.Clone()
        self._region_geom_local.Transform(self._tform_to_pz_srs)
        self._pz_lyr.SetSpatialFilter(self._region_geom_local)
    
    def is_valid(self, loc_geom):
        zone = self.get_zone_at_location(loc_geom)
        if zone in self.allowed_zone_codes:
            return True
        else:
            return False

    def get_zone_at_location(self, loc_geom):
        # Do a naive linear search for now, since we already use spatial
        # filter
        zone_code = None
        loc_geom_local = loc_geom.Clone()
        loc_geom_local.Transform(self._tform_to_pz_srs)
        for feat in self._pz_lyr:
            if feat.GetGeometryRef().Contains(loc_geom_local):
                zone_code = feat.GetField(self.zone_code_field)
                break
        self._pz_lyr.ResetReading()
        loc_geom_local.Destroy()
        return zone_code

    def cleanup(self):
        if self._pz_shp:
            self._pz_shp.Destroy()
        self._pz_lyr = None
        self._pz_shp = None
        if self._region_geom_local:
            self._region_geom_local.Destroy()
            self._region_geom_local = None

class WithinShapeLocConstraintChecker(LocConstraintChecker):
    def __init__(self, test_shpfilename, trips_srs):
        self.test_shpfilename = test_shpfilename
        self._tform_to_test_srs = None
        self._trips_srs = trips_srs
        self._test_geom_in_region = None
        self._test_shp = None
    
    def initialise(self):
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
            self._trips_srs, test_srs)

    def update_region(self, region_geom):
        self._test_lyr.SetSpatialFilter(None)
        if self._test_geom_in_region:
            self._test_geom_in_region.Destroy()
        region_geom_local = region_geom.Clone()
        region_geom_local.Transform(self._tform_to_test_srs)
        # There is just one shape in the layer :- take intersection.
        #test_shp = self._test_lyr.GetFeature(0)
        #int_geom = test_shp.GetGeometryRef().Intersection(
        #    region_geom_local)
        #region_geom_local.Destroy()
        #self._test_geom_in_region = int_geom

        # This is in decimal degrees given particular shpfile input.
        BUFFER_DIST = 0.0015
        # Spatial filter
        self._test_lyr.SetSpatialFilter(region_geom_local)
        print "Calculating buffered shape in sub-region to search " \
            "around the %d shapes ..." % (self._test_lyr.GetFeatureCount())
        buffered_geoms = []
        for feat in self._test_lyr:
            isect_geom = feat.GetGeometryRef().Intersection(region_geom_local)
            buffer_geom = isect_geom.Buffer(BUFFER_DIST)
            buffered_geoms.append(buffer_geom)
        self._test_lyr.SetSpatialFilter(None)

        if len(buffered_geoms) > 0:
            self._test_geom_in_region 
            union_geom = buffered_geoms[0]
            for bgeom in buffered_geoms[1:]:
                new_union_geom = union_geom.Union(bgeom)
                union_geom.Destroy()
                bgeom.Destroy()
                union_geom = new_union_geom
            self._test_geom_in_region = union_geom
        else:
            self._test_geom_in_region = None
        print "...done."
        return
 
    def is_valid(self, loc_geom):
        if self._test_geom_in_region:
            loc_geom2 = loc_geom.Clone()
            loc_geom2.Transform(self._tform_to_test_srs)
            if self._test_geom_in_region.Contains(loc_geom2):
                within = True
            else:
                within = False
            loc_geom2.Destroy()
        else:
            within = True
        return within

    def cleanup(self):
        if self._test_shp:
            self._test_shp.Destroy()
        self._test_lyr = None
        self._test_shp = None
        if self._test_geom_in_region:
            self._test_geom_in_region.Destroy()
            self._test_geom_in_region = None
