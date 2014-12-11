
import os.path
import operator
import itertools

GTFS_BEAN = "org.opentripplanner.graph_builder.model.GtfsBundle"
GTFS_PROP_PATH = "path"
GTFS_PROP_BIKES = "defaultBikesAllowed"
GTFS_PROP_AGENCY_ID = "defaultAgencyId"

MODE_ALLOW_BIKES = {
    'train': 'true',
    'tram': 'false',
    'bus': 'false',
    'bus-mway': 'false'}

GRAPH_JAR='graph-builder.jar'

MODE_PLURALS = {
    'train': 'trains',
    'tram': 'trams',
    'bus': 'buses',
    'bus-mway': 'mway_buses',
    }

def create_gtfs_xml_entry(mode, gtfs_type, gtfs_name, agency_id,
            get_gtfs_fname_func):
        gtfs_fname = get_gtfs_fname_func(mode, gtfs_type, gtfs_name)
        PRE = ' ' * 6 * 4
        gtfs_xml_entry = PRE + '<bean class="%s">\n' % GTFS_BEAN 
        PRE = ' ' * 7 * 4
        gtfs_xml_entry += PRE + '<property name="%s" value="%s" />\n' %\
            (GTFS_PROP_PATH, gtfs_fname)
        gtfs_xml_entry += PRE + '<property name="%s" value="%s" />\n' % \
            (GTFS_PROP_BIKES, MODE_ALLOW_BIKES[mode])
        gtfs_xml_entry += PRE + '<property name="%s" value="%s" />\n' % \
            (GTFS_PROP_AGENCY_ID, agency_id)
        PRE = ' ' * 6 * 4
        gtfs_xml_entry += PRE + '</bean>\n'
        return gtfs_xml_entry

def create_graph_xml(graph_spec, graph_full_dir, xml_file_base,
        get_gtfs_fname_func):
    gc_base_file = open(xml_file_base, 'r')
    graph_config_xml_base = gc_base_file.read()
    gc_base_file.close()

    graph_config_xml = graph_config_xml_base

    all_gtfs_xml_strs = ''
    PRE = ' ' * 6 * 4
    for mode in ['train', 'tram', 'bus', 'bus-mway']:
        if mode not in graph_spec:
            continue
        all_gtfs_xml_strs += PRE + "<!-- %s GTFS -->\n" % mode.title()
        for gtfs_type, gtfs_name, agency_id in graph_spec[mode]:
            entry_xml_str = create_gtfs_xml_entry(mode, gtfs_type, gtfs_name,
                agency_id, get_gtfs_fname_func)
            all_gtfs_xml_strs += entry_xml_str
    
    graph_config_xml = graph_config_xml.replace("GTFS_ENTRIES_REPLACE",
        all_gtfs_xml_strs)
    graph_config_xml = graph_config_xml.replace("GRAPH_BUILD_PATH_REPLACE",
        os.path.abspath(graph_full_dir))
    return graph_config_xml

def create_graph_config_file(graph_base_dir, graph_name, graph_spec,
        xml_file_base, get_gtfs_fname_func):
    graph_dir = graph_name
    graph_full_dir = os.path.abspath(
        os.path.join(graph_base_dir, graph_dir))
    print "Building OTP graph in Dir %s ..." % graph_full_dir
    if not os.path.exists(graph_full_dir):
        os.makedirs(graph_full_dir)
    graph_config_xml = create_graph_xml(graph_spec, graph_full_dir,
        xml_file_base, get_gtfs_fname_func)
    graph_config_xml_fname = os.path.join(graph_full_dir,
        "graph-config.xml")
    gc_file = open(graph_config_xml_fname, "w")
    gc_file.write(graph_config_xml)
    gc_file.close()
    return graph_config_xml_fname

def create_graph(graph_config_xml_fname, otp_base):
    graph_full_dir = os.path.dirname(graph_config_xml_fname)
    graph_build_log_fname = os.path.join(graph_full_dir, "build-graph-log.txt")
    jar_path = os.path.join(otp_base, "opentripplanner-graph-builder/target")
    cmdline = "java -Xmx4096M -jar %s %s > %s 2>&1" % \
        (os.path.join(jar_path, GRAPH_JAR),
         graph_config_xml_fname, graph_build_log_fname)
    print cmdline
    os.system(cmdline)
    print "...done."
    return
 
### Funcs for manipulating a group of graphs.

def pprint_all_graph_specs(pp, gspecs):
    """argument pp is a pretty printer."""
    for gname, gspec in gspecs.iteritems():
        print gname
        pp.pprint(gspec)
    print ""    

#def process_gtfs_entry_X(mode_spec, mode_ext,
#        mode_non_orig, mode_upgraded, mode_versions):
#   Must return a tuple of (graph type, gtfs name, agency id) - all str

def create_graphs(graph_name_base, process_gtfs_entry_func, list_iterator_func,
        *mode_specs):
    """process_gtfs_entry_func passed as a func pointer, since it is specific
    to the type of graphs you're handling.
    
    list_iterator_func will be applied to the extensions of the mode_specs.
    E.g. pass in itertools.product, or itertools.izip.
    """
    graph_specs = {}
    modes_list = map(operator.itemgetter(0), list(mode_specs))
    # There could legitimately be duplicates in the above, so build a list
    # with no dups.
    all_modes = []
    for mode in modes_list:
        if mode not in all_modes:
            all_modes.append(mode)
    for mode_combo in \
            list_iterator_func(*map(operator.itemgetter(2), list(mode_specs))):
        graph_name = graph_name_base + "-add"
        graph_spec = {}
        mode_non_orig = {}
        mode_upgraded = {}
        mode_versions = {}
        for mode in all_modes:
            graph_spec[mode] = []
            mode_non_orig[mode] = False
            mode_upgraded[mode] = ""
            mode_versions[mode] = None
        for mode_i, mode_ext in enumerate(mode_combo):
            mode = mode_specs[mode_i][0]
            if mode_ext == None or type(mode_ext) == str:
                gtfs_entry = process_gtfs_entry_func(mode_specs[mode_i], mode_ext,
                    mode_non_orig, mode_upgraded, mode_versions)
                graph_spec[mode].append(gtfs_entry)
            else:
                # There are multiple entries for this mode-type in the combo.
                mode_ext_group = mode_ext
                for sub_mode_ext in mode_ext_group:
                    gtfs_entry = process_gtfs_entry_func(mode_specs[mode_i],
                        sub_mode_ext, mode_non_orig, mode_upgraded,
                        mode_versions)
                    graph_spec[mode].append(gtfs_entry)
        for mode in all_modes:
            mode_str = ""
            if mode_non_orig[mode]:
                if mode_upgraded[mode]:
                    mode_str = '_%s_%s' \
                        % (mode_upgraded[mode], MODE_PLURALS[mode])
                else:
                    mode_str += '_non_upgraded_%s' % MODE_PLURALS[mode]
                if mode_versions[mode]:
                    mode_str += '-' + mode_versions[mode]
            graph_name += mode_str
        graph_specs[graph_name] = graph_spec
    return graph_specs
