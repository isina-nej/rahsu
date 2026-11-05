# دستور کار هماهنگ برای تیم توسعه یا عامل‌های کدنویسی

**این سند یک دستور اجرایی پیشنهادی برای تیم/agent است، نه ادعای انجام کار.**

## مأموریت
یک monorepo جدید `pridefuel/` بساز که در یک برنامه هماهنگ و با یک release نهایی یک وب‌سایت تخمین مصرف بنزین پراید ۱۳۱ دنده دستی در تهران تحویل دهد. جزئیات فنی، طرح پایگاه داده، درستی علمی، امنیت، API و استقرار دقیقاً در MASTER_IMPLEMENTATION_PLAN.md و OBSERVABILITY_API_SPEC.md تعریف شده‌اند. از فایل‌های موجود pride_tehran_schema.sql و pride_tehran_database_design.md به‌عنوان مرجع طراحی استفاده کن، اما یک سیستم واحد Django migration بساز.

## قواعد اجباری
1. اول ساختار پروژه، DTOها، OpenAPI و migration + CI را بساز؛ بعد ماژول‌ها را اجرا کن. هیچ کد بین ماژولی خارج از ports/contracts نباشد.
2. API responses با JSON schema تست شوند و TS SDK از OpenAPI تولید شود.
3. route optimizer با OSRM فقط candidateها را رتبه‌بندی می‌کند؛ هیچ ادعای global optimum نداشته باشد.
4. اگر داده ترافیک، ارتفاع یا OSM missing است، warning/data quality و fallback آشکار ارائه کند.
5. هیچ coefficient علمی، درصد دقت یا دیتای OBD ساختگی تولید نکن. constants پراید منبع‌دار، nullable و versioned باشند.
6. ingestion/estimate workflows idempotent و قابل retry؛ database snapshots و model versions immutable.
7. از شروع Logging + tracing + metrics را پیاده کن؛ API مشاهده logs فقط با role+MFA, bounded read-only templates؛ private Loki.
8. استقرار Production فقط پس از CI green، smoke، backup و rollback؛ شکست مرحله تست نباید با نادیده‌گرفتن تست‌ها دور زده شود.
9. هیچ credential/secret/آدرس خصوصی در commit و log وارد نشود.
10. پس از هر milestone یک changelog خودکار + نتایج تست + known issues در docs/status/ بنویس؛ خروجی نهایی باید تمام وابستگی‌ها و محدودیت‌ها را مشخص کند.

## تحویل مورد انتظار
- کد اپ واقعی، نه تنها placeholder یا pseudocode؛ API و UI و migration و compose و monitoring configs کار کنند.
- seed پراید و تهران؛ نمونه داده کوچک تست (fixture)، script import بزرگ خارج از CI؛ sample routes تهران با صحت کنترل‌شده.
- تمام تست‌های unit/integration/E2E/observability/security اجراشده و گزارش در artifactهای CI.
- مستند نصب یک‌دستورِ (دستورات `make setup`, `make test`, `make up`, `make observability-smoke`, `make backup`, `make rollback`).
- README فارسی و انگلیسی، OpenAPI و docs پژوهشی.

## نقاط کنترل بدون توقف غیرضروری
- تنها در موارد تغییر غیرقابل برگشت دیتای کاربر، هزینه خارجی/پرداخت، نیاز به secret/credential واقعی یا انتشار Production که مجوزش وجود ندارد، اجرای عملیات را متوقف و approval بگیر.
- در سایر موارد از defaultهای برنامه استفاده کن، با تکیه بر تست‌ها، بدون درخواست‌های ریز برای هر انتخاب.
- پایان هر گام باید خروجی آزمایش و Git commit متمایز داشته باشد.
