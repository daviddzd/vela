export type Filters = { district?: string; from?: string; to?: string; institution?: string };

export type Operation = {
  from: string; to: string; on_time_minutes: number;
  counters: { queued: number; on_the_way: number; in_visit: number; done_today: number };
  on_time_pct: number | null; unattended_pct: number | null;
  periods: Record<"baseline" | "vela", { on_time_pct: number | null; unattended_pct: number | null; arrived: number; decided: number }>;
  daily: { day: string; period: "baseline" | "vela"; on_time_pct: number | null; unattended_pct: number | null; visits: number }[];
  staff_load: { caregiver_id: string; name: string; type: string; shift_hours: number; hours_today: number;
    avg_hours_per_day: number }[];
  queue_by_priority: { priority: string; waiting: number; max_wait_min: number | null }[];
};

export type DistrictRow = { district_id: string; district_name: string; persons_60_plus: number;
  multimorbidity_pct: number; dependency_moderate_severe_pct: number; pollution_sensitive_pct: number;
  age_80_plus_pct: number; avg_chronic_diseases: number; multimorbidity_broad_pct: number };

export type Population = {
  city: Record<string, number>; districts: DistrictRow[];
  indicator_reference: Record<string, { reference_pct: number; survey: string; source: string; note: string } | null>;
  conditions: { condition: string; prevalence_pct: number;
    reference: { reference_pct: number; survey: string; adjusted: boolean; note: string } | null }[];
};

export type Boundaries = { available: true; geojson: any } |
  { available: false; points: { district_id: string; name: string; lat: number; lon: number }[] };

export type Air = {
  station: string; from: string; to: string; data_until: string | null;
  stations: { station_id: string; name: string; district_id: string; district_name: string; location_source: string }[];
  thresholds: { o3_ppb_1h: number; pm25_ugm3_24h: number; watch_fraction: number };
  series: { t: string; o3: number | null; pm25_24h: number | null; scenario?: boolean }[];
  max_o3: number | null; max_pm25_24h: number | null;
};

export type Traffic = { cells: { day_type: string; hour: number; congestion_pct: number; avg_speed_kmh: number }[];
  peak: { day_type: string; hour: number; congestion_pct: number } };
