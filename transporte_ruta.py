import random
from datetime import datetime
import pandas as pd
import networkx as nx
import heapq

# ----------------------------
# 1) Generador de dataset
# ----------------------------
random.seed(123)

stops_sample = [
    "Usme", "Portal Sur", "Centro", "San Victorino", "Av.Calle26", "Modelo", "Chapinero",
    "Usaquén", "Suba", "Chía", "Kennedy", "Acueducto", "SanAndresito", "Marly", "LasAguas",
    "SimónBolívar", "ZonaFranc", "Avenida19", "Calle80", "NQS", "Avenida39", "Museo", "PortalNorte",
    "Bosa", "Engativá", "Soacha", "CiudadBolívar", "Tunal", "Fontibón", "Teusaquillo", "Galerías",
    "Parque93", "Cedritos", "Monserrate", "La Candelaria", "ColinaCampestre", "El Tintal", "Salitre",
    "GranEstación", "PlazaBolívar", "Restrepo", "Venecia", "Marsella", "La Castellana", "Alquería", "Quirigua"
]
modes = ["transmilenio_troncal", "alimentador", "sitp_urban", "sitp_complementaria", "cable"]
operators = ["Transmilenio S.A.", "Operador A", "Operador B", "Empresa SITP", "Consorcio Zonal"]

def random_time_str(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def generate_dataset(csv_path="bogota_transit_dataset_500.csv", num_routes=500):
    routes = []
    for i in range(1, num_routes+1):
        route_id = f"R{i:04d}"
        mode = random.choice(modes)
        num_stops = random.randint(5, 20)
        stops = random.sample(stops_sample, num_stops)
        start_stop = stops[0]
        end_stop = stops[-1]
        distance_km = num_stops * random.uniform(0.7, 1.2)
        travel_time_mins = max(5, int((distance_km / 20) * 60 + random.gauss(0, 5)))
        dwell_total = int(num_stops * random.uniform(0.3, 1.0))
        travel_time_mins += dwell_total
        frequency_min = random.choice([5,7,10,12,15,20,30])
        operator = random.choice(operators)
        start_time = random.randint(4*60, 7*60)
        end_time = random.randint(20*60, 24*60-1)
        trips_per_day = max(1, int((end_time - start_time) / (frequency_min)))
        route_name = f"{mode.upper()} {start_stop} — {end_stop}"
        geometry = "LINESTRING(...)"
        routes.append({
            "route_id": route_id,
            "route_name": route_name,
            "mode": mode,
            "operator": operator,
            "start_stop": start_stop,
            "end_stop": end_stop,
            "stops_count": num_stops,
            "stops_list": ";".join(stops),
            "distance_km_est": round(distance_km,2),
            "total_travel_time_min": travel_time_mins,
            "dwell_time_total_min": dwell_total,
            "avg_speed_kmh_est": round(distance_km / (travel_time_mins/60), 2),
            "frequency_min": frequency_min,
            "service_start": datetime.strptime(random_time_str(start_time), "%H:%M").time().isoformat(),
            "service_end": datetime.strptime(random_time_str(end_time), "%H:%M").time().isoformat(),
            "trips_per_day_est": trips_per_day,
            "geometry_wkt": geometry,
            "source": "synthetic_generated_by_chatgpt"
        })
    df = pd.DataFrame(routes)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"✅ Archivo creado: {csv_path}")
    return csv_path

# ----------------------------
# 2) Construcción de base de conocimiento desde el CSV
# ----------------------------
# Definimos reglas sencillas que pueden personalizarse.
DEFAULT_RULES = {
    "bloquear_estaciones": [],               # lista de nombres de estaciones a bloquear
    "preferir_accesible": True,              # si true penaliza estaciones no accesibles
    "penalizacion_no_accesible": 100,        # minutos añadidos para estaciones no accesibles
    "penalizar_transbordo_min": 3,           # minutos añadidos al cambiar de linea
    "estadisticas": True
}

# Para el ejemplo sintetizamos atributos de estaciones (lat/lon/estado/accesible)
# como no tenemos coordenadas reales, generamos coordenadas ficticias por nombre.
def synth_station_attributes(stop_name):
    # hash simple para reproducibilidad
    seed = sum(ord(c) for c in stop_name) % 1000
    lat = 4.6 + (seed % 100) * 0.0005
    lon = -74.08 + (seed % 100) * 0.0006
    estado = "open" if (seed % 17) != 0 else "closed"   # algunas cerradas
    accesible = (seed % 5) != 0
    return {"id": stop_name, "nombre": stop_name, "lat": lat, "lon": lon, "estado": estado, "accesible": accesible}

# ----------------------------
# 3) Construir grafo desde rutas (CSV)
# ----------------------------
def build_graph_from_csv(csv_path, reglas=DEFAULT_RULES):
    df = pd.read_csv(csv_path, encoding="utf-8")
    G = nx.DiGraph()
    # Crear nodos por cada parada encontrada en any stops_list
    estaciones_map = {}
    for _, row in df.iterrows():
        stops = str(row["stops_list"]).split(";")
        for s in stops:
            if s not in estaciones_map:
                estaciones_map[s] = synth_station_attributes(s)
    # Añadir nodos
    for s, attrs in estaciones_map.items():
        G.add_node(s, **attrs)
    # Añadir aristas en orden de parada para cada ruta; línea = route_id (para distinguir)
    for _, row in df.iterrows():
        route_id = row["route_id"]
        tiempo_total = float(row["total_travel_time_min"])
        stops = str(row["stops_list"]).split(";")
        if len(stops) < 2:
            continue
        # repartir tiempo total entre tramos
        tramo_time = max(1.0, tiempo_total / (len(stops)-1))
        for i in range(len(stops)-1):
            u = stops[i]; v = stops[i+1]
            # si ya existe arco entre u->v, elegimos el mínimo tiempo (mejor servicio)
            if G.has_edge(u, v):
                existing = G[u][v]
                existing_time = existing.get("tiempo", float("inf"))
                if tramo_time < existing_time:
                    G[u][v].update({"tiempo": tramo_time, "linea": route_id, "mode": row["mode"], "operator": row["operator"]})
            else:
                G.add_edge(u, v, tiempo=tramo_time, linea=route_id, mode=row["mode"], operator=row["operator"])
            # si ruta es bidireccional implícita (asimilamos muchas rutas bidireccionales)
            if not G.has_edge(v, u):
                G.add_edge(v, u, tiempo=tramo_time, linea=route_id, mode=row["mode"], operator=row["operator"])
    # Aplicar regla: bloquear estaciones listadas y las que tengan estado closed
    for blocked in reglas.get("bloquear_estaciones", []):
        if G.has_node(blocked):
            G.remove_node(blocked)
    for node, data in list(G.nodes(data=True)):
        if data.get("estado") == "closed":
            G.remove_node(node)
    # Aplicar preferencia accesible: penalizar aristas que van a estaciones no accesibles
    if reglas.get("preferir_accesible", False):
        penal = reglas.get("penalizacion_no_accesible", 0)
        for u, v, data in G.edges(data=True):
            dst_accesible = G.nodes[v].get("accesible", False)
            if not dst_accesible:
                data["tiempo"] = data.get("tiempo", 0) + penal
    return G

# ----------------------------
# 4) Algoritmo de ruta: Dijkstra adaptado para penalizar transbordos
# ----------------------------
def dijkstra_with_transfer_penalty(G, origen, destino, penal_transbordo=3):
    if origen not in G.nodes or destino not in G.nodes:
        return None
    # estado del nodo incluye la linea previa para contabilizar transbordos
    pq = []
    heapq.heappush(pq, (0.0, origen, None, [origen]))  # (coste, nodo, linea_prev, path)
    visited = {}  # (nodo, linea_prev) -> mejor coste
    while pq:
        coste, nodo, linea_prev, path = heapq.heappop(pq)
        if nodo == destino:
            return {"coste_min": coste, "ruta": path}
        key = (nodo, linea_prev)
        if visited.get(key, float("inf")) <= coste:
            continue
        visited[key] = coste
        for vecino in G.neighbors(nodo):
            edge = G[nodo][vecino]
            base = float(edge.get("tiempo", 1.0))
            linea = edge.get("linea", None)
            extra = penal_transbordo if (linea_prev is not None and linea != linea_prev) else 0
            nuevo_coste = coste + base + extra
            key2 = (vecino, linea)
            if visited.get(key2, float("inf")) > nuevo_coste:
                heapq.heappush(pq, (nuevo_coste, vecino, linea, path + [vecino]))
    return None

# ----------------------------
# 5) Utilidades y presentación
# ----------------------------
def describe_route(G, result):
    if not result:
        return "No existe ruta disponible con las reglas aplicadas."
    ruta = result["ruta"]
    total = round(result["coste_min"], 2)
    detalles = []
    transbordos = 0
    prev_line = None
    for i in range(len(ruta)-1):
        u = ruta[i]; v = ruta[i+1]
        data = G[u][v]
        linea = data.get("linea", "?")
        tiempo = round(data.get("tiempo", 0),2)
        detalles.append(f"{u} -> {v} via {linea} tiempo {tiempo}min")
        if prev_line is not None and linea != prev_line:
            transbordos += 1
        prev_line = linea
    texto = f"Ruta encontrada (coste estimado): {total} minutos\nNúmero de transbordos estimado: {transbordos}\n" + "\n".join(detalles)
    return texto

# ----------------------------
# 6) Flujo principal
# ----------------------------
def main():
    csv_path = "bogota_transit_dataset_500.csv"
    # Generar dataset si no existe o siempre (aquí lo regeneramos para reproducibilidad)
    generate_dataset(csv_path, num_routes=500)

    # Reglas de ejemplo (puedes editarlas)
    reglas = DEFAULT_RULES.copy()
    reglas["bloquear_estaciones"] = ["La Candelaria", "ColinaCampestre"]   # ejemplo: bloquear manualmente
    reglas["preferir_accesible"] = True
    reglas["penalizacion_no_accesible"] = 50
    reglas["penalizar_transbordo_min"] = 10

    print("Cargando grafo desde CSV...")
    G = build_graph_from_csv(csv_path, reglas=reglas)
    print(f"Nodos en grafo: {len(G.nodes)}; Arcos: {len(G.edges)}")

    origen = "Usme"
    destino = "Chía"
    print(f"Calculando mejor ruta de {origen} a {destino} con penalización por transbordo {reglas['penalizar_transbordo_min']}min...")
    resultado = dijkstra_with_transfer_penalty(G, origen, destino, penal_transbordo=reglas["penalizar_transbordo_min"])
    print(describe_route(G, resultado))

if __name__ == "__main__":
    main()