# وضعیت اجرای راه‌سو

## پیاده‌سازی‌شده در برش اول
- Monorepo Python/Django + React/TypeScript، Docker Compose، workflow CI.
- هسته مستقل فیزیکی و baseline تخمین سوخت همراه آزمون‌های واحد.
- موتور ساده تولید پروفایل سرعت/شتاب با توقف‌های نمونه؛ ورودی‌های آن هنوز کالیبره نشده‌اند.
- APIهای اولیه سلامت، خودرو، تخمین، مانع و مشاهده لاگ با مجوز محدود.
- models و migrations اولیه حوزه‌های vehicle/geo/routing.
- UI نقشه و فرم انتخاب مبدأ/مقصد و نمایش مسیر و نتایج.
- فایل‌های اولیه مانیتورینگ و logging و مستند عملیات.

## تکمیل‌نشده و نیازمند داده/زیرساخت
- import واقعی نقشه و گراف OSRM تهران، geocoder فارسی مستقل، مسیرها و OSM segmentation دقیق.
- تطبیق صحیح توپولوژیک و جهت موانع، چراغ و صف واقعی، DEM، داده ترافیک.
- کالیبراسیون پراید با OBD/سوخت‌گیری و اثبات کاهش خطا نسبت به baseline.
- درک exact منبع/پوشش OSM و گزارش coverage با confidence.
- load test و smoke test محیط واقعی، نهایی‌سازی retention/backup/alert.
- endpointهای batch jobs، تحلیل ML و نسخه calibrated VT-Micro.
