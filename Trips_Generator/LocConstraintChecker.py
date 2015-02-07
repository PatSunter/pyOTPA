
import os.path

from osgeo import ogr, osr

DEFAULT_ZONE_CODE_FIELD = "ZONE_CODE"

class PlanningZoneLocConstraintChecker:
    def __init__(self, pz_shpfilename, allowed_zone_codes,
            trips_srs, zone_code_field=DEFAULT_ZONE_CODE_FIELD):
        self.pz_shpfilename = pz_shpfilename
        self.allowed_zone_codes = allowed_zone_codes
        self.zone_code_field = zone_code_field
        self._tform_to_pz_srs = None
        self._trips_srs = trips_srs
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
        self._pz_shp.Destroy()
        self._pz_lyr = None
        self._pz_shp = None
        if self._region_geom_local:
            self._region_geom_local.Destroy()
            self._region_geom_local = None
