-- Optional: geometry columns for maps and distance queries (requires the postgis/postgis Docker image).
CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE districts            ADD COLUMN geom geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED;
ALTER TABLE persons              ADD COLUMN geom geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED;
ALTER TABLE caregivers           ADD COLUMN geom geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(base_lon, base_lat), 4326)) STORED;
ALTER TABLE air_quality_stations ADD COLUMN geom geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED;

CREATE INDEX ON persons    USING gist (geom);
CREATE INDEX ON caregivers USING gist (geom);

-- District / colonia polygons are loaded by scripts/download_reference_data.py into:
CREATE TABLE IF NOT EXISTS district_boundaries (district_id char(5) PRIMARY KEY REFERENCES districts, geom geometry(MultiPolygon, 4326));
CREATE TABLE IF NOT EXISTS neighborhoods (neighborhood_id text PRIMARY KEY, name text NOT NULL, district_id char(5) REFERENCES districts, geom geometry(MultiPolygon, 4326));
