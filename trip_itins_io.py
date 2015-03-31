
import os, os.path
import sys
import glob

import TripItinerary

LOAD_STATUS_PRINT_PERCENT = 5

def save_trip_itineraries(output_base_dir, trip_results_by_graph):
    print "\nSaving trip itinerary results to base dir %s:" % output_base_dir
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
    for graph_name, trip_results in trip_results_by_graph.iteritems():
        saved_valid_cnt = 0
        subdir = os.path.join(output_base_dir, graph_name)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        for trip_id, trip_itin in trip_results.iteritems():
            fname = os.path.join(subdir, "%s.json" % trip_id)
            if trip_itin:
                trip_itin.save_to_file(fname)
                saved_valid_cnt += 1
        print "...saved %d valid results (out of %d trip reqs) on "\
            "graph '%s' to dir %s ." \
            % (saved_valid_cnt, len(trip_results), graph_name, subdir)
    return

def load_trip_itineraries(output_base_dir, graph_names=None):
    print "\nLoading trip itinerary results from base dir %s:" \
        % output_base_dir
    trip_results_by_graph = {}
    if not graph_names:
        # Calculate these based on all sub-directories of output dir.
        graph_names = []
        for entry in os.listdir(output_base_dir):
            if os.path.isdir(os.path.join(output_base_dir, entry)):
                graph_names.append(entry)
    for graph_name in graph_names:
        print "Loading results for graph %s" % graph_name
        trip_results = {}
        subdir = os.path.join(output_base_dir, graph_name)
        trip_result_files = glob.glob("%s%s*.json" % (subdir, os.sep))
        if len(trip_result_files) == 0:
            print "Error:- no trip results found in dir %s." % (subdir)
            sys.exit(1)
        else:
            print "Found %d result files in this directory." % \
                len(trip_result_files)
        load_count_print_inc = LOAD_STATUS_PRINT_PERCENT / 100.0 \
            * len(trip_result_files)
        load_count_print_inc = max(1, load_count_print_inc)
        next_print_cnt = load_count_print_inc
        for ii, fname in enumerate(trip_result_files):
            fbase = os.path.basename(fname)
            trip_id = os.path.splitext(fbase)[0]
            itin = TripItinerary.read_trip_itin_from_file(fname)
            trip_results[trip_id] = itin
            loaded_cnt = ii + 1
            if loaded_cnt > next_print_cnt:
                while loaded_cnt > next_print_cnt:
                    next_print_cnt += load_count_print_inc
                loaded_pct = loaded_cnt / float(len(trip_result_files)) * 100.0
                print "  ...loaded %d results (%.2f %% of total)" \
                    % (loaded_cnt, loaded_pct)    

                
        trip_results_by_graph[graph_name] = trip_results
        print "...loaded %d results on graph '%s' from dir %s ." \
            % (len(trip_results), graph_name, subdir)
    return trip_results_by_graph

