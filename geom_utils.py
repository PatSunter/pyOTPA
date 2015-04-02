
import itertools
from math import radians, cos, sin, asin, sqrt

# Chose EPSG:28355 ("GDA94 / MGA zone 55") as an appropriate projected
    # spatial ref. system, in meters, for the Melbourne region.
    #  (see http://spatialreference.org/ref/epsg/gda94-mga-zone-55/)
COMPARISON_EPSG = 28355

# Note:- could possibly also use the shapely length function, or 
# geopy has a Vincenty Distance implementation
# see:- http://gis.stackexchange.com/questions/4022/looking-for-a-pythonic-way-to-calculate-the-length-of-a-wkt-linestring
def haversine(lon1, lat1, lon2, lat2):
    """
     Calculate the great circle distance between two points 
     on the earth (specified in decimal degrees) - return in metres
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    metres = km * 1000
    return metres 

def within_bbox(pt_coord, bbox):
    """Tests if geom is within the bbox envelope. Bbox of form (minx, maxx,
    miny, maxy) - IE the result of an ogr GetEnvelope() call."""
    result = False
    if pt_coord[0] >= bbox[0] and pt_coord[0] <= bbox[1] \
            and pt_coord[1] >= bbox[2] and pt_coord[1] <= bbox[3]:
        result = True      
    return result

def bbox_within_bbox(inner_bbox, outer_bbox):
    result = False
    if inner_bbox[0] >= outer_bbox[0] \
            and inner_bbox[1] <= outer_bbox[1] \
            and inner_bbox[2] >= outer_bbox[2] \
            and inner_bbox[3] <= outer_bbox[3]:
        result = True
    return result

def bbox_partially_within_bbox(inner, outer):
    # test the Xs
    if inner[1] >= outer[0]:
        if inner[0] <= outer[1]:
            x_partially_within = True
        else:
            return False
    else:
        return False
    # Now test the Ys
    if inner[3] >= outer[2]:
        if inner[2] <= outer[3]:
            return True
        else:
            return False
    else:
        return False
    return True

def build_and_populate_gridded_spatial_index(lyr, levels, grid_per_level):
    print "Building a spatial index for layer, with %d levels, of "\
        "grid size %d * %d per level..." \
            % (levels, grid_per_level, grid_per_level)
    assert levels > 1
    assert grid_per_level > 1
    lyr_extent = lyr.GetExtent()
    print "  ...creating the empty index..."
    gridded_index = build_empty_index(lyr_extent, levels, grid_per_level)
    print "  ...done creating the empty index..."

    print "  ...adding the features..."
    added_count = 0
    for shp in lyr:
        add_shp_to_index(gridded_index, shp)
        added_count += 1
    lyr.ResetReading()
    print "...done (added %d features to the index.)" % added_count
    lowest_cnt_min, lowest_cnt_max, total_lowest_lev_entries = \
        get_index_lowest_level_counts(gridded_index, added_count)
    print "(%d lowest level indices, ranging in count from from %d to %d)" \
        % (total_lowest_lev_entries, lowest_cnt_min, lowest_cnt_max)
    assert total_lowest_lev_entries == (grid_per_level ** 2) ** levels
    return gridded_index

def build_and_populate_gridded_spatial_index_dynamic_splitting(lyr, 
        max_levels, grid_per_level, target_count_per_cell):
    print "Building a spatial index for layer, with max %d levels, of "\
        "grid size %d * %d per level, with target cnt/cell of %d" \
            % (max_levels, grid_per_level, grid_per_level, target_count_per_cell)
    assert max_levels >= 1
    assert grid_per_level > 1
    lyr_extent = lyr.GetExtent()
    print "  ...creating initial one-level empty index..."
    gridded_index = build_empty_index(lyr_extent, 1, grid_per_level)
    print "  ...done creating inital empty index..."

    print "  ...adding the features, (and dynamically adding sub-levels)..."
    added_count = 0
    for shp in lyr:
        add_shp_to_index_dynamic_splitting(gridded_index, max_levels,
            grid_per_level, target_count_per_cell, shp)
        added_count += 1
    lyr.ResetReading()
    print "...done (added %d features to the index.)" % added_count
    lowest_cnt_min, lowest_cnt_max, total_lowest_lev_entries = \
        get_index_lowest_level_counts(gridded_index, added_count)

    potential_max_entries = (grid_per_level ** 2) ** max_levels
    print "(%d lowest level indices (out of potential max of %d), "\
        "ranging in count from from %d to %d)" \
        % (total_lowest_lev_entries, potential_max_entries,
           lowest_cnt_min, lowest_cnt_max)
    assert total_lowest_lev_entries <= potential_max_entries
    return gridded_index

def calc_sub_bboxes(extent, grid_per_level):
    #print "Calculating sub bboxes at level, from extent %s:" % (str(extent))
    assert grid_per_level > 1
    sub_bboxes = []
    x_sub_size = abs(extent[1] - extent[0]) / float(grid_per_level)
    y_sub_size = abs(extent[3] - extent[2]) / float(grid_per_level)
    for ii in range(grid_per_level):
        for jj in range(grid_per_level):
            x_min = extent[0] + jj * x_sub_size
            y_min = extent[2] + ii * y_sub_size
            sub_bbox = (x_min, x_min + x_sub_size, y_min, y_min + y_sub_size)
            sub_bboxes.append(sub_bbox)
            #print "  calculated new sub-bbox as %s:" % (str(sub_bbox))
    #print "...done."
    return sub_bboxes

def build_empty_index(extent, levels, grid_per_level):
    sub_levels_left = levels-1
    assert sub_levels_left >= 0
    index_at_curr_level = {}
    sub_bboxes = calc_sub_bboxes(extent, grid_per_level)
    if sub_levels_left > 0:
        for sub_bbox in sub_bboxes:
            index_at_curr_level[sub_bbox] = \
                build_empty_index(sub_bbox, sub_levels_left, grid_per_level)
    else:
        for sub_bbox in sub_bboxes:
            index_at_curr_level[sub_bbox] = []
    return index_at_curr_level

def get_index_lowest_level_counts(gridded_index, entries_total):
    total_lowest_level_indices = 0
    lowest_level_min = entries_total
    lowest_level_max = 0
    indexes_to_search = gridded_index.values()
    while indexes_to_search:
        index_entries_at_level = indexes_to_search.pop()
        if isinstance(index_entries_at_level, dict):
            indexes_to_search.extend(index_entries_at_level.values())
        else:
            total_lowest_level_indices += 1
            entry_count = len(index_entries_at_level) 
            if entry_count < lowest_level_min:
                lowest_level_min = entry_count
            if entry_count > lowest_level_max:
                lowest_level_max = entry_count
    return lowest_level_min, lowest_level_max, total_lowest_level_indices

def get_index_entries_of_geom(gridded_index, geom, find_mode=False):
    geom_bbox = geom.GetEnvelope()
    partially_within_bboxes = []
    partially_within_indexes = []
    partially_within_levels = []
    partially_within_parent_indices = []
    start_level = 1
    indexes_to_search = \
        zip(gridded_index.keys(), gridded_index.values(),
            itertools.repeat(start_level), itertools.repeat(gridded_index))
    while indexes_to_search:
        index_bbox, index_entries_at_level, curr_level, parent_index = \
            indexes_to_search.pop()
        if bbox_partially_within_bbox(geom_bbox, index_bbox):
            if isinstance(index_entries_at_level, dict):
                sub_level = curr_level + 1
                sub_dict = index_entries_at_level
                #new_entries = []
                new_entries = [None] * len(sub_dict)
                for ii, item in enumerate(sub_dict.iteritems()):
                    sub_bbox, sub_index_entry = item
                    new_entries[ii] = (sub_bbox, sub_index_entry, 
                        sub_level, sub_dict)
                    #if not find_mode or len(sub_index_entry):
                    #    new_entries.append((sub_bbox, sub_index_entry, 
                    #         sub_level, sub_dict))
                indexes_to_search.extend(new_entries)
            else:
                partially_within_bboxes.append(index_bbox)
                partially_within_indexes.append(index_entries_at_level)
                partially_within_levels.append(curr_level)
                partially_within_parent_indices.append(parent_index)
    return partially_within_bboxes, partially_within_indexes, \
        partially_within_levels, partially_within_parent_indices 

def add_shp_to_index(gridded_index, new_shp):
    geom = shp.GetGeometryRef()
    found_bboxes, found_indexes, found_levels, parent_indexes = \
        get_index_entries_of_geom(gridded_index, shp_geom)
    assert found_bboxes
    shp_bbox = new_shp.GetGeometryRef().GetEnvelope()
    for found_index in found_indexes:
        # Need to put a reference to this shp in all the bounding boxes it is
        # at least partially within
        found_index.append((new_shp, shp_bbox))
    return

def add_shp_to_index_dynamic_splitting(gridded_index, max_levels,
        grid_per_level, target_count_per_cell, new_shp):
    shp_geom = new_shp.GetGeometryRef()
    found_bboxes, found_indexes, found_levels, parent_indexes = \
        get_index_entries_of_geom(gridded_index, shp_geom)
    assert found_bboxes
    shp_bbox = new_shp.GetGeometryRef().GetEnvelope()
    # Need to put a reference to this shp in all the bounding boxes it is
    # at least partially within
    for ii, found_index in enumerate(found_indexes):
        found_level = found_levels[ii]
        if len(found_index) < target_count_per_cell \
                or found_level >= max_levels:
            found_index.append((new_shp, shp_bbox))
        else:
            # We need to split, build new sub-level of index, and add
            # within
            found_bbox = found_bboxes[ii]
            new_sub_index = build_empty_index(found_bbox, 1, grid_per_level)
            rem_levels = max_levels - found_level
            for existing_shp, existing_bbox in found_index:
                add_shp_to_index_dynamic_splitting(new_sub_index,
                    rem_levels, grid_per_level,
                    target_count_per_cell, existing_shp)
            add_shp_to_index_dynamic_splitting(new_sub_index,
                rem_levels, grid_per_level,
                target_count_per_cell, new_shp)
            parent_indexes[ii][found_bbox] = new_sub_index    
    return

POTENTIAL_SHP_BBOX_TESTS = 0
ACTUAL_SHP_BBOX_TESTS = 0
ACTUAL_CONTAINS_TESTS = 0
PASSED_CONTAINS_TESTS = 0

def get_shp_geom_is_within_using_index(gridded_index, geom):
    shp_within = None
    global POTENTIAL_SHP_BBOX_TESTS
    global ACTUAL_SHP_BBOX_TESTS
    global ACTUAL_CONTAINS_TESTS
    global PASSED_CONTAINS_TESTS
    found_bboxes, found_indexes, found_levels, parent_indexes = \
        get_index_entries_of_geom(gridded_index, geom, find_mode=True)
    if not found_bboxes:
        print "Warning:- didn't find requested geom within _any_ of the "\
            "spatial index boxes. Is it outside the known region, or in "\
            "a different SRS to the index?"
        return None
    geom_bbox = geom.GetEnvelope()
    for found_index in found_indexes:
        #POTENTIAL_SHP_BBOX_TESTS += len(found_index)
        for shp, shp_bbox in found_index:
            #ACTUAL_SHP_BBOX_TESTS += 1
            if bbox_within_bbox(geom_bbox, shp_bbox):
                shp_geom = shp.GetGeometryRef()
                #ACTUAL_CONTAINS_TESTS += 1
                if shp_geom.Contains(geom):
                    #PASSED_CONTAINS_TESTS += 1
                    shp_within = shp
                    break
        if shp_within:
            # Remember, if we broke out of an inner loop after finding a
            # valid shp, can break here too.
            break
    if not shp_within:
        # This import is a bit of a hack here.
        from pyOTPA.Trips_Generator import abs_zone_io
        cand_shapes = []
        cand_shape_bboxes = []
        cand_shape_ccds = []
        for found_index in found_indexes:
            for shp, shp_bbox in found_index:
                cand_shapes.append(shp)
                cand_shape_bboxes.append(shp_bbox)
                cand_shape_ccds.append(
                    shp.GetField(abs_zone_io.CCD_CODE_FIELD))
        print "Warning:- found requested geom %s was within %d of the "\
            "spatial index boxes (with bboxes %s).\nHowever didn't "\
            "find the geom to be within any of the %d shapes in these "\
            "index boxes (with bboxes %s, and CCD codes %s).\n"\
            "Is it outside the known region, or in "\
            "a different SRS to the index?" \
            % (geom.ExportToWkt(), len(found_indexes), found_bboxes,
               len(cand_shapes), cand_shape_bboxes, cand_shape_ccds)
        #import pdb
        #pdb.set_trace()
    return shp_within
