# راه‌سو | Rahsu

**سامانه پژوهشی تخمین مصرف بنزین پراید ۱۳۱ در تهران** با مسیریابی، شواهد موانع، مدل فیزیکی، ابزار کالیبراسیون و مشاهده‌پذیری از راه دور.

> وضعیت: MVP توسعه‌ای و قابل تست. مسیر تهران فقط بعد از تأمین گراف OSRM و داده‌های OSM واقعی کار می‌کند. اعداد مصرف هنوز با رانندگی واقعی پراید اعتبارسنجی نشده‌اند؛ برآورد علمی‌اند، نه اندازه‌گیری.

## فناوری‌ها

- Django 5.2 LTS + Django REST Framework + GeoDjango / PostGIS
- دامنه مستقل `backend/domain`: فیزیک سوخت، سناریوی حرکت، شیب، تطبیق موانع، VT-Micro آزمایشگاهی
- React + TypeScript + MapLibre + OpenFreeMap
- OSRM (نیازمند داده تهران)، OSM / osmium و سرویس ارتفاع اختیاری OpenTopoData
- Redis، Celery، OpenTelemetry، Grafana، Prometheus، Tempo، Loki، Alloy
- GitHub Actions برای Python، PostGIS، Frontend و اعتبارسنجی Compose

## اجرا

1. `cp .env.example .env` و تمام رمزها و کلیدهای پیش‌فرض را عوض کنید.
2. `docker compose up --build -d`
3. `docker compose exec api python manage.py migrate`
4. `docker compose exec api python manage.py seed_pride`
5. فایل `iran-latest.osm.pbf` را از Geofabrik تهیه و checksum را تأیید کنید.
6. `bash scripts/prepare_tehran_data.sh /path/to/iran-latest.osm.pbf`
7. `bash scripts/prepare_osrm.sh data/osrm/tehran.osm.pbf`
8. `docker compose --profile routing up -d osrm`
9. `docker compose exec api python manage.py import_osm_geojson /data/osm/tehran-obstacles.geojson`
10. `docker compose --profile monitoring up -d` (اختیاری، برای ابزارهای نظارتی)

پس از راه‌اندازی، وب از `http://localhost:8080` و API از مسیر `/api/` در دسترس است. `/admin/` پنل Django است؛ با `createsuperuser` حساب مدیر ایجاد کنید.

آدرس‌یابی فارسی فقط با تنظیم `GEOCODER_BASE_URL` روی سرویس مجاز Nominatim-compatible فعال می‌شود؛ در غیر این صورت انتخاب دستی نقاط روی نقشه در دسترس است. داده ارتفاع با `ELEVATION_BASE_URL` اختیاری است. ترافیک زنده **در این نسخه موجود نیست**.

## APIها

- `POST /api/v1/estimates/` — مسیر، هزینه تخمینی سوخت و بازه سناریو
- `GET /api/v1/geocode/?q=...` — جست‌وجوی فارسی تهران، در صورت اتصال ارائه‌دهنده
- `GET /api/v1/obstacles/?bbox=...` — موانع موجود
- `POST /api/v1/obstacle-reports/` — گزارش تأییدنشده با حساب کاربری
- `GET/PATCH /api/v1/admin/obstacle-reports/` — تأیید مدیر با تاریخچه ممیزی
- `GET /api/v1/auth/csrf/`, `POST /api/v1/auth/login/`, `GET /api/v1/auth/me/`
- `GET/POST /api/v1/trips/observations/` — داده واقعی سوخت با رضایت
- `DELETE /api/v1/me/study-data/` — حذف داده شخصی با تأیید
- `GET /api/v1/admin/observability/logs` — جست‌وجوی محدود لاگ
- `GET /api/v1/admin/observability/metrics/summary` — متریک‌های محدود
- `GET /api/v1/admin/observability/traces/{id}` — Trace مشخص
- `GET /api/schema/`, `GET /api/docs/` — مستند OpenAPI

## تحقیقات و محدودیت‌ها

- مدل فیزیکی و VT-Micro هنوز نیازمند داده واقعی خودرو و اعتبارسنجی بر اساس سفرهای مستقل هستند.
- موانع OSM بدون بازبینی و تطبیق محافظه‌کارانه، وارد مدل مصرف نمی‌شوند.
- چراغ راهنمایی به‌صورت دو سناریوی سبز/قرمز با احتمال فرضی محاسبه می‌شود.
- مقایسه فقط بین مسیرهای ارائه‌شده OSRM است، نه بهینه‌سازی سراسری تمام مسیرهای ممکن.
- برای چگونگی تهیه داده، حریم خصوصی، API و پایش، پوشه `docs/` را ببینید.
- کاشی‌های نقشه به‌صورت پیش‌فرض از OpenFreeMap با انتساب داده OpenStreetMap ارائه می‌شوند. شرایط ارائه‌دهنده و مجوز ODbL را رعایت کنید.

## توسعه و تست

```bash
uv sync --extra dev --extra science
uv run --extra dev --extra science pytest -q --ignore=tests/test_estimate_api.py --ignore=tests/test_moderation_api.py --ignore=tests/test_calibration_api.py --ignore=tests/test_auth_api.py --ignore=tests/test_privacy_api.py
cd frontend && npm install && npm run build
```

تست‌های دیتابیس به PostgreSQL + PostGIS نیاز دارند و در Job اختصاصی CI اجرا می‌شوند. وضعیت دقیق در `docs/STATUS.md` ثبت شده است.
