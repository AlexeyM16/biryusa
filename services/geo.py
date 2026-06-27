import json
import math
from shapely.geometry import shape, Point, LineString
from shapely.ops import unary_union, nearest_points

WATER_POLY = None
GRAPH_NODES = []
GRAPH_EDGES = {}
STEP = 0.002


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def line_of_sight(n1, n2):
    line = LineString([(n1[1], n1[0]), (n2[1], n2[0])])
    return WATER_POLY.contains(line)


IS_INITIALIZED = False


def init_advanced_gis():
    global WATER_POLY, GRAPH_NODES, GRAPH_EDGES

    if WATER_POLY is not None: return

    with open("water.geojson", "r", encoding="utf-8") as f:
        data = json.load(f)

    polys = [shape(feat["geometry"]) for feat in data.get("features", []) if shape(feat["geometry"]).is_valid]
    WATER_POLY = unary_union(polys)

    min_lat, max_lat = 55.70, 56.00
    min_lon, max_lon = 91.80, 92.45

    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            if WATER_POLY.contains(Point(lon, lat)):
                GRAPH_NODES.append((round(lat, 4), round(lon, 4)))
            lon += STEP
        lat += STEP

    for node in GRAPH_NODES:
        GRAPH_EDGES[node] = []
        lat, lon = node
        for dlat in [-STEP, 0, STEP]:
            for dlon in [-STEP, 0, STEP]:
                if dlat == 0 and dlon == 0: continue
                n_node = (round(lat + dlat, 4), round(lon + dlon, 4))
                if n_node in GRAPH_NODES and line_of_sight(node, n_node):
                    GRAPH_EDGES[node].append(n_node)


def smooth_path(path):
    if len(path) < 3: return path
    smoothed = [path[0]]
    i = 0
    while i < len(path) - 2:
        if line_of_sight(smoothed[-1], path[i + 2]):
            i += 1
        else:
            smoothed.append(path[i + 1])
            i += 1
    smoothed.append(path[-1])
    return smoothed


def snap_to_water_and_connect(lat, lon):
    pt = Point(lon, lat)
    if not WATER_POLY.contains(pt):
        p_safe, _ = nearest_points(WATER_POLY, pt)
        lat, lon = p_safe.y, p_safe.x

    node_coord = (lat, lon)
    visible_nodes = [
        n for n in GRAPH_NODES
        if haversine_km(lat, lon, n[0], n[1]) < 4.0 and line_of_sight(node_coord, n)
    ]

    if not visible_nodes:
        best = min(GRAPH_NODES, key=lambda n: haversine_km(lat, lon, n[0], n[1]))
        return node_coord, [best]
    return node_coord, visible_nodes


def get_dynamic_physics(lat, lon, temp_c, base_surfaces):
    pt = Point(lon, lat)
    dist_m = WATER_POLY.boundary.distance(pt) * 111000 * math.cos(math.radians(lat))

    depth = min(45.0, (dist_m + 15) * 0.12)

    if temp_c <= -15: return base_surfaces["ice"], depth
    if temp_c <= -5 and depth < 2.5: return base_surfaces["slush"], depth
    if depth < 2.5: return base_surfaces["shallow"], depth
    return base_surfaces["water"], depth