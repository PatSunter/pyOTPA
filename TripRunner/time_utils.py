
def get_total_sec(td):
    return td.days * 24 * 3600 + td.seconds + td.microseconds / float(10**6)

def get_td_pct(td1, td2):
    return get_total_sec(td1) / float(get_total_sec(td2)) * 100

