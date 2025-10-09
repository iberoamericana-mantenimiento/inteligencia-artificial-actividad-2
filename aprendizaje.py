import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import joblib

# modelos
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, precision_score, recall_score, f1_score, classification_report

# Generar dataset sintético de rutas (usa tu función o genera nuevo)
def generate_routes(csv_path="bogota_transit_dataset_500.csv", num_routes=500, seed=123):
    random.seed(seed)
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
            "avg_speed_kmh_est": round(distance_km / (travel_time_mins/60 + 1e-6), 2),
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

# Expandir por viaje/trip y simular observaciones
def expand_to_trips(csv_path, trips_csv="trips_expanded.csv", seed=123):
    random.seed(seed)
    df = pd.read_csv(csv_path, encoding="utf-8")
    trips = []
    for _, r in df.iterrows():
        freq = max(1, int(r["frequency_min"]))
        start = datetime.strptime(r["service_start"], "%H:%M:%S").replace(year=2025, month=10, day=1)
        for t in range(r["trips_per_day_est"]):
            depart = start + timedelta(minutes=int(t*freq))
            # Simula variabilidad por hora pico (6-9 y 16-19)
            hour = depart.hour
            peak_factor = 1.0
            if 6 <= hour <= 9 or 16 <= hour <= 19:
                peak_factor = random.uniform(1.05, 1.35)
            # clima aleatorio simple (0=normal, 1=lluvia)
            rain = random.random() < 0.12
            if rain:
                peak_factor *= random.uniform(1.05, 1.25)
            # simular observed travel time con ruido
            base = float(r["total_travel_time_min"])
            noise = random.gauss(0, 0.08)  # 8% ruido relativo
            observed = max(1.0, base * peak_factor * (1 + noise))
            # pasajeros simulados: depende del modo y frecuencia
            mode = r["mode"]
            if mode == "transmilenio_troncal":
                lam = max(20, int(200 / max(1, r["frequency_min"])))
            elif mode == "alimentador":
                lam = 30
            else:
                lam = 15
            # variar por hora pico
            passengers = np.random.poisson(lam * (1.2 if peak_factor>1.05 else 1.0))
            trips.append({
                "route_id": r["route_id"],
                "mode": mode,
                "operator": r["operator"],
                "departure_time": depart.isoformat(),
                "hour": depart.hour,
                "weekday": depart.weekday(),
                "stops_count": r["stops_count"],
                "distance_km_est": r["distance_km_est"],
                "scheduled_travel_time_min": r["total_travel_time_min"],
                "observed_travel_time_min": round(observed,2),
                "passenger_count": int(passengers),
                "frequency_min": r["frequency_min"],
                "trips_per_day_est": r["trips_per_day_est"],
                "source": r["source"]
            })
    df_trips = pd.DataFrame(trips)
    df_trips.to_csv(trips_csv, index=False, encoding="utf-8")
    print(f"✅ Trips generado: {trips_csv} filas: {len(df_trips)}")
    return trips_csv

# Crear labels útiles: delay_flag y high_demand
def label_trips(trips_csv, labeled_csv="trips_labeled.csv", demand_threshold_quantile=0.85):
    df = pd.read_csv(trips_csv, parse_dates=["departure_time"])
    # delay: observed - scheduled
    df["delay_min"] = df["observed_travel_time_min"] - df["scheduled_travel_time_min"]
    df["delayed_flag"] = (df["delay_min"] > 5).astype(int)  # ejemplo: >5min
    # high demand según umbral cuantifico por route/hour
    threshold = df["passenger_count"].quantile(demand_threshold_quantile)
    df["high_demand"] = (df["passenger_count"] >= threshold).astype(int)
    df.to_csv(labeled_csv, index=False, encoding="utf-8")
    print(f"✅ Labels creados: {labeled_csv} (threshold passengers >= {threshold})")
    return labeled_csv

# Pipeline de pre procesado y modelos (regresión y clasificación)
def train_models(labeled_csv, output_dir="models"):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(labeled_csv, parse_dates=["departure_time"])

    # variables y targets
    target_reg = "observed_travel_time_min"
    target_clf = "high_demand"

    features = ["mode", "operator", "hour", "weekday", "stops_count", "distance_km_est", "frequency_min", "trips_per_day_est"]
    X = df[features]
    y_reg = df[target_reg]
    y_clf = df[target_clf]

    # Pre procesado: OneHot para categóricas, scaler para numéricas
    cat_features = ["mode", "operator"]
    num_features = [c for c in features if c not in cat_features]

    preproc = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_features),
        ("num", StandardScaler(), num_features)
    ])

    # Regresión
    reg_pipe = Pipeline([
        ("pre", preproc),
        ("rf", RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1))
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    reg_pipe.fit(X_train, y_train)
    y_pred = reg_pipe.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print("REGRESIÓN - RandomForest")
    print(f"RMSE: {rmse:.3f}  MAE: {mae:.3f}  R2: {r2:.3f}")

    joblib.dump(reg_pipe, os.path.join(output_dir, "rf_regressor.pkl"))

    # Clasificación
    clf_pipe = Pipeline([
        ("pre", preproc),
        ("rf", RandomForestClassifier(n_estimators=150, class_weight="balanced", random_state=42, n_jobs=-1))
    ])

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X, y_clf, test_size=0.2, random_state=42, stratify=y_clf)
    clf_pipe.fit(X_train_c, y_train_c)
    y_pred_c = clf_pipe.predict(X_test_c)
    acc = accuracy_score(y_test_c, y_pred_c)
    prec = precision_score(y_test_c, y_pred_c, zero_division=0)
    rec = recall_score(y_test_c, y_pred_c, zero_division=0)
    f1 = f1_score(y_test_c, y_pred_c, zero_division=0)
    print("\nCLASIFICACIÓN - RandomForest")
    print(f"Accuracy: {acc:.3f}  Precision: {prec:.3f}  Recall: {rec:.3f}  F1: {f1:.3f}")
    print("\nClassification report:\n", classification_report(y_test_c, y_pred_c, zero_division=0))

    joblib.dump(clf_pipe, os.path.join(output_dir, "rf_classifier.pkl"))

    return {
        "regressor": os.path.join(output_dir, "rf_regressor.pkl"),
        "classifier": os.path.join(output_dir, "rf_classifier.pkl")
    }

# Flujo principal
def main_flow():
    csv_routes = generate_routes(num_routes=500)
    trips_csv = expand_to_trips(csv_routes, trips_csv="trips_expanded.csv")
    labeled_csv = label_trips(trips_csv, labeled_csv="trips_labeled.csv")
    models = train_models(labeled_csv, output_dir="models")
    print("Modelos guardados:", models)

if __name__ == "__main__":
    main_flow()
