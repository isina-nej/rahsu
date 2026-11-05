# راه‌سو | Rahsu

**برآورد پژوهشی مصرف بنزین پراید در تهران، بر مبنای مسیر، سرعت، توقف، شیب و موانع**.

> وضعیت: اسکلت اجرایی و اولین برش عمودی MVP. نتایج سوخت تا کالیبراسیون با داده رانندگی واقعی **تخمینی** هستند؛ سرویس مسیریابی بدون داده OSRM تهران پاسخ واقعی تولید نمی‌کند.

## معماری

- Backend: Python 3.12, Django 5.2, DRF, PostGIS; `backend/domain` مستقل از Django.
- Frontend: React, TypeScript, Vite, MapLibre GL JS.
- Routing: آداپتور OSRM مستقل؛ data ingestion جداگانه.
- Observability: JSON logs/trace context, Loki API read-only, Prometheus/Grafana/Tempo/Alloy configs.
- CI: Python tests/syntax lint, JS build, Docker Compose validation (environment-dependent).

## راه‌اندازی

```bash
cp .env.example .env
# replace DJANGO_SECRET_KEY and POSTGRES_PASSWORD
# docker compose --profile routing up --build -d    # after importing Tehran OSRM data
# docker compose up --build -d                       # API/UI/DB only; route estimation needs OSRM
# docker compose exec api python manage.py migrate
# docker compose exec api python manage.py seed_pride
```

> اجرای سرویس‌های full-telemetry و routing پروفایل اختیاری دارد؛ مستندات `docs/operations/` را ببینید. URL نقشه نمونه برای توسعه است و تولید به tile provider مجاز نیاز دارد.

## اجرای توسعه محلی

```bash
uv sync --extra dev
cd backend && uv run --project .. python manage.py check
cd ../frontend && npm ci && npm run build
```

## مسیرها

- `POST /api/v1/estimates/` — محاسبه پایه و فیزیکی روی مسیرهای برگشتی OSRM (در صورت در دسترس بودن).
- `GET /api/v1/vehicles/` — مشخصات پراید.
- `GET /api/v1/obstacles/` — موانع ثبت‌شده در دیتابیس.
- `POST /api/v1/obstacle-reports/` — گزارش اصلاح؛ نیازمند احراز هویت.
- `GET /api/v1/health/live` و `/api/v1/health/ready`.
- `GET /api/v1/admin/observability/logs` — API فقط‌خواندنی و محافظت‌شده Loki.
- `GET /api/schema/` و `/api/docs/` — OpenAPI.

## اصول توسعه

1. محور پژوهش: یک پراید ۱۳۱ دنده‌دستی در تهران؛ معماری قابل تعمیم به خودرو و شهر دیگر.
2. واحدها در Domain به SI؛ هر پارامتر بدون داده با برچسب unknown ثبت شود.
3. تغییرات ساختار DB فقط با Django Migrations، SQL قدیمی در `docs/architecture/reference-schema.sql` صرفاً مرجع است.
4. لاگ حاوی Token/Secret/مشخصات کامل مکان کاربر نباشد.
5. هر مدل با `version`, provenance و داده اعتبارسنجی ثبت شود. هیچ درصد خطای تضمینی فعلاً اعلام نمی‌شود.

## وضعیت تحویل

برای تشخیص فاصله بین **پیاده‌سازی واقعی** و **برنامه آتی**، فایل `docs/STATUS.md` را بخوانید.