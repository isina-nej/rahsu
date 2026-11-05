# PrideFuel Tehran — سند جامع اجرای یکپارچه

**نسخه سند:** 2.0 | **تاریخ:** 2026-11-05 | **وضعیت:** برنامه، نه ادعای پیاده‌سازی

## 0. هدف و مرزهای صداقت علمی
سامانه تخمین و مقایسه مصرف بنزین خودرو پراید ۱۳۱ دنده‌دستی در محدوده شهر تهران، با مسیریابی، تحلیل موانع ثبت‌شده در OSM، اصلاح دستی، شیب، پروفایل حرکت مصنوعی، گزارش عدم‌قطعیت و ثبت سفر واقعی برای کالیبراسیون. معماری از ابتدا امکان اضافه‌کردن شهر، خودرو، مدل و منبع داده جدید را می‌دهد.

**خط قرمز:** دقت نهایی بدون آزمایش رانندگی و اندازه‌گیری واقعی پراید قابل تضمین نیست؛ ترافیک لحظه‌ای تهران و چرخه واقعی چراغ‌ها را داده OSM تأمین نمی‌کند؛ ادعای «بهینه‌ترین مسیر کل شبکه» با رتبه‌بندی چند مسیر OSRM مجاز نیست.

**تعریف یک‌مرحله‌ای:** اجرای یک برنامه هماهنگ با تحویل یک نسخه یکپارچه؛ توسعه در شاخه‌ها و گیت‌های تست داخلی، بدون انتشار ناقص روی Production.

### معیارهای خروجی
- React فارسی و RTL: انتخاب نقاط روی نقشه، جست‌وجوی کنترل‌شده آدرس، نمایش مسیرها، عوامل مصرف، کیفیت داده و توضیح اثر موانع.
- Django API نسخه‌دار، PostGIS، OSRM مستقل، ingestion تهران، داشبورد مدیریت، workflow بازبینی موانع.
- مدل baseline و physical/VSP با پارامترهای منبع‌دار؛ VT-Micro با feature flag تا زمان داده واقعی.
- ثبت و نگهداری داده سفر واقعی با رضایت کاربر، مستند ارزیابی MAE/RMSE/MAPE/SMAPE و گزارش خطای مسیر.
- لاگ ساختاریافته + trace + metrics + alert + API امن مشاهده لاگ از راه دور، داشبورد سلامت، audit.
- CI/CD با تست، اسکن امنیتی، بکاپ، restore drill، راهنمای اجرا و rollback.

## 1. فناوری تثبیت‌شده
| لایه | انتخاب | نقش |
|---|---|---|
| Runtime | Python 3.12؛ TypeScript؛ Node LTS | نسخه‌ها در lockfile/image digest تثبیت |
| Backend | Django 5.2 LTS, DRF, GeoDjango, drf-spectacular | API/ORM/PostGIS/OpenAPI؛ پشتیبانی Django 5.2 تا 2028-04 |
| Domain | dataclasses/pydantic v2, NumPy, SciPy, pandas | مدل علمی تایپ‌دار و تست‌پذیر |
| GIS | PostGIS, Shapely, pyproj, GeoPandas, osmium/pyosmium, OSMnx | راه/مانع/ارتفاع/مساحت و جهت |
| Routing | self-hosted OSRM؛ RouterPort برای GraphHopper | مسیرهای جایگزین موجود، نه global fuel optimum |
| Geocoding | جست‌وجوی نقطه روی نقشه همیشه؛ geocoding قابل تعویض از نمونه اختصاصی یا سرویس مجاز | عدم اتکا به auto-complete Nominatim عمومی |
| Elevation | DEM آفلاین، rasterio و نمونه‌برداری هموارسازی‌شده | منبع و دقت DEM نسخه‌دار |
| Frontend | React, TypeScript, Vite, MapLibre GL JS, TanStack Query, Zod, React Hook Form, Tailwind, RTL-compatible UI | رابط کاربر و پنل ادمین |
| Queue | Celery + Redis | ingestion و محاسبات asynchronous، retry idempotent |
| Quality | Ruff, mypy, pytest, pytest-django, Hypothesis, Vitest, Playwright, Bandit, pip-audit, Trivy, Gitleaks | تست/اسکن |
| Infrastructure | Docker Compose, Caddy/Nginx, GitHub Actions, pgBackRest یا pg_dump | انتشار single-node و بازیابی |
| Telemetry | structlog, OpenTelemetry SDK/OTLP, Grafana Alloy, Loki, Prometheus, Tempo, Grafana, Alertmanager | مشاهده‌پذیری |

### منابع اصلی، مستندات و شرایط استفاده
- https://www.djangoproject.com/download/
- https://docs.djangoproject.com/en/5.2/ref/contrib/gis/
- https://project-osrm.org/docs/
- https://github.com/graphhopper/graphhopper/blob/master/docs/core/custom-models.md
- https://download.geofabrik.de/asia/iran.html
- https://operations.osmfoundation.org/policies/nominatim/ (public: <= 1 RPS، بدون autocomplete)
- https://operations.osmfoundation.org/policies/tiles/ (بدون bulk tile download)
- https://opentelemetry.io/docs/languages/python/instrumentation/
- https://grafana.com/docs/alloy/latest/monitor/monitor-docker-containers/
- https://grafana.com/docs/loki/latest/reference/loki-http-api/
- https://grafana.com/docs/tempo/latest/set-up-for-tracing/

## 2. مرزبندی دامنه و طراحی ماژول
معماری Modular Monolith با API درونی Ports/Adapters، هر دامنه صاحب منطق و نگارش دیتای خود. route و dataset سرویس‌های اجرایی جدا اما **نه** microservice کسب‌وکار.

| ماژول | مسئولیت | جداول فعلی | API درونی |
|---|---|---|---|
| identity_access | کاربر، role، توکن، سشن | core.app_users | authorize(action,subject) |
| reference_data | provenance، import batch، factor catalog | core.data_sources, ingestion_batches, factor_catalog | dataset_version(), source_quality() |
| map_ingestion | بارگیری PBF، roads/elevation؛ به‌روزرسانی atomic | geo.cities, road_segments, elevation_samples | import_city(), active_snapshot() |
| geocoding | تبدیل متن/پین و normalization فارسی | cache جدید اختیاری | search(), reverse(), resolve_point() |
| route_planner | کاندیدهای هندسی، نرمال‌سازی خطوط | routing.requests, candidates | find_routes(RouteQuery) |
| obstacle_registry | تشخیص و تطبیق موانع، ورود گزارش و تأیید | geo.obstacles, obstacle_reports, routing.segment_obstacles | match_obstacles(), review_report() |
| context_engine | ترافیک تاریخی، هوا، شیب، محدودیت سرعت | geo.traffic_profiles, geo.weather_observations | build_context(route,time) |
| motion_engine | شبیه‌سازی سرعت، شتاب، توقف و توالی زمانی | routing.segments, motion_samples | generate_motion_profile(context,scenario,seed) |
| vehicle_catalog | مشخصات Pride و شرایط سرویس | vehicle.variants, instances, maintenance_events | get_effective_parameters() |
| fuel_engine | baseline، VSP/power، VT-Micro، provenance | fuel.model_versions, predictions, prediction_components, factor_attributions | estimate(profile,vehicle,model_version) |
| calibration | تله‌متری، تفکیک train/validation، نسخه ضرایب | telemetry.trips, samples | fit(), evaluate(), publish_if_accepted() |
| operations | audit، گزارش سلامت، export، monitoring proxy | ops.audit_events؛ داده Loki/Prometheus/Tempo خارج DB | query_logs(), get_health(), audit() |

**قواعد توسعه:**
1. Domain pure Python، بدون HTTP/ORM در هسته مدل سوخت. View -> Application Service -> Domain -> Port -> Adapter.
2. DTOهای versioned، import مستقیم models متعلق به دامنه دیگر فقط از لایه read-only مجاز و مستند.
3. وابستگی‌های بیرونی با Timeout، retry با backoff/jitter، circuit breaker و خروجی degradable.
4. تمام ورودی‌ها واحد SI در Domain؛ لایه Presentation تبدیل km/h و L/100km انجام دهد.
5. فاکتور فاقد داده => `unknown` + warning؛ هیچ‌وقت null = zero.
6. پارامترهای calibration، منبع، snapshot نسخه PBF/DEM و نسخه کد ذخیره شوند.
7. اضافه‌کردن خودرو یا شهر جدید: adapter/data/model configuration، نه شرط `if city == Tehran` در تمام فایل‌ها.

### قراردادهای مشترک تایپ‌دار
- `RouteQuery(origin, destination, departure_at, vehicle_class='car', alternatives=True)`
- `RouteCandidate(geometry, edge_refs, distance_m, nominal_duration_s, provenance)`
- `ObstacleMatch(segment_ref, obstacle_ref, direction, confidence, expected_speed_reduction, expected_delay)`
- `DrivingScenario(mass_extra_kg, ac_mode, cold_start, tire_pressure, driving_style, conditions)`
- `MotionPoint(t_s, s_m, v_mps, a_mps2, grade_rad, stopped, source)`
- `FuelResult(liters, components, assumptions, warnings, model_version, quality)`
- `PredictionRun(run_id, route_data_version, model_version, status, timestamps, trace_id, error_code)`

## 3. طرح بانک اطلاعاتی و Migration
**Baseline:** `/mnt/data/pride_tehran_schema.sql` دارای ۲۷ جدول در schemaهای core/geo/vehicle/routing/fuel/telemetry/ops است؛ سند فعلی `pride_tehran_database_design.md` مبناست، نه script قابل اعمال کورکورانه روی Production. کاتالوگ ۹۴ عامل مرجع است؛ ورودی‌های user/data provenance در MVP باید subset مشخص شوند.

**Source of truth:** Django migrations + `RunSQL` versioned برای extension و index و seed. SQL اولیه یک مرجع طراحی است، نه کانال موازی migration. اول migrationهای متناظر با schema قبلی تولید، سپس CI روی PostgreSQL/PostGIS واقعی از دیتابیس خالی تست شود.

**Migrationهای افزایشی الزامی**:
- `core.integration_events` یا `ops.job_runs`: وضعیت worker/job، attempt، idempotency_key، progress، code و `trace_id`.
- `geo.dataset_snapshots`: نسخه PBF/DEM، checksum، زمان publish، کیفیت، import batch، active pointer.
- `fuel.calibration_runs`: hash دیتاست train/validation، پارامترها، خطا و provenance.
- `ops.security_events`: trace تغییر مجوز/توکن؛ برای حذف/بازبینی رخداد حساس audit بدون اطلاعات محرمانه.
- `telemetry.consent_records`: رضایت، زمان، نوع داده، مدت نگهداری، درخواست پاک‌سازی.
- `ops.outbound_call_stats` اختیاری برای ردیابی سرویس خارجی؛ برای هر درخواست HTTP رویداد کوتاه‌عمر metrics/traces کافی است.

**indexها:** GiST روی geometry، unique بر `(source_id,osm_element_type,osm_element_id)`، B-tree برای `(city, road_class)`, `(job_id,status)`, `(route_id,segment_no)`, `(model_version,created_at)`، BRIN/partition برای telemetry.samples حجیم.

**ملاحظات correctness:** `ST_Covers(city.boundary, origin/destination)`؛ شبکه road segments از OSM/topology نرمال؛ جهت حرکت و layer bridge/tunnel در match؛ route snapshot immutability؛ `prediction_components` additive sum با predicted_l تطبیق؛ فاکتورهای توضیحی ممکن است additive نباشند.

## 4. نقشه تهران و pipeline ورودی داده
1. دانلود PBF ایران از Geofabrik به artifact با checksum/hash؛ استخراج پلیگون تهران + حاشیه برای اتصال مسیرهای مرزی (حاشیه باید با تست شبکه تعیین شود).
2. `osmium extract` + import topology/راه‌های خودرویی + استخراج obstacle tags؛ حافظه و فضای دیسک را از روی داده واقعی benchmark کنیم.
3. ساخت موتور OSRM آفلاین و نسخه‌بندی graph؛ در زمان import سرویس فعلی باقی بماند؛ swap atomic پس از health/route test.
4. بارگیری DEM آفلاین با منبع/مجوز ثبت‌شده؛ نمونه‌گیری فاصله‌ای با smoothing و تشخیص پل/تونل/خطای DEM.
5. گزارش‌های اصلاح دستی `pending` -> مدیر approve/reject -> audit/version -> overlay به dataset؛ داده OSM اصلی غیرقابل ویرایش.
6. جداکردن road data version از obstacle overlay version؛ invalidate cacheهای affected tile/route.
7. geocoder adapter برای سرویس مجاز یا self-hosted؛ fallback انتخاب مستقیم روی نقشه؛ حذف dependency به autocomplete عمومی Nominatim.
8. برنامه update دوره‌ای OSM، با revalidation mappingها و rollback به dataset قدیمی هنگام افت کیفیت.

**عدم قطعیت‌ها:** نه اطلاعات OSM همه چراغ‌ها را شامل می‌شود، نه فاز چراغ را؛ traffic واقعی در یک API مستقل نیاز دارد. اگر unknown بود، سناریوی range و برچسب no-live-traffic نمایش دهیم.

## 5. موتور حرکت و سوخت
### 5.1 فرآیند
- OSRM route -> segment-specific geometry/road class/maxspeed/grade -> obstacles matched by way + direction + elevation layer.
- سرعت هدف بر اساس road class, speed limit, traffic profile(if available), driving style؛ constraints حرکت و توان خودرو؛ عامل توقف چراغ با انتظار آماری و confidence.
- شبیه‌سازی حرکت discretized با `dt` قابل تنظیم (پیشنهاد آغاز ۱ ثانیه)، توقف/کاهش سرعت/شتاب‌گیری و جابه‌جایی؛ deterministic with seed.
- mass = curb mass semantics + payload + fuel mass exactly once؛ air-relative speed wind vector؛ rolling and slope energy; idling, auxiliary energy, cold start separately.
- **Baseline**: D * C_ref /100؛ **physics**: `P_wheel = (m_eq*a + m*g*Crr*cos(theta) + m*g*sin(theta) + 0.5*rho*Cd*A*v_rel^2) * v`؛ توان مثبت بعد از drivetrain/engine efficiency و LHV به fuel flow؛ brake/fuel-cut/idle conditional؛ **VT-Micro** only if calibrated coefficients.
- route consumption = integrate nonnegative liters/s over dt؛ compare expected fuel, time, distance, uncertainty and data coverage.
- preventing double count: چراغ/سرعت‌گیر فقط حرکت را تغییر می‌دهد و «جریمه سوخت» جداگانه ندارد اگر مدل dynamic آن را قبلاً پوشش داده.

### 5.2 کالیبراسیون و سنجش
- داده GPS + سوخت‌گیری دقیق یا OBD پشتیبانی‌شده با provenance، timezone و unit؛ سنجش consumption واقعی باید uncertainty گزارش شود.
- حداقل طرح اولیه ۲۰–۳۰ سفر متنوع برای feasibility؛ برای ادعای دقت بالا داده بیشتر و تکرار/رانندگان/زمان‌های مختلف نیاز است.
- تقسیم train/validation/test بر اساس سفر و روز (جلوگیری از data leakage)، baseline vs physical vs VT-Micro؛ MAE (L/trip), RMSE, MAPE فقط در مقادیر مثبت و قابل اعتماد، خطای L/100km و بایاس.
- model artifact و coefficients immutable؛ عدم انتشار خودکار نسخه جدید اگر regression نسبت به baseline دارد.

## 6. قراردادهای HTTP عمومی
`/api/v1/`، OpenAPI/Swagger؛ ورودی/خروجی JSON UTC ISO8601؛ geometry GeoJSON [longitude,latitude].

| روش و مسیر | عملکرد | دسترسی |
|---|---|---|
| GET /meta/version | build SHA، نسخه dataset/model و flagها (بدون اسرار) | عمومی |
| GET /cities/tehran | مرز سرویس و داده پوشش | عمومی |
| GET /geocode/search?q= | جست‌وجوی فارسی با rate limit | عمومی محدود |
| POST /route-estimates | ایجاد job، `202 Accepted`, Idempotency-Key | کاربر/مهمان با quota |
| GET /route-estimates/{id} | وضعیت و مراحل job؛ `queued/running/completed/failed` | مالک |
| GET /route-estimates/{id}/results | چند مسیر، اجزا، quality، warning | مالک |
| GET /obstacles?bbox= | موانع تأییدشده با pagination | عمومی محدود |
| POST /obstacle-reports | گزارش تغییر/افزودن/حذف | authenticated |
| GET /admin/obstacle-reports | صف بازبینی | moderator |
| PATCH /admin/obstacle-reports/{id} | approve/reject با revision check | moderator |
| POST /telemetry/trips | ثبت سفر/رضایت و نمونه‌های کنترل‌شده | مالک |
| GET /models | نسخه و وضعیت مدل، بدون اسرار | عمومی |
| GET /health/live | آیا process زنده است | internal / load balancer |
| GET /health/ready | آماده پذیرش درخواست/اتصال DB+deps | internal / load balancer |

**Endpoint پردازش**: درخواست کوتاه با `POST` job آسنکرون؛ frontend polling؛ پاسخ 202 شامل request_id، status_url و trace_id بدون اطلاعات حساس. Timeout stage-specific، retries با backoff و idempotency، dead-letter/requeue دستی و job cancellation.

**خطاهای دامنه:** INVALID_COORDINATE, OUTSIDE_TEHRAN, NO_ROUTE, ROUTING_UNAVAILABLE, GEO_DATA_STALE, OBSTACLE_LOW_COVERAGE, ELEVATION_UNAVAILABLE, ESTIMATION_FAILED, RATE_LIMITED. پاسخ failure با code، message_fa، trace_id و retryable.

## 7. مشاهده‌پذیری حرفه‌ای
### 7.1 topology
```
Django API / Celery Worker / Geo Imports / OSRM / DB / Docker Host
  ├── JSON stdout logs (structlog) ──> Grafana Alloy ──> Loki
  ├── OpenTelemetry OTLP spans ──────> Grafana Alloy ──> Tempo
  └── /metrics Prometheus exporters ─> Prometheus ──> Alertmanager
                                                  └──> Grafana dashboards
                             Restricted Django Observability API ──> Loki/Prometheus/Tempo
```
**علت Alloy:** Promtail در 2026-03-02 EOL شده و نباید برای پروژه جدید استفاده شود.

### 7.2 schema JSON log
هر event با UTC timestamp, severity, service, environment, module, event, message_code, request_id, trace_id, span_id, job_id, route_id (شناسه تصادفی)، dataset_version, model_version, stage, duration_ms, status, error_type, retryable, build_sha. مقادیر پرکاردینال مثل route_id فقط JSON field؛ Loki label فقط app/env/service/level (کاهش cardinality).

**هرگز در لاگ ثبت نشود:** JWT, API key, cookie, authorization headers, precise home coordinates, raw user GPS traces, email/phone, raw request body or telemetry payload. Masking at source + Alloy processors; tests برای leak.

مثال:
```json
{"timestamp":"2026-11-05T14:00:00Z","level":"ERROR","service":"fuel-api","module":"routing","event":"routing.provider.timeout","trace_id":"3c6a0c52d7e24a51b8738e4d9a10b94f","job_id":"7b6f...","provider":"osrm","duration_ms":3001,"retryable":true,"build_sha":"example"}
```
### 7.3 متریک‌های ضروری
- HTTP RED: requests_total, request_duration_seconds histogram, 5xx/429.
- jobs: queued, running, failures by stage, retry count, queue_age_seconds, stage_duration_seconds.
- routing: route_found_rate, provider timeout, candidate_count, duration, geo data version.
- spatial: obstacle matched/unmatched, pct_uncertain, stale_dataset_age, number corrected, invalid layer matches.
- fuel: predicted_l histogram, model_runtime_ms, model_invalid_count, calibration_mae_by_version (**بدون شناسه‌های پرکاردینال**).
- infra: CPU/memory/disk, Postgres latency/connections, Redis memory, worker heartbeat, Loki ingest latency, telemetry drop count.

### 7.4 dashboardهای اولیه
1. Operations overview: availability, requests, 5xx, p50/p95/p99, queue age, disk.
2. Geodata: import health, تهران coverage, obstacle provenance, matched vs uncertain, last sync.
3. Fuel science: predictions, no-data warnings, versions, MAE/Bias after calibration.
4. Security/audit: 401/403 spikes, role changes, admin log read actions.

### 7.5 هشدارهای نمونه (قابل تنظیم پس از load test)
- نرخ 5xx بیش از 2% در 5 دقیقه و حداقل 100 درخواست: warning.
- OSRM unavailable > 2 min: critical.
- صف پردازش oldest job > 120s for 10 min: warning.
- import mismatch یا dataset > 48h از update هدف: warning.
- disk > 80% برای 15 دقیقه: warning؛ > 90% critical.
- backup failure، absence successful backup 26h، restore drill failure: critical.
- monitoring ingest absence > 5min: warning؛ هشدار از outside stack (dead-man switch).
- critical security events / unusual unauthorized log API access: notify admin.

### 7.6 API امن لاگ‌ها و مانیتورینگ از راه دور
لایه Django: `GET /api/v1/admin/observability/logs?service=&level=&from=&to=&limit=&trace_id=`؛ `GET /api/v1/admin/observability/logs/{event_id}`؛ `GET /api/v1/admin/observability/health`; `GET /api/v1/admin/observability/metrics/summary`; `GET /api/v1/admin/observability/traces/{trace_id}`؛ `GET /api/v1/admin/audit-events`.

لایه خواندن: backend با credential **read-only** و network private فقط از Loki `/loki/api/v1/query_range`، Prometheus query، Tempo trace API استفاده می‌کند؛ هیچ کاربر نمی‌تواند LogQL/PromQL raw ارسال کند. فیلترها allowlist، max page=500، max range=24h، max query timeout=5s، rate 20/min/admin (configurable)، export محدوده بزرگ به job کنترل‌شده.

**امنیت:** role=ops_observer/admin و MFA، token با scopes مثل `observability.logs.read` و TTL کوتاه؛ audit هر query؛ mTLS/VPN (WireGuard/Tailscale) ترجیحی برای Grafana و زیرساخت؛ IP allowlist در صورت امکان؛ CORS محدود؛ Grafana و Loki/Tempo/Prometheus بر روی پورت عمومی expose نشوند. Loki self-hosted **authorization داخلی ندارد**، `X-Scope-OrgID` جای احراز هویت نیست.

### 7.7 نگهداری و حریم خصوصی
پیشنهاد شروع: logs 14 روز، traces 7 روز، metrics 30 روز، security audit 365 روز (متناسب با دیسک/نیاز دانشگاه)، داده GPS خام فقط با رضایت و سیاست حذف؛ backup رمزنگاری‌شده و حذف‌پذیری داده خصوصی. ذخیره‌سازی volume و retention با sizing عملی تنظیم شوند.

## 8. امنیت و data governance
- HTTPS/TLS، secure cookie/same-site/CSRF برای پنل، JWT/OAuth scopes only where needed، rotate secrets.
- permissions object-level؛ route result قابل خواندن فقط مالک؛ admin APIs محدود به role+MFA.
- SQL parametrized؛ GeoJSON validated, bbox max size, path sampling cap, SSRF protection برای خدمات خارجی، outbound allowlist.
- Ratelimit IP/user، WAF optional، no external remote command exec از داخل observability API.
- license attribution ODbL و شرایط tile؛ data source/license/updated timestamp در UI و DB.
- SAST/DAST/dependency scan، secrets scan، image digest، signed CI artifact اختیاری.
- Audit append-only با رخدادهای integrity-protected؛ مدیران audit trail را از طریق API تغییر نمی‌دهند.

## 9. ساختار مونوریپو
```
pridefuel/
├── apps/
│   ├── web/                    # React+TypeScript+RTL+MapLibre
│   └── api/                    # Django+DRF
│       ├── config/             # settings/urls/celery/otel
│       ├── modules/
│       │   ├── identity_access/
│       │   ├── reference_data/
│       │   ├── map_ingestion/
│       │   ├── geocoding/
│       │   ├── route_planner/
│       │   ├── obstacle_registry/
│       │   ├── context_engine/
│       │   ├── motion_engine/
│       │   ├── vehicle_catalog/
│       │   ├── fuel_engine/
│       │   ├── calibration/
│       │   └── operations/
│       └── tests/
├── packages/
│   ├── contracts/              # OpenAPI schema + generated TS client
│   ├── scientific-fixtures/    # golden samples/units/calibration tests
│   └── ui/                     # shared presentation components
├── infrastructure/
│   ├── compose/                # dev/staging/prod profiles
│   ├── proxy/                  # TLS, security headers
│   ├── monitoring/             # alloy/loki/tempo/prometheus/grafana/alerts
│   ├── routing/                # osrm build/import versioning
│   └── backups/
├── scripts/                    # deterministic import/seed/restore/benchmark
├── docs/
│   ├── adr/                    # design decisions
│   ├── api/
│   ├── runbooks/
│   ├── research/
│   ├── privacy/
│   └── acceptance/
├── .github/workflows/
├── pyproject.toml
├── uv.lock
├── pnpm-lock.yaml
├── Makefile
└── README.md
```

## 10. استقرار و منابع
- توسعه: Docker Compose profiles `core` / `full-observability`; Testcontainers برای PostGIS/Redis. staging به production نزدیک.
- production پیشنهادی (تخمین اولیه و نه benchmark): 4 vCPU، 8–16GiB RAM، SSD سریع با headroom برای داده و لاگ؛ import بزرگ routing و ابزارهای مانیتورینگ را هنگام build جدا اجرا کنید. میزبان حدود 4GiB RAM برای **تمام** OSRM+PostGIS+Loki+Prometheus+Tempo+Grafana+worker بدون benchmark مناسب فرض نشود.
- یک Production host + external backup object storage کافی برای دامنه کارشناسی، اما HA واقعی نیست؛ RPO هدف <=24h و RTO هدف <=4h **تنها با آزمایش restore**.
- reverse proxy تنها 443 public؛ API health محدود؛ DB/Redis/OSRM/Loki/Tempo/Prometheus private network؛ Grafana private/VPN.
- نشر: build/pin artifact -> staging migrations -> DB backup -> deployment release -> smoke+synthetic routes -> promote -> rollback images/config، migrations expand-contract.
- snapshots of Tehran map/DEM old/new parallel for safe switch؛ no downtime import lock.

## 11. CI/CD و quality gates
1. style/type: ruff, mypy, ESLint/tsc, prettier, OpenAPI compatibility.
2. unit: geometry edge cases, physical units, no negative fuel, deterministic seeds, null != zero, no double count.
3. integration: PostGIS in Docker; OSM import small fixture; Celery/Redis; OSRM stub and live smoke fixture; admin approval+audit.
4. contract: OpenAPI generated client and schema validation; backward compat API.
5. E2E: Tehran pin-to-pin, one route, multiple route, failed geocode, outside boundary, no obstacle, low-data, permission denied.
6. security: unauthenticated /admin logs 401, forbidden 403, raw Loki ports not public, LogQL blocked, leaked token tests, rate limit.
7. observability: generate trace and error -> correlation log in Loki + span in Tempo + metric in Prometheus + admin API query returns sanitized record.
8. backup/restore drill: empty DB -> restore -> migrations -> known route regression.
9. load: p95 first result warm request target <=10s (goal only), memory within resource budget, no queue starvation.
10. science: test models against data set held out, report MAE/RMSE/MAPE and confidence/limitations; compare to baseline.

## 12. دستورات اجرایی هدف (بعد از پیاده‌سازی)
```
make setup
make data-tehran-import
make up
make migrate
make seed-pride
make test
make e2e
make observability-smoke
make backup
make restore-test
make deploy-staging
make deploy-production
make rollback
```
این دستورات **قرارداد ساخت آینده** هستند و در لحظه نگارش اجرا یا ساخته نشده‌اند.

## 13. مراحل داخلی یک انتشار یکپارچه
- G0 Foundation: monorepo, lockfiles, compose, base DB migrations, secrets, CI. Gate: fresh install green.
- G1 Data: Tehran OSM/DEM pipeline, OSRM, routing adapters, geodata snapshot. Gate: route + geometry/topology fixtures green.
- G2 Domain: 27-table models migration، obstacle overlay، admin review، feature registry. Gate: audit and no-double-count tests green.
- G3 Science: motion+physics+baseline+VT-Micro gated، uncertainty، validation fixtures. Gate: conservation, reproducibility, no negative fuel.
- G4 Product: user web, admin console, jobs OpenAPI. Gate: E2E RTL mobile+desktop green.
- G5 Ops: Loki/Tempo/metrics/alerts/admin logs API, backups. Gate: simulated 500 + trace lookup + alert + restore test.
- G6 Hardening: security, load, data quality report, academic results, docs. Gate: release checklist all green.
- G7 One coordinated release: staging review + production deployment + smoke + monitored rollback availability.

## 14. Definition of Done قطعی
- `make setup && make test` از صفر سبز؛ همه ماژول‌ها lint/type/test مستند دارند.
- ورودی معتبر تهران -> حداقل یک candidate یا خطای دامنه واضح؛ مختصات اشتباه رد می‌شود.
- تصحیح مانع بعد از تأیید در خروجی بعدی اثر قابل ردیابی دارد و audit مستقل دارد.
- مقادیر سوخت و واحدها معتبرند؛ کمبود ترافیک/ارتفاع را پنهان نمی‌کنیم.
- وضعیت مدل و نسخه داده همراه هر پیش‌بینی ثبت می‌شود؛ نتایج deterministic با snapshot ثابت.
- مقادیر علمی به‌صورت گزارش شده و با baseline مقایسه می‌شوند؛ هیچ accuracy ساختگی چاپ نمی‌شود.
- خطای عمدی OSRM/DB/worker -> log ساختاریافته، trace، metric و اخطار؛ API فقط با credential درست log می‌دهد.
- Loki/Tempo/Prometheus/Redis/Postgres از اینترنت عمومی قابل اتصال مستقیم نیستند.
- Grafana dashboard provisioning، backup و restore drill، runbook و rollback اجرا/مستندسازی شده‌اند.
- UI موبایل/دسکتاپ فارسی، RTL، نقشه با attribution و پنل مدیر نقش‌محور.

## 15. ریسک‌ها و تصمیم‌های مهندسی
| ریسک | تصمیم |
|---|---|
| نقشه موانع تهران ناقص | ناحیه کم‌اطمینان + گزارش دستی + confirmation workflow |
| ترافیک زنده/فاز چراغ موجود نیست | سناریوهای probabilistic، not-live badge، traffic adapter optional |
| ناهمخوانی OSM road edges و OSRM candidates | map-match, direction/layer checks, strict geometry fixture |
| داده واقعی پراید برای accuracy نداریم | model experimental, record trips, calibrate, no fabricated % |
| کمبود RAM/دیسک | build offline، external monitoring یا hosted stack در صورت اندازه‌گیری، retention controls |
| log API خطر افشای داده | read-only bounded queries, RBAC+MFA+audit+private Loki, redaction tests |
| شکست آپدیت داده یا کد | immutable snapshots + swap/rollback + backups |
| کنترل کد تیم/عامل خودکار | owner per module, openapi/DTO contract, no cross-module shortcuts, CI gates |

## 16. ترتیب شروع کار توسعه
ابتدا یک repository جدید مستقل بسازید و dataset و فایل مرجع SQL موجود را به `docs/reference/` منتقل کنید. فایل SQL قبلی را مستقیم روی دیتابیس زنده اجرا نکنید. نخست ORM migrations source-of-truth و تست integration پایه؛ سپس ingestion تهران و endpoint async؛ سپس scientific engine و observability; در آخر رابط کاربری. تمام این کارها در یک برنامه کاری و یک انتشار نهایی هماهنگ انجام می‌شود.

---
**اصول کلیدی:** هر داده provenance دارد؛ هر مدل version دارد؛ هر درخواست trace دارد؛ هر تغییر مدیر audit دارد؛ هر انتشار rollback دارد؛ هر ادعای دقت آزمایش دارد.
