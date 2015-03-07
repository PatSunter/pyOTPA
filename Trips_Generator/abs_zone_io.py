
SLA_NAME_FIELD = "SLA_NAME06"
CCD_CODE_FIELD = "CD_CODE06"

def create_ccd_code_map(ccd_lyr):
    """Creates a dict mapping CCD codes to geometry polygons."""
    polys_dict = {}
    for ccd_shp in ccd_lyr:
        ccd_code = ccd_shp.GetField(CCD_CODE_FIELD)       
        ccd_geom = ccd_shp.GetGeometryRef()
        polys_dict[ccd_code] = ccd_shp
    return polys_dict

def create_sla_name_map(sla_lyr):
    """Creates a dict mapping SLA names to geometry polygons."""
    polys_dict = {}
    for sla_shp in sla_lyr:
        sla_name = sla_shp.GetField(SLA_NAME_FIELD)       
        sla_geom = sla_shp.GetGeometryRef()
        polys_dict[sla_name] = sla_shp
    return polys_dict

def get_sla_name_ccd_within(ccd_feats_dict, ccd_code_interest):
    matching_sla_name = None
    try:
        ccd_feat = ccd_feats_dict[ccd_code_interest]
        matching_sla_name = ccd_feat.GetField(SLA_NAME_FIELD)    
    except KeyError:
        # We'll just return None if the CCD isn't found.
        pass
    return matching_sla_name

def get_zone_name_within(zones_dict, loc):
    zone_name_within = None
    for zone_name, zone_feat in zones_dict.iteritems():
        # TODO: geom transform?
        if zone_feat.GetGeometryRef().Contains(loc):
            zone_name_within = zone_name
    return zone_name_within

