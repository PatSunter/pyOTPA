
import os

from osgeo import gdal

from PyQt4.QtCore import QFileInfo, QSize, QRectF
from PyQt4.QtGui import QApplication, QImage, QPainter
from PyQt4.QtXml import QDomDocument

from qgis.core import *
from qgis.gui import *
import qgis.utils

SHPFILE_PROVIDER_NAME = "ogr"

TMS_SERVER_URL_KEYWORD = "TMS_SERVER_URL"
TMS_IMAGE_TYPE_KEYWORD = "TMS_IMAGE_TYPE"
TMS_ZOOM_KEYWORD = "TMS_ZOOM"
TMS_EPSG_KEYWORD = "TMS_EPSG"
GDAL_RASTER_FROM_TILE_XML_TEMPLATE = """<GDAL_WMS>
<Service name="TMS">
<ServerUrl>%s/${z}/${x}/${y}.%s</ServerUrl>
</Service>
<DataWindow>
<UpperLeftX>-20037508.34</UpperLeftX>
<UpperLeftY>20037508.34</UpperLeftY>
<LowerRightX>20037508.34</LowerRightX>
<LowerRightY>-20037508.34</LowerRightY>
<TileLevel>%s</TileLevel>
<TileCountX>1</TileCountX>
<TileCountY>1</TileCountY>
<YOrigin>top</YOrigin>
</DataWindow>
<Projection>EPSG:%s</Projection>
<BlockSizeX>256</BlockSizeX>
<BlockSizeY>256</BlockSizeY>
<BandsCount>3</BandsCount>
<Cache />
</GDAL_WMS>""" \
    % (TMS_SERVER_URL_KEYWORD, TMS_IMAGE_TYPE_KEYWORD,
       TMS_ZOOM_KEYWORD, TMS_EPSG_KEYWORD)

def load_register_raster_layer_from_tms(layerReg, tms_url, image_type,
        tms_epsg, tile_zoom, layer_id):
    """
    Loads a Tile Map Service web URL (e.g. OpenStreetMap tiles) as a raster
    layer. Returns the new layer, and also registers the layer with the layer
    registry passed in as parameter layerReg. 
    (After trying a few different approaches to get this working, settled on
    this one using a GDAL virtual file, from:-
    http://www.gislounge.com/using-the-openstreetmap-service-qgis-python-programming-cookbook/)
    """
    vfn = "/vsimem/osm.xml"
    xml_str = GDAL_RASTER_FROM_TILE_XML_TEMPLATE
    xml_str = xml_str.replace(TMS_SERVER_URL_KEYWORD, tms_url)
    xml_str = xml_str.replace(TMS_IMAGE_TYPE_KEYWORD, image_type)
    xml_str = xml_str.replace(TMS_ZOOM_KEYWORD, str(tile_zoom))
    xml_str = xml_str.replace(TMS_EPSG_KEYWORD, str(tms_epsg))
    gdal.FileFromMemBuffer(vfn, xml_str)
    layer = QgsRasterLayer(vfn, layer_id)
    if not layer.isValid():
        print "Raster layer failed to load from TMS URL %s (as '%s')!" \
            % (tms_url, base_name)
        return None
    layerReg.addMapLayer(layer)
    return layer

def load_register_raster_layer(layerReg, layer_fname):
    fileInfo = QFileInfo(layer_fname)
    base_name = fileInfo.baseName()
    layer = QgsRasterLayer(layer_fname, base_name)
    if not layer.isValid():
        print "Raster layer failed to load from file %s (as '%s')!" \
            % (layer_fname, base_name)
        return None
    layerReg.addMapLayer(layer)
    return layer

def load_register_vec_layer(layerReg, layer_fname, layer_id):
    layer = QgsVectorLayer(layer_fname, layer_id, SHPFILE_PROVIDER_NAME)
    if not layer.isValid():
        print "Layer failed to load from file %s (as '%s')!" \
            % (layer_fname, layer_id)
        return None
    layerReg.addMapLayer(layer)
    return layer

def save_composition_to_png_image(comp, dpi, image_fname):
    dpmm = dpi / 25.4
    width = int(dpmm * comp.paperWidth())
    height = int(dpmm * comp.paperHeight())

    # create output image and initialize it
    image = QImage(QSize(width, height), QImage.Format_ARGB32)
    image.setDotsPerMeterX(dpmm * 1000)
    image.setDotsPerMeterY(dpmm * 1000)
    image.fill(0)

    # render the composition
    imagePainter = QPainter(image)
    comp.renderPage(imagePainter, 0)
    # See http://www.faqssys.info/how-to-refresh-the-view-in-qgis-print-composer-using-python/
    # To use the renderPage func, rather than default at the Cookbook page.
    imagePainter.end()

    image.save(image_fname, "png")
    return

def calc_largest_layer_extents(shpfile_fnames):
    """Calculate the largest extent of a set of layers."""
    largest = None
    for shp_fname in shpfile_fnames:
        layer = QgsVectorLayer(shp_fname, "temp_layer", 
            SHPFILE_PROVIDER_NAME)
        if not layer.isValid():
            print "Layer failed to load from file %s!" \
                % (shp_fname)
            continue
        layer_extent = layer.extent()
        xMin = layer_extent.xMinimum()
        xMax = layer_extent.xMaximum()
        yMin = layer_extent.yMinimum()
        yMax = layer_extent.yMaximum()
        if largest == None:
            largest = (xMin, xMax, yMin, yMax)
        else:
            updLargest = [0.0] * 4
            updLargest[0] = min(largest[0], xMin)
            updLargest[1] = max(largest[1], xMax)
            updLargest[2] = min(largest[2], yMin)
            updLargest[3] = max(largest[3], yMax)
            largest = tuple(updLargest)
    return largest
