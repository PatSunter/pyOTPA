from osgeo import ogr, osr

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

# Times are: 5AM, 6AM, 7AM, 8AM, 9AM, 10AM, 11AM blocks.
TEST_OD_COUNTS_SLAS_TIMES = {
    ("Melton (S) - East", "Melton (S) - East"):
        {"5:00": 30, "6:00": 24, "7:00": 200},
    ("Melton (S) - East", "Melbourne (C) - Inner"):
        {"5:00": 584, "6:00": 1023, "7:00": 899},
    ("Melton (S) - East", "Nillumbik (S) - South-West"):
        {"5:00": 0, "6:00": 0, "7:00": 0},
    ("Melbourne (C) - Inner", "Melton (S) - East"):
        {"5:00": 30, "6:00": 24, "7:00": 68},
    ("Melbourne (C) - Inner", "Melbourne (C) - Inner"):
        {"5:00": 987, "6:00": 2345, "7:00": 2999},
    ("Melbourne (C) - Inner", "Nillumbik (S) - South-West"):
        {"5:00": 100, "6:00": 204, "7:00": 200},
    ("Nillumbik (S) - South-West", "Melton (S) - East"):
        {"5:00": 30, "6:00": 100, "7:00": 109},
    ("Nillumbik (S) - South-West", "Melbourne (C) - Inner"):
        {"5:00": 99, "6:00": 654, "7:00": 543},
    ("Nillumbik (S) - South-West", "Nillumbik (S) - South-West"):
        {"5:00": 0, "6:00": 234, "7:00": 299},
    }
