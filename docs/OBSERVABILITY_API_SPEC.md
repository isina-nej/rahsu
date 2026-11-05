# PrideFuel — قرارداد API مشاهده‌پذیری و لاگ از راه دور

**وضعیت:** طرح API برای پیاده‌سازی؛ endpointها هنوز عملیاتی نشده‌اند.

## معماری اعتماد و احراز هویت
- اینترنت -> Caddy(443) -> Django `/api/v1/admin/observability/**` -> شبکه خصوصی -> Loki/Prometheus/Tempo.
- هیچ پورت Loki:3100، Prometheus:9090، Tempo و Grafana بدون محافظ عمومی نمی‌شود.
- فقط `ops_observer` یا `admin` با MFA و scope معتبر (`observability.logs.read`, `observability.metrics.read`, `observability.traces.read`).
- نشست مرورگر با SameSite/CSRF؛ توکن API شخصی کوتاه‌عمر و read-only، شناسه توکن hashed در DB.
- همه عملیات observability API در `ops.audit_events` ثبت می‌شوند: actor/role/query time range/filters/result_count/trace_id، بدون raw message یا secret.
- Loki standalone auth/authorization ندارد؛ tenant header احراز هویت نیست. backend از credential/service mesh private استفاده کند.
- داده‌های حساس قبل از ذخیره scrub می‌شوند؛ در پاسخ API نیز redaction نهایی انجام می‌شود.

## فهرست endpointها
| Method | Path | پارامتر | نتیجه |
|---|---|---|---|
| GET | `/api/v1/admin/observability/logs` | service,level,from,to,trace_id,job_id,limit | لیست redacted لاگ |
| GET | `/api/v1/admin/observability/logs/{event_id}` | event_id | جزئیات یک event در بازه retention |
| GET | `/api/v1/admin/observability/health` | — | heartbeat سرویس‌ها و وضعیت ingestion |
| GET | `/api/v1/admin/observability/metrics/summary` | window=5m/15m/1h/24h | aggregations امن predefined |
| GET | `/api/v1/admin/observability/traces/{trace_id}` | trace_id | خلاصه spanها، بدون attributes حساس |
| GET | `/api/v1/admin/audit-events` | from,to,actor_id,action,limit | رخدادهای مدیریتی read-only |

### مثال مشاهده لاگ
```
GET /api/v1/admin/observability/logs?service=fuel-api&level=ERROR&from=2026-11-05T13:00:00Z&to=2026-11-05T14:00:00Z&limit=50
Authorization: Bearer <redacted-token>
```
```json
{
  "request_id": "req_01HX",
  "query": {"service":"fuel-api","level":"ERROR","from":"2026-11-05T13:00:00Z","to":"2026-11-05T14:00:00Z","limit":50},
  "data": [{"event_id":"ev_19","timestamp":"2026-11-05T13:20:00Z","service":"fuel-api","level":"ERROR","event":"route.provider.timeout","message":"Provider timed out","trace_id":"7dc76dd2c3a74ff99bbfe273f13d58d0","job_id":"job_42","duration_ms":3000,"retryable":true}],
  "next_cursor": null,
  "truncated": false
}
```

### سیاست درخواست
- فیلتر level فقط DEBUG/INFO/WARNING/ERROR/CRITICAL؛ service فقط enum شناخته‌شده؛ IDها فقط pattern معتبر؛ `limit` 1..500.
- range پیش‌فرض 15 دقیقه؛ سقف 24 ساعت؛ `query_timeout` <= 5s؛ rate 20/min برای ادمین (اعداد قابل تنظیم).
- ورودی `query`, `logql`, `promql`, `regex` یا label آزاد ممنوع؛ ساخت query فقط در server از templateهای allowlist.
- pagination پایدار باید بر اساس timestamp و unique event-id یا hash و فیلتر ساخته شود؛ duplicate timestamp و out-of-order events در تست بررسی شوند.
- خطاها: 401 unauthenticated، 403 forbidden، 400 invalid_filter، 429 rate_limited، 503 monitoring_backend_unavailable.
- `health` نباید اطلاعات سرور، آدرس داخلی، version secrets یا config sensitive لو بدهد.

## قراردادهای استاندارد لاگ
```json
{
 "timestamp":"2026-11-05T14:00:00.000Z",
 "severity":"ERROR",
 "service":"fuel-worker",
 "environment":"production",
 "module":"motion_engine",
 "event":"motion.profile.validation_failed",
 "message_code":"INVALID_MOTION_SEGMENT",
 "trace_id":"1e73400b45854d5cb8219f1ca7ecf312",
 "span_id":"bca5d1ce9933ab04",
 "request_id":"req_01HX",
 "job_id":"job_42",
 "model_version":"physical-v1.0",
 "dataset_version":"tehran-osm-20261105",
 "stage":"simulation",
 "duration_ms":742,
 "error_type":"InvalidSpeedProfile",
 "retryable":false,
 "build_sha":"4f3b2a1"
}
```
**از logها حذف:** name,email,phone,GPS coordinates, user addresses, tokens, passwords, cookies, request/response full body و استثناهایی که چنین داده‌هایی را داخل stacktrace دارند.

## Dashboards و Alerts
**overview:** req/s, p95 latency, 5xx, queue age, OSRM availability, database, disk.
**scientific:** prediction count, model runtime, input quality, non-calibrated warning count, calibration baseline deltas.
**geo:** ingestion status, last import, road match errors, count obstacles by verification.
**security:** admin read logs, 401/403, token rotation, suspicious access.

**هشدارها:** sustained 5xx >2% (با sample>=100)، OSRM down >2min، queue age>120s، stale dataset >48h هدف، disk >80%, backup failure، no telemetry from Alloy >5min. قیود load/retention بعد از benchmark اصلاح شوند.

## تست‌های لازم
1. بدون توکن: 401؛ با توکن کاربر عادی: 403.
2. `logs` با service یا level غیرمجاز رد شود؛ payload حاوی LogQL در ورودی هرگز اجرا نشود.
3. توکن ops read-only نتواند log push/delete کند.
4. token/authorization/GPS مصنوعی به log ارسال شود و assertion کند هیچ ردپای حساس در Loki/API وجود ندارد.
5. درخواست با `trace_id` یک error حقیقی API/worker را در Loki و Tempo پیدا کند.
6. قطع Loki منجر به 503 امن و alert شود؛ app اصلی همچنان قابلیت تخمین را (در صورت سلامت سایر اجزا) داشته باشد.
7. ورودی 25h، limit 501، درخواست‌های پشت‌سرهم -> خطا/429.
8. Port scanner نشان دهد backend DB/Loki/Prometheus/Tempo از Internet route قابل اتصال نیست.

## docs
- https://grafana.com/docs/loki/latest/reference/loki-http-api/
- https://grafana.com/docs/tempo/latest/set-up-for-tracing/
- https://grafana.com/docs/alloy/latest/monitor/monitor-docker-containers/
- https://opentelemetry.io/docs/languages/python/instrumentation/
