import heapq

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
                    surf = surfaces.get(surf_name, surfaces.get("water"))
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