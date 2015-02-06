
import random
from datetime import time

from osgeo import ogr

class RandomTimeGenerator:
    def __init__(self, seed):
        self._random_seed = seed
        self._randomiser = random.Random(seed)

    def gen_time_in_range(self, time_start, time_end):
        assert time_end > time_start
        ts_min = time_start.hour * 60 + time_start.minute
        te_min = time_end.hour * 60 + time_end.minute
        gt_min = self._randomiser.randrange(ts_min, te_min)
        gen_time = time(gt_min / 60, gt_min % 60)
        return gen_time

class BasicRandomLocGenerator:
    def __init__(self, seed, bbox):
        self._random_seed = seed
        self._randomiser = random.Random(seed)
        self.bbox = bbox
    
    def gen_loc_within_zone(self, zone_code):
        # Ignore the zone code in this case.
        loc_x = self._randomiser.uniform(self.bbox[0][0], self.bbox[1][0])
        loc_y = self._randomiser.uniform(self.bbox[0][1], self.bbox[1][1])
        return (loc_x, loc_y)

class WithinZoneLocGenerator:
    def __init__(self, seed, zone_polys_dict):
        self._random_seed = seed
        self._randomiser = random.Random(seed)
        self._zone_polys_dict = zone_polys_dict
    
    def gen_loc_within_zone(self, zone_name):
        zone_poly = self._zone_polys_dict[zone_name]
        zone_env = zone_poly.GetEnvelope()
        while True:
            # First generate a random point within the extents
            loc_x = self._randomiser.uniform(zone_env[0], zone_env[1])
            loc_y = self._randomiser.uniform(zone_env[2], zone_env[3])
            loc_pt = ogr.Geometry(ogr.wkbPoint)
            loc_pt.AddPoint(loc_x, loc_y)
            if zone_poly.Contains(loc_pt):
                break
            else:
                loc_pt.Destroy()
        return loc_pt

class OD_Based_TripGenerator:
    def __init__(self, random_time_gen, od_counts,
            origin_loc_generator, dest_loc_generator, n_trips):
        self._random_time_gen = random_time_gen
        self._od_counts = od_counts
        self.n_trips = n_trips
        self._od_counts_total = sum(od_counts.itervalues())
        self._ordered_ods = sorted(od_counts.iterkeys())
        self._curr_trip_i = 0
        self._curr_od_i = 0
        self._init_ctrs_for_od(self._curr_od_i)
        self._origin_loc_generator = origin_loc_generator
        self._dest_loc_generator = dest_loc_generator

    def _init_ctrs_for_od(self, od_i):
        self._curr_od = self._ordered_ods[od_i]
        print "Updating to generate trips between ODs '%s' and '%s'" \
            % (self._curr_od[0], self._curr_od[1])
        self._trip_i_in_od = 0    
        self._scaled_trips_in_curr_od = self._calc_scaled_trips_in_od(
            self._curr_od)

    def gen_next(self):
        while self._trip_i_in_od >= self._scaled_trips_in_curr_od:
            if self._curr_od_i < (len(self._ordered_ods)-1):
                self._curr_od_i += 1
                self._init_ctrs_for_od(self._curr_od_i)
            else:
                return None

        origin_loc = self._origin_loc_generator.gen_loc_within_zone(
            self._curr_od[0])
        dest_loc = self._dest_loc_generator.gen_loc_within_zone(
            self._curr_od[1])
        # TODO:- need to link up start times with O-Ds properly later.
        T_START = time(06,00)
        T_END = time(11,00)
        start_time = self._random_time_gen.gen_time_in_range(T_START, T_END)
        trip = (origin_loc, dest_loc, start_time, self._curr_od[0], \
            self._curr_od[1])
        self._trip_i_in_od += 1
        self._curr_trip_i += 1
        return trip

    def _calc_scaled_trips_in_od(self, od_pair):
        base_trip_cnt = self._od_counts[od_pair]
        scaled_trip_cnt = int(round(base_trip_cnt * self.n_trips / \
            float(self._od_counts_total)))
        return scaled_trip_cnt

TEST_OD_COUNTS = {
    ("A", "A"): 254,
    ("A", "B"): 2345,
    ("A", "C"): 0,
    ("B", "A"): 43,
    ("B", "B"): 4356,
    ("B", "C"): 500,
    ("C", "A"): 23,
    ("C", "B"): 1231,
    ("C", "C"): 581,
    }

a_geom = ogr.Geometry(ogr.wkbLinearRing)
a_geom.AddPoint(144.765, -37.9)
a_geom.AddPoint(144.865, -37.9)
a_geom.AddPoint(144.865, -37.8)
a_geom.AddPoint(144.825, -37.85)
a_geom.AddPoint(144.8, -37.9)
a_geom.AddPoint(144.765, -37.9)
a_poly = ogr.Geometry(ogr.wkbPolygon)
a_poly.AddGeometry(a_geom)

b_geom = ogr.Geometry(ogr.wkbLinearRing)
b_geom.AddPoint(145.0, -37.70)
b_geom.AddPoint(145.05, -37.70)
b_geom.AddPoint(145.05, -37.60)
b_geom.AddPoint(145.0, -37.60)
b_geom.AddPoint(145.0, -37.70)
b_poly = ogr.Geometry(ogr.wkbPolygon)
b_poly.AddGeometry(b_geom)

c_geom = ogr.Geometry(ogr.wkbLinearRing)
c_geom.AddPoint(145.2, -37.65)
c_geom.AddPoint(145.3, -37.65)
c_geom.AddPoint(145.25, -37.68)
c_geom.AddPoint(145.2, -37.65)
c_poly = ogr.Geometry(ogr.wkbPolygon)
c_poly.AddGeometry(c_geom)

TEST_ZONE_POLYS_DICT = {
    "A": a_poly,
    "B": b_poly,
    "C": c_poly,
    }

def main():
    N_TRIPS = 20
    RANDOM_TIME_SEED = 5
    RANDOM_ORIGIN_SEED = 5
    RANDOM_DEST_SEED = 5
    od_counts = TEST_OD_COUNTS

    #MELB_BBOX = ((144.765, -37.9), (145.36, -37.645))
    #origin_loc_gen = BasicRandomLocGenerator(RANDOM_ORIGIN_SEED, MELB_BBOX)
    #dest_loc_gen = BasicRandomLocGenerator(RANDOM_DEST_SEED, MELB_BBOX)

    zone_polys_dict = TEST_ZONE_POLYS_DICT
    origin_loc_gen = WithinZoneLocGenerator(RANDOM_ORIGIN_SEED,
        zone_polys_dict)
    dest_loc_gen = WithinZoneLocGenerator(RANDOM_DEST_SEED,
        zone_polys_dict)

    random_time_gen = RandomTimeGenerator(RANDOM_TIME_SEED)

    trip_generator = OD_Based_TripGenerator(random_time_gen, od_counts,
        origin_loc_gen, dest_loc_gen, N_TRIPS)

    trips = []
    trip = trip_generator.gen_next()
    for trip_i in range(N_TRIPS):
        trip = trip_generator.gen_next()
        if not trip: break
        trips.append(trip)
        print "%f,%f to %f,%f at %s ('%s'->'%s')" % (trip[0].GetX(), trip[0].GetY(), \
            trip[1].GetX(), trip[1].GetY(), trip[2], trip[3], trip[4])
    print "Generated %d trips." % len(trips)

    return

if __name__ == "__main__":
    main()
