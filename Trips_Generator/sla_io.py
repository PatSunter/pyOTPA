
SLA_NAME_FIELD = "SLA_NAME06"

def populate_zone_polys_dict_from_layer(sla_lyr):
    polys_dict = {}
    for sla_shp in sla_lyr:
        sla_name = sla_shp.GetField(SLA_NAME_FIELD)       
        sla_geom = sla_shp.GetGeometryRef()
        polys_dict[sla_name] = sla_shp
    return polys_dict
