
import sys
import os.path

#from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QFileInfo
from PyQt4.QtXml import QDomDocument

from qgis.core import *
from qgis.gui import *
import qgis.utils

import pyOTPA.Isochrones.utils
import qgis_utils

# Hard-code this for now - good be good to load from file and style 
# it ...
VECTOR_BASE_LAYER_ID = "cstviccd_r20140620145403419"
TMS_LAYER_ID = "TMS_base_layer"

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
        datetime_num_each_sides, iso_descs, isos_base_dirs, iso_set_names,
        iso_exts, use_smoothed_isos):
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
            
            num_each_side = datetime_num_each_sides[datetime_str]
            datestr = datetime_str.split('-')[0]
            timestr = datetime_str.split('-')[1] 
            fname_func = pyOTPA.Isochrones.utils.isoBandsName
            if use_smoothed_isos:
                fname_func = \
                    pyOTPA.Isochrones.utils.smoothedIsoBandsNameCombined
            save_path_0 = os.path.join(isos_base_dir_0, iso_set_names[0])
            req_dict['iso_1_fname'] = fname_func(loc_name, datestr, timestr,
                save_path_0, iso_exts[0], num_each_side)
            save_path_1 = os.path.join(isos_base_dir_1, iso_set_names[1])
            req_dict['iso_2_fname'] = fname_func(loc_name, datestr, timestr,
                save_path_1, iso_exts[1], num_each_side)

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
        tms_bg_layer, map_extents, general_map_config):
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
        if tms_bg_layer:
            base_layer_id = tms_bg_layer.id()
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
    larger_iso_extent.scale(general_map_config['viewing_scale_factor'])

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

def make_all_composer_maps(qgis_proj_fname, qgis_comp_template_fname,
        iso_map_reqs_dict, general_map_config, tms_params, output_dir,
        make_pngs, make_pdfs):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    canvas = QgsMapCanvas()
    print "Reading in QgsProject from file %s." % qgis_proj_fname
    project = QgsProject.instance()
    project.read(QFileInfo(qgis_proj_fname))

    bridge = QgsLayerTreeMapCanvasBridge(
        project.layerTreeRoot(), canvas)
    bridge.setCanvasLayers()

    layerReg = QgsMapLayerRegistry.instance()    
    layers = layerReg.mapLayers()
    if not layers.keys():
        print "No layers loaded in layer registry! Exiting."
        QgsApplication.exitQgis()
        sys.exit(1)
    print "Loaded %d layers so far." % len(layers.keys())

    print "Creating Composer."
    # Need to initiate canvas as 2 lines, because of weirdo-QGIS
    # referencing issues
    # See https://hub.qgis.org/issues/11077
    ms = canvas.mapSettings()
    comp = QgsComposition(ms)

    # Set general output settings
    comp.setPrintResolution(general_map_config['print_resolution_dpi'])
    #comp.setPaperSize(width, height)

    print "Loading in composer content from template file %s" \
        % qgis_comp_template_fname
    comp_temp_file = file(qgis_comp_template_fname)
    template_content = comp_temp_file.read()
    comp_temp_file.close()
    comp_temp_doc = QDomDocument()
    comp_temp_doc.setContent(template_content)

    # Load other necessary layers, style files etc.
    iso_locs_layer_id = general_map_config['iso_locations_layer_id']
    iso_locs_layer = layerReg.mapLayer(iso_locs_layer_id)
    
    tms_bg_layer = None
    if general_map_config['use_tms_background']:
        print "Loading the OSM background map tiles as a Raster layer:"
        # We need to load the OSM tiles from Vector.
        tms_bg_layer = qgis_utils.load_register_raster_layer_from_tms(layerReg,
            tms_params['url'], tms_params['image_type'],
            tms_params['epsg'], tms_params['zoom'], 
            TMS_LAYER_ID)
        if not tms_bg_layer:
            print "TMS basemap requested but failed to load from URL '%s', "\
                "exiting." % tms_params['url']
            sys.exit(1)
        print "...done."    

    largest_iso_extents_by_loc = {}
    if general_map_config['use_max_extents_all_times_per_loc']:
        largest_iso_extents_by_loc = \
            calc_largest_extents_by_loc_all_date_times(
                iso_map_reqs_dict)

    ISOS_LAYER_1_ID = "ISOS_LAYER_1"
    ISOS_LAYER_2_ID = "ISOS_LAYER_2"

    for isos_name in sorted(iso_map_reqs_dict.keys()):
        print "\nCreating comparison maps for Isochrones at loc/date/time %s:" \
                % isos_name

        isos_dict = iso_map_reqs_dict[isos_name]

        loc_name = isos_dict['loc_name']
        # Select appropriate iso centre location to show
        res = iso_locs_layer.setSubsetString("name='%s'" % loc_name)
        if not res:
            "Failed to find an isochrone center location '%s' in the "\
                "isochrone center layer." % loc_name

        print "loading the two isochrone set shapefiles:"
        ptv_isos_fname = isos_dict['iso_1_fname']
        ptua_isos_fname = isos_dict['iso_2_fname']

        iso_layer_1 = None
        iso_layer_2 = None
        iso_layer_1 = qgis_utils.load_register_vec_layer(layerReg,
            ptv_isos_fname, ISOS_LAYER_1_ID)
        iso_layer_2 = qgis_utils.load_register_vec_layer(layerReg,
            ptua_isos_fname, ISOS_LAYER_2_ID)
        if not (iso_layer_1 and iso_layer_2):
            print "Problem loading an isochrone for this result comparison. "\
                "Skipping to next."
            for layer in [iso_layer_1, iso_layer_2]:
                if layer:
                    layerReg.removeMapLayer(layer.id())
            continue
   
        iso_layers = [iso_layer_1, iso_layer_2]
        print "applying chosen style to loaded isochrone layers."
        for layer in iso_layers:
            layer.loadNamedStyle(general_map_config['isos_style_fname'])

        if general_map_config['use_max_extents_all_times_per_loc']:
            extents = largest_iso_extents_by_loc[loc_name]
        else:
            extents = None

        prepare_composer(comp, comp_temp_doc, canvas, isos_dict,
            iso_layers, tms_bg_layer, extents, general_map_config)
        
        dpi_res = general_map_config['print_resolution_dpi']
        output_fname_pdf = os.path.join(output_dir, 
            isos_name+"-comparison-%ddpi.pdf" % dpi_res)
        output_fname_png = os.path.join(output_dir,
            isos_name+"-comparison-%ddpi.png" % dpi_res)
        if make_pdfs:
            print "Exporting composer image to PDF file: %s" \
                % output_fname_pdf
            comp.exportAsPDF(output_fname_pdf)
            print "done."
        if make_pngs:
            print "Exporting composer image as PNG image: %s" \
                % output_fname_png
            qgis_utils.save_composition_to_png_image(comp, dpi_res,
                output_fname_png)
            print "done."
        print "removing the isochrones from map layer registry."
        layerReg.removeMapLayer(iso_layer_1.id())
        layerReg.removeMapLayer(iso_layer_2.id())

    print "tidying up (closing project)"
    project.clear()
    return
