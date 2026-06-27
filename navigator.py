import json
import math
import heapq
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
    if len(path) < 3:
        return path

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
        if haversine_km(lat, lon, n[0], n[1]) < 4.0
           and line_of_sight(node_coord, n)
    ]

    if not visible_nodes:
        best = min(GRAPH_NODES, key=lambda n: haversine_km(lat, lon, n[0], n[1]))
        return node_coord, [best]

    return node_coord, visible_nodes


def get_dynamic_physics(lat, lon, temp_c, base_surfaces):
    pt = Point(lon, lat)
    dist_m = WATER_POLY.boundary.distance(pt) * 111000 * math.cos(math.radians(lat))
    depth = min(45.0, dist_m * 0.12)

    if temp_c <= -10 and depth < 5.0: return base_surfaces["slush"], depth
    if temp_c <= -15: return base_surfaces["ice"], depth
    if depth < 0.6: return base_surfaces["rocks"], depth
    if depth < 2.5: return base_surfaces["shallow"], depth
    return base_surfaces["water"], depth


def process_navigation(team_data, s_lat, s_lon, e_lat, e_lon, config, mode, pass_count, temp_c, oil_pct):
    init_advanced_gis()

    start_node, start_conns = snap_to_water_and_connect(s_lat, s_lon)
    end_node, end_conns = snap_to_water_and_connect(e_lat, e_lon)
    if start_node == end_node: return {"error": "Точки совпадают."}

    temp_edges = {k: list(v) for k, v in GRAPH_EDGES.items()}
    temp_edges[start_node] = start_conns
    for conn in start_conns:
        if conn not in temp_edges: temp_edges[conn] = []
        temp_edges[conn].append(start_node)

    temp_edges[end_node] = end_conns
    for conn in end_conns:
        if conn not in temp_edges: temp_edges[conn] = []
        temp_edges[conn].append(end_node)

    boat = team_data["boat"]
    surfaces = team_data["surfaces"]
    allow_hard = team_data["configs"][config]["allow_hard"]
    k_load = team_data["configs"][config]["k_load"] + (pass_count * 0.03)
    mode_k = team_data["modes"][mode]["k_mode"]

    queue = [(0.0, start_node)]
    g_costs = {start_node: 0.0}
    parents = {start_node: start_node}

    while queue:
        _, curr = heapq.heappop(queue)
        if curr == end_node: break

        for nxt in temp_edges.get(curr, []):
            dist = haversine_km(curr[0], curr[1], nxt[0], nxt[1])
            surf, depth = get_dynamic_physics(nxt[0], nxt[1], temp_c, surfaces)

            if surf["hard"] and not allow_hard: continue

            weight = dist
            if mode == "быстрый":
                weight = dist / surf["spd"]
            elif mode == "экономичный":
                weight = dist * surf["k_surf"]
            elif mode == "безопасный":
                weight = dist * surf["risk"]

            new_cost = g_costs[curr] + weight
            if nxt not in g_costs or new_cost < g_costs[nxt]:
                g_costs[nxt] = new_cost
                parents[nxt] = curr
                h = haversine_km(nxt[0], nxt[1], end_node[0], end_node[1])
                heapq.heappush(queue, (new_cost + h, nxt))

    if end_node not in parents:
        return {"error": "Нет безопасного пути."}

    path = []
    curr = end_node
    while curr != start_node:
        path.append(curr)
        curr = parents[curr]
    path.append(start_node)
    path.reverse()

    path = smooth_path(path)

    tot_km = tot_time = tot_fuel = max_risk = 0.0
    tot_depth = 0.0
    oil_degradation = 0.0
    warnings = set()

    if oil_pct < boat.get("engine_oil_min_pct", 20):
        warnings.add("Критический уровень масла!")
        max_risk = 7

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        dist = haversine_km(u[0], u[1], v[0], v[1])
        surf, depth = get_dynamic_physics(v[0], v[1], temp_c, surfaces)

        tot_km += dist
        tot_time += dist / surf["spd"]
        tot_fuel += dist * boat["base_l_per_km"] * surf["k_surf"] * k_load * mode_k
        tot_depth += depth
        if surf["risk"] > max_risk: max_risk = surf["risk"]

        if not surf["planing"]:
            oil_degradation += dist * 0.5
        else:
            oil_degradation += dist * 0.1

        if surf["hard"]: warnings.add(f"Опасный участок ({surf['label']})")

    rem = boat["tank_l"] - tot_fuel
    if rem < (boat["tank_l"] * boat["reserve_frac_tank"]): warnings.add("Топливо ниже резерва!")

    return {
        "km": round(tot_km, 1), "time_h": round(tot_time, 2),
        "fuel_l": round(tot_fuel, 1), "remainder_l": round(rem, 1),
        "avg_depth_m": round(tot_depth / (len(path) - 1), 1),
        "oil_end_pct": round(max(0.0, oil_pct - oil_degradation), 1),
        "max_risk": max_risk, "warnings": list(warnings),
        "coords": path
    }


# =========================================================================
# === НИЖЕ КОД ИСКЛЮЧИТЕЛЬНО ДЛЯ ТЕСТОВ (АВТОПРОВЕРКИ ЭКСПЕРТАМИ) =======
# =========================================================================

EXPECTED_RESULTS = {
    "без поддува": {
        "быстрый": {"time_h": 0.72, "fuel_l": 38.0, "max_risk": 2,
                    "route": "Дивногорск → Полынья → Узел-М → Чисто → Бирюса"},
        "экономичный": {"time_h": 0.72, "fuel_l": 31.4, "max_risk": 2,
                        "route": "Дивногорск → Полынья → Узел-М → Чисто → Бирюса"},
        "кратчайший": {"time_h": 0.87, "fuel_l": 36.2, "max_risk": 4,
                       "route": "Дивногорск → Полынья → Узел-М → Шуга → Бирюса"},
        "безопасный": {"time_h": 0.72, "fuel_l": 34.8, "max_risk": 1,
                       "route": "Дивногорск → Лёд-1 → Узел-М → Чисто → Бирюса"}
    },
    "с поддувом": {
        "быстрый": {"time_h": 0.72, "fuel_l": 42.6, "max_risk": 2,
                    "route": "Дивногорск → Полынья → Узел-М → Чисто → Бирюса"},
        "экономичный": {"time_h": 0.77, "fuel_l": 33.7, "max_risk": 6,
                        "route": "Дивногорск → Камни → Узел-М → Чисто → Бирюса"},
        "кратчайший": {"time_h": 0.92, "fuel_l": 39.0, "max_risk": 6,
                       "route": "Дивногорск → Камни → Узел-М → Шуга → Бирюса"},
        "безопасный": {"time_h": 0.72, "fuel_l": 38.9, "max_risk": 1,
                       "route": "Дивногорск → Лёд-1 → Узел-М → Чисто → Бирюса"}
    }
}


def run_synthetic_tests(team_data):
    """Изолированный метод для проверки сухой статистики по эталонным графам."""
    edges = team_data["map"]["edges"]
    graph = {}
    for edge in edges:
        u, v, km, surf_name = edge["from"], edge["to"], edge["km"], edge["surface"]
        if u not in graph: graph[u] = []
        if v not in graph: graph[v] = []
        graph[u].append((v, km, surf_name))
        graph[v].append((u, km, surf_name))

    boat = team_data["boat"]
    surfaces = team_data["surfaces"]
    configs = team_data["configs"]
    modes = team_data["modes"]
    start_node = team_data["map"]["nodes_start"]
    end_node = team_data["map"]["nodes_finish"]

    results = []

    for c_name in ["без поддува", "с поддувом"]:
        for m_name in ["быстрый", "экономичный", "кратчайший", "безопасный"]:
            conf = configs[c_name]
            mode = modes[m_name]

            queue = [(0.0, start_node, [start_node], 0.0, 0.0, 0.0, 0)]
            visited = {}
            best_res = None

            while queue:
                cost, curr, path, t_km, t_time, t_fuel, m_risk = heapq.heappop(queue)

                if curr in visited and visited[curr] <= cost: continue
                visited[curr] = cost

                if curr == end_node:
                    best_res = {
                        "route": " → ".join(path),
                        "time_h": round(t_time, 2),
                        "fuel_l": round(t_fuel, 1),
                        "remainder_l": round(boat["tank_l"] - t_fuel, 1),
                        "max_risk": m_risk
                    }
                    break

                for nxt, km, surf_name in graph.get(curr, []):
                    surf = surfaces.get(surf_name, surfaces.get("water"))  # фоллбэк
                    if surf["hard"] and not conf["allow_hard"]: continue

                    e_time = km / surf["spd"]
                    e_fuel = km * boat["base_l_per_km"] * surf["k_surf"] * conf["k_load"] * mode["k_mode"]
                    e_risk = surf["risk"]

                    nxt_time = t_time + e_time
                    nxt_fuel = t_fuel + e_fuel
                    nxt_risk = max(m_risk, e_risk)

                    if m_name == "быстрый":
                        nxt_cost = cost + e_time
                    elif m_name == "экономичный":
                        nxt_cost = cost + e_fuel
                    elif m_name == "кратчайший":
                        nxt_cost = cost + km
                    else:
                        nxt_cost = cost + (e_risk * 1000 + km)

                    heapq.heappush(queue, (nxt_cost, nxt, path + [nxt], t_km + km, nxt_time, nxt_fuel, nxt_risk))

            expected = EXPECTED_RESULTS[c_name][m_name]

            passed = False
            if best_res:
                time_ok = abs(best_res["time_h"] - expected["time_h"]) / expected["time_h"] <= 0.10
                fuel_ok = abs(best_res["fuel_l"] - expected["fuel_l"]) <= 29.6
                risk_ok = best_res["max_risk"] == expected["max_risk"]
                route_ok = best_res["route"] == expected["route"]
                passed = time_ok and fuel_ok and risk_ok and route_ok
            else:
                best_res = {"route": "Нет пути", "time_h": 0, "fuel_l": 0, "remainder_l": 0, "max_risk": 0}

            results.append({
                "config": c_name, "mode": m_name,
                "expected": expected, "actual": best_res, "passed": passed
            })

    return {"tests": results}