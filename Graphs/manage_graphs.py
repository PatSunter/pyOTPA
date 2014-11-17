
import os.path

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
