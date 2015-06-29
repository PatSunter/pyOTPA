
import os.path

from qgis.core import QgsRectangle

import qgis_utils

# Hard-code this for now - good be good to load from file and style 
# it ...
VECTOR_BASE_LAYER_ID = "cstviccd_r20140620145403419"

# TODO:- should use the pyOTPA.Isochrones.utils functions for these 
#  probably ...

def isos_fname(results_base_path, place_date_time, run_set_name, run_set_ext):
    fname = os.path.join(results_base_path, run_set_name,
                '%s-%s-avg9-isobands.shp' % (place_date_time, run_set_ext))
    return fname

def isos_smoothed_fname(results_base_path, place_date_time, run_set_name,
        run_set_ext):
    fname = os.path.join(results_base_path, run_set_name,
                '%s-%s-avg9-isobands-smoothed.shp' \
                    % (place_date_time, run_set_ext))
    return fname

#iso_dicts = {
#    'CHADSTONE-2015_02_18-09_00_00':
#        {'loc_name': 'CHADSTONE',
#         'loc_text': "(going to) Chadstone, weekdays, 9AM",
#         'iso_descs': ISO_SET_DESCS,
#         'iso_1_fname': isos_fname(ISOS_BASE_DIR, 'CHADSTONE-2015_02_18-09_00_00',
#            PTV_SET_NAME, PTV_EXT),
#         'iso_2_fname': isos_fname(ISOS_BASE_DIR, 'CHADSTONE-2015_02_18-09_00_00',
#            PTUA_SET_NAME, PTUA_EXT)},
#    }

def make_iso_map_requests_dict(loc_names_descs, datetime_str_descs,
        iso_descs, isos_base_dirs, iso_set_names, iso_exts, use_smoothed_isos):
    iso_reqs_dict = {}
    for loc_name, loc_desc in loc_names_descs.iteritems():
        for datetime_str, datetime_desc in datetime_str_descs.iteritems():
            loc_datetime_str = loc_name.replace(' ','_')+'-'+datetime_str
            req_dict = {}
            req_dict['loc_name'] = loc_name
            req_dict['loc_text'] = "travelling to %s, %s." \
                % (loc_desc, datetime_desc)
            req_dict['iso_descs'] = iso_descs
            try:
                isos_base_dir_0 = isos_base_dirs[0]
                isos_base_dir_1 = isos_base_dirs[1]
            except TypeError:
                isos_base_dir = isos_base_dirs
                isos_base_dir_0 = isos_base_dir
                isos_base_dir_1 = isos_base_dir
            fname_func = isos_fname
            if use_smoothed_isos:
                fname_func = isos_smoothed_fname
            req_dict['iso_1_fname'] = fname_func(isos_base_dir_0,
                loc_datetime_str, iso_set_names[0], iso_exts[0])
            req_dict['iso_2_fname'] = fname_func(isos_base_dir_1,
                loc_datetime_str, iso_set_names[1], iso_exts[1])
            iso_reqs_dict[loc_datetime_str] = req_dict
    return iso_reqs_dict

def calc_largest_extents_by_loc_all_date_times(iso_map_reqs_dict):
    """Calculates the largest layer extents of isochrones at each location in
    iso_map_reqs_dict. Useful for creating output maps with the same extent at
    different times of day."""
    print "Calculating max extents across all times at each location:"
    # First, get a new dict of just loc_names, and file names.
    iso_fnames_by_loc = {}
    for isos_name in sorted(iso_map_reqs_dict.keys()):
        isos_dict = iso_map_reqs_dict[isos_name]
        loc_name = isos_dict['loc_name']
        iso_fnames = [isos_dict['iso_1_fname'], isos_dict['iso_2_fname']]

        if loc_name not in iso_fnames_by_loc:
            iso_fnames_by_loc[loc_name] = list(iso_fnames)
        else:
            iso_fnames_by_loc[loc_name] += iso_fnames

    # Now pass to QGIS API utils to calculate.
    largest_extents_by_loc = {}
    for loc_name, iso_fnames_at_loc in iso_fnames_by_loc.iteritems():
        largest_extents_by_loc[loc_name] = \
            qgis_utils.calc_largest_layer_extents(iso_fnames_at_loc)
    print "... done."
    return largest_extents_by_loc


def prepare_composer(comp, comp_temp_doc, canvas, isos_dict, iso_layers,
        osm_layer, map_extents, map_view_scale_factor, general_map_config):
    """Prepares a composer (argument 'comp') based on the input comp_temp_doc 
    ( a QDomDocument ) - and the input parameters.
    
    This function assumes the comp_temp_doc was loaded based on a QGIS
    composer .qgs file that has appropriate keywords in the necessary places,
    for substitution."""

    subst_map = {
        'LOC_TEXT': isos_dict['loc_text'],
        'LICENSE_TEXT': general_map_config['license_text'],
        'MAP_DESCRIPTION_TEXT': general_map_config['map_description_text'],
        'LEFT_ISO_DESC': isos_dict['iso_descs'][0],
        'RIGHT_ISO_DESC': isos_dict['iso_descs'][1],
        'LEFT_ISO_LAYER_ID': iso_layers[0].id(),
        'RIGHT_ISO_LAYER_ID': iso_layers[1].id()}
    comp.loadFromTemplate(comp_temp_doc, subst_map)

    # Set the base layer of maps appropriately.
    for map_name in ['Left_Map', 'Right_Map']:
        map_item = comp.getComposerItemById(map_name)
        layerSet = map_item.layerSet()
        # Replace the bottom layer with appropriate option.
        if osm_layer:
            base_layer_id = osm_layer.id()
        else:
            base_layer_id = VECTOR_BASE_LAYER_ID
        layerSet[-1] = base_layer_id
        map_item.setLayerSet(layerSet)

    if map_extents:
        xMin, xMax, yMin, yMax = map_extents
    else:
        print "re-calculating and updating map extents based on "\
            "max isochrone size"
        iso_1_extent = iso_layers[0].extent()
        iso_2_extent = iso_layers[1].extent()
        xMin = min(iso_1_extent.xMinimum(), iso_2_extent.xMinimum())
        xMax = max(iso_1_extent.xMaximum(), iso_2_extent.xMaximum())
        yMin = min(iso_1_extent.yMinimum(), iso_2_extent.yMinimum())
        yMax = max(iso_1_extent.yMaximum(), iso_2_extent.yMaximum())

    larger_iso_extent = QgsRectangle(xMin, yMin, xMax, yMax)
    larger_iso_extent.scale(map_view_scale_factor)

    #Set up transform of coordinate systems
    larger_iso_extent_xformed = canvas.mapSettings().layerToMapCoordinates(
        iso_layers[0],
        larger_iso_extent)

    for map_name in ['Left_Map', 'Right_Map']:
        map_item = comp.getComposerItemById(map_name)
        map_item.setMapCanvas(canvas)
        map_item.zoomToExtent(larger_iso_extent_xformed)
    
    print "Refreshing the %d composer items:" % len(comp.items())
    comp.refreshItems()
    return
