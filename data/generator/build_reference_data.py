"""Build calibrated reference datasets: air-quality stations and hourly readings, traffic profile.

These are SYNTHETIC series calibrated to published figures (see docs/spec/07_datos.md). The script
scripts/download_reference_data.py replaces them with real SIMAT data when run on a machine with internet access.
"""
import os, sys, math, datetime as dt
import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "data/reference"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(2026)

# Approximate locations of SIMAT/RAMA stations inside CDMX (replace with official cat_estacion.csv).
# o3_factor / pm25_factor: relative level vs city average (south-west higher ozone, east higher PM2.5).
STATIONS = [
    # id, name, district_id, lat, lon, o3_factor, pm25_factor
    ("AJM", "Ajusco Medio", "09012", 19.2721, -99.2077, 1.12, 0.80),
    ("BJU", "Benito Juárez", "09014", 19.3713, -99.1590, 1.03, 0.95),
    ("CAM", "Camarones", "09002", 19.4685, -99.1698, 0.98, 1.05),
    ("CCA", "Centro de Ciencias de la Atmósfera", "09003", 19.3262, -99.1762, 1.10, 0.90),
    ("CUA", "Cuajimalpa", "09004", 19.3653, -99.2917, 1.06, 0.75),
    ("GAM", "Gustavo A. Madero", "09005", 19.4827, -99.0947, 0.95, 1.15),
    ("HGM", "Hospital General de México", "09015", 19.4116, -99.1522, 0.97, 1.05),
    ("IZT", "Iztacalco", "09006", 19.3844, -99.1176, 0.97, 1.10),
    ("MER", "Merced", "09017", 19.4246, -99.1196, 0.96, 1.12),
    ("MGH", "Miguel Hidalgo", "09016", 19.4041, -99.2027, 1.02, 0.92),
    ("MPA", "Milpa Alta", "09009", 19.1769, -98.9902, 1.05, 0.85),
    ("PED", "Pedregal", "09010", 19.3253, -99.2041, 1.12, 0.85),
    ("SAC", "Santiago Acahualtepec", "09007", 19.3460, -99.0094, 0.95, 1.30),
    ("SFE", "Santa Fe", "09010", 19.3574, -99.2629, 1.05, 0.78),
    ("TAH", "Tláhuac", "09011", 19.2465, -99.0106, 1.00, 1.15),
    ("UAX", "UAM Xochimilco", "09013", 19.3044, -99.1036, 1.04, 1.00),
    ("UIZ", "UAM Iztapalapa", "09007", 19.3608, -99.0739, 0.98, 1.22),
]
st = pd.DataFrame(STATIONS, columns=["station_id", "name", "district_id", "lat", "lon", "o3_factor", "pm25_factor"])
st["location_source"] = "approximate"
st.to_csv(os.path.join(OUT, "air_quality_stations.csv"), index=False, lineterminator="\n")

# ---------------------------------------------------------------- hourly readings, 30 days of normal conditions
start = dt.datetime(2026, 10, 21)
hours = pd.date_range(start, periods=30 * 24, freq="h")
# city-level daily drivers: daily max ozone ~ 93-113 ppb, daily max PM2.5 ~ 43-60 ug/m3 (SSA weekly reports)
days = 30
o3_daily_max = np.clip(rng.normal(86, 10, days), 62, 120)
pm_daily_mean = np.clip(rng.normal(22, 5.5, days), 11, 36)
rows = []
for t in hours:
    d = (t - start).days; h = t.hour
    # ozone: photochemical, peak between 13:00 and 17:00
    shape_o3 = 0.15 + 0.85 * math.exp(-((h - 15) ** 2) / (2 * 2.6 ** 2))
    # PM2.5: morning peak (traffic + low mixing layer) around 8-10 h, secondary evening bump
    shape_pm = 0.75 + 0.55 * math.exp(-((h - 9) ** 2) / (2 * 2.2 ** 2)) + 0.2 * math.exp(-((h - 21) ** 2) / (2 * 2.5 ** 2))
    for s in STATIONS:
        o3 = o3_daily_max[d] * shape_o3 * s[5] * rng.lognormal(0, 0.08)
        pm = pm_daily_mean[d] * shape_pm * s[6] * rng.lognormal(0, 0.15)
        rows.append((s[0], t.strftime("%Y-%m-%d %H:00:00-06"), round(o3, 1), round(pm, 1)))
aq = pd.DataFrame(rows, columns=["station_id", "measured_at", "o3_ppb", "pm25_ugm3"])
aq["source"] = "synthetic_calibrated"
aq.to_csv(os.path.join(OUT, "air_quality_hourly.csv"), index=False, lineterminator="\n")

# ---------------------------------------------------------------- traffic profile (TomTom Traffic Index 2025, CDMX)
# Average congestion 75.9 %, avg speed 17.4 km/h, rush-hour speed 13.5 km/h, slowest ~12 km/h around 18 h,
# morning rush +106.6 %, evening rush +125.8 %. Free-flow speed implied: 17.4 * 1.759 = 30.6 km/h.
FREE_FLOW = 17.4 * 1.759
wk = []
for h in range(24):
    base = 0.22 + 0.86 * math.exp(-((h - 8) ** 2) / (2 * 1.3 ** 2)) + 1.30 * math.exp(-((h - 18) ** 2) / (2 * 1.8 ** 2)) \
        + 0.55 * math.exp(-((h - 13.5) ** 2) / (2 * 2.5 ** 2))
    if h < 5: base = [0.12, 0.09, 0.07, 0.07, 0.10][h]
    wk.append(base)
wk = np.array(wk)
day_hours = np.arange(6, 23)
wk = wk * (0.759 / wk[day_hours].mean())            # weekday daytime mean = 75.9 %
we = wk * 0.65
rows = []
for dtype, prof in [("weekday", wk), ("weekend", we)]:
    for h in range(24):
        c = float(prof[h])
        rows.append((dtype, h, round(c * 100, 1), round(FREE_FLOW / (1 + c), 1), round(1 + c, 3)))
tr = pd.DataFrame(rows, columns=["day_type", "hour", "congestion_pct", "avg_speed_kmh", "travel_time_factor"])
tr["free_flow_speed_kmh"] = round(FREE_FLOW, 1)
tr.to_csv(os.path.join(OUT, "traffic_hourly_profile.csv"), index=False, lineterminator="\n")
print(st.shape, aq.shape, tr.shape)
print(aq.groupby(aq.measured_at.str[:10]).o3_ppb.max().describe().round(1).to_dict())
print(aq.groupby(aq.measured_at.str[:10]).pm25_ugm3.max().describe().round(1).to_dict())
print(tr[tr.day_type == "weekday"][["hour", "congestion_pct", "avg_speed_kmh"]].to_string(index=False))
