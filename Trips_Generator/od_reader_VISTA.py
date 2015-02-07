import csv
import sys
from datetime import time

#General strategy is
# Keep parsing up lines till I find one that says "Destination SLA"
# Then pull in all the other columns, so we get their indices.
# Then skip out the "Annotations" columns, build a dict of Indices->SLA

# Next row then can find the "Origin SLA" and "Start Hour of Travel" column
# indices.
# Then for the rest of the rows:-
 # If the "Origin SLA" contains something:- start a new dict.
 # Then parse the "start hour of travel".
 # Then for each of the destination indices:- pull out relevant value, add an
 # entry.

def get_dest_sla_index_map(dest_hdrs_row, slas_to_ignore):
    dest_hdrs_row_clean = map(lambda x: x.strip('"'), dest_hdrs_row)
    dest_sla_hdr_i = dest_hdrs_row_clean.index("Destination SLA")
    dest_sla_index_map = {}
    for ii, hdr_entry in enumerate(dest_hdrs_row_clean[dest_sla_hdr_i+1:]):
        # Make sure there are no repeats - not interested in subsidiary
        # columns
        if hdr_entry in dest_sla_index_map.values():
            break
        if not (hdr_entry.endswith("Annotations") or hdr_entry.endswith("RSE")):
            dest_sla = hdr_entry
            if dest_sla not in slas_to_ignore:
                dest_sla_index_map[dest_sla_hdr_i+1+ii] = dest_sla
    return dest_sla_index_map        

def read_od_trip_cnts_by_dep_hour(vista_csv_filename, slas_to_ignore=None):
    # Assumes CSV file is in the form exported by VISTA website.
    csv_file = open(vista_csv_filename, 'r')
    reader = csv.reader(csv_file, delimiter=',', quotechar='"')
    if slas_to_ignore == None:
        slas_to_ignore = []

    while True:
        try:
            row = reader.next()
        except StopIteration:
            sys.exit("Error: OD matrix didn't contain needed headers.")
        if "Destination SLA" in map(lambda x: x.strip('"'), row):
            dest_hdrs_row = row
            break
    dest_sla_index_map = get_dest_sla_index_map(dest_hdrs_row,
        slas_to_ignore)
    dest_slas = [dest_sla_index_map[ii] for ii in \
        sorted(dest_sla_index_map.iterkeys())]
    # One more row to define start hour of travel
    row = reader.next()
    matrix_row_hdr_line_clean = map(lambda x: x.strip('"'), row)
    origin_sla_ii = matrix_row_hdr_line_clean.index("Origin SLA")
    start_hr_ii = matrix_row_hdr_line_clean.index("Start hour of travel")

    # Now process the rest of the entries.
    od_trip_cnts_by_dep_hour = {}
    origin_slas = []
    for matrix_entry_row in reader:
        origin_sla_entry = matrix_entry_row[origin_sla_ii]    
        if len(origin_sla_entry) > 0:
            origin_sla = origin_sla_entry.strip('"')
            if origin_sla not in slas_to_ignore:
                origin_slas.append(origin_sla)
                for dest_sla in dest_slas:
                    od_pair = (origin_sla, dest_sla)
                    od_trip_cnts_by_dep_hour[od_pair] = {}
        if origin_sla in slas_to_ignore:
            continue
        start_time_entry = matrix_entry_row[start_hr_ii].strip('"')
        start_time_hr = start_time_entry[0:-2]
        start_time_am_pm = start_time_entry[-2:]
        start_hr_24 = int(start_time_hr)
        if start_time_am_pm == "pm": start_hr_24 += 12
        start_time = time(hour=start_hr_24)
        start_time_str = start_time.strftime("%H:%M")
        for dest_sla_i, dest_sla in dest_sla_index_map.iteritems():
            od_pair = (origin_sla, dest_sla)
            od_trip_cnts_by_dep_hour[od_pair][start_time_str] = \
                int(round(float(matrix_entry_row[dest_sla_i])))

    return od_trip_cnts_by_dep_hour, origin_slas, dest_slas
