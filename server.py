from flask import Flask, request, jsonify, render_template
import datetime
import requests
from siphon.catalog import TDSCatalog
import numpy as np
import math
from meteostat import Point, Hourly, Stations

app = Flask(__name__)

latest_data = {
    'temperature': None,
    'humidity': None,
    'timestamp': None
}

locations_coords = {
    "libourne": {"lat": 44.9183, "lon": -0.2417},
    "saintciers": {"lat": 45.0167, "lon": -0.2333},
    "lacanau": {"lat": 45.0047, "lon": -1.2039},
    "anglet": {"lat": 43.4830, "lon": -1.5450},
    "lormont": {"lat": 44.8600, "lon": -0.5330},
}

def format_date_ddmmyyyy(date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%d/%m/%Y")

def parse_openmeteo_time(t_str):
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.datetime.strptime(t_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Format de date/heure Open-Meteo inattendu : {t_str}")


def parse_openmeteo_time(t_str):
    # Harmoniser : si pas de "Z", l'ajouter (comme Open-Meteo le ferait)
    if not t_str.endswith("Z"):
        t_str += "Z"

    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return datetime.datetime.strptime(t_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Format de date/heure Open-Meteo inattendu : {t_str}")


def get_openmeteo_forecast(lat, lon):
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&hourly=temperature_2m,relativehumidity_2m,wind_speed_10m,wind_direction_10m,precipitation,cloudcover"
            "&timezone=UTC"
        )
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        hourly = data["hourly"]

        # Nettoyer chaque liste reçue avec clean_openmeteo_value
        forecast_time = hourly["time"]
        wind_speed_raw = hourly["wind_speed_10m"]
        wind_direction_raw = hourly["wind_direction_10m"]
        temperature_raw = hourly["temperature_2m"]
        humidity_raw = hourly["relativehumidity_2m"]
        precipitation_raw = hourly["precipitation"]
        cloud_cover_raw = hourly["cloudcover"]

        # Heure actuelle en UTC pour filtrage
        now_utc = datetime.datetime.utcnow()

        filtered_times = []
        filtered_ws = []
        filtered_wd = []
        filtered_temp = []
        filtered_hum = []
        filtered_prcp = []
        filtered_cloud = []

        for i, t_str in enumerate(forecast_time):
            t_dt = parse_openmeteo_time(t_str)

            # Accepter prévisions à partir de 30 minutes avant l'instant présent
            if t_dt >= (now_utc - datetime.timedelta(minutes=30)):

                filtered_times.append(t_str)
                filtered_ws.append(clean_openmeteo_value(wind_speed_raw[i]))
                wd = clean_openmeteo_value(wind_direction_raw[i])
                # Corriger la direction: "from" -> "to"
                filtered_wd.append((wd + 180) % 360 if wd is not None else None)
                filtered_temp.append(clean_openmeteo_value(temperature_raw[i]))
                filtered_hum.append(clean_openmeteo_value(humidity_raw[i]))
                filtered_prcp.append(clean_openmeteo_value(precipitation_raw[i]))
                filtered_cloud.append(clean_openmeteo_value(cloud_cover_raw[i]))
                print(f"[DEBUG] Open-Meteo : {len(filtered_times)} points conservés après filtrage")


        return {
            "forecast_time": filtered_times,
            "wind_speed": filtered_ws,
            "wind_direction": filtered_wd,
            "temperature": filtered_temp,
            "humidity": filtered_hum,
            "precipitation": filtered_prcp,
            "cloud_cover": filtered_cloud
        }
    except Exception as e:
        print(f"[EXCEPTION] Open-Meteo : {e}")
        return None





def get_gfs_forecast(lat, lon):
    try:
        cat = TDSCatalog('http://thredds.ucar.edu/thredds/catalog/grib/NCEP/GFS/Global_0p25deg/catalog.xml')
        best_ds = list(cat.datasets.values())[0]
        ncss = best_ds.subset()

        data = ncss.query()
        data.variables('u-component_of_wind_height_above_ground', 'v-component_of_wind_height_above_ground')

        now = datetime.datetime.utcnow()
        end_time = now + datetime.timedelta(hours=72)
        data.time_range(now, end_time)
        data.lonlat_point(lon, lat)
        data.vertical_level(10)

        response = ncss.get_data(data)
        times = response['time']
        u = response['ucomponent_of_wind_height_above_ground'].squeeze()
        v = response['vcomponent_of_wind_height_above_ground'].squeeze()

        if u.ndim < 1 or u.size == 0:
            print("[WARN] Données GFS vides")
            return None

        speeds, directions, time_strs = [], [], []
        for i in range(u.shape[0]):
            speed = np.sqrt(u[i]**2 + v[i]**2).mean()
            direction = (np.degrees(np.arctan2(u[i], v[i])) + 360) % 360
            speeds.append(float(speed))
            directions.append(float(direction.mean()))
            time_dt = str(times[i])
            time_strs.append(time_dt)

        return {"forecast_time": time_strs, "wind_speed": speeds, "wind_direction": directions}

    except Exception as e:
        print(f"[EXCEPTION] GFS : {e}")
        return None
    

def build_grouped_openmeteo_data(openmeteo_data):
    grouped = {}
    if not openmeteo_data:
        return grouped

    n_points = len(openmeteo_data["forecast_time"])
    for i in range(n_points):
        t = openmeteo_data["forecast_time"][i]
        date_part, time_part = t.split("T")
        time_part = time_part.replace("Z", "")
        formatted_date = format_date_ddmmyyyy(date_part)
        if formatted_date not in grouped:
            grouped[formatted_date] = []

        entry = {
            "time": time_part,
            "speed": openmeteo_data["wind_speed"][i] if i < len(openmeteo_data["wind_speed"]) else None,
            "direction": openmeteo_data["wind_direction"][i] if i < len(openmeteo_data["wind_direction"]) else None,
            "temperature": openmeteo_data.get("temperature", [None]*n_points)[i],
            "humidity": openmeteo_data.get("humidity", [None]*n_points)[i],
            "pressure": openmeteo_data.get("pressure", [None]*n_points)[i],  # clé absente chez Open-Meteo -> None
            "precipitation": openmeteo_data.get("precipitation", [None]*n_points)[i],
            "snow_depth": openmeteo_data.get("snow_depth", [None]*n_points)[i],  # pas fournie -> None
            "cloud_cover": openmeteo_data.get("cloud_cover", [None]*n_points)[i]
        }
        grouped[formatted_date].append(entry)

    return grouped

def clean_openmeteo_value(val):
    if val is None:
        return None
    try:
        # Forcer en float pour capturer les valeurs non numériques improbables
        return float(val)
    except (ValueError, TypeError):
        return None


def clean_meteostat_value(val):
    import pandas as pd
    if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
        return None
    return val

def get_meteostat_forecast(lat, lon):
    try:
        location = Point(lat, lon)
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(hours=72)

        stations = Stations().nearby(lat, lon).fetch(1)
        if stations.empty:
            print("[WARN] Meteostat : aucune station trouvée")
            return None

        station_id = stations.index[0]
        print(f"[INFO] Meteostat : station {station_id}")
        data = Hourly(station_id, now, end).fetch()

        if data.empty:
            print("[WARN] Meteostat : aucune donnée récupérée")
            return None

        times = data.index.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()

        wind_speeds = [clean_meteostat_value(x) for x in data['wspd']] if 'wspd' in data.columns else []
        wind_dirs = [clean_meteostat_value((x + 180) % 360) for x in data['wdir']] if 'wdir' in data.columns else []
        temps = [clean_meteostat_value(x) for x in data['temp']] if 'temp' in data.columns else []
        humidities = [clean_meteostat_value(x) for x in data['rhum']] if 'rhum' in data.columns else []
        pressures = [clean_meteostat_value(x) for x in data['pres']] if 'pres' in data.columns else []
        precipitations = [clean_meteostat_value(x) for x in data['prcp']] if 'prcp' in data.columns else []
        snow_depths = [clean_meteostat_value(x) for x in data['snow']] if 'snow' in data.columns else []
        cloud_covers = [clean_meteostat_value(x) for x in data['cldc']] if 'cldc' in data.columns else []

        wind_speeds_ms = [ws / 3.6 if ws is not None else None for ws in wind_speeds]

        return {
            "forecast_time": times,
            "wind_speed": wind_speeds_ms,
            "wind_direction": wind_dirs,
            "temperature": temps,
            "humidity": humidities,
            "pressure": pressures,
            "precipitation": precipitations,
            "snow_depth": snow_depths,
            "cloud_cover": cloud_covers
        }

    except Exception as e:
        print(f"[EXCEPTION] Meteostat : {e}")
        return None


def build_grouped_meteostat_data(meteostat_data):
    grouped = {}
    if not meteostat_data:
        return grouped

    n_points = len(meteostat_data["forecast_time"])
    for i in range(n_points):
        t = meteostat_data["forecast_time"][i]
        date_part, time_part = t.split("T")
        time_part = time_part.replace("Z", "")
        formatted_date = format_date_ddmmyyyy(date_part)
        if formatted_date not in grouped:
            grouped[formatted_date] = []

        entry = {
            "time": time_part,
            "speed": meteostat_data["wind_speed"][i] if i < len(meteostat_data["wind_speed"]) else None,
            "direction": meteostat_data["wind_direction"][i] if i < len(meteostat_data["wind_direction"]) else None,
            "temperature": meteostat_data["temperature"][i] if i < len(meteostat_data["temperature"]) else None,
            "humidity": meteostat_data["humidity"][i] if i < len(meteostat_data["humidity"]) else None,
            "pressure": meteostat_data["pressure"][i] if i < len(meteostat_data["pressure"]) else None,
            "precipitation": meteostat_data["precipitation"][i] if i < len(meteostat_data["precipitation"]) else None,
            "snow_depth": meteostat_data["snow_depth"][i] if i < len(meteostat_data["snow_depth"]) else None,
            "cloud_cover": meteostat_data["cloud_cover"][i] if i < len(meteostat_data["cloud_cover"]) else None
        }
        grouped[formatted_date].append(entry)

    return grouped

def build_grouped_gfs_data(gfs_data):
    grouped = {}
    if not gfs_data:
        return grouped

    n_points = len(gfs_data["forecast_time"])
    for i in range(n_points):
        t = gfs_data["forecast_time"][i]
        date_part, time_part = t.split("T")
        time_part = time_part.replace("Z", "")
        formatted_date = format_date_ddmmyyyy(date_part)
        if formatted_date not in grouped:
            grouped[formatted_date] = []

        entry = {
            "time": time_part,
            "speed": gfs_data["wind_speed"][i] if i < len(gfs_data["wind_speed"]) else None,
            "direction": gfs_data["wind_direction"][i] if i < len(gfs_data["wind_direction"]) else None
        }
        grouped[formatted_date].append(entry)

    return grouped


@app.route('/post_data', methods=['POST'])
def post_data():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Aucune donnée reçue'}), 400
    latest_data['temperature'] = data.get('temperature')
    latest_data['humidity'] = data.get('humidity')
    latest_data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{latest_data['timestamp']}] Temp={latest_data['temperature']}°C, Hum={latest_data['humidity']}%")
    return jsonify({'status': 'success', 'message': 'Données reçues'})

# ... tout ton code jusqu'à la fin de build_grouped_meteostat_data() ...







@app.route('/')
def dashboard():
    location_key = request.args.get("location", "libourne")
    selected_model = request.args.get("model", "openmeteo")
    coords = locations_coords.get(location_key, locations_coords["libourne"])

    gfs_forecast = get_gfs_forecast(coords["lat"], coords["lon"])
    meteostat_forecast = get_meteostat_forecast(coords["lat"], coords["lon"])
    openmeteo_forecast = get_openmeteo_forecast(coords["lat"], coords["lon"])

    grouped_avg = {}

    if selected_model == "gfs" and gfs_forecast:
        model_data = gfs_forecast
        grouped_avg = build_grouped_gfs_data(model_data)

    elif selected_model == "meteostat" and meteostat_forecast:
        model_data = meteostat_forecast
        grouped_avg = build_grouped_meteostat_data(model_data)
    elif selected_model == "openmeteo" and openmeteo_forecast:
        model_data = openmeteo_forecast
        grouped_avg = build_grouped_openmeteo_data(model_data)
    
    elif selected_model == "avg" and gfs_forecast and meteostat_forecast:
        model_data = {"forecast_time": [], "wind_speed": [], "wind_direction": []}
        common_times = sorted(set(gfs_forecast["forecast_time"]) & set(meteostat_forecast["forecast_time"]))
        for t in common_times:
            idx_gfs = gfs_forecast["forecast_time"].index(t)
            idx_meteo = meteostat_forecast["forecast_time"].index(t)

            ws_gfs = gfs_forecast["wind_speed"][idx_gfs]
            ws_meteo = meteostat_forecast["wind_speed"][idx_meteo]
            wd_gfs = gfs_forecast["wind_direction"][idx_gfs]
            wd_meteo = meteostat_forecast["wind_direction"][idx_meteo]

            if None in [ws_gfs, ws_meteo, wd_gfs, wd_meteo]:
                continue

            avg_speed = 0.6 * ws_gfs + 0.4 * ws_meteo
            sin_sum = 0.6 * math.sin(math.radians(wd_gfs)) + 0.4 * math.sin(math.radians(wd_meteo))
            cos_sum = 0.6 * math.cos(math.radians(wd_gfs)) + 0.4 * math.cos(math.radians(wd_meteo))
            avg_dir = (math.degrees(math.atan2(sin_sum, cos_sum)) + 360) % 360

            model_data["forecast_time"].append(t)
            model_data["wind_speed"].append(avg_speed)
            model_data["wind_direction"].append(avg_dir)

        if model_data:
            for i in range(len(model_data["forecast_time"])):
                t = model_data["forecast_time"][i]
                date_part, time_part = t.split("T")
                time_part = time_part.replace("Z", "")
                formatted_date = format_date_ddmmyyyy(date_part)
                if formatted_date not in grouped_avg:
                    grouped_avg[formatted_date] = []
                grouped_avg[formatted_date].append({
                    "time": time_part,
                    "speed": model_data["wind_speed"][i],
                    "direction": model_data["wind_direction"][i]
                })
    current_temperature = None
    current_cloud_cover = None
    current_precipitation = None
    current_date = datetime.datetime.utcnow().strftime("%d/%m/%Y")

    if openmeteo_forecast and openmeteo_forecast.get("temperature"):
        # Protéger contre dépassement d'index
        idx_temp = 1 if len(openmeteo_forecast["temperature"]) > 1 else 0
        current_temperature = openmeteo_forecast["temperature"][idx_temp]
        current_cloud_cover = openmeteo_forecast["cloud_cover"][0]
        current_precipitation = openmeteo_forecast["precipitation"][0]

    current_wind_speed = None
    current_wind_direction = None

    current_wind_speed = None
    current_wind_direction = None

    if gfs_forecast and gfs_forecast.get("forecast_time"):
        # Prendre la première prévision GFS comme "actuel"
        current_wind_speed = gfs_forecast["wind_speed"][0]
        current_wind_direction = gfs_forecast["wind_direction"][0]

    daily_bulletin = []

    if openmeteo_forecast and openmeteo_forecast.get("forecast_time"):
        today = datetime.datetime.utcnow().date()
        now_utc = datetime.datetime.utcnow()
        today = now_utc.date()

        # Si heure actuelle UTC > 18h00, bascule sur le lendemain
        if now_utc.hour >= 18:
            target_date = today + datetime.timedelta(days=1)
        else:
            target_date = today

        now_utc = datetime.datetime.utcnow()
        today = now_utc.date()

        if now_utc.hour >= 18:
            target_date = today + datetime.timedelta(days=1)
            bulletin_date_label = f"BULLETIN POUR DEMAIN ({target_date.strftime('%d/%m/%Y')})"
        else:
            target_date = today
            bulletin_date_label = f"BULLETIN POUR AUJOURD’HUI ({target_date.strftime('%d/%m/%Y')})"



        target_hours = {"10h": 10, "14h": 14, "18h": 18}

        for label, target_hour in target_hours.items():
            closest_entry = None
            min_time_diff = None

            for t, temp, cloud, precip in zip(
                openmeteo_forecast["forecast_time"],
                openmeteo_forecast["temperature"],
                openmeteo_forecast["cloud_cover"],
                openmeteo_forecast["precipitation"]
            ):
                dt = parse_openmeteo_time(t)
                if dt.date() != target_date:

                    continue

                time_diff = abs((dt - dt.replace(hour=target_hour, minute=0, second=0)).total_seconds())

                if closest_entry is None or time_diff < min_time_diff:
                    closest_entry = (dt, temp, cloud, precip)
                    min_time_diff = time_diff

            if closest_entry:
                _, temp, cloud, precip = closest_entry
                if precip > 0:
                    icon = "🌧️"
                elif cloud < 20:
                    icon = "☀️"
                elif cloud < 50:
                    icon = "🌤️"
                else:
                    icon = "☁️"

                daily_bulletin.append({
                    "hour": label,
                    "temp": f"{temp:.1f}°C",
                    "icon": icon
                })




    return render_template("dashboard.html",
                       temperature=latest_data['temperature'],
                       humidity=latest_data['humidity'],
                       timestamp=latest_data['timestamp'],
                       selected_location=location_key,
                       selected_model=selected_model,
                       grouped_avg=grouped_avg,
                       current_temperature=current_temperature,
                       current_cloud_cover=current_cloud_cover,
                       current_precipitation=current_precipitation,
                       current_wind_speed=current_wind_speed,
                       current_wind_direction=current_wind_direction,
                       current_date=current_date, 
                       daily_bulletin=daily_bulletin,
                       bulletin_date_label=bulletin_date_label
                       )




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
