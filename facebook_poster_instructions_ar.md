# دليل تشغيل سكربت النشر التلقائي على فيسبوك من الإنترنت

هذا السكربت (`online_fb_poster.py`) مصمم ليعمل بدون متصفح (بدون Playwright) ليتمكن من العمل على سيرفر في الإنترنت (مثل Heroku, PythonAnywhere, أو مساحات GitHub Actions مجاناً).

## خطوات التشغيل الأساسية:

### 1. الحصول على بيانات الربط مع فيسبوك (Facebook Graph API)
لكي ينشر السكربت مباشرة في صفحتك، تحتاج إلى:
1. الذهاب إلى منصة المطورين في فيسبوك [Facebook Developers](https://developers.facebook.com/).
2. إنشاء تطبيق جديد (App) واختيار نوعه (Business أو ما يشابهه).
3. إعداد منتج "Facebook Login for Business" أو استخدام أداة Graph API Explorer.
4. توليد **Page Access Token** (رمز وصول الصفحة) الذي يحتوي على الصلاحيات التالية:
   - `pages_manage_posts`
   - `pages_read_engagement`
5. نسخ **Page ID** (معرف الصفحة الخاصة بك).

*بمجرد الحصول عليهما، قم بلصقهما في ملف `online_fb_poster.py` في المتغيرين `FB_PAGE_ID` و `FB_PAGE_ACCESS_TOKEN`*.

---

### 2. طرق تشغيل السكربت على الإنترنت مجاناً

لديك عدة خيارات ممتازة ومجانية لرفع السكربت وجعله يعمل تلقائياً كل بضع ساعات:

#### الخيار الأول (الأسهل والأفضل): GitHub Actions
1. قم بإنشاء مستودع (Repository) خاص بك على GitHub وضع فيه الملف `online_fb_poster.py`.
2. أنشئ مجلد باسم `.github` وبداخله مجلد `workflows`، ثم أنشئ ملف `main.yml`.
3. يمكنك برمجة GitHub Actions لتشغيل السكربت تلقائياً كل ساعة أو كل يوم (عبر Cron Job).

#### الخيار الثاني: PythonAnywhere
1. قم بإنشاء حساب مجاني على موقع [PythonAnywhere](https://www.pythonanywhere.com/).
2. ارفع ملف `online_fb_poster.py` إلى السيرفر.
3. من لوحة التحكم، اذهب إلى تبويب **Tasks** وأضف مهمة مجدولة (Scheduled Task) تعطيها أمر تشغيل الملف يومياً: `python3 online_fb_poster.py`.

#### الخيار الثالث: خوادم مجانية أخرى
مثل Railway, Render، وغيرها من المنصات التي تدعم تشغيل أوامر بايثون.

### 3. ما الذي يحتاجه السكربت ليعمل؟
السيرفر يحتاج فقط إلى تثبيت المكتبات:
```bash
pip install requests beautifulsoup4 lxml
```

---
**ملاحظة هامة**: السكربت الحالي يقوم بقراءة أحدث الأخبار من رابط موقعك `http://elgeza.42web.io/feed/`. تأكد أن نظام RSS يعمل لديك. السكربت سيقوم بإنشاء ملف `posted_urls.txt` لحفظ الروابط التي تم نشرها سابقاً كي لا تتكرر الأخبار على صفحتك.
