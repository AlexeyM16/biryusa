import heapq
from services.geo import (
    init_advanced_gis, snap_to_water_and_connect, haversine_km,
    get_dynamic_physics, smooth_path, GRAPH_EDGES
)


def process_navigation(team_data, s_lat, s_lon, e_lat, e_lon, config, mode, pass_count, temp_c, oil_pct, current_fuel):
    init_advanced_gis()

    start_node, start_conns = snap_to_water_and_connect(s_lat, s_lon)
    end_node, end_conns = snap_to_water_and_connect(e_lat, e_lon)
    if start_node == end_node: return {"error": "Точки совпадают или находятся слишком близко."}

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

    k_load = team_data["configs"][config]["k_load"]
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

            if surf["hard"] and not allow_hard:
                continue

            e_time = dist / surf["spd"]
            e_fuel = dist * boat["base_l_per_km"] * surf["k_surf"] * k_load * mode_k
            e_risk = surf["risk"]

            if mode == "быстрый":
                weight = e_time
            elif mode == "экономичный":
                weight = e_fuel
            elif mode == "кратчайший":
                weight = dist
            elif mode == "безопасный":
                weight = dist + (e_risk ** 3) * 10

            new_cost = g_costs[curr] + weight

            if nxt not in g_costs or new_cost < g_costs[nxt]:
                g_costs[nxt] = new_cost
                parents[nxt] = curr

                h_dist = haversine_km(nxt[0], nxt[1], end_node[0], end_node[1])
                if mode == "быстрый":
                    h = h_dist / 64.0
                elif mode == "экономичный":
                    h = h_dist * boat["base_l_per_km"] * 0.9 * k_load * mode_k
                else:
                    h = h_dist

                heapq.heappush(queue, (new_cost + h, nxt))

    if end_node not in parents:
        return {"error": "Невозможно проложить безопасный маршрут. Попробуйте конфигурацию 'с поддувом'."}

    path = []
    curr = end_node
    while curr != start_node:
        path.append(curr)
        curr = parents[curr]
    path.append(start_node)
    path.reverse()

    path = smooth_path(path)

    tot_km = tot_time = tot_fuel = max_risk = tot_depth = oil_degradation = 0.0
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

        oil_degradation += dist * (0.1 if surf["planing"] else 0.5)

        if surf["hard"]: warnings.add(f"Маршрут проходит через опасный участок: {surf['label']}")
        if not surf["planing"]: warnings.add(f"Потеря глиссирования на участке: {surf['label']}")
        if e_risk >= 5: warnings.add(f"Зона высокого риска ({surf['label']})")

    rem = current_fuel - tot_fuel

    if rem < 0:
        warnings.add("НЕДОСТАТОЧНОЕ КОЛ-ВО БЕНЗИНА: МАРШРУТ НЕПРОХОДИМ!")
        max_risk = 7
    elif rem < (boat["tank_l"] * boat["reserve_frac_tank"]):
        warnings.add("ВНИМАНИЕ: Остаток топлива ниже допустимого резерва (20%)!")

    return {
        "km": round(tot_km, 1),
        "time_h": round(tot_time, 2),
        "fuel_l": round(tot_fuel, 1),
        "remainder_l": round(rem, 1) if rem >= 0 else 0,
        "avg_depth_m": round(tot_depth / max(1, len(path) - 1), 1),
        "oil_end_pct": round(max(0.0, oil_pct - oil_degradation), 1),
        "max_risk": max_risk,
        "warnings": list(warnings),
        "coords": path
    }