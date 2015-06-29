
def flatten_dict(input_dict, max_levels=None):
    """'Flatten' a dictionary with multiple sub-levels into a single level
    dict, where each entry has a key which is a tuple of all original sub-dict
    keys. 
    e.g. calling flatten_dict on: {"A" : {"B":1, "C": 5}, "B": {"B":32, "A": 12}}
    produces: {('B', 'A'): 12, ('A', 'B'): 1, ('A', 'C'): 5, ('B', 'B'): 32}

    The optional max_levels can force stopping recursion at a certain depth,
    even if there are still dict's remaining.
    """
    return recurse_into_dict(input_dict, [], max_levels)

def recurse_into_dict(work_dict, prev_keys, max_levels=None):
    #print "recurse called with work_dict = %s, prev_keys = %s" \
    #    % (work_dict, prev_keys)
    first_val = work_dict.itervalues().next() 
    if isinstance(first_val, dict) and \
            ((not max_levels) or len(prev_keys) < max_levels-1):
        result = {}
        for kw, val in work_dict.iteritems():
            result.update(recurse_into_dict(val, prev_keys + [kw], max_levels))
    else:
        flat_dict_vals = {}
        for kw, val in work_dict.iteritems():
            flat_dict_vals[tuple(prev_keys + [kw])] = val
        result = flat_dict_vals
    return result

def remove_formatting_chars(in_str):
    out_str = in_str.replace('\n', '').replace('\t', '')
    out_str = out_str.replace(' '*4, ' ')
    return out_str

