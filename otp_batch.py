import os
import os.path
import csv
import operator
import itertools

import makepaths
import taz_files
import make_od_matrix
import od_matrix_analysis

TAG_GRAPH = "REPLACE_GRAPH_NAME"
TAG_RUN_NAME = "REPLACE_RUN_NAME"
TAG_RESULTS_BASE_PATH = "REPLACE_RESULTS_BASE_PATH"
TAG_GRAPHS_PATH = "REPLACE_GRAPHS_PATH"
TAG_ZONE_SHP_FILE = "REPLACE_ZONE_SHP_FILE"

OTP_CONFIG_JAVA_MEM_ARGS = 'java_mem_args'
OTP_CONFIG_JAR_PATH = 'jar_path'

def get_xml_fname(run_name):
    return os.path.join(os.getcwd(), run_name, 'batch-routing-config.xml')

def get_log_fname(run_name):
    return os.path.join(os.getcwd(), run_name, 'batch-routing-run-log.txt')

def get_od_matrix_fname(run_name):
    return os.path.join(os.getcwd(), run_name, 'tazs_od_matrix.csv')

def get_comp_csv_fname(run_name, comparison_ext=None):
    if comparison_ext:
        comp_fname ='ODs_Comparison_Basic-%s.csv' % comparison_ext
    else:    
        comp_fname ='ODs_Comparison_Basic.csv'
    return os.path.join(os.getcwd(), run_name, comp_fname)

def get_comp_shapefile_fname(run_name):
    return os.path.join(os.getcwd(), run_name,
        'OD_route_infos-%s.shp' % run_name)

def create_routing_result_output_paths(results_base_path, run_dicts,
        csv_zone_locs_fname=None, runs_to_process=None):
    if csv_zone_locs_fname:
        taz_tuples = taz_files.read_tazs_from_csv(csv_zone_locs_fname)
        taz_ids = itertools.imap(operator.itemgetter(0), taz_tuples)
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        run_data = run_dicts[run_name]
        if not csv_zone_locs_fname:
            zones_shp_file_name = run_data['zones']
            taz_tuples = taz_files.read_tazs_from_shp(zones_shp_file_name)
            taz_ids = itertools.imap(operator.itemgetter(0), taz_tuples)
        out_subdirs = makepaths.get_paths(taz_ids,
            os.path.join(results_base_path, run_name))
        print "Making %d paths under dir %s" \
            % (len(out_subdirs), \
               os.path.join(results_base_path, run_name))
        makepaths.make_paths(out_subdirs)
    print ""        

def create_batch_config_files(template_filename, graphs_path,
        results_base_path, run_dicts, runs_to_process=None):
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        run_data = run_dicts[run_name]
        create_batch_config_file(template_filename, graphs_path,
            results_base_path, run_name, run_data)
    print ""            

def create_batch_config_file(template_filename, graphs_path, 
        results_base_path, run_name, run_data):
    try:
        graph_name = run_data['graph']
        zone_shp_file = run_data['zones']
    except TypeError:
        graph_name = run_data
        zone_shp_file = None
    template_XML_file = open(template_filename, 'r')
    template_XML = template_XML_file.read()
    template_XML_file.close()
    print "Creating XML file for run '%s' to use graph '%s':" % \
        (run_name, graph_name)
    new_fname = get_xml_fname(run_name)
    config_dir = os.path.dirname(new_fname)
    if not os.path.exists(config_dir):
        print "Making necessary directory %s" % config_dir
        os.mkdir(config_dir)
    print "Creating file %s" % new_fname
    new_XML = template_XML
    new_XML = new_XML.replace(TAG_GRAPHS_PATH, graphs_path)
    new_XML = new_XML.replace(TAG_RESULTS_BASE_PATH, results_base_path)
    new_XML = new_XML.replace(TAG_RUN_NAME, run_name)

    new_XML = new_XML.replace(TAG_GRAPH, graph_name)
    if zone_shp_file:
        new_XML = new_XML.replace(TAG_ZONE_SHP_FILE, zone_shp_file)
    new_XML_file = open(new_fname, "w")
    new_XML_file.write(new_XML)
    new_XML_file.close()

def run_batch_calc(run_name, run_data, otp_config):
    xml_fname = get_xml_fname(run_name)
    log_fname = get_log_fname(run_name)
    run_cmd = "java %s -jar %s %s > %s 2>&1" %\
        (otp_config[OTP_CONFIG_JAVA_MEM_ARGS], \
         otp_config[OTP_CONFIG_JAR_PATH], \
         xml_fname, log_fname)
    print "Command to run:"    
    print run_cmd
    print "Running ..."
    os.system(run_cmd)
    print "done"

def run_batch_calcs(template_filename, run_dicts, otp_config,
        runs_to_process=None, re_run=True):
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        run_data = run_dicts[run_name]
        out_files_exist = False
        if os.path.exists(get_log_fname(run_name)):
            out_files_exist = True
        if re_run == True or not out_files_exist:
            run_batch_calc(run_name, run_data, otp_config)
    print ""            

def make_od_matrices(run_dicts, csv_zone_locs_fname=None, runs_to_process=None):
    if csv_zone_locs_fname:
        taz_tuples = taz_files.read_tazs_from_csv(csv_zone_locs_fname)
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        run_data = run_dicts[run_name]
        if not csv_zone_locs_fname:
            zones_shp_file_name = run_data['zones']
            taz_tuples = taz_files.read_tazs_from_shp(zones_shp_file_name)
        run_results_path = os.path.join(os.getcwd(), run_name)
        output_csv_filename = get_od_matrix_fname(run_name)
        print "Creating OD-Matrix file of results for run '%s' in file %s" % \
            (run_name, output_csv_filename)
        make_od_matrix.make_od_matrix(output_csv_filename,
            run_results_path, taz_tuples)
    print ""            

def make_comparison_files(run_dicts, comparison_run_name, 
        nv_routes_interest_fname=None, csv_zone_locs_fname=None,
        runs_to_process=None, comparison_ext=None):
    """Make comparison spreadsheets, and GIS files, of travel times between
    each run in run_dicts, and times in the comparison_run_name run.
    Requires that the runs specified in run_dicts already exist, and OD matrix
    CSV files have been created in each directory using make_od_matrix.
    Only compare routes defined by OD pairs in the Netview file
    nv_routes_interest_fname. (TODO:- would be good to generalise the
    latter.)"""
    # Only import this here, since its only essential for running comparisons
    import numpy

    if csv_zone_locs_fname:
        taz_tuples_comp = taz_files.read_tazs_from_csv(csv_zone_locs_fname)
    else:
        zones_shp_file_name = run_dicts[comparison_run_name]['zones']
        taz_tuples_comp = taz_files.read_tazs_from_shp(zones_shp_file_name)

    max_zone_num = max(itertools.imap(operator.itemgetter(0), taz_tuples_comp))
    # Note: add one, since our OD points start from 1, and we will avoid
    #  converting back to zero etc to access the matrix.
    asize = (max_zone_num+1, max_zone_num+1)

    otp_od_matrix_curr_fname = get_od_matrix_fname(comparison_run_name)
    od_matrix_curr = numpy.zeros(asize)
    od_matrix_analysis.readOTPMatrix(otp_od_matrix_curr_fname, od_matrix_curr)

    if nv_routes_interest_fname:
        nv_mat = numpy.zeros(asize)
        # To get nroutes, really just need number of entries in this file ...
        nroutes = od_matrix_analysis.readNVMatrix(nv_routes_interest_fname, nv_mat)
        routesArray = od_matrix_analysis.readNVRouteIDs(nv_routes_interest_fname,
            nroutes)
    else:
        taz_ids_comp = itertools.imap(operator.itemgetter(0), taz_tuples_comp)
        routesArray = list(itertools.permutations(taz_ids_comp, 2))

    lonlats = numpy.zeros((max_zone_num+1, 2))
    for taz_tuple in taz_tuples_comp:
        lonlats[int(taz_tuple[0])] = [taz_tuple[1], taz_tuple[2]]
    
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        run_data = run_dicts[run_name]
        if run_name == comparison_run_name: continue

        od_matrix_new_fname = get_od_matrix_fname(run_name)
        if not csv_zone_locs_fname:
            zones_shp_file_name = run_data['zones']
            taz_tuples = taz_files.read_tazs_from_shp(zones_shp_file_name)
            max_zone_num = max(itertools.imap(operator.itemgetter(0),
                taz_tuples))
            asize = (max_zone_num+1, max_zone_num+1)
        od_matrix_new = numpy.zeros(asize)
        od_matrix_analysis.readOTPMatrix(od_matrix_new_fname, od_matrix_new)
        comp_csv_filename = get_comp_csv_fname(run_name, comparison_ext)
        od_matrix_analysis.saveComparisonFile(routesArray, od_matrix_curr,
            od_matrix_new, comp_csv_filename, ['OTPCUR', 'OTPNEW'])
        routesArray, otpCurrTimes, otpNew_Times = \
            od_matrix_analysis.readComparisonFile(comp_csv_filename)
        shapefilename = get_comp_shapefile_fname(run_name)
        od_matrix_analysis.createShapefile(routesArray, lonlats, otpCurrTimes,
            otpNew_Times, ['OTPCUR', 'OTPNEW'], shapefilename)    
    return
    print ""            

def print_comparison_stats(run_dicts, comparison_run_name, 
        runs_to_process=None, comparison_ext=None):
    if runs_to_process == None:
        runs_to_process = sorted(run_dicts.keys())
    for run_name in runs_to_process:
        if run_name == comparison_run_name: continue
        print "Computing stats for run '%s':" % run_name
        comp_csv_filename = get_comp_csv_fname(run_name, comparison_ext)
        stats = od_matrix_analysis.compute_comparison_stats(comp_csv_filename)
        od_matrix_analysis.print_comparison_stats(stats)
