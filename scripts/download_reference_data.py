"""Download official reference data on the laptop (the build sandbox had no internet).

Usage (from the repo root):   python scripts/download_reference_data.py [--year 2025]

Only the Python standard library is used. Every source has a fallback: if a download fails the
script prints manual instructions and the system keeps working with the calibrated synthetic files
already in data/reference/.

Outputs go to data/reference/official/ (git-ignored except the small catalog files).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "reference" / "official"
TIMEOUT = 60
SIMAT_TIMEOUT = 180   # the SIMAT server is slow and sometimes silent: wait longer
SIMAT_RETRIES = 3     # attempts per URL, with a growing pause in between
HEADERS = {"User-Agent": "vela-academic-project/1.0"}

SIMAT_BASE = "http://148.243.232.112:8080/opendata"
SIMAT_STATIONS = f"{SIMAT_BASE}/catalogos/cat_estacion.csv"
SIMAT_HOURLY_CANDIDATES = [  # the portal has used several layouts over the years
    f"{SIMAT_BASE}/anuales_horarios_gz/contaminantes_{{year}}.csv.gz",
    f"{SIMAT_BASE}/anuales_horarios/contaminantes_{{year}}.csv.zip",
    f"{SIMAT_BASE}/anuales_horarios/contaminantes_{{year}}.csv",
]
CKAN = "https://datos.cdmx.gob.mx/api/3/action/package_show?id={}"
CKAN_PACKAGES = {
    "neighborhoods": "04a1900a-0c2f-41ed-94dc-3d2d5bad4065",  # first: the district fallback needs it
    "district_boundaries": "alcaldias",  # was "limite-de-las-alcaldias" (404); checked in Nov 2026
}


def fetch(url: str, timeout: int = TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_retry(url: str, retries: int = SIMAT_RETRIES, timeout: int = SIMAT_TIMEOUT) -> bytes:
    """Like fetch, but tries several times (pause 5 s, 10 s, ...) and raises the last error."""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fetch(url, timeout)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"      attempt {attempt}/{retries} failed ({exc})")
            if attempt < retries:
                time.sleep(5 * attempt)
    raise last  # type: ignore[misc]


def save(name: str, data: bytes) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_bytes(data)
    print(f"  ok  {path.relative_to(ROOT)}  ({len(data) / 1e6:.1f} MB)")
    return path


def simat_stations() -> None:
    print("SIMAT station catalog")
    try:
        save("simat_stations.csv", fetch_retry(SIMAT_STATIONS))
    except Exception as exc:  # noqa: BLE001
        manual("SIMAT station catalog", exc, SIMAT_STATIONS)


def simat_hourly(year: int) -> None:
    print(f"SIMAT hourly pollutants {year}")
    for template in SIMAT_HOURLY_CANDIDATES:
        url = template.format(year=year)
        try:
            raw = fetch_retry(url, retries=2)  # 404 on a wrong layout fails fast; timeouts get a 2nd try
        except Exception:  # noqa: BLE001
            continue
        if url.endswith(".gz"):
            raw = gzip.decompress(raw)
        elif url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                raw = zf.read(zf.namelist()[0])
        keep_o3_pm25(raw, year)
        return
    manual(f"SIMAT hourly {year}", "the SIMAT server did not answer or none of the URL layouts worked",
           "http://www.aire.cdmx.gob.mx/default.php?opc=%27aKBhnmI=%27&opcion=Zg==")
    print(f"      On that page choose 'Contaminantes' -> year {year}; keep only O3 and PM2.5 and save it as "
          f"simat_o3_pm25_{year}.csv (or save the whole file; Claude Code can filter it).")


def keep_o3_pm25(raw: bytes, year: int) -> None:
    """Keep only O3 and PM2.5 rows to make the file small enough for Git."""
    text = raw.decode("latin-1").splitlines()
    start = next(i for i, line in enumerate(text) if line.lower().startswith(("date", "fecha")))
    reader = csv.reader(text[start:])
    header = next(reader)
    cols = [h.strip().lower() for h in header]
    i_param = cols.index("id_parameter") if "id_parameter" in cols else cols.index("parametro")
    rows = [r for r in reader if len(r) > i_param and r[i_param].strip().upper() in ("O3", "PM2.5", "PM25")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    save(f"simat_o3_pm25_{year}.csv", buf.getvalue().encode("utf-8"))


def ckan_geojson(key: str, package: str) -> None:
    print(f"datos.cdmx · {key}")
    try:
        meta = json.loads(fetch(CKAN.format(package)))
        resources = meta["result"]["resources"]
        geo = next(r for r in resources if "geojson" in (r.get("format", "") + r.get("url", "")).lower())
        save(f"{key}.geojson", fetch(geo["url"]))
    except Exception as exc:  # noqa: BLE001
        if key == "district_boundaries" and districts_from_neighborhoods():
            return
        manual(key, exc, f"https://datos.cdmx.gob.mx/dataset/{package}")


def districts_from_neighborhoods() -> bool:
    """Fallback: build the 16 alcaldia polygons by merging the neighborhoods of each alcaldia.

    Needs `shapely` (not in the standard library): run the script with `uv run --with shapely ...`
    or `pip install shapely`. Returns True if the file was written.
    """
    src = OUT / "neighborhoods.geojson"
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        print("  ..  fallback needs shapely: run  uv run --with shapely python scripts/download_reference_data.py")
        return False
    if not src.exists():
        return False
    groups: dict[str, list] = {}
    for feat in json.loads(src.read_text(encoding="utf-8"))["features"]:
        name = feat["properties"].get("NOMDT")  # NOMDT = alcaldia name in the neighborhoods file
        if name:
            groups.setdefault(name.strip().title(), []).append(shape(feat["geometry"]).buffer(0))
    features = [{"type": "Feature", "properties": {"NOMGEO": n}, "geometry": mapping(unary_union(g))}
                for n, g in sorted(groups.items())]
    save("district_boundaries.geojson",
         json.dumps({"type": "FeatureCollection", "features": features}).encode("utf-8"))
    print(f"      built from neighborhoods: {len(features)} alcaldias (approximate borders)")
    return True


def manual(what: str, why: object, url: str) -> None:
    print(f"  !!  {what} could not be downloaded ({why}).")
    print(f"      Download it by hand from {url} and save it in {OUT.relative_to(ROOT)}/")
    print("      Until then the system uses the calibrated synthetic files in data/reference/.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    simat_stations()
    simat_hourly(args.year)
    for key, package in CKAN_PACKAGES.items():
        ckan_geojson(key, package)
    print("\nINEGI AGEB (optional, manual): https://www.inegi.org.mx/app/scitel/ -> Ciudad de México -> "
          "Censo 2020, resultados por AGEB urbana. Save as data/reference/official/inegi_ageb_cdmx.csv")
    print("Next step: python scripts/load_official_data.py  (Claude Code writes it once the files exist)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
