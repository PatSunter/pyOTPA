import os
import os.path
import csv
import operator
import itertools

import makepaths
import taz_files
import make_od_matrix

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

def get_comp_csv_fname(run_name):
    return os.path.join(os.getcwd(), run_name, 'ODs_Comparison_Basic.csv')

def get_comp_shapefile_fname(run_name):
    return os.path.join(os.getcwd(), run_name,
        'OD_route_infos-%s.shp' % run_name)

def create_routing_result_output_paths(results_base_path, run_dicts,
        csv_zone_locs_fname=None):
    if csv_zone_locs_fname:
        taz_tuples = taz_files.read_tazs_from_csv(csv_zone_locs_fname)
        taz_ids = itertools.imap(operator.itemgetter(0), taz_tuples)
    for run_name, run_info in run_dicts.iteritems():
        if not csv_zone_locs_fname:
            zones_shp_file_name = run_info['zones']
            taz_tuples = taz_files.read_tazs_from_shp(zones_shp_file_name)
            taz_ids = itertools.imap(operator.itemgetter(0), taz_tuples)
        makepaths.make_paths(taz_ids,
            os.path.join(results_base_path, run_name))

def create_batch_config_files(template_filename, graphs_path,
        results_base_path, run_dicts):
    for run_name, run_data in run_dicts.iteritems():
        create_batch_config_file(template_filename, graphs_path,
            results_base_path, run_name, run_data)

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

def run_batch_calcs(template_filename, run_dicts, otp_config):
    for run_name, run_data in run_dicts.iteritems():
        run_batch_calc(run_name, run_data, otp_config)

def make_od_matrices(run_dicts, csv_zone_locs_fname=None):
    if csv_zone_locs_fname:
        taz_tuples = taz_files.read_tazs_from_csv(csv_zone_locs_fname)

    for run_name, run_data in run_dicts.iteritems():
        if not csv_zone_locs_fname:
            zones_shp_file_name = run_data['zones']
            taz_tuples = taz_files.read_tazs_from_shp(zones_shp_file_name)
        run_results_path = os.path.join(os.getcwd(), run_name)
        output_csv_filename = get_od_matrix_fname(run_name)
        print "Creating OD-Matrix file of results for run '%s' in file %s" % \
            (run_name, output_csv_filename)
        make_od_matrix.make_od_matrix(output_csv_filename,
            run_results_path, taz_tuples)

