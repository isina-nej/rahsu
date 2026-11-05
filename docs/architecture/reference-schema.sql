-- Pride / Tehran Fuel Estimation — PostgreSQL 15+ and PostGIS 3+
-- Reference DDL, v1.0, 2026-11-05. Run in a fresh database with CREATE EXTENSION privilege.
-- Authentication is intentionally external; core.app_users stores identity/role only.
-- All locations use EPSG:4326 in longitude/latitude order; physical distances are METERS.
-- NULL means unknown/not observed; never silently interpret missing data as zero.

BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS vehicle;
CREATE SCHEMA IF NOT EXISTS routing;
CREATE SCHEMA IF NOT EXISTS fuel;
CREATE SCHEMA IF NOT EXISTS telemetry;
CREATE SCHEMA IF NOT EXISTS ops;

-- CORE ----------------------------------------------------------------------
CREATE TABLE core.app_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_subject text UNIQUE,                -- link to Django/custom auth provider
  email text,
  role text NOT NULL DEFAULT 'user' CHECK (role IN ('user','moderator','admin')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX app_users_email_lower_unique ON core.app_users (lower(email)) WHERE email IS NOT NULL;

CREATE TABLE core.data_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  provider_url text,
  license_name text,
  license_url text,
  attribution_text text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.ingestion_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES core.data_sources(id),
  dataset_version text,
  city_id uuid,                             -- free until geo.cities exists
  status text NOT NULL DEFAULT 'running' CHECK (status IN ('running','success','failed')),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  record_count integer CHECK (record_count >= 0),
  checksum_sha256 text,
  error_detail text,
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE core.factor_catalog (
  factor_key text PRIMARY KEY,
  factor_group text NOT NULL,
  title_fa text NOT NULL,
  unit text,
  effect_direction text NOT NULL DEFAULT 'conditional'
    CHECK (effect_direction IN ('increase','decrease','conditional','indirect')),
  availability text NOT NULL DEFAULT 'unknown'
    CHECK (availability IN ('osm','user','external','sensor','derived','unknown')),
  stage text NOT NULL DEFAULT 'later' CHECK (stage IN ('mvp','calibration','later')),
  definition text
);

-- GEOGRAPHIC DATA -----------------------------------------------------------
CREATE TABLE geo.cities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  city_code text NOT NULL UNIQUE,
  name_fa text NOT NULL,
  boundary geometry(MultiPolygon,4326),    -- import actual official or OSM polygon
  timezone text NOT NULL DEFAULT 'Asia/Tehran',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cities_boundary_gix ON geo.cities USING gist(boundary);
ALTER TABLE core.ingestion_batches
  ADD CONSTRAINT ingestion_batches_city_fk FOREIGN KEY (city_id) REFERENCES geo.cities(id);

CREATE TABLE geo.road_segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  city_id uuid NOT NULL REFERENCES geo.cities(id),
  osm_way_id bigint,                       -- may be NULL for non-OSM/corrected roads
  osm_way_version bigint,
  part_no integer NOT NULL DEFAULT 0 CHECK (part_no >= 0),
  name text,
  road_class text NOT NULL,
  directionality smallint NOT NULL DEFAULT 0 CHECK (directionality IN (-1,0,1)),
  geom geometry(LineString,4326) NOT NULL,
  length_m numeric(12,2) NOT NULL CHECK (length_m > 0),
  maxspeed_kph numeric(6,2) CHECK (maxspeed_kph > 0 AND maxspeed_kph <= 200),
  lanes smallint CHECK (lanes BETWEEN 1 AND 20),
  surface text,
  smoothness text,
  osm_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  lit boolean,
  is_bridge boolean,
  is_tunnel boolean,
  source_id uuid REFERENCES core.data_sources(id),
  ingestion_batch_id uuid REFERENCES core.ingestion_batches(id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ST_IsValid(geom))
);
CREATE UNIQUE INDEX road_osm_way_part_unique ON geo.road_segments(city_id,osm_way_id,part_no)
  WHERE osm_way_id IS NOT NULL;
CREATE INDEX roads_city_idx ON geo.road_segments(city_id,road_class);
CREATE INDEX roads_geom_gix ON geo.road_segments USING gist(geom);

CREATE TABLE geo.elevation_samples (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  road_segment_id uuid NOT NULL REFERENCES geo.road_segments(id) ON DELETE CASCADE,
  offset_m numeric(12,2) NOT NULL CHECK (offset_m >= 0),
  location geometry(Point,4326) NOT NULL,
  elevation_m numeric(9,2),
  vertical_accuracy_m numeric(8,2) CHECK (vertical_accuracy_m >= 0),
  source_id uuid REFERENCES core.data_sources(id),
  sampled_at timestamptz,
  UNIQUE (road_segment_id,offset_m)
);
CREATE INDEX elevation_samples_location_gix ON geo.elevation_samples USING gist(location);

CREATE TABLE geo.obstacles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  city_id uuid NOT NULL REFERENCES geo.cities(id),
  road_segment_id uuid REFERENCES geo.road_segments(id) ON DELETE SET NULL,
  obstacle_type text NOT NULL CHECK (obstacle_type IN
    ('traffic_signal','speed_bump','speed_hump','raised_table','rumble_strip',
     'stop_sign','give_way','pedestrian_crossing','roundabout','rail_crossing',
     'roadworks','pothole','lane_narrowing','speed_camera','other')),
  location geometry(Point,4326) NOT NULL,
  direction text NOT NULL DEFAULT 'unknown'
    CHECK (direction IN ('forward','reverse','both','unknown')),
  osm_element_type text CHECK (osm_element_type IN ('node','way','relation')),
  osm_element_id bigint,
  source_id uuid REFERENCES core.data_sources(id),
  ingestion_batch_id uuid REFERENCES core.ingestion_batches(id),
  verification_status text NOT NULL DEFAULT 'imported'
    CHECK (verification_status IN ('imported','verified','disabled')),
  confidence numeric(4,3) CHECK (confidence BETWEEN 0 AND 1),
  active boolean NOT NULL DEFAULT true,
  tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  observed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((osm_element_type IS NULL) = (osm_element_id IS NULL))
);
CREATE UNIQUE INDEX obstacles_osm_unique ON geo.obstacles(source_id,osm_element_type,osm_element_id)
  WHERE source_id IS NOT NULL AND osm_element_id IS NOT NULL;
CREATE INDEX obstacles_geo_gix ON geo.obstacles USING gist(location);
CREATE INDEX obstacles_city_type_idx ON geo.obstacles(city_id,obstacle_type) WHERE active;
CREATE INDEX obstacles_road_idx ON geo.obstacles(road_segment_id) WHERE active;

CREATE TABLE geo.obstacle_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  obstacle_id uuid REFERENCES geo.obstacles(id),
  reporter_id uuid REFERENCES core.app_users(id),
  report_kind text NOT NULL CHECK (report_kind IN ('add','edit','deactivate')),
  proposed_type text,
  proposed_location geometry(Point,4326),
  proposed_direction text CHECK (proposed_direction IN ('forward','reverse','both','unknown')),
  details text,
  evidence_url text,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected')),
  reviewer_id uuid REFERENCES core.app_users(id),
  reviewed_at timestamptz,
  review_note text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (report_kind <> 'add' OR (proposed_location IS NOT NULL AND proposed_type IS NOT NULL)),
  CHECK (report_kind = 'add' OR obstacle_id IS NOT NULL),
  CHECK ((status = 'pending' AND reviewed_at IS NULL)
     OR (status <> 'pending' AND reviewed_at IS NOT NULL))
);
CREATE INDEX obstacle_reports_status_idx ON geo.obstacle_reports(status,created_at);

CREATE TABLE geo.traffic_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  road_segment_id uuid NOT NULL REFERENCES geo.road_segments(id) ON DELETE CASCADE,
  day_of_week smallint NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- Mon=0
  minute_of_day smallint NOT NULL CHECK (minute_of_day BETWEEN 0 AND 1425
    AND minute_of_day % 15 = 0),
  median_speed_kph numeric(7,2) CHECK (median_speed_kph >= 0),
  p10_speed_kph numeric(7,2) CHECK (p10_speed_kph >= 0),
  mean_queue_delay_s numeric(8,2) CHECK (mean_queue_delay_s >= 0),
  sample_count integer NOT NULL CHECK (sample_count > 0),
  source_id uuid NOT NULL REFERENCES core.data_sources(id),
  valid_from date,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (road_segment_id,day_of_week,minute_of_day,source_id)
);
CREATE INDEX traffic_profiles_lookup_idx ON geo.traffic_profiles(road_segment_id,day_of_week,minute_of_day);

CREATE TABLE geo.weather_observations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES core.data_sources(id),
  observed_at timestamptz NOT NULL,
  location geometry(Point,4326) NOT NULL,
  air_temp_c numeric(6,2),
  air_pressure_pa numeric(9,1) CHECK (air_pressure_pa > 0),
  wind_speed_mps numeric(6,2) CHECK (wind_speed_mps >= 0),
  wind_from_deg numeric(6,2) CHECK (wind_from_deg >= 0 AND wind_from_deg < 360),
  precipitation_mm_h numeric(7,2) CHECK (precipitation_mm_h >= 0),
  relative_humidity_pct numeric(5,2) CHECK (relative_humidity_pct BETWEEN 0 AND 100)
);
CREATE INDEX weather_geo_gix ON geo.weather_observations USING gist(location);
CREATE INDEX weather_date_idx ON geo.weather_observations(observed_at DESC);

-- VEHICLES ------------------------------------------------------------------
CREATE TABLE vehicle.variants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  variant_key text NOT NULL UNIQUE,
  brand text NOT NULL,
  model_name text NOT NULL,
  trim_name text,
  engine_code text,
  fuel_type text NOT NULL DEFAULT 'gasoline',
  transmission text NOT NULL DEFAULT 'manual',
  production_year_from smallint,
  production_year_to smallint,
  displacement_cc numeric(7,1) CHECK (displacement_cc > 0),
  curb_mass_kg numeric(8,2) CHECK (curb_mass_kg > 0),
  curb_mass_basis text,                     -- occupants/fuel included in reported curb mass
  c_d numeric(5,3) CHECK (c_d > 0 AND c_d < 2),
  frontal_area_m2 numeric(5,3) CHECK (frontal_area_m2 > 0),
  rolling_resistance_coeff numeric(6,4) CHECK (rolling_resistance_coeff > 0),
  drivetrain_efficiency numeric(5,3) CHECK (drivetrain_efficiency > 0 AND drivetrain_efficiency <= 1),
  idle_fuel_lph numeric(6,3) CHECK (idle_fuel_lph >= 0),
  baseline_city_l_100km numeric(6,3) CHECK (baseline_city_l_100km > 0),
  nominal_tire_pressure_kpa numeric(6,2) CHECK (nominal_tire_pressure_kpa > 0),
  source_id uuid REFERENCES core.data_sources(id),
  specification_version text NOT NULL DEFAULT 'initial',
  other_specs jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (production_year_to IS NULL OR production_year_from IS NULL OR production_year_to >= production_year_from)
);

CREATE TABLE vehicle.instances (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid REFERENCES core.app_users(id),
  variant_id uuid NOT NULL REFERENCES vehicle.variants(id),
  nickname text,
  manufacturing_year smallint,
  odometer_km numeric(11,1) CHECK (odometer_km >= 0),
  fuel_system text,
  tire_model text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(id,variant_id)
);
CREATE INDEX vehicle_instances_owner_idx ON vehicle.instances(owner_id);

CREATE TABLE vehicle.maintenance_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id uuid NOT NULL REFERENCES vehicle.instances(id) ON DELETE CASCADE,
  event_at timestamptz NOT NULL,
  event_type text NOT NULL,
  odometer_km numeric(11,1) CHECK (odometer_km >= 0),
  recorded_value numeric(11,3),
  value_unit text,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX maintenance_vehicle_time_idx ON vehicle.maintenance_events(instance_id,event_at DESC);

-- ROUTING AND IMMUTABLE TRIP-SPECIFIC CONDITIONS ----------------------------
CREATE TABLE routing.requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES core.app_users(id),
  city_id uuid NOT NULL REFERENCES geo.cities(id),
  vehicle_variant_id uuid NOT NULL REFERENCES vehicle.variants(id),
  vehicle_instance_id uuid,
  origin geometry(Point,4326) NOT NULL,
  destination geometry(Point,4326) NOT NULL,
  planned_departure_at timestamptz,
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','running','completed','failed')),
  request_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (NOT ST_Equals(origin,destination)),
  FOREIGN KEY(vehicle_instance_id,vehicle_variant_id) REFERENCES vehicle.instances(id,variant_id)
);
CREATE INDEX requests_user_date_idx ON routing.requests(user_id,created_at DESC);
CREATE INDEX requests_origin_gix ON routing.requests USING gist(origin);

CREATE TABLE routing.scenarios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid NOT NULL UNIQUE REFERENCES routing.requests(id) ON DELETE CASCADE,
  -- Extra passenger+cargo weight beyond the specified curb-mass definition.
  additional_mass_kg numeric(7,2) CHECK (additional_mass_kg >= 0),
  passengers_count smallint CHECK (passengers_count BETWEEN 0 AND 7),
  fuel_in_tank_l numeric(6,2) CHECK (fuel_in_tank_l >= 0),
  front_tire_pressure_kpa numeric(7,2) CHECK (front_tire_pressure_kpa > 0),
  rear_tire_pressure_kpa numeric(7,2) CHECK (rear_tire_pressure_kpa > 0),
  ac_mode text DEFAULT 'unknown' CHECK (ac_mode IN ('off','low','medium','high','unknown')),
  windows_open_pct numeric(5,2) CHECK (windows_open_pct BETWEEN 0 AND 100),
  cabin_heater_on boolean,
  electrical_load_w numeric(8,1) CHECK (electrical_load_w >= 0),
  cold_start boolean,
  engine_off_duration_min numeric(9,1) CHECK (engine_off_duration_min >= 0),
  engine_coolant_temp_c numeric(6,2),
  driving_style text NOT NULL DEFAULT 'normal'
    CHECK (driving_style IN ('eco','normal','aggressive')),
  air_temp_c numeric(6,2),
  air_pressure_pa numeric(9,1) CHECK (air_pressure_pa > 0),
  wind_speed_mps numeric(6,2) CHECK (wind_speed_mps >= 0),
  wind_from_deg numeric(6,2) CHECK (wind_from_deg >= 0 AND wind_from_deg < 360),
  precipitation_mm_h numeric(7,2) CHECK (precipitation_mm_h >= 0),
  road_wetness text DEFAULT 'unknown' CHECK (road_wetness IN ('dry','wet','snow','unknown')),
  estimated_tire_condition text DEFAULT 'unknown' CHECK (estimated_tire_condition IN ('good','worn','unknown')),
  fuel_quality_code text,
  assumptions jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE routing.candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid NOT NULL REFERENCES routing.requests(id) ON DELETE CASCADE,
  alternative_no smallint NOT NULL CHECK (alternative_no >= 0),
  routing_engine text NOT NULL DEFAULT 'OSRM',
  engine_version text,
  road_data_version text,
  geom geometry(LineString,4326) NOT NULL,
  length_m numeric(12,2) NOT NULL CHECK (length_m > 0),
  nominal_travel_time_s numeric(12,2) CHECK (nominal_travel_time_s >= 0),
  ascent_m numeric(10,2) CHECK (ascent_m >= 0),
  descent_m numeric(10,2) CHECK (descent_m >= 0),
  quality_score numeric(4,3) CHECK (quality_score BETWEEN 0 AND 1),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (request_id,alternative_no)
);
CREATE INDEX candidates_geom_gix ON routing.candidates USING gist(geom);

CREATE TABLE routing.segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL REFERENCES routing.candidates(id) ON DELETE CASCADE,
  segment_no integer NOT NULL CHECK (segment_no >= 0),
  road_segment_id uuid REFERENCES geo.road_segments(id) ON DELETE SET NULL,
  geom geometry(LineString,4326) NOT NULL,
  distance_m numeric(11,2) NOT NULL CHECK (distance_m > 0),
  mean_grade_pct numeric(8,3),
  ascent_m numeric(9,2) CHECK (ascent_m >= 0),
  descent_m numeric(9,2) CHECK (descent_m >= 0),
  speed_limit_kph numeric(7,2) CHECK (speed_limit_kph > 0),
  planned_mean_speed_kph numeric(7,2) CHECK (planned_mean_speed_kph >= 0),
  expected_delay_s numeric(9,2) CHECK (expected_delay_s >= 0),
  traffic_speed_kph numeric(7,2) CHECK (traffic_speed_kph >= 0),
  speed_profile_source text,
  data_quality numeric(4,3) CHECK (data_quality BETWEEN 0 AND 1),
  UNIQUE (candidate_id,segment_no)
);
CREATE INDEX route_segments_candidate_idx ON routing.segments(candidate_id,segment_no);
CREATE INDEX route_segments_road_idx ON routing.segments(road_segment_id);
CREATE INDEX route_segments_geom_gix ON routing.segments USING gist(geom);

-- The predicted 1-second speed/acceleration timeline is essential for VSP/VT-Micro.
-- Predictions are only reproducible if motion-profile version/source are tracked.
CREATE TABLE routing.motion_samples (
  candidate_id uuid NOT NULL REFERENCES routing.candidates(id) ON DELETE CASCADE,
  sample_no integer NOT NULL CHECK (sample_no >= 0),
  elapsed_s numeric(12,3) NOT NULL CHECK (elapsed_s >= 0),
  distance_along_m numeric(12,2) NOT NULL CHECK (distance_along_m >= 0),
  speed_mps numeric(8,4) NOT NULL CHECK (speed_mps >= 0),
  acceleration_mps2 numeric(9,4),
  grade_pct numeric(8,3),
  predicted_idle boolean NOT NULL DEFAULT false,
  generation_method text NOT NULL,          -- stop-go template, driving cycle, etc.
  generation_version text NOT NULL,
  PRIMARY KEY (candidate_id,sample_no),
  UNIQUE (candidate_id,elapsed_s)
);

CREATE TABLE routing.segment_obstacles (
  segment_id uuid NOT NULL REFERENCES routing.segments(id) ON DELETE CASCADE,
  obstacle_id uuid NOT NULL REFERENCES geo.obstacles(id),
  expected_stop_probability numeric(5,4) CHECK (expected_stop_probability BETWEEN 0 AND 1),
  expected_delay_s numeric(8,2) CHECK (expected_delay_s >= 0),
  approach_speed_kph numeric(7,2) CHECK (approach_speed_kph >= 0),
  passing_speed_kph numeric(7,2) CHECK (passing_speed_kph >= 0),
  confidence numeric(4,3) CHECK (confidence BETWEEN 0 AND 1),
  matching_method text,
  PRIMARY KEY (segment_id,obstacle_id)
);
CREATE INDEX segment_obstacles_obstacle_idx ON routing.segment_obstacles(obstacle_id);

-- FUEL MODELS / RESULTS ------------------------------------------------------
CREATE TABLE fuel.model_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_key text NOT NULL,                 -- baseline, vsp_physics, vt_micro
  version text NOT NULL,
  vehicle_variant_id uuid REFERENCES vehicle.variants(id),
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','calibrating','validated','retired')),
  coefficients jsonb NOT NULL DEFAULT '{}'::jsonb,
  feature_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  code_commit_sha text,
  training_dataset_version text,
  calibrated_at timestamptz,
  validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (model_key,version,vehicle_variant_id)
);

CREATE TABLE fuel.predictions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL REFERENCES routing.candidates(id) ON DELETE CASCADE,
  model_version_id uuid NOT NULL REFERENCES fuel.model_versions(id),
  baseline_l numeric(10,5) CHECK (baseline_l >= 0),
  predicted_l numeric(10,5) NOT NULL CHECK (predicted_l >= 0),
  predicted_l_100km numeric(10,5) NOT NULL CHECK (predicted_l_100km >= 0),
  p10_l numeric(10,5) CHECK (p10_l >= 0),
  p90_l numeric(10,5) CHECK (p90_l >= 0),
  data_completeness numeric(4,3) CHECK (data_completeness BETWEEN 0 AND 1),
  uncertainty_method text,                -- calibrated residuals / bootstrap / none
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  feature_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  predicted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(candidate_id,model_version_id),
  CHECK (p10_l IS NULL OR p90_l IS NULL OR p10_l <= p90_l)
);

-- Mutually exclusive ADDITIVE categories, not one category for each physical cause.
CREATE TABLE fuel.prediction_components (
  prediction_id uuid NOT NULL REFERENCES fuel.predictions(id) ON DELETE CASCADE,
  component_code text NOT NULL CHECK (component_code IN
    ('moving_engine','idle_engine','engine_start','accessory_increment','other')),
  liters numeric(11,6) NOT NULL CHECK (liters >= 0),
  computation_method text,
  PRIMARY KEY (prediction_id,component_code)
);

-- Non-additive counterfactual effects: do NOT sum these to make total fuel.
CREATE TABLE fuel.factor_attributions (
  prediction_id uuid NOT NULL REFERENCES fuel.predictions(id) ON DELETE CASCADE,
  factor_key text NOT NULL REFERENCES core.factor_catalog(factor_key),
  counterfactual_change_l numeric(11,6), -- signed, (prediction - one-factor-switched-off)
  counterfactual_reference jsonb NOT NULL DEFAULT '{}'::jsonb,
  method text NOT NULL DEFAULT 'counterfactual',
  PRIMARY KEY (prediction_id,factor_key)
);

-- EXPERIMENTS / MEASURED TRIPS ----------------------------------------------
CREATE TABLE telemetry.trips (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES core.app_users(id),
  vehicle_instance_id uuid REFERENCES vehicle.instances(id),
  route_request_id uuid REFERENCES routing.requests(id),
  matched_candidate_id uuid REFERENCES routing.candidates(id),
  started_at timestamptz NOT NULL,
  ended_at timestamptz,
  actual_path geometry(LineString,4326),
  actual_distance_m numeric(12,2) CHECK (actual_distance_m >= 0),
  measured_fuel_l numeric(10,5) CHECK (measured_fuel_l >= 0),
  measurement_method text NOT NULL
    CHECK (measurement_method IN ('obd_fuel_rate','maf','injector_pulse','fuel_meter','tank_refill','unknown')),
  measurement_quality numeric(4,3) CHECK (measurement_quality BETWEEN 0 AND 1),
  traffic_notes text,
  is_calibration_sample boolean,
  extra_measurements jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_at IS NULL OR ended_at > started_at)
);
CREATE INDEX trip_vehicle_time_idx ON telemetry.trips(vehicle_instance_id,started_at DESC);
CREATE INDEX trip_path_gix ON telemetry.trips USING gist(actual_path);

-- At modest MSc/BSc prototype volume a composite PK is simpler than early partitioning.
-- If data becomes large, time partitioning requires a migration plan and new constraints.
CREATE TABLE telemetry.samples (
  trip_id uuid NOT NULL REFERENCES telemetry.trips(id) ON DELETE CASCADE,
  recorded_at timestamptz NOT NULL,
  gps_point geometry(Point,4326),
  gps_accuracy_m numeric(7,2) CHECK (gps_accuracy_m >= 0),
  speed_kph numeric(7,2) CHECK (speed_kph >= 0),
  acceleration_mps2 numeric(8,3),
  engine_rpm numeric(8,1) CHECK (engine_rpm >= 0),
  throttle_pct numeric(5,2) CHECK (throttle_pct BETWEEN 0 AND 100),
  engine_coolant_temp_c numeric(6,2),
  maf_g_per_s numeric(9,4) CHECK (maf_g_per_s >= 0),
  map_kpa numeric(7,2) CHECK (map_kpa >= 0),
  intake_air_temp_c numeric(6,2),
  lambda_ratio numeric(7,4) CHECK (lambda_ratio > 0),
  fuel_rate_lph numeric(10,5) CHECK (fuel_rate_lph >= 0),
  engine_on boolean,
  ac_on boolean,
  PRIMARY KEY (trip_id,recorded_at)
);
CREATE INDEX samples_recorded_at_idx ON telemetry.samples(recorded_at DESC);
CREATE INDEX samples_gps_gix ON telemetry.samples USING gist(gps_point);

-- APPEND-ONLY AUDIT ---------------------------------------------------------
CREATE TABLE ops.audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid REFERENCES core.app_users(id),
  entity_table text NOT NULL,
  entity_id uuid,
  action text NOT NULL CHECK (action IN ('insert','update','delete','approve','reject','disable','recalculate')),
  old_value jsonb,
  new_value jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  correlation_id uuid
);
CREATE INDEX audit_entity_date_idx ON ops.audit_events(entity_table,entity_id,occurred_at DESC);

-- Initial reference data, not a claim of calibrated Pride parameters.
INSERT INTO core.data_sources(source_key,display_name,provider_url,license_name,license_url,attribution_text)
VALUES
 ('osm','OpenStreetMap','https://www.openstreetmap.org','ODbL 1.0','https://opendatacommons.org/licenses/odbl/1-0/','© OpenStreetMap contributors'),
 ('user_reports','Moderated user corrections',NULL,'internal',NULL,NULL),
 ('elevation','Elevation DEM provider',NULL,NULL,NULL,NULL),
 ('traffic','Traffic speed provider',NULL,NULL,NULL,NULL),
 ('weather','Weather provider',NULL,NULL,NULL,NULL),
 ('telemetry','Collected vehicle measurements',NULL,'research consent',NULL,NULL)
ON CONFLICT (source_key) DO NOTHING;

INSERT INTO geo.cities(city_code,name_fa,timezone) VALUES ('tehran','تهران','Asia/Tehran')
ON CONFLICT (city_code) DO NOTHING;

-- Do not seed fictional vehicle coefficients. Fill variant fields only from verified
-- specs or measured calibration; this variant is an identity record, not a calibrated car.
INSERT INTO vehicle.variants(variant_key,brand,model_name,trim_name,displacement_cc,transmission)
VALUES ('saipa_pride_131_manual','Saipa','Pride','131',1323,'manual')
ON CONFLICT (variant_key) DO NOTHING;

-- Catalog is a dictionary for attributions; actual numeric values live in typed
-- tables, measured telemetry, or per-request feature_snapshot — not an EAV substitute.
INSERT INTO core.factor_catalog(factor_key,factor_group,title_fa,unit,effect_direction,availability,stage) VALUES
('distance_m','route','مسافت مسیر','m','increase','derived','mvp'),
('road_bearing_deg','route','جهت حرکت نسبت به شمال','degree','conditional','derived','later'),
('intersection_density','route','تراکم تقاطع','count/km','indirect','derived','later'),
('road_closure','route','محدودیت/بسته بودن راه','boolean','indirect','external','later'),
('route_curvature','route','انحنای مسیر','1/m','conditional','derived','later'),
('turn_count','route','تعداد گردش‌های مسیر','count','conditional','derived','later'),
('slope_pct','route','شیب طولی مسیر','%','conditional','derived','mvp'),
('ascent_m','route','ارتفاع‌گیری تجمعی','m','increase','derived','mvp'),
('descent_m','route','کاهش ارتفاع','m','conditional','derived','mvp'),
('road_class','route','رده راه',NULL,'indirect','osm','mvp'),
('speed_limit_kph','route','حداکثر سرعت','km/h','conditional','osm','mvp'),
('surface','route','نوع روسازی',NULL,'conditional','osm','mvp'),
('smoothness','route','همواری و کیفیت سطح',NULL,'conditional','osm','later'),
('lanes','route','تعداد خط عبور','count','indirect','osm','later'),
('junction_density','route','تراکم تقاطع','count/km','indirect','derived','later'),
('rail_crossing_count','obstacle','تعداد تقاطع با راه‌آهن','count','conditional','osm','later'),
('road_narrowing_count','obstacle','تعداد محل تنگ‌شدن راه','count','indirect','osm','later'),
('signal_count','obstacle','تعداد چراغ راهنمایی','count','conditional','osm','mvp'),
('signal_red_probability','obstacle','احتمال توقف چراغ','probability','conditional','derived','mvp'),
('signal_wait_s','obstacle','زمان انتظار چراغ','s','increase','derived','mvp'),
('speed_bump_count','obstacle','تعداد سرعت‌گیر','count','conditional','osm','mvp'),
('bump_crossing_speed_kph','obstacle','سرعت عبور از سرعت‌گیر','km/h','conditional','derived','mvp'),
('stop_sign_count','obstacle','تابلو توقف اجباری','count','conditional','osm','mvp'),
('crossing_count','obstacle','گذرگاه عابر','count','conditional','osm','later'),
('potholes_count','obstacle','دست‌انداز و چاله','count','conditional','user','later'),
('roadworks_count','obstacle','محدوده عملیات راهسازی','count','conditional','osm','later'),
('traffic_speed_kph','traffic','سرعت برآوردی جریان','km/h','conditional','external','mvp'),
('traffic_volume_veh_h','traffic','حجم عبور خودروها','veh/h','indirect','external','later'),
('braking_events_count','traffic','تعداد رویداد ترمز','count','conditional','derived','later'),
('stop_count','traffic','تعداد توقف','count','increase','derived','mvp'),
('stop_go_cycles','traffic','تعداد چرخه توقف و حرکت','count','increase','derived','mvp'),
('queue_delay_s','traffic','زمان تأخیر صف','s','increase','derived','mvp'),
('trip_departure_time','traffic','ساعت شروع سفر','datetime','indirect','user','mvp'),
('mean_speed_kph','dynamics','سرعت میانگین','km/h','conditional','derived','mvp'),
('speed_std_kph','dynamics','نوسان سرعت','km/h','conditional','derived','calibration'),
('acceleration_mps2','dynamics','شتاب لحظه‌ای','m/s2','conditional','derived','mvp'),
('deceleration_mps2','dynamics','کاهش سرعت','m/s2','conditional','derived','mvp'),
('jerk_mps3','dynamics','نرخ تغییر شتاب','m/s3','conditional','derived','later'),
('idle_duration_s','dynamics','مدت درجا کارکردن','s','increase','derived','mvp'),
('driving_style','driver','سبک رانندگی',NULL,'conditional','user','mvp'),
('gear_change_count','driver','تعداد تعویض دنده','count','conditional','sensor','later'),
('driver_headway_s','driver','فاصله زمانی از خودروی جلو','s','indirect','sensor','later'),
('gear_selection','driver','دنده انتخابی','gear','conditional','sensor','later'),
('shift_rpm','driver','دور موتور زمان تعویض دنده','rpm','conditional','sensor','later'),
('vehicle_age_years','vehicle','سن خودرو','year','indirect','user','later'),
('odometer_km','vehicle','کارکرد خودرو','km','indirect','user','later'),
('fuel_tank_load_l','vehicle','مقدار سوخت داخل باک','L','conditional','user','later'),
('roof_rack','vehicle','باربند و بار روی سقف','boolean','conditional','user','later'),
('vehicle_mass_kg','vehicle','جرم مؤثر خودرو','kg','increase','derived','mvp'),
('curb_mass_kg','vehicle','جرم خالی خودرو','kg','conditional','external','mvp'),
('extra_payload_kg','vehicle','وزن افزوده سرنشین و بار','kg','increase','user','mvp'),
('aerodynamic_cd','vehicle','ضریب درگ Cd',NULL,'conditional','external','calibration'),
('frontal_area_m2','vehicle','سطح مقطع روبه‌جلو','m2','increase','external','calibration'),
('rolling_resistance_coeff','vehicle','ضریب مقاومت غلتشی',NULL,'increase','external','calibration'),
('drivetrain_efficiency','vehicle','بازده انتقال نیرو','fraction','decrease','external','calibration'),
('engine_efficiency','vehicle','بازده موتور','fraction','decrease','sensor','calibration'),
('engine_idle_lph','vehicle','مصرف موتور درجا','L/h','increase','sensor','calibration'),
('engine_load_pct','vehicle','درصد بار موتور','%','conditional','sensor','calibration'),
('bsfc_g_kwh','vehicle','مصرف ویژه ترمزی سوخت','g/kWh','conditional','sensor','calibration'),
('maf_g_per_s','vehicle','دبی جرمی هوای ورودی','g/s','conditional','sensor','calibration'),
('map_kpa','vehicle','فشار مطلق مانیفولد','kPa','conditional','sensor','calibration'),
('fuel_trim_pct','vehicle','تصحیح سوخت کوتاه/بلندمدت','%','conditional','sensor','later'),
('lambda_ratio','vehicle','نسبت هوای واقعی به استوکیومتری',NULL,'conditional','sensor','later'),
('injector_pulse_ms','vehicle','زمان پالس انژکتور','ms','conditional','sensor','later'),
('engine_rpm','vehicle','دور موتور','rpm','conditional','sensor','calibration'),
('engine_coolant_c','vehicle','دمای مایع خنک‌کننده موتور','C','conditional','sensor','calibration'),
('engine_maintenance','vehicle','وضعیت فنی موتور',NULL,'conditional','user','later'),
('tire_pressure_kpa','vehicle','فشار باد لاستیک','kPa','conditional','user','mvp'),
('engine_oil_grade','vehicle','ویسکوزیته روغن موتور',NULL,'conditional','user','later'),
('injector_health','vehicle','وضعیت انژکتورها',NULL,'conditional','user','later'),
('ignition_health','vehicle','شمع و سیستم جرقه‌زنی',NULL,'conditional','user','later'),
('air_filter_health','vehicle','وضعیت فیلتر هوا',NULL,'conditional','user','later'),
('wheel_bearing_drag','vehicle','مقاومت بلبرینگ چرخ',NULL,'increase','sensor','later'),
('tire_type','vehicle','نوع و مقاومت لاستیک',NULL,'conditional','user','later'),
('wheel_alignment','vehicle','تنظیم فرمان و زوایا',NULL,'conditional','user','later'),
('brake_drag','vehicle','گیرکردگی ترمز',NULL,'increase','sensor','later'),
('ac_mode','auxiliary','شدت استفاده از کولر',NULL,'conditional','user','mvp'),
('electrical_load_w','auxiliary','بار الکتریکی','W','increase','user','later'),
('windows_open_pct','auxiliary','میزان باز بودن شیشه','%','conditional','user','later'),
('cold_start','auxiliary','استارت سرد','boolean','conditional','user','mvp'),
('engine_soak_min','auxiliary','مدت خاموشی پیش از سفر','min','conditional','user','later'),
('altitude_m','weather','ارتفاع از سطح دریا','m','conditional','derived','later'),
('humidity_pct','weather','رطوبت نسبی','%','conditional','external','later'),
('relative_air_speed_mps','weather','سرعت نسبی خودرو و هوا','m/s','conditional','derived','later'),
('air_density_kg_m3','weather','چگالی هوا','kg/m3','conditional','derived','later'),
('ambient_temp_c','weather','دمای محیط','C','conditional','external','mvp'),
('air_pressure_pa','weather','فشار هوا','Pa','conditional','external','later'),
('wind_speed_mps','weather','سرعت باد','m/s','conditional','external','later'),
('wind_direction_deg','weather','جهت وزش باد','degree','conditional','external','later'),
('rain_mm_h','weather','شدت بارش','mm/h','conditional','external','later'),
('road_wetness','weather','خیسی جاده',NULL,'conditional','external','later'),
('fuel_density_kg_l','fuel','چگالی بنزین','kg/L','conditional','external','later'),
('fuel_lhv_mj_kg','fuel','ارزش حرارتی پایین سوخت','MJ/kg','conditional','external','calibration'),
('fuel_quality','fuel','کیفیت بنزین',NULL,'conditional','user','later')
ON CONFLICT (factor_key) DO NOTHING;

-- Sanity check for an integrated prediction. The rows should be complete before running it:
-- SELECT p.id,p.predicted_l,COALESCE(SUM(c.liters),0) AS additive_sum
-- FROM fuel.predictions p LEFT JOIN fuel.prediction_components c ON c.prediction_id=p.id
-- GROUP BY p.id HAVING abs(p.predicted_l-COALESCE(SUM(c.liters),0)) > 0.001;
-- Non-additive factor_attributions are deliberately excluded from this sum.

COMMIT;
