# 📒 PROJECT_LOG — سجل أعمال مشروع "دورها" (Odoo 19)

> **الغرض من هذا الملف**: مصدر واحد للحقيقة. أي جلسة عمل جديدة (مطوّر أو AI Agent)
> تقرأ هذا الملف أولاً بدل إعادة فحص كل ملفات المشروع.
> **آخر تحديث**: 2026-07-20

---

## 1) نظرة سريعة على البيئة

| العنصر | القيمة |
|---|---|
| الموديول | `addons/recycle_warehouse` (Odoo 19) |
| الحاويات | `odoo19` (odoo:19.0) · `odoo19-db` (postgres:16, user/pass: odoo/odoo) · `odoo19-pgadmin` |
| قاعدة البيانات | `odoo19` |
| حساب التطوير | `admin` / `admin` (⚠️ للتطوير المحلي فقط — غيّر كلمة السر قبل أي Production) |
| المتطلبات المرجعية | `prompt-dawraha.md` (Persona + أقسام 0–20) |
| دليل فهم المشروع | `.FOLDER_INSTRUCTIONS.md` |

### أوامر التشغيل المعتمدة
```bash
# ترقية الموديول (الطريقة المجربة — انتبه لـ MSYS_NO_PATHCONV في Git Bash):
MSYS_NO_PATHCONV=1 docker exec odoo19 odoo --db_host=db --db_user=odoo --db_password=odoo \
    -d odoo19 -u recycle_warehouse --stop-after-init --no-http

docker restart odoo19          # تفعيل تعديلات Python
# أو ببساطة: upgrade_module.bat (يمسح كاش الأصول أيضاً)
```

---

## 2) ما تم تنفيذه — الجلسة 1 (أقسام 1–10 من البرومبت)

| القسم | التنفيذ | الملفات |
|---|---|---|
| §4 CSRF Logout | مسار جديد محصّن `/dawrha/logout` (GET, csrf=False, no-store) + استبدال كل روابط `/web/session/logout` (3 قوالب + 6 ملفات JS) | `controllers/website.py`, `views/website_templates.xml`, `static/src/js/recycle_*.js` |
| §4 Redirects | Login → `/` (الرئيسية) لكل الأدوار · Register ناجح → دخول تلقائي ثم `/` · تصحيح توجيه المسجلين من `/jobs` إلى `/` | `controllers/website.py` (`_login_redirect`, `verify_email`, `register`) |
| §2 Jobs | الأدمن يرى غير المنشورة بشارة "Unpublished" (قائمة + صفحة التفاصيل) | `controllers/website.py`, `views/website_templates.xml` |
| §3 Business Rules | قيود جديدة: اسم المستودع فريد · NID فريد و Email فريد على مستوى `res.users` (موديل-level) | `models/warehouse.py` |
| §5 الهوية | توكنز Dark = Navy `#0B1220` · Primary = `#1FB876` (4 مواضع :root) · خلفية `hero4.jpg` لكل صفحات Auth · نقوش شبكية + توهج على الـ Hero | `views/website_templates.xml`, `views/auth_templates.xml` |
| §5 بيانات حية | الرئيسية: 5 إحصائيات من DB (مستودعات، موظفون، طلبات، أطنان، نمو شهري) — صفر أرقام ثابتة | `home_page()` + قالب `home_stat_card` قابل لإعادة الاستخدام |
| §9 Dark/Light | أزرار عائمة (ثيم + لغة) لصفحات Login/Reset (`auth_dawrha_style`) و Register/Verify (قالب `dw_floating_controls`) — فوري + Persist عبر localStorage | `views/auth_templates.xml`, `views/website_templates.xml` |
| §6 i18n | مفاتيح جديدة (Orders, Tons Recycled, Monthly Growth) — المحرك `website_i18n.js` يترجم النصوص والـ placeholders تلقائياً | `static/src/js/website_i18n.js` |
| §7 البريد | ✅ كان موحداً أصلاً (OTP، Set Password، مقابلة، قبول/رفض بنفس الكارد الأخضر) — بلا تغيير | — |

**درس مهم**: تعبير `%` formatting داخل QWeb `t-value` يكسر الرندر (`ValueError: incomplete format`) — التنسيق يتم في الكونترولر (`growth_display`).

---

## 3) ما تم تنفيذه — الجلسة 2 (أقسام 11–20 الجديدة)

| القسم | التنفيذ | الملفات |
|---|---|---|
| §11+§17 صفحة الحساب | إعادة تصميم كاملة: Sidebar لاصق (Avatar + تنقل: Overview/Dashboard/My Applications/Edit/Password/Logout) + بانر ترحيب متدرج بنقوش شبكية + كروت إحصائيات (Applications/Role/Warehouse/Member Since) + كارد بيانات الحساب + "آخر النشاطات" بشارات حالة دلالية. المودالات القديمة (تعديل الملف/كلمة السر) محفوظة كما هي | `views/website_templates.xml` (template `account_page`), `controllers/website.py` (`_account_values`: أضيف `recent_activity`, `member_since`) |
| §12 Login | حذف قائمة الحسابات المحفوظة نهائياً: CSS `.o_user_switch{display:none}` + سكربت MutationObserver يزيل `d-none` من النموذج — النموذج يظهر مباشرة دائماً · **إزالة الكاروسيل** من Login/Signup/Reset/Register/Verify (خلفية hero4 ثابتة فقط — السلايدر حصراً بالرئيسية) · كاروسيل About استُبدل بصورة hero4 ثابتة | `views/auth_templates.xml`, `views/website_templates.xml` |
| §14 توقيع بصري | خط أخضر فاصل تلقائي تحت كل `.dw-section-title` (::after) + عناوين كروت الحساب · خط Cairo للعربي على الموقع كامل (`html[dir=rtl] body`) | `views/website_templates.xml` |
| §17 Jobs | شريط أدوات: بحث فوري (client-side) + تبويبات (All / Warehouse Management / Recycling Operations) + كروت أفقية (أيقونة + عنوان + وصف + Tags + زر تقديم) تتكدس عمودياً بالموبايل + رسالة "لا نتائج" | `views/website_templates.xml` (template `jobs_list_page`) |
| §18 Responsive | الجداول (My Applications + My Jobs) تتحول لبطاقات مكدسة تحت 640px عبر `.dw-td-lbl` (Labels قابلة للترجمة، بدون Scroll أفقي) | `views/website_templates.xml` |
| §19 Inspector deterrents | طبقة في `website_i18n.js` (يُحمَّل بكل الصفحات): منع زر يمين + حجب F12/Ctrl+Shift+I,J,C/Ctrl+U + `draggable=false` لكل الصور. **ملاحظة**: هذه Friction فقط — الحماية الحقيقية بالـ Backend | `static/src/js/website_i18n.js` |
| §20 دور الأدمن | قيمة جديدة `('admin','Administration')` بحقل `recycle_role` + Seed بـ `<function>` (لأن `base.user_admin` عليه `noupdate=1` فسجل `<record>` عادي **يُتجاهل بصمت**) يسند الدور + مجموعة `group_recycle_admin` تلقائياً مع كل تثبيت/ترقية. صفحة الحساب تعرض "Administration / الإدارة العامة" | `models/warehouse.py`, `data/data.xml`, `controllers/website.py` |
| §6/§11 تدقيق الترجمة | فحص فعلي للـ HTML المُقدَّم: Login (كل النصوص data-i18n ✅)، رسائل أخطاء السيرفر بالسجل ✅، أضيفت مفاتيح: Overview, Dashboard, Edit Profile, Set Password, Welcome back, Member Since, Account Details, Recent Activity, Administration, All, Search positions…, Wrong login/password | `static/src/js/website_i18n.js` |

### نتائج الفحص النهائي (مُتحقق منها فعلياً)
- ترقية الموديول: **0 أخطاء**.
- كل الصفحات العامة **200**، `/dawrha/logout` → **303 → /web/login**.
- Login POST → **303 → `/`** (الرئيسية) ✅.
- صفحة الحساب (بجلسة admin): التصميم الجديد يظهر والدور = **Administration** ✅.
- `SELECT recycle_role FROM res_users WHERE login='admin'` → `admin` ✅.

---

## 3.5) الجلسة 3 — إصلاحات من ملاحظات المستخدم على النتيجة الفعلية

| الملاحظة | الإصلاح | الملفات |
|---|---|---|
| Login لا يُترجم للعربية | **السبب الجذري**: محرك i18n كان يخرج مبكراً (`return`) على `/web/login` و `/web/reset_password` — أُزيل الاستثناء فصار `apply()` يعمل على كل الصفحات | `static/src/js/website_i18n.js` (INIT block) |
| Placeholder «Confirm Password» بالتسجيل | أُضيف مفتاح `Repeat your password` + مفاتيح Reset (`Confirm`, رسائل الإرسال...) | `website_i18n.js` |
| زر Reset Password ليس أخضر | قاعدة الزر الأخضر كانت تشمل login/signup فقط — أُضيف `.oe_reset_password_form .btn-primary` | `views/auth_templates.xml` |
| Active بالـ Navbar لا يعمل ببعض الصفحات | صفحات تفاصيل/تقديم الوظيفة كانت تمرر `nav_active='jobs'` بينما الـ Navbar يفحص `'openings'` — وُحدت على `'openings'` | `controllers/website.py` |
| الشبكة + خلفيات ملونة بكل الواجهات | طبقة خلفية موحدة على `body`: 4 توهجات Aurora (أخضر/تركوازي/أزرق عبر توكنز `--fx1..3` تختلف Dark/Light) + الشبكة + `background-attachment:fixed`، مع جعل `.dw-feat-section` شبه شفاف كي تظهر | `views/website_templates.xml` |
| كاروسيل احترافي | إعادة بناء: Crossfade + Ken Burns zoom + أسهم زجاجية تظهر بالـ hover + نقاط Pill متحركة + **شريط تقدم** مُحقن من JS يتزامن مع الـ Autoplay (4.5s) + Vignette سفلية + دعم RTL/Reduced-motion | `static/src/css/carousel_animations.css` (كامل), `static/src/js/carousel_controller.js` |
| الأفاتار: حرف أول إن لا صورة | حقل جديد `recycle_avatar_custom` يُفعَّل فقط عند رفع صورة فعلية من الموقع؛ بدونه يظهر الحرف الأول دائماً (يتجاهل صورة Odoo الافتراضية للأدمن) — تم التحقق: admin يعرض «A» | `models/warehouse.py`, `controllers/website.py` |

---

## 3.6) الجلسة 4 — الترجمة الفعلية لصفحات Auth (وليس قلب الاتجاه فقط)

**السبب الجذري المكتشف**: المانيفست كان يسجل `website_i18n.js` تحت باندل **`website.assets_frontend`** — اسم قديم لا وجود له في Odoo 19 (الصحيح `web.assets_frontend`) فيُتجاهل بصمت. النتيجة: محرك الترجمة لم يكن يُحمَّل إطلاقاً على `/web/login` و `/web/reset_password` (صفحات الموقع كانت تعمل لأنها تضمّنه بوسم `<script>` مباشر). قلبُ RTL كان يحدث من سكربت inline منفصل — ما أوحى خطأً أن "الترجمة تعمل".

| الإصلاح | الملفات |
|---|---|
| تصحيح اسم الباندل إلى `web.assets_frontend` + تضمين مباشر للمحرك في `auth_dawrha_style` (يغطي Login/Signup/Reset مهما كان سلوك الباندل) + حارس `__dwI18nLoaded` ضد التحميل المزدوج | `__manifest__.py`, `views/auth_templates.xml`, `static/src/js/website_i18n.js` |
| ترجمة عناوين التبويب (segment-wise: "Login \| Dawrha") + تلميحات `title` عامة | `website_i18n.js` (داخل `apply()`) |
| Responsive صارم للصفحات الثلاث تحت 480px (padding/خط/حقول أصغر — لا قص ولا إخفاء) | `auth_templates.xml`, قالبا register/verify في `website_templates.xml` |
| Active بالأخضر داخل قائمة الجوال (رابط Jobs بالـ Drawer كان بلا شرط active) | `views/website_templates.xml` |

**التحقق الإلزامي (سكربت تدقيق كلمة-بكلمة)**: فحص آلي بـ lxml لكل نص/placeholder/tooltip ظاهر بالصفحات الثلاث مقابل قاموس الترجمة (298 مفتاحاً) → نموذج الدخول/التسجيل/الاستعادة **مغطى 100%**؛ المتبقي الوحيد عناصر هيدر/فوتر Odoo الافتراضية **المخفية بالـ CSS** (غير مرئية) وزر "AR" نفسه (مقصود). ملاحظة: أي تعديل قوالب يتطلب **ترقية الموديول** لتحديثها بقاعدة البيانات — التعديل على XML وحده لا يكفي.

---

## 3.7) الجلسة 5 — الداشبورد + ميزات الأدمن + طبقة الـ API

| البند | التنفيذ | الملفات |
|---|---|---|
| إزالة شريط أودو الأفقي | CSS يخفي كل عناصر `.o_main_navbar` (Dropdowns، Discuss systray، المستخدم...) ويبقي **زر المربعات التسعة فقط** كزر زجاجي عائم (ظاهر دائماً حتى بالجوال)، والواجهة تأخذ كامل الشاشة | `static/src/css/tailwind_theme.css` (نهاية الملف) |
| شات بوت الدعم | الضغط على اسم النظام بالشريط الجانبي (`.o_ra_sb_brand_txt`) يفتح لوحة محادثة داكنة بهوية دورها: ترحيب، Chips مواضيع سريعة (شحنات/طلبات/صيانة/ورديات/تواصل)، ردود قاعدية بالعربي والإنجليزي حسب لغة النظام، Responsive | `static/src/js/recycle_chatbot.js` (جديد، مسجل في web.assets_backend) |
| فلتر الفترة (يومي/أسبوعي/شهري) | **تحقق: حقيقي وليس وهمياً** — `dashboard_api.py` يبني نطاقات تواريخ فعلية (اليوم/الأسبوع/الشهر + الفترة السابقة للمقارنة) والداشبورد يمرر `period` مع كل تحميل | (بلا تغيير — تحقق فقط) |
| Active فوري بالـ Navbar (الموقع) | عند الضغط يتلون الخيار أخضر فوراً قبل انتقال الصفحة ويعمل بنفس المنطق داخل قائمة الجوال | `views/website_templates.xml` |
| إضافة مستخدم أدمن | Configuration ← **Add Administrator**: ويزارد ينشئ مستخدماً داخلياً بدور `Administration` حصراً + مجموعة الأدمن + إيميل تعيين كلمة السر بالقالب الموحد | `models/wizard.py`, `views/warehouse_views.xml`, `security/ir.model.access.csv` |
| الورديات | الوردية تُسند **لمستودع أو تبقى غير مسندة** (حقل مستودع بالنموذج/القائمة + فلتر Unassigned) — لا إسناد لموظف من هنا؛ الإسناد يتم من نموذج الموظف (shift_id/warehouse/role موجودة أصلاً على res.users) | `views/shift_views.xml` |
| إشعارات الأدمن | إشعار عند **تخزين الشحنة** بمنطقة التخزين (action_finish_sorting) وعند **إتمام الطلبية** (action_complete) + نوعا إشعار جديدان | `models/shipment.py`, `models/order.py`, `models/notification.py` |
| الأسعار | حذف "السعر الأساسي" من واجهات المنتج (بقي سعر المعمل وسعر الجهات الحرة) + إعادة تسمية الترجمة "سعر المنشآت المجانية" ← **"سعر الجهات الحرة"** | `views/product_views.xml`, `static/src/js/recycle_i18n_shared.js` |
| المخزون بالزون والحالة | `recycle.stock` أصبح مفصلاً لكل (مستودع × زون تخزين × منتج × حالة ممتاز/جيد): الفرز يضيف بحسب حالة السطر وزون التخزين، والخصم يستهلك الممتاز أولاً عبر كل الأسطر. واجهة المخزون: أعمدة الزون والحالة + فلاتر (متوفر/ممتاز/جيد) + تجميع حسب مستودع/زون/حالة + بحث بالمنتج | `models/stock.py`, `models/shipment.py`, `views/stock_views.xml` |
| فلاتر الشحنات/الطلبات/الزونات | شحنات: بحث بالاسم/معرف الباك إند + فلترة باسم الزون ونوعه وبالحالة وتجميع بالزون. طلبات: حقل `output_zone_id` (يُملأ تلقائياً عند الإتمام) + فلاتر حالة كاملة وزون. زونات (Configuration): بحث بالاسم + فلترة بالمستودع ونوع الزون | `views/shipment_views.xml`, `views/order_views.xml`, `views/warehouse_views.xml`, `models/order.py` |
| معرف الشحنة الخارجي | حقل `backend_shipment_id` على الشحنة (فهرس + بالنموذج والبحث) لربطها بشحنة الـ NestJS | `models/shipment.py`, `views/shipment_views.xml` |
| **ملف الـ API المركزي** | `models/backend_sync.py`: كل استدعاءات Odoo→Backend في ملف واحد مع خريطة Endpoints موثقة بأعلى الملف — عند جهوز الـ NestJS يكفي ضبط بارامترين: `recycle.backend_base_url` و `recycle.backend_api_key`. مربوط فعلياً: تخزين شحنة، إتمام طلبية، إنشاء منتج/تصنيف، **تحديث الأسعار** (fire-and-forget لا يعطل العمل). الاستقبال الداخلي موجود في `controllers/api.py` | `models/backend_sync.py` (جديد), hooks في shipment/order/product |

## 3.8) الجلسة 6 — إصلاحات حرجة بالداشبوردات + منطق الورديات والأرشيف

| البند | الإصلاح | الملفات |
|---|---|---|
| **بروفايل الأدمن "لا يعمل إطلاقاً"** | **السبب الجذري**: الكود يستدعي `this._rpc()` والدالة **غير معرفة** في `recycle_admin_dashboard.js` — التحميل يفشل بصمت والحفظ يرمي استثناء. أضيفت الدالة (fetch JSON-RPC بنفس نمط داشبورد المدير). نقاط `/api/recycle/my-profile` و `/api/recycle/save-profile` كانت سليمة أصلاً | `static/src/js/recycle_admin_dashboard.js` |
| **داشبورد موظف الإخراج "سيئ"** | نفس العلة وأشد: **14 استدعاء `_rpc` بلا تعريف** — كل تحميلات البيانات (داشبورد/طلبات/تفاصيل) كانت ميتة، فبدت الواجهة فارغة/افتراضية. أضيفت الدالة → الواجهة عادت تعمل بتصميمها الكامل | `static/src/js/recycle_output_dashboard.js` |
| **§11 الوظائف تظهر للمدير** | إصلاح منطقي (وليس CSS): `_base_values` كان يخفي الوظائف فقط لمن له سجل `hr.employee` (القادمين عبر التوظيف). الآن أي حساب له **دور تشغيلي** (manager/input/sorting/output/maintenance) تُخفى عنه الوظائف من كل الموقع؛ الأدمن مستثنى | `controllers/website.py` |
| **§6ب ورديات المدير** | نقطة جديدة `/api/manager/warehouse-shifts` (ورديات مستودعه فقط) + توسيع `/api/manager/employee/update` ليقبل `shift_id` (يُتحقق أنها من مستودعه، و0 = إلغاء الإسناد) و`warehouse_id` (مع إسقاط الوردية غير المتوافقة عند نقل الموظف) — إضافةً للدور والاسم والهاتف. **إنشاء الوردية (أدمن) يتجاهل الآن أي إسناد موظفين** — الإسناد حصراً من شاشة تعديل الموظف | `controllers/dashboard_api.py` |
| **§8 الأرشيف** | Actions + قوائم "Shipments Archive" و"Orders Archive" (أدمن + مدير) على `recycle_archived=True` بنفس Search views (كل الفلاتر والبحث) + فلتر "Archived" سريع في بحث الشحنات والطلبات | `views/shipment_views.xml`, `views/order_views.xml`, `views/menus.xml` |

⚠️ **درس**: لا تستخدم perl regex لحقن XML متعدد الأسطر في Attributes تحتوي `|` — كسر `shipment_views.xml` (أُصلح يدوياً وتحقق بـ lxml قبل الترقية).

## 3.9) الجلسة 7 — توحيد تصميم واجهات الموظفين (استقبال/فرز/إخراج/صيانة)

**الاكتشاف الجذري**: متغيرات الثيم الاحترافي `--ra-*` (ألوان/زجاجية/ظلال ثيم الأدمن) كانت معرفة **فقط** تحت `.o_recycle_admin_theme`، بينما جذور واجهات الموظفين هي `.tw-dashboard` — فكل مكوناتها `o_ra_*` كانت تسقط على قيم fallback فاتحة بدائية، **وزر الدارك مود لا يغيّر فيها شيئاً**. هذا هو سبب "الواجهات السيئة/الافتراضية".

**الحل**: ملف جسر `static/src/css/recycle_employee_theme.css` (مُسجل بعد recycle_home.css) يعرّف نفس لوحتي الألوان (Light/Dark navy+emerald) على `.tw-dashboard` و `.tw-dashboard.dark` + خط Cairo للـ RTL + صقل المكونات المشتركة (Hero متدرج، حقول بحواف وFocus أخضر، أزرار بحركة، Bottom-nav زجاجي) — **دون لمس ملف القوالب 533KB**، فتوحّدت هوية الأدوار الأربعة مع الأدمن/المدير بالوضعين.

**إصلاح مرافق**: زر المربعات التسعة نُقل للطرف المقابل (inset-inline-end) كي لا يتصادم مع زر القائمة الجانبية (☰) للجوال الموجود بطرف البداية بكل الداشبوردات.

**تحقق**: ترقية 0 أخطاء، الملف يُخدَّم، كل الداشبوردات لديها كود بروفايل + إعدادات (الصيانة بلا شاشة إعدادات — فجوة معروفة).

### مؤجل لجلسة قادمة (يتطلب عملاً على ملفات ضخمة: recycle_home_action.xml ٥٣٣KB + JS الداشبوردات ~٣٥٠KB)
- المراجعة البصرية الشاملة لداشبوردات الأدوار (توحيد الخطوط/الأحجام/التداخلات عنصراً-عنصراً).
- توحيد شاشة الإعدادات + عرض/تعديل البروفايل داخل الداشبورد لكل الأدوار.
- Responsive عميق لكل شاشة داشبورد على الجوال.

---

## 4) تدقيق ملفات جذر المشروع (المطلوب: أيها يبقى وأيها يُحذف)

### ✅ ضرورية — لا تحذفها
| الملف | السبب |
|---|---|
| `addons/` | كود المشروع نفسه |
| `docker-compose.yml` | تعريف البيئة كاملة (odoo + postgres + pgadmin) |
| `CLAUDE.md` | تعليمات المشروع لأدوات الـ AI |
| `prompt-dawraha.md` | المتطلبات المرجعية الحالية (0–20) |
| `.FOLDER_INSTRUCTIONS.md` | دليل فهم الأدوار/العزل/الهيكلية — يُستخدم كمرجع دائم |
| `upgrade_module.bat` | أداة الترقية العملية (تمسح كاش الأصول + ترقية + تشغيل) |
| `DIAGNOSE.bat` | تشخيص آمن للحاويات/القواعد/السجلات (read-only) |
| `PROJECT_LOG.md` | هذا الملف — سجل الأعمال المرجعي |

### 🗑️ حُذفت فعلياً بتاريخ 2026-07-14 (بموافقة صريحة بعد عرض القائمة)
| الملف | السبب |
|---|---|
| `.AGENT_PROMPTS.md` | برومبتات جاهزة قديمة — حل محلها `prompt-dawraha.md` |
| `COMPLETE_PROMPTS_AR.md` | أرشيف برومبتات قديم — نفس الغرض أعلاه |
| `DEVELOPMENT_PLAN.md` | خطة مراحل قديمة تجاوزها الواقع — هذا الملف هو المرجع الحالي |
| `QUICK_START.md` | مكرر مع `.FOLDER_INSTRUCTIONS.md`/README |
| `SYSTEM_SUMMARY.txt` | ملخص تنفيذي قديم مكرر |
| `README_AR.md` | وثيقة تعريفية قديمة |
| `requirements.txt` | غير مستخدم — الـ compose يستخدم صورة `odoo:19.0` الجاهزة |
| `addons/recycle_warehouse/static/src/err.tmp` و `static/src/js/e.tmp` | ملفات مؤقتة خاطئة داخل الموديول |

**تحقق قبل الحذف**: بحث شامل عبر كل ملفات `.py/.js/.xml/.yml/.bat` وDockerfile* لم يجد أي إشارة لأي من هذه الملفات الثمانية — لا كود ولا سكربت ولا docker-compose يعتمد عليها.

---

## 5) ملاحظات معمارية مهمة (اقرأها قبل أي تعديل جديد)

1. **الترجمة**: محرك واحد `static/src/js/website_i18n.js` (مفاتيح EN→AR). أي نص جديد بالموقع = أضف `data-i18n="key"` + سطر `_('key','ترجمة')`. الـ placeholders تُترجم تلقائياً إذا كان نصها مفتاحاً بالقاموس.
2. **الثيم**: كل الألوان عبر CSS Variables في `:root` / `html[data-theme=dark]` داخل `dawrha_layout` (والقوالب المستقلة: register/verify/auth_dawrha_style). لا تكتب ألواناً صلبة بالكومبوننتات.
3. **`base.user_admin` عليه noupdate=1** — أي Seed عليه يجب أن يكون `<function>` وليس `<record>`.
4. **QWeb**: لا تستخدم `%` formatting داخل `t-value` — جهّز النص بالكونترولر.
5. **Git Bash + docker exec**: استخدم `MSYS_NO_PATHCONV=1` لأي مسار يبدأ بـ `/`.
6. **صفحات Auth المستقلة** (`register_page`, `verify_email_page`) لها `<html>` كامل خاص بها — أي تعديل هوية يجب تكراره فيها (توكنز + خطوط + أزرار عائمة `dw_floating_controls`).
7. **تكامل NestJS المستقبلي** (§0): لا تكسر REST APIs في `controllers/api.py` و `dashboard_api.py` — هي نقطة المزامنة المخططة.
8. **تعديلات Python (كونترولرز/موديلز) تتطلب `docker restart odoo19` — ترقية الموديول وحدها لا تكفي**. عملية أودو الحية (PID الرئيسي بالحاوية) تحمّل كود Python بالذاكرة عند الإقلاع فقط؛ `docker exec odoo19 odoo -u ... --stop-after-init` يشغّل عملية **منفصلة** تُحدّث قاعدة البيانات (سكيما/بيانات) لكنها لا تمسّ العملية الحية إطلاقاً. تعديلات JS/XML/CSS تُخدَّم مباشرة من القرص (لا حاجة لإعادة تشغيل)، لكن الـ bundle المُجمَّع (`web.assets_*`) يحتاج ترقية موديول لإعادة توليده.
9. **Odoo 19 غيّر اسم حقل مجموعات المستخدم**: `res.users.group_ids` (وليس `groups_id` القديم) — أي كود/شل يحاول `user.groups_id = [(4, gid)]` يفشل بـ `AttributeError`.
10. **`_sql_constraints` (list قديمة) يُتجاهل بصمت في Odoo 19** — يظهر تحذير بالسجل فقط، لا خطأ، ولا يُنشئ القيد الفعلي بقاعدة البيانات. استخدم `models.Constraint('unique(...)', 'رسالة')` دائماً.
11. **محرك قوالب Owl لا يسمح باستدعاء دوال JS عامة اعتباطياً داخل التعبيرات** (`t-esc`, `t-att-*`, إلخ) — القائمة البيضاء محدودة جداً (`Math, RegExp, Array, Object, Date` فقط، من `RESERVED_WORDS` بمصدر `owl.js`). أي استدعاء آخر (`String()`, `Number()`, `parseInt()`, `JSON.parse()`...) يتحول لـ `ctx.<name>(...)` وينهار بـ `TypeError`. البديل الآمن لتحويل نص: عامل الجمع `'' + x` بدل `String(x)`.
12. **درع تخزين المتصفح** (`static/src/js/recycle_storage_guard.js`) يجب أن يبقى **أول** ملف مسجَّل بكل من `web.assets_backend` و`web.assets_frontend` بالمانيفست — لا تُزل هذا الترتيب.
13. **تصميم "ورديتي" الموحَّد**: أي شاشة جديدة يجب أن تبدأ برأس `o_ra_page_hero`/`o_ra_page_hero_icon`/`o_ra_page_hero_body` وتُحاط بـ `o_recycle_view_container` — **لا تستخدم** كلاسات `tw-hero*`/`tw-content` القديمة (بقايا ما قبل توحيد التصميم، انظر 3.7 و3.13).
14. **قوائم Odoo الطويلة تحتاج نمطين للعرض معاً دائماً**: جدول سطح مكتب (`o_recycle_tbl_wrap` > `table.o_recycle_data_table`) **و** بطاقات جوال (`o_ra_mobile_card_view`) — الأخير `display:none` افتراضياً ولا يظهر إلا ≤767px عبر media query. شاشة ببطاقات فقط بلا جدول = **غير مرئية إطلاقاً على أي شاشة أكبر من الجوال** (خلل حقيقي وقع فعلياً، انظر 3.13).

---

## 3.8) الجلسة 7 — تحقق بصري فعلي بالمتصفح + ميزات موظف الاستقبال والمدير

**منهجية جديدة**: كل بند تحقق منه بفتح الواجهة فعلياً بالمتصفح (Preview) ولقطات شاشة — لا اعتماد على "الكود موجود".

| البند | الحالة (مثبت بصرياً) |
|---|---|
| خلل البروفايل بين التبويبات | **حارس جلسة** بكل الداشبوردات الست: عند فتح داشبورد بجلسة مستخدم آخر (تسجيل دخول من تبويب ثانٍ) يعاد التوجيه لـ `/recycle/open-dashboard` — لا تظهر بيانات مستخدم داخل واجهة دور آخر أبداً. السبب لم يكن الكوكيز بل طبيعة جلسة Odoo الواحدة لكل متصفح |
| أرشفة الموظف | عند الأرشفة يُلغى الرول والمستودع والوردية وتُحفظ في `recycle_prev_role/prev_warehouse` للمراجعة؛ الاستعادة تعيد الحساب **بدون** رول/مستودع وتبقي قيم المراجعة |
| فلاتر شحنات موظف الاستقبال | ✅ بالشاشة: الكل / قيد الاستلام / تمت معالجتها / محوّل + بحث — وأزيل زر "Holding" المكرر. القائمة تعرض شحناته هو فقط (receiver_user_id=me) |
| منطقة الاستقبال | حقل `receiving_zone_id` على الشحنة + **إلزامي** في `action_accept` و`action_resolve_escalated` + قائمة اختيار بواجهة موظف الاستقبال (مناطق استقبال مستودعه فقط، اختيار تلقائي إن كانت واحدة) وواجهة المدير للشحنات المحولة — مثبت بصرياً |
| الأرشيف | قائمة "Archive" واحدة ضمن Operations (أدمن + مدير) تضم الشحنات المؤرشفة والطلبات المؤرشفة بنفس فلاتر البحث |
| زر Apps (المربعات) | **3 أسباب متراكبة** كانت تخفيه: (1) لا وجود لـ `.o_navbar_apps_menu` في Odoo 19 — الصحيح `a.o_menu_toggle`، (2) `recycle_home.css` يخفيه بقاعدة `body.o_ra_no_main_navbar ... !important` — لزم تجاوز بأعلى تخصيص `html body...`, (3) **سيرفر Odoo يكاشي الأصول بالذاكرة — أي تعديل CSS/JS للأصول يتطلب إعادة تشغيل السيرفر + حذف `/web/assets/%`**. الزر الآن عائم زجاجي بأسفل البداية، دائم الظهور حتى بالموبايل |
| ثيم داشبوردات الموظفين | جسر متغيرات `--ra-*` على `.tw-dashboard/.dark` أصلح المظهر الافتراضي والدارك مود المعطل — مثبت بلقطات (Hero متدرج، كروت KPI، فلاتر فترة Pills) |
| ترجمات ناقصة اكتُشفت بالعين | Scan QR / Start Camera / Or upload / My Warehouse Dashboard / Avg Time / وصف الشحنات — أضيفت كلها |

**ملاحظات تشغيلية مهمة**:
- التحقق البصري: `.claude/launch.json` يشغل `docker start -a odoo19` عبر أداة Preview (يتطلب إيقاف الحاوية أولاً).
- كلمة سر مؤقتة وُضعت لحساب `abodealwan32@gmail.com` = `Test12345!` (للاختبار — غيّرها).
- شحنة تجريبية `SHP00012` أنشئت بمستودع دمشق.

---

## 3.10) الجلسة 8 — المخزون بحسب الحالة + الخصم بالحالة + طبقة ربط NestJS

| البند | التنفيذ | الملفات |
|---|---|---|
| **حالة رابعة "تالفة"** | `STOCK_CONDITIONS` في `models/stock.py` أصبح **المصدر الوحيد** للحالات الأربع (excellent/good/poor/damaged) — يستورده `order.py` و`shipment.py` (سطر الفرز) و`controllers/api.py`. أي تعديل مستقبلي = سطر واحد | `models/stock.py`, `order.py`, `shipment.py` |
| **الخصم بحسب الحالة** | `_deduct_quantity(condition=...)` يخصم **حصراً** من أسطر نفس الحالة (نقص الحالة = خطأ واضح حتى لو توفرت حالات أخرى) + `_available_qty(condition=...)`. سطر الطلبية حمل حقل `condition` (إلزامي، افتراضي good) و`action_complete` يمرر حالة كل سطر. بدون condition يبقى السلوك القديم (أفضل حالة أولاً — تقرير التلف) | `models/stock.py`, `models/order.py` |
| **مخزون الأدمن** | فلتر المستودع أصبح **قائمة منسدلة**؛ "جميع المستودعات" = لا فلتر زون (القائمة مخفية)، اختيار مستودع يُظهر زونات **ذلك المستودع فقط** + عمود وفلتر Pills للحالة + الحالة بكروت الجوال — مثبت بصرياً بالجوال | `recycle_admin_dashboard.js` (`stockZonesForWH`, `setStockCondFilter`), القالب |
| **مخزون المدير + موظف الفرز** | عمود الحالة + فلتر الحالة للمدير؛ خيار جديد "المخزون" بسايدبار موظف الفرز (مقيد بمستودعه عبر Record Rules الموجودة أصلاً) بجدول ديسكتوب + كروت جوال — مثبت بصرياً | `recycle_manager_dashboard.js`, `recycle_sorting_dashboard.js`, القالب |
| **موظف الإخراج** | تفاصيل الطلب/المعالجة/الفاتورة تعرض حالة كل مادة + المتوفر **بنفس الحالة** (شارة خضراء/حمراء) + تحذير عربي + زر الإتمام معطّل عند النقص + الكونترولر يتحقق ويترجم UserError لرسالة ودية | `dashboard_api.py` (order_detail/complete/storage-zones), القالب, `recycle_output_dashboard.js` |
| **طبقة NestJS** | `BACKEND_ROUTES` dict وحيد بأعلى `backend_sync.py` (+ override لكل مسار عبر `recycle.backend_route_<key>` بدون كود) + راوت وارد جديد `POST /api/recycle/shipments` (X-API-KEY) ينشئ شحنة ويعيد `shipment_id` أودو للباركود + `condition` بأسطر إنشاء/قراءة الطلبات + **`BACKEND_INTEGRATION.md`** بجذر المشروع: العقد الكامل بالاتجاهين وخطوات الربط | `models/backend_sync.py`, `controllers/api.py`, `BACKEND_INTEGRATION.md` |
| فيوهات أودو الخلفية | فلترا Poor/Damaged ببحث المخزون + عمود condition بكل قوائم أسطر الطلبات (4 فيوهات) | `views/stock_views.xml`, `views/order_views.xml` |

**تحقق فعلي**: ترقية 0 أخطاء · 5 اختبارات Shell (إضافة تالف، خصم ممتاز لا يمس الجيد، رفض تجاوز الحالة، إتمام طلبية يخصم -3 ممتاز فقط، حظر طلبية بحالة غير متوفرة) كلها ناجحة · تحقق بصري بالجوال 390px: مخزون الأدمن (قائمة المستودعات + إظهار زونات المستودع المختار فقط + فلتر الحالة 6→3 كروت) ومخزون الفرز (فلتر رديئة → كرت واحد) ومعالجة الطلب عند الإخراج (شارات الحالة + المتوفر بالحالة + رسالة الحظر) · API الإتمام يرفض: "Insufficient Damaged stock..." — طلب تجريبي `ORD00011` (سطر ممتاز متوفر + سطر تالف ناقص) تُرك بحالة pending للتجربة اليدوية.

---

## 3.11) الجلسة 9 — PWA + توحيد الإيميلات + سير عمل الطلبات بالأولوية والتخزين المتعدد المناطق

**5 مطالب رئيسية نُفذت بالكامل ومُثبتة بصرياً عبر Preview + Odoo Shell:**

| البند | التنفيذ | الملفات |
|---|---|---|
| **PWA لوغو التطبيق** | `controllers/webmanifest.py` (جديد) يرث `WebManifest` ويُرجّع `name/short_name="Dawrha"` + أيقونات 192/512 مولّدة من `icon_logo.png` عبر PIL | `controllers/webmanifest.py`, `static/src/img/pwa_icon_*.png` |
| **توحيد تصميم كل الإيميلات** | تصميم OTP (هيدر أخضر متدرج `#047857→#10b981` + "Dawrha" + صندوق منقط) أصبح المرجع الوحيد. `res.users._notify_security_setting_update` تم Override لإرسال نفس التصميم عند أي تغيير باسورد/إيميل من أودو نفسه. قالب أودو الأصلي `auth_signup.reset_password_email` (يُستخدم فعلياً لكل من Set Password و Forgot Password) استُبدل بالكامل عبر `email_layouts.xml` (xpath replace). تدرّج أحمر برسائل الرفض ورديّت لأخضر موحّد | `models/warehouse.py` (ResUsers)، `views/email_layouts.xml` (جديد)، `models/notification.py`، `data/email_templates.xml` |
| **مستودعي (موظف الإخراج)** | أُزيلت كل إحصائيات الشحنات/الطلبات، تبقى فقط: الاسم + الرمز + المحافظة + المدير | `static/src/xml/recycle_home_action.xml` (my_warehouse view) |
| **صفحة My Account بالموقع** | `maximum-scale=1, user-scalable=no` بالـ viewport meta (`dawrha_layout`) + إصلاح تجاوز أفقي حقيقي بالجوال (375px): `.dw-acc-layout > * { min-width:0 }` + `max-width:100%` على فقرة الترحيب داخل `@media max-width:600px` — كان `scrollWidth=594` قبل الإصلاح و`=375` بعده | `views/website_templates.xml` (account_page) |
| **سير عمل الطلبات (الأكبر)**: أولوية + إخراج معمل ID + خصم متعدد المناطق + توقيت الخصم | تفصيل أدناه ⬇ |  |

### سير عمل الطلبات الجديد (تفصيل)
- **الأولوية**: `recycle.order.get_blocking_order()` يرجّع أعلى طلبية أولوية (priority أصغر) بنفس المستودع بحالة pending — **يتخطى** أي طلبية أعلى أولوية إن كان مخزونها غير كافٍ حالياً (`_line_stock_sufficient`). `action_start_processing` (والـ API `reserve_order`) يرفضان البدء برسالة "يجب معالجة الطلبية X أولاً" حتى يجيء دورها.
- **الباك إند**: `POST /api/recycle/orders` يقبل `factory_id` (نص حر، يُحفظ بـ `backend_factory_id`، لا يُستخدم كمفتاح داخلي) و`priority` (افتراضي 10) — السعر **دائماً** من `price_factory`/`price_free_facility` حسب `order_type`، لا يُرسل من الباك إند أبداً. الاستجابة والقراءة (`GET /orders/<id>`) تُرجعان `priority`+`factory_id`+`output_zone`+`stock_deducted_at`+`finished_at`.
- **خصم متعدد المناطق**: نموذج جديد `recycle.order.zone.movement` (زون × مادة × حالة × كمية × من قام بالخصم × `moved_at`). `action_complete(allocations=[{line_id,zone_id,quantity},...])` يتحقق أن مجموع تخصيصات كل سطر ≥ الكمية المطلوبة، يخصم عبر `Stock._deduct_from_zone` (يرمي خطأ صريح إن نقصت منطقة بعينها)، ثم `processing → ready` (وليس completed مباشرة).
- **إنهاء الطلبية**: `action_finish(output_zone_id)` منفصل تماماً — يتحقق أن المنطقة `zone_type=output` بنفس المستودع، `ready → completed`، يسجّل `finished_at`.
- **واجهة الإخراج (JS+XML جديدة بالكامل)**: `process_order`/`process_detail` تُظهر بانر حظر الأولوية وتُعطّل الزر؛ `complete_order` أصبحت شاشة **اختيار مناطق تخزين متعددة** (بطاقة لكل مادة تعرض فقط المناطق التي تحوي هذه المادة/الحالة تحديداً، إدخال كمية لكل منطقة، شارة تقدم X/Y حمراء→خضراء)؛ شاشة جديدة `finish_order` لاختيار منطقة الإخراج. كلاسات CSS جديدة `.o_ra_alloc_*` و`.o_ra_zone_pick_*` بـ`recycle_home.css` (grid متجاوب: عمودين بالجوال، عمود واحد ≤480px).
- **الكونترولرات**: `dashboard_api.py` — `orders_list`/`order_detail` يُرجعان `blocking_order_name`؛ `reserve_order` يفوّض بالكامل لـ `action_start_processing` (بدل منطق مكرر)؛ `complete_order` يستقبل `allocations` ويمرّرها؛ `storage_zones` تُفلتر لتُظهر فقط مناطق تحوي منتج/حالة **موجودين فعلاً بأسطر الطلبية**؛ راوتان جديدان `output-zones` و`order/finish`.

**تحقق فعلي (Odoo Shell)**: سيناريو كامل — طلبية أولوية 1 (كمية 7، موزعة على منطقتين 5+3) وطلبية أولوية 5 (كمية 2) بنفس المستودع: حظر الطلبية الثانية ✅، بدء الأولى ✅، إكمال بتخصيص منطقتين ✅ (تحقق من `zone_movement_ids` ووقت `stock_deducted_at`)، تحرر الحظر عن الثانية بعد اكتمال الأولى ✅، إنهاء بمنطقة إخراج ✅، رفض تخصيص ناقص برسالة واضحة ✅.

**تحقق فعلي (متصفح، موظف إخراج فعلي `abodealwan32@gmail.com`)**: تدفق كامل من قائمة الطلبات (حظر الأولوية ظاهر ورسالة عربية) → حجز → شاشة اختيار مناطق تخزين (بطاقتان 4+6، تعبئة 4+3 → شارة 7/7 خضراء) → إكمال (فاتورة + توقيت الخصم ظاهر) → اختيار منطقة إخراج → "تم إنهاء الطلبية بنجاح!" — كل خطوة بلقطة شاشة. اختبار جوال 375px لشاشة اختيار المناطق (4 مناطق، منطقة فارغة من هذه المادة لا تظهر) — تصميم بطاقات عمودي نظيف.

**فخ مهم اكتُشف ومُصلح**: `data/email_templates.xml` كان يستخدم CDATA + Jinja `{{ }}` داخل حقل `type="html"` — هذا **يفشل** RelaxNG schema الخاص بأودو (يتطلب عناصر XML حرفية فعلية داخل حقل html/xml، وليس نص CDATA) وكان يمنع أي ترقية للموديول بالكامل (`ERROR: Element odoo has extra content: data`). الإصلاح: تحويله لـ QWeb حرفي (`t-out`/`t-att-href`) بنفس نمط `email_layouts.xml` — تحقق عبر `lxml.etree.RelaxNG` مباشرة قبل إعادة المحاولة.

**إصلاحات ريسبونسف سابقة بنفس اليوم (الجلسة 7.5)**: كسر `@media` بالعرض فقط كان يترك أوضاع اللاندسكيب بالجوال على تنسيق الديسكتوب — أضيف `(max-height: 500px) and (orientation: landscape)` لكل نقاط الكسر بالملفات الثلاثة (tailwind_theme/recycle_home/dashboard_navbar_fix) + إصلاح إخفاء نص «نظام إعادة تدوير» تحت 480px + إضافة كروت جوال لجدولي sort_queue وContents (كانا يختفيان بالبورتريه لعدم وجود بديل كروت).

## جلسة 2026-07-13 — بوابة موافقة المدير على الطلبيات + إعادة هيكلة الملفات الضخمة

**بوابة موافقة المدير (طلبيات الـ API)**: حقل `manager_approval` جديد على `recycle.order` (approved/pending/rejected، الافتراضي approved للطلبيات اليدوية والاختبارات). طلبيات `/api/recycle/orders` تُنشأ `pending` + إشعار فوري لمدير المستودع. موظف الإخراج لا يرى إلا approved (فلتر في `/api/output/orders` + حارس في `order_detail` + حارس في `action_start_processing` + طابور الأولوية `get_blocking_order` يتجاهل غير الموافَق عليها). نقاط `/api/manager/order/approve|reject` (نطاق المستودع مُتحقق، تنفَّذ بهوية المدير الفعلية للـ chatter). واجهة المدير: عمود Approval + أزرار ✓/✗ + مودال سبب الرفض + بانر عدّاد المعلّقة + فلتر، في الجدول والبطاقات والتفاصيل. الرفض ممكن التراجع عنه بالموافقة طالما لم يبدأ التنفيذ. 3 اختبارات جديدة (12/12 كلها تمر). فخ: `_is_supervisor` احتاج `env.su` bypass للاختبارات (superuser ليس عضو المجموعات المخصصة).

**إعادة هيكلة**: `recycle_home_action.xml` (‎~11400 سطر) قُسم آليًا (سكربت node بتحقق تطابق بايت-ببايت لإعادة التجميع) إلى 6 ملفات: recycle_home_action (استقبال 1099) + dashboard_sorting (1487) + dashboard_output (1323) + dashboard_manager (2879) + dashboard_admin (4241) + dashboard_shared_components (429، 8 قوالب مشتركة). `_rpc` المكرر بالملفات الخمسة استُخرج لـ `dashboard_shared.js` (نسختان: `rpcJson` و`rpcJsonSafe` لأن نسخة الفرز لها عقد أخطاء مختلف — لا ترمي أبدًا). كل الـ 13 قالب مؤكد وجودها في الحزمة الحية بعد الترقية.

**جلسات الأجهزة + PWA (نفس اليوم، أبكر)**: نموذج `recycle.user.device` — صف واحد لكل جهاز فعلي (upsert ذري على قيد فريد user+device_key)، اسم الجهاز الحقيقي من الـ User-Agent (موديل أندرويد/iOS/Windows)، تحديث "آخر نشاط" عند الدخول والخروج، `/api/recycle/my-devices` للواجهات الخمس (عمود "آخر عملية" بدل Location). فخ الـ PWA: manifest الموقع كان يعلن icon_logo.png بحجم كاذب 192 (حقيقته 512) فيرفضه كروم — الآن name=Dawrha + أحجام حقيقية + start_url=/.

---

## 3.12) جلسة 2026-07-12/13 — مراجعة أمنية وأداء شاملة (Round E) + قفل الدخول + التحديث الحي

### أ) طلب المستخدم الأصلي (6 بنود) وتنفيذها
| البند | التنفيذ | الملفات |
|---|---|---|
| حذف عمود Weight من جدول المنتجات (أدمن/مدير) | إزالة العمود من `view_recycle_product_list` ومن قائمة المنتجات بالداشبورد | `views/product_views.xml`, `static/src/xml/recycle_home_action.xml` (وقتها) |
| زر التطبيقات (9 نقاط) يظهر أسود غامق بالجوال لغير الأدمن بعد تدوير الشاشة | **الجذر**: تعارض تخصيص CSS — قاعدة بعنصر+كلاس `html body.class .selector` تتفوق على قاعدة كلاسات فقط بنفس العدد رغم تحميلها لاحقاً (مكوّن "c" بمعادلة التخصيص). أُضيف `body.o_ra_dash_admin` (يُفعَّل فقط أثناء تحميل داشبورد الأدمن) وأُعيد بناء قواعد الإخفاء/الإظهار حصراً عليه بثلاث ملفات CSS | `recycle_employee_theme.css`, `recycle_home.css`, `dashboard_navbar_fix.css`, `dashboard_page_state.js` |
| مسار التوظيف: "جدولة مقابلة" يظهر فقط بمرحلة المقابلة، لكن يبقى ظاهراً بعدها + توقيت دقيق لكل قرار + تجميد الأزرار بعد القبول النهائي (والرفض بمرحلة مبكرة قابل للتراجع دائماً) | حقل `recycle_interview_sent_at` (وقت الإرسال الفعلي، مختلف عن وقت المقابلة نفسها) + نموذج `recycle.applicant.stage.log` (سجل تدقيق لكل مرحلة) + حارس `_recycle_check_pipeline_open()` | `models/recruitment.py`, `views/recruitment_views.xml`, `static/src/js/recycle_admin_dashboard.js` |
| تقييم المدير للموظف 1-5 نجوم | حقول `recycle_performance_rating/_rated_by/_rated_at` + مسار `/api/manager/employee/rate` | `models/warehouse.py` (ResUsers), `controllers/dashboard_api.py` |
| راوت Postman جاهز لإنشاء طلبية | وثّق فعلياً + اختُبر حياً (`POST /api/recycle/orders`, هيدر `X-API-KEY`) | `BACKEND_INTEGRATION.md` |
| مراجعة كود شاملة (أمان/أداء/قابلية توسّع) وتقييم /10 | نُفّذت — نتائجها بالجدول التالي | — |

### ب) نتائج المراجعة والإصلاحات الفعلية (الجولة التي تلت "اصلحهم كلهم ولا تكسر النظام")
| الثغرة/المشكلة | الإصلاح | التحقق |
|---|---|---|
| XSS: حقول المستخدم (اسم المتقدم، مكان/ملاحظات المقابلة، سبب الرفض، اسم المستخدم بإيميلات الأمان، إيميل OTP) تُدرج خاماً بجسم HTML | `from html import escape as _esc` بكل الملفات المتأثرة؛ نمط `job_name_raw` (للـ subject الخام) مقابل `job_name` (escaped، للجسم) | اختبار محاكاة (`mock` على `mail.mail.create`) بحمولة `<script>`/`<img onerror>` حقيقية → escaped بنجاح |
| مقارنة مفتاح الـ API بزمن غير ثابت (`==`) | `hmac.compare_digest` | — |
| لا حد أقصى على قوائم الطلبات (orders_list) — تنمو للأبد | استعلامان منفصلان: غير محدود للحالات النشطة (pending/processing/ready — محدودة ذاتياً)، محدود (200، الأحدث أولاً) لـ completed فقط — لا يُقتطع أبداً طلب لا يزال بحاجة لإجراء | — |
| لا Rate Limiting على `/api/recycle/*` الخارجية | نموذج `recycle.api.rate.limit` — عداد نافذة-دقيقة بـ upsert ذري (`INSERT...ON CONFLICT...RETURNING`) آمن لعدة workers، بدون Redis. `@api.autovacuum` لتنظيف الصفوف القديمة | اختبار حي: 429 بعد تجاوز الحد المضبوط بـ`recycle.api_rate_limit_per_minute` (افتراضي 120/د) |
| اختبارات آلية للمنطق الحرج | `tests/test_order_workflow.py` (طابور الأولوية، الخصم بالحالة، التخصيص متعدد المناطق) + `tests/test_recruitment_pipeline.py` (تجميد التوظيف، تراجع الرفض، سجل التدقيق) | 9/9 ناجحة وقتها |
| فهارس DB ناقصة على حقول الفلترة الساخنة | `index=True` على `recycle.order.warehouse_id/state`, `recycle.shipment.warehouse_id/state`, `recycle.zone.warehouse_id`, `res.users.recycle_warehouse_id` | تحقق بـ`\d` بـ psql فعلياً |
| N+1: استعلام مخزون منفصل لكل سطر بكل طلبية بقائمة موظف الإخراج | استعلام مخزون واحد لكل المستودع + تجميع Python (`stock_by_key`) بدل `_available_qty` لكل سطر | مطابقة رياضية 100% بين الطريقتين (تحقق سكربت) |
| `warehouse_id` مفقود من إنشاء الطلبية عبر API (بالكود فقط) | `create_order` يقبل الآن `warehouse_id` (رقمي) بجانب `warehouse_code` — إن أُرسلا معاً يجب أن يتطابقا وإلا رفض واضح | curl حي: 201 بكل الحالات |

**فخ اكتُشف أثناء الإصلاح نفسه** (وليس من المستخدم): `_sql_constraints` بصيغته القديمة (list) **يُتجاهل بصمت** في Odoo 19 (تحذير فقط بالسجل، بلا خطأ) — القيد الفريد الفعلي لم يُنشأ بقاعدة البيانات، وكان سيكسر تحديد المعدل بالإنتاج عند أول upsert. الإصلاح: صيغة `models.Constraint(...)` الجديدة.

**التقييم النهائي المُسلَّم**: 8.5/10 (أمان 8.5، أداء 8.5، بنية الكود 8) — مع توضيح صريح أن بنية الكود تحتاج تقسيم `recycle_home_action.xml` الضخم (تم لاحقاً، انظر 3.11).

### ج) نظام قفل تسجيل الدخول المتدرّج (Login Lockout)
حقول جديدة على `res.users`: `recycle_failed_login_count`, `recycle_lockout_stage` (0-3), `recycle_locked_until`. المنطق بـ `controllers/website.py` (`DawrhaBackendGuard.web_login` + دوال مساعدة بـ `RecycleWebsiteController`):
- 5 محاولات خاطئة → قفل دقيقة واحدة. 5 أخرى → دقيقتان. 5 أخرى → 24 ساعة (الحد الأقصى، يبقى 24س لأي محاولة تالية).
- أثناء القفل: **لا يُختبر كلمة المرور الحقيقية إطلاقاً** — Odoo core يقرأ بيانات الدخول من `request.params` مباشرة (وليس من `**kw` بالتوقيع) فتم استبدال `request.params['password']` بقيمة وهمية غير فارغة لإجبار Odoo على أخذ مسار "كلمة مرور خاطئة" دائماً (يضمن رسالة قفل واضحة دوماً، حتى لو أُدخلت كلمة المرور الصحيحة أثناء القفل، ويوفر تكلفة bcrypt الحقيقية أثناء هجوم القوة الغاشمة).
- نجاح تسجيل الدخول يصفّر كل العدادات. الزيادة atomic عبر SQL خام (`UPDATE...RETURNING`) — آمن لعدة workers متزامنين.
- الواجهة: قالب `login_dawrha` (`auth_templates.xml`) يقرأ `recycle_login_locked` من الـ qcontext ويعطّل زر الدخول (`t-att-disabled`) + رسالة القفل بالعربي/الإنجليزي مع الوقت المتبقي.
- **تحقق حي كامل**: تسلسل HTTP فعلي (User-Agent مختلفة، CSRF حقيقي) أثبت: القفل يُفعَّل بالضبط عند المحاولة الخامسة، تصاعد المراحل الثلاث بالمدد الصحيحة، الزر معطَّل فعلياً بالـ HTML المُخدَّم، النجاح يصفّر كل شيء، الجلسة لا تُنشأ أبداً أثناء القفل حتى بكلمة مرور صحيحة.

### د) التحديث التلقائي الحي (Auto-Refresh / Polling)
لكل الداشبوردات الخمس: `_startPolling()`/`_stopPolling()` بفاصل **5 ثوانٍ**، يعمل فقط على الشاشة الحالية (list/overview) — **متعمداً لا يعمل** على شاشات التفاصيل/المعالجة/النماذج المفتوحة (لتفادي فقدان إدخال جارٍ). يتوقف تلقائياً عند إخفاء التبويب (`document.hidden`). Admin وManager كانا يملكان نسخة أبطأ (30 ثانية، محصورة بشاشة Home فقط) — وُسّعت لتغطي شاشات القوائم الأخرى (شحنات/طلبات) عبر دوال تحديث "صامتة" منفصلة (`_pollRefreshX`) لا تلمس فلاتر البحث ولا سجل التنقّل (بعكس دوال الفتح `openX` الأصلية). Sorting وOutput وReception لم يكن لديهم أي تحديث تلقائي — أُضيف من الصفر بنفس النمط.

**أثر جانبي إيجابي اكتُشف لاحقاً**: زيادة تردد الاستعلامات كشفت فهارس ناقصة إضافية (`receiver_user_id`/`sorter_user_id` على الشحنات) — أُضيفت كجزء من نفس الجولة.

### هـ) درع أخطاء تخزين المتصفح (IndexedDB) — إصداران
**السبب الجذري (مكتشف عبر قراءة كود Owl/Odoo core مباشرة)**: قاعدة `bus_websocket_worker` (سجل تشخيصي داخلي بمتصفح Odoo نفسه، غير متعلق بموديول المشروع) تتلف عندما يمتلئ قرص الجهاز — كل كتابة عليها ترمي `DOMException` **بلا خاصية `.stack`**، فينهار مُبلِّغ أخطاء Odoo نفسه (`error.stack.split(...)` بلا حماية بـ`formatTraceback`) قبل أن يصل لأي معالج مخصص.
- **الإصدار 1**: `recycle_storage_guard.js` (جديد، مسجّل أولاً بكل من `web.assets_backend` و`web.assets_frontend`) — تنظيف ذاتي (حذف القاعدة التالفة مرة يومياً) + مستمع `unhandledrejection` يمتص الاستثناءات عديمة الـ stack المطابقة لأنماط تخزين معروفة، **قبل** تسجيل Odoo لمستمعه (كود الموديول ينفَّذ قبل بدء الخدمات).
- **الإصدار 2** (بعد ظهور صيغتين إضافيتين تحملان `.stack` فعلياً: `FILE_ERROR_NO_SPACE` و`idb-keyval: UnknownError`): توسيع المطابقة بتوقيعات دقيقة إضافية (رسالة تحتوي `.ldb`، أو `name==='UnknownError' && message==='Internal error'`) — **أي خطأ حقيقي بالتطبيق يبقى ظاهراً دائماً** لأن التوقيعات محدودة جداً وحرفية.

---

## 3.13) جلسة 2026-07-13 (متابعة) — إصلاحات نهائية وميزات إضافية

| البند | التفصيل | الملفات |
|---|---|---|
| **إصلاح `TypeError: ctx.String is not a function`** | محرك قوالب Owl لا يسمح باستدعاء دوال JS عامة داخل التعبيرات إلا قائمة محدودة (`RESERVED_WORDS` بمصدر owl.js: `Math, RegExp, Array, Object, Date` فقط — **ليست** `String`/`Number`/`parseInt`/`JSON`). أي استخدام آخر يتحول لـ `ctx.<name>` وينهار. الاستخدام الوحيد لـ `String()` بكل قوالب المشروع كان بشاشة "تعيين الوردية" (أدمن + مدير) — استُبدل بـ `'' + x` | `dashboard_admin.xml`, `dashboard_manager.xml` |
| **إلغاء "طلبات الفرز المتضررة" من قائمة العمليات (المدير)** | إزالة سطر واحد من `navSections` — الشاشة/الكود الخلفي بقيا كما هما (لم يُحذف، فقط أُزيل من القائمة) | `recycle_manager_dashboard.js` |
| **مساعد دورها بالجوال** | البوت (قواعد ثابتة، عربي/إنجليزي، يجيب عن مسارات الشحنات/الطلبات/الورديات) كان موجوداً أصلاً لكن مربوطاً فقط بنص الشعار داخل الدرج الجانبي القابل للطي — أُضيف **زر عائم دائري (💬)** ظاهر فقط ≤767px، مستقل تماماً عن حالة الدرج | `recycle_chatbot.js` |
| **"إضافة مستودع" بواجهة الأدمن** | حقل `address` جديد بالموديل (لم يكن موجوداً) + شاشة كاملة (اسم/كود/محافظة/خط عرض وطول/عنوان/مناطق اختيارية). منطق `_ensure_zones()` الموجود أصلاً بالموديل يتكفّل بالباقي دون أي تعديل: مناطق فارغة → 4 مناطق قياسية تلقائياً؛ منطقة مخصصة واحدة (مثلاً تخزين) → تبقى كما هي + تُضاف 3 المتبقية تلقائياً. **تحقق فعلي بسيناريوهين عبر الكود الحقيقي (وليس افتراضاً)** أثبت الحالتين معاً | `models/warehouse.py`, `recycle_admin_dashboard.js`, `dashboard_admin.xml` |
| **إصلاح: قائمة "معالجة طلبية" (موظف الإخراج) غير مرئية على اللابتوب إطلاقاً** | خلل **موجود أصلاً قبل أي تعديل بهذه الجلسة** (مؤكَّد عبر تحقق التقسيم بايت-ببايت): الشاشة كانت تُعرض **حصراً** ببطاقات جوال (`.o_ra_mobile_card_view`) بلا أي جدول لسطح المكتب — وهذا الكلاس `display:none` افتراضياً (يُفعَّل فقط ≤767px)، فتكون الشاشة فارغة تماماً على أي عرض أكبر. أُضيف جدول سطح مكتب مطابق لبقية الشاشات | `dashboard_output.xml` |
| **توحيد تصميم "ورديتي" للموظفين الثلاثة** | الاستقبال والفرز كانا متطابقين أصلاً. موظف الإخراج فقط كان يستخدم رأس صفحة قديم (`tw-hero`) من قبل توحيد التصميم بدل `o_ra_page_hero` الأخضر القياسي — استُبدل ليطابق الاثنين الآخرين حرفياً | `dashboard_output.xml` |

**تحقق فعلي بعد كل بند من الجلستين 3.12 و3.13**: ترقية الموديول (0 أخطاء) + إعادة تشغيل الحاوية (إلزامي لتفعيل تعديلات Python — الترقية وحدها لا تكفي، العملية الحيّة لا تُعيد تحميل كودها) + مجموعة الاختبارات الآلية كاملة (12/12 بنهاية الجولة) + تحقق حي عبر curl/odoo shell لكل ميزة أمنية أو منطق أعمال جديد.

---

## 3.14) جلسة 2026-07-14 — عرض المحافظة بكل الأدوار + تنظيف الجذر + تدقيق Pagination

### أ) عرض محافظة المستودع (Admin)
كل الأدوار الأخرى (مدير/استقبال/فرز/إخراج) كانت تعرض المحافظة بشكل صحيح مسبقاً عبر `govLabel()` (مضاف بجلسة سابقة). الفجوة الوحيدة المتبقية: شاشة "مستودعات" بواجهة الأدمن لم تكن تجلب حقل `governorate` أصلاً من `openWarehouses()`. أُضيف الحقل لقائمة الجلب + عرضه ببطاقات المستودع وشاشة التفاصيل، بنفس نمط `govLabel()` المستخدَم بكل مكان آخر.

### ب) تنظيف ملفات جذر المشروع (خارج `addons/`)
بموافقة صريحة من المستخدم بعد عرض القائمة (اختيار "احذف الكل")، حُذفت 9 ملفات غير مستخدمة: `.AGENT_PROMPTS.md`, `COMPLETE_PROMPTS_AR.md`, `DEVELOPMENT_PLAN.md`, `QUICK_START.md`, `SYSTEM_SUMMARY.txt`, `README_AR.md`, `requirements.txt`, `static/src/err.tmp`, `static/src/js/e.tmp`. الباقي بالجذر (`BACKEND_INTEGRATION.md`, `CLAUDE.md`, `DIAGNOSE.bat`, `PROJECT_LOG.md`, `prompt-dawraha.md`, `upgrade_module.bat`) كلها مستخدَمة فعلياً — أُبقيت.

### ج) تدقيق شامل للـ pagination/الاستعلامات غير المحدودة (أداء، **بدون** أزرار ترقيم مرئية — تحديد بحجم فقط)
دُقِّقت 3 طبقات: استعلامات `.search()` بـ`controllers/*.py`، استعلامات `orm.searchRead()` بكل شاشات الأدمن، والمكتبة الخارجية `api.py`. **أهم اكتشاف**: دالة `_loadNotifCount()` (شارة الإشعارات غير المقروءة) كانت تجلب **كل** إشعارات المستخدم منذ إنشاء حسابه (فقط لعدّها بالـ JS)، وتُستدعى كل 5 ثوانٍ بكل الداشبوردات الخمس عبر آلية التحديث الحي — أخطر نقطة أداء بالتدقيق كله لأنها الأكثر تكراراً. أُصلحت بالتحول لـ `orm.searchCount()` (استعلام COUNT على الخادم بدل جلب كل السجلات).

| البند | الإصلاح | الملفات |
|---|---|---|
| شارة الإشعارات (كل الأدوار الخمسة) — كانت تجلب كل السجلات كل 5 ثوانٍ | `orm.searchCount(..., [...,['is_read','=',false]])` بدل `searchRead` + عدّ بالـ JS | `recycle_admin_dashboard.js`, `recycle_manager_dashboard.js`, `recycle_sorting_dashboard.js`, `recycle_output_dashboard.js`, `recycle_home_action.js` |
| شحنات/طلبات الأدمن (عرض عام لكل المستودعات) بلا أي حد — نفس الاستعلام عند المدير كان محدوداً `limit:200` مسبقاً ولم يكن قد طُبِّق على الأدمن | `limit: 200` على `openShipments`/`openOrders`/`_pollRefreshShipments`/`_pollRefreshOrders` | `recycle_admin_dashboard.js` |
| 8 شاشات أخرى بالأدمن تكبر مع الزمن بلا حد (طلبات توظيف، بركة المواهب، موظفون محذوفون ×2، حسابات الموقع، مقبولون/مرفوضون/محذوفون من التوظيف، أرشيف الشحنات/الطلبات) | `limit: 300` على كل استعلام | `recycle_admin_dashboard.js` |
| كتالوج المنتجات بالـ API الخارجي (NestJS) بلا حد | `limit=500` | `controllers/api.py` |
| سجل تغييرات الموظف (شاشة الأدمن) بلا حد | `limit=300` | `controllers/dashboard_api.py` |

**استعلامات فُحصت وتبيّن أنها آمنة كما هي (لا تحتاج تعديل)**: ~15 موقع بـ`dashboard_api.py`/`website.py`/`attendance_api.py` إما محدودة أصلاً بسطر مجاور فات الفحص الأول (`limit=1` لبحث سجل واحد)، أو محكومة طبيعياً بحجم كيان صغير لا ينمو تشغيلياً (عدد المناطق/الموظفين لكل مستودع، عدد المستودعات نفسها، مخزون مستودع واحد = تركيبة منتج×منطقة×حالة محدودة).

**تحقق فعلي**: `node --check` لكل ملفات JS المعدَّلة (نجاح) + `lxml.etree.parse` لكل XML (نجاح) + `py_compile` للـ Python المعدَّل (نجاح) + ترقية الموديول (0 أخطاء) + إعادة تشغيل الحاوية (تعديلات Python بـ`api.py`/`dashboard_api.py`) + **12/12 اختبار ناجح** + تحقق حي عبر `odoo shell`: حقل `governorate` يُقرأ فعلياً من `recycle.warehouse`، `search_count` يعمل، `limit=` يعمل فعلياً على `recycle.product`.

### د) جولة تدقيق ثانية أعمق (بطلب المستخدم: "تأكد من قصة الـ pagination ع كل مشروع، لا تنسى أي فكرة")
الجولة الأولى (البند أعلاه) غطّت فقط `dashboard_api.py` وشاشات الأدمن الرئيسية. طُلب تدقيق **شامل فعلاً** — تمت مراجعة كل استعلامات `.search()`/`.search_read()`/`.search_count()` بكل ملفات `controllers/*.py` و`models/*.py` (~100 موقع) + كل استدعاءات `orm.searchRead()` بكل ملفات JS بالمشروع (بما فيها شاشات فرعية مستقلة لم تُفحص بالجولة الأولى: `recycle_applications_board.js`, `recycle_employees_board.js`, `recycle_manager_attendance.js`).

| البند | الإصلاح | الملفات |
|---|---|---|
| صفحة الموقع العامة (Home) تحسب "الأطنان المُعاد تدويرها" بجلب **كل** سجلات الشحنات المكتملة تاريخياً لجمعها بـ Python | استُبدلت بـ `_read_group` (جمع SUM حقيقي على مستوى قاعدة البيانات، بلا نقل أي صفوف للخادم) — **تحقق رياضي فعلي**: النتيجة الجديدة طابقت القديمة تماماً (`4440.0 == 4440.0`) على البيانات الحالية، يعني الإصلاح تحسين أداء بحت بلا أي تغيير بالرقم المعروض | `controllers/website.py` |
| شاشة "طلبات التوظيف" المستقلة بالأدمن (تصل عبر قائمة إعدادات Odoo، منفصلة عن الداشبورد الرئيسي) بلا أي حد | `limit: 300` | `recycle_applications_board.js` |
| دالة `get_history_for_user()` بالموديل (توأم لنفس الاستعلام المُصلَح بالجولة الأولى، لكن بمكان مختلف — غير مُستخدَمة حالياً لكنها نفس نوع العلة الكامنة) | `limit=300` (اتساقاً مع نظيرتها) | `models/employee_history.py` |

**استُبعد عمداً من التعديل** (بعد فحص دقيق): طابور طلبات الإخراج النشطة (`pending/processing/ready`) بـ`dashboard_api.py:2133` — **لم يُحدَّد بحد أقصى عمداً** لأنه عمل لم يُنجز بعد يجب أن يظهر كاملاً لموظف الإخراج (تحديده يعني إخفاء عمل حقيقي عن الموظف، وهذا خطأ وظيفي وليس تحسين أداء)؛ كذلك `get_blocking_order()` بـ`models/order.py` (منطق أولوية الطابور — لأسباب مطابقة). قوائم الموظفين بكل الشاشات (bounded بعدد الموظفين الحقيقي، ليس بيانات معاملات متراكمة). ~15 استعلاماً آخر بـ`website.py`/`attendance_api.py`/الموديلات محكومة طبيعياً بحجم صغير (منطقة واحدة، مستودع واحد، مستخدم واحد، إلخ).

**تحقق فعلي للجولة الثانية**: نفس تسلسل الجولة الأولى بالكامل (فحص صيغة + ترقية + إعادة تشغيل + **12/12 اختبار ناجح** + تحقق حي عبر `odoo shell` أثبت تطابق رقم "الأطنان" بين الطريقتين القديمة والجديدة حرفياً).

### و) Pagination حقيقي (تمرير-للتحميل بدل "أول 200 وخلص") — عمّم على كل المشروع
بعد نقاش مع المستخدم اتضح إنه الهدف مو بس "حدّد الأقدم"، بل "التمرير للأسفل يحمّل الدفعة التالية تلقائياً" — نفس الأسلوب اللي طُبِّق أول مرة على شحنات/طلبات الأدمن (راجع بند "هـ" أعلاه) لازم يشمل **كل مكان بالمشروع** فيه هالنمط، مو بس الشاشتين الأصليتين.

**بنية تحتية مشتركة جديدة** (`dashboard_shared.js`): `makePager(orm, {model, fields, order, pageSize, context})` — يرجّع `{fetchFirst(domain), fetchMore(domain, lastId)}` بمنطق تصفح بمؤشر `id` موحّد؛ و`attachInfiniteScroll(getView, handlers)` — مستمع `scroll` واحد على `window` لكل الشاشات، يوزّع حسب الشاشة الحالية. أي شاشة جديدة تحتاج تمرير-للتحميل تصير مجرد استدعاء لهاتين الدالتين بدل تكرار نفس الكود.

**الشاشات المُحوَّلة بالكامل** (بحث فعلي على مستوى السيرفر + تمرير للتحميل، بدون أي أزرار صفحات):

| الشاشة | الواجهة | ملاحظة خاصة |
|---|---|---|
| طلبات التوظيف (Applicants) | أدمن | — |
| بركة المواهب (Talent Pool) | أدمن | كان فيها بحث نصي client-side فقط (نفس علة الشحنات الأصلية) — صار بحث سيرفر حقيقي |
| حسابات الموقع (Website Users) | أدمن | — |
| الموظفون المحذوفون | أدمن | نفس الدالة تخدم مكانين باستدعاء الشاشة (تبويب "محذوف" + `switchEmployeeTab`) — تم توحيدهما بدالة واحدة مشتركة `_refetchDeletedEmployees()` |
| المقبولون / المرفوضون من التوظيف | أدمن | — |
| المحذوفون من التوظيف (حسابات) | أدمن | كان الحقل `id` غير مطلوب صراحة بالجلب (Odoo يرجعه دائماً تلقائياً، فما كان خلل فعلي، لكن أُضيف صراحة للوضوح) |
| أرشيف الشحنات / أرشيف الطلبات | أدمن **و**المدير | **كانت تشارك نفس متغيرات الحالة `state.shipments`/`state.orders` تبع الشاشة الرئيسية** (خلل بنيوي موجود أصلاً من قبل هالجلسة) — أُعطيت متغيرات مستقلة (`archivedShipments`/`archivedOrders`) لكل من الأدمن والمدير لمنع أي تصادم بين الشاشتين |
| الشحنات / الطلبات | المدير | بالإضافة للبحث والتمرير: فلتر "المنطقة" (استقبال/فرز/تخزين) كان يُحسب على العميل فقط من حالة الشحنة — تُرجم لشرط `state` مكافئ تماماً بجانب السيرفر (`state in [accepted,sorting]` لمنطقة الفرز، إلخ) فبقي البحث يعمل بشكل صحيح حتى مع الفلتر |
| لوحة "طلبات التوظيف" المستقلة (تصل من إعدادات Odoo) | أدمن | حالة خاصة: حاوية الشاشة تمرّر داخلياً (`overflow-y:auto`) مو بالصفحة كلها، فاستُخدم مستمع تمرير مخصص (`t-ref` + مستمع على العنصر نفسه) بدل المستمع المشترك اللي يراقب نافذة المتصفح |

**تحديث آلية التحديث الحي**: `_pollRefreshShipments`/`_pollRefreshOrders` (أدمن والمدير) صارت تتوقف تلقائياً عن إعادة الجلب الصامت إذا كان المستخدم قد حمّل أكثر من صفحة واحدة (بالتمرير)، بدل ما تصفّر الصفحات الإضافية المحمّلة تحت يده كل 5 ثوانٍ.

**فحص دقيق لكل شرط بحث "OR" متعدد** (لتفادي كسر ترتيب رموز `|` بصيغة Odoo البادئة) — تحقق فعلي حي عبر `odoo shell` لخمسة نماذج مختلفة (بركة المواهب 4-way OR، المقبولون 2-way OR على حقل مرتبط `job_id.name`، الموظفون المحذوفون، حسابات الموقع، فلتر منطقة الشحنات) — **كلها نُفِّذت بنجاح بلا أي خطأ** على بيانات حقيقية بالقاعدة.

**تحقق فعلي**: فحص صيغة لكل ملفات JS المعدَّلة (نجاح) + فحص XML لكل القوالب المعدَّلة (نجاح) + ترقية الموديول (0 أخطاء، بلا تعديلات Python فما احتاج إعادة تشغيل) + **12/12 اختبار ناجح** + تحقق حي بالشل لكل شروط البحث كما بالأعلى.

---

## جلسة 2026-07-14 (متابعة) — خطأ نشر حقيقي + تدقيق شامل لكل الكود بطلب المستخدم

### أ) خطأ حقيقي واجهه المستخدم: `External ID not found: recycle_warehouse.menu_recycle_config`
حصل وقت ضغط المستخدم "تثبيت" لموديول من واجهة Odoo (Settings > Apps)، وهاد أعاد بناء الـ registry بالكامل فأعاد معالجة كل ملفات بيانات `recycle_warehouse`. **السبب الجذري**: ملفي `views/uom_views.xml` و`views/warehouse_views.xml` يحتويان `<menuitem>` بـ`parent="menu_recycle_config"`، لكن `menu_recycle_config` **معرَّف فقط داخل `views/menus.xml`** — و`menus.xml` بترتيب التحميل بـ`__manifest__.py` يُحمَّل **بعد** الملفين هدول، فما يلاقي الأب وينهار.

**الإصلاح**: نقل بندي القائمة (`menu_recycle_uom`, `menu_recycle_add_admin`) من مكانهم لجوا `menus.xml` نفسه (بجانب تعريف `menu_recycle_config`)، وإبقاء تعريف الـ`action` (الإجراء) بمكانه الأصلي (ما كان فيه مشكلة بترتيبه).

### ب) تدقيق شامل لكل الكود (بطلب صريح: "شيك ع كود كامل و حل اذا في مشاكل")
تسلسل تحقق كامل تجاوز الممارسة المعتادة هالجلسة:
1. **فحص صيغة كل ملفات Python** بالموديول (عدا الاختبارات) عبر `py_compile` — كلها سليمة.
2. **فحص صيغة كل ملفات JS** (19 ملف) عبر `node --check` — كلها سليمة.
3. **فحص صيغة كل ملفات XML** (27 ملف) عبر `lxml.etree.parse` — كلها سليمة الآن (بعد إصلاح بند "أ").
4. **الفحص الأهم — تثبيت كامل من الصفر على قاعدة بيانات تجريبية فارغة تماماً** (`recycle_fresh_test`, أُنشئت ثم حُذفت بعد الفحص): يُعيد إنتاج **بالضبط** نفس السيناريو يلي واجه المستخدم (تثبيت جديد بيعالج كل ملفات البيانات من الصفر بترتيب المانيفست الكامل، 58 موديول). **نجح بالكامل بلا أي خطأ** — دليل قاطع إنه ما تبقى أي خلل ترتيب تحميل مشابه بباقي المشروع.
5. **12/12 اختبار ناجح** — مرتين: على قاعدة البيانات التجريبية الفارغة، وعلى قاعدة الإنتاج الحية بعد كل إصلاح.
6. **فحص xmlid مكررة عبر كل ملفات XML** (سكربت مقارنة): لقى نمط طبيعي متكرر بـ`menus.xml` (نفس الـid يتكرر مرتين بقصد: مرة `<menuitem>` لإنشاء القائمة، ومرة `<record>` لضبط `group_ids` عليها لاحقاً — هاد اصطلاح Odoo قياسي، مو خطأ) **+ اكتشاف حقيقي واحد**: `rule_attendance_admin` و`rule_attendance_manager` كانا **معرَّفين مرتين بملفين مختلفين** (`security/security.xml` و`views/attendance_views.xml`) بقيم `domain_force` مختلفة فعلياً — بما إنه `attendance_views.xml` يُحمَّل بعد `security.xml`، فالتعريف الثاني كان يطغى صامتاً على الأول بلا أي تحذير. **قارنت** القاعدة الفعّالة (النسخة بـ`attendance_views.xml`: `manager_user_id == user.id` فقط) مع النمط القياسي المستخدم بكل مكان تاني بالمشروع (`_get_manager_warehouse()` بـ`dashboard_api.py`) — **متطابقين** — يعني القاعدة الفعّالة فعلياً صحيحة ومتسقة، والنسخة الميتة بـ`security.xml` كانت مجرد كود قديم متروك بيربك أي تعديل مستقبلي (لو حد عدّل نسخة `security.xml` ظانّاً إنها الفعّالة، تعديله ما كان رح يأثر أبداً). **حُذفت النسخة الميتة**.

**تحقق فعلي نهائي بعد كل إصلاح**: ترقية على قاعدة الإنتاج (0 أخطاء) + إعادة تشغيل الحاوية + **12/12 اختبار ناجح** + تحقق حي عبر `odoo shell` أثبت إنه القائمتين المنقولتين مرتبطتين صح بالأب والإجراء الصحيحين.

### هـ) تطبيق "Pagination حقيقي" على شحنات/طلبات الأدمن (بطلب صريح من المستخدم بعد نقاش توضيحي)
اكتُشفت مشكلة حقيقية أثناء شرح تأثير `limit:200`: صندوق البحث وفلتر الحالة بشاشتي "الشحنات"/"الطلبات" (أدمن) كانا يفلتران **فقط داخل الـ 200 سجل المحمّلة أصلاً بالذاكرة** (`filteredShipments`/`filteredOrders` — getter بـ JS)، وليس بكل قاعدة البيانات — يعني البحث عن شحنة أقدم من آخر 200 ما كان يلاقيها إطلاقاً حتى لو الاسم مطابق تماماً. طلب المستخدم توضيحاً بمعنى "Pagination الحقيقي" فعّال: التمرير للأسفل يحمّل الدفعة التالية (الأقدم) تلقائياً، بدون أي أزرار أرقام صفحات.

**التنفيذ** (`recycle_admin_dashboard.js` + `dashboard_admin.xml` + `recycle_home.css` + `recycle_i18n_shared.js`):
- البحث النصي وفلتر الحالة تحولا لاستعلام حقيقي على السيرفر (`_shipmentDomain()`/`_orderDomain()`)، بدل الفلترة على القائمة المحمّلة فقط. البحث النصي مؤجَّل (debounce 400ms) لتفادي إغراق السيرفر بطلب لكل ضغطة زر.
- **تمرير-للتحميل (Infinite Scroll) بدل أزرار الصفحات**: مستمع `scroll` واحد على `window` (مسجَّل بـ`onMounted`، مُزال بـ`onWillDestroy`) — عند الاقتراب من أسفل الصفحة يستدعي `loadMoreShipments()`/`loadMoreOrders()`، واللي يجيب الدفعة التالية عبر **مؤشر على `id`** (`id < آخر معرّف محمّل`, `order: 'id desc'`) بدل `offset` (أسرع على الجداول الكبيرة، ولا يتخطى/يكرر صفوفاً لو انضافت سجلات جديدة أثناء التصفح).
- التحديث الحي (auto-refresh كل 5 ثوانٍ) لا يلمس القوائم الموسّعة: إذا كان المستخدم قد حمّل أكثر من صفحة واحدة، يتوقف التحديث الصامت تلقائياً (بدل ما يصفّر السجلات المحمّلة الإضافية تحت يد المستخدم وهو يتصفح).
- تُرجم النصان الجديدان ("جارٍ تحميل المزيد…" / "نهاية القائمة.") للعربية عبر نظام الترجمة الموجود.

**تحقق فعلي حي عبر `odoo shell`** (على بيانات حقيقية بالقاعدة، 38 شحنة):
- استعلام الـ OR الثلاثي (اسم/سائق/اسم مستودع) نُفِّذ بدون خطأ وأرجع نتائج صحيحة.
- تحقق التصفح بالمؤشر: الصفحة الأولى `[41,40,39]`، الصفحة الثانية (`id < 39`) `[38,37,36]` — **بدون أي تداخل أو تكرار أو فجوة** بين الصفحتين.
- ترقية الموديول (0 أخطاء، لا تعديلات Python بهالجزء فلا حاجة لإعادة تشغيل الحاوية) + **12/12 اختبار ناجح**.

**نطاق التنفيذ**: شاشتي "الشحنات" و"الطلبات" بواجهة **الأدمن** فقط (نفس الشاشتين اللي بدأ منهم النقاش). نفس النمط قابل للتطبيق على شاشات المدير المكافئة (محدودة بمستودع واحد فعلياً، فالمشكلة أخف بكثير هناك) لو طلب المستخدم لاحقاً.

---

## جلسة 2026-07-14 (متابعة) — إدارة الشاحنات (Fleet) في الأودو + ربطها بالباك إند

**الطلب**: الأدمن (في الأودو) يضيف/يعدّل/يعرض الشاحنات ويسندها لمستودع أو يتركها غير مسندة، وكل ذلك ينعكس على الباك إند (NestJS) ويُعلَم أدمن الباك إند بإضافة الشاحنة وإسنادها. مع خيار مستقل "الشاحنات" في نافبار الأدمن فيه إضافة/عرض/تعديل.

### أ) موديل الشاحنة (Odoo هو سيّد الأسطول)
- نموذج جديد `recycle.truck` (`models/truck.py`) بأسماء حقول **عقد** مع الباك إند (لا تُعاد تسميتها): `name, plate_number, model, year, max_payload_kg, warehouse_id (M2o recycle.warehouse, ondelete=set null), is_active, notes`. قيد فريد على `plate_number` + تحقق سنة الصنع (1980..السنة القادمة) والحمولة (≥0) عبر `models.Constraint`/`@api.constrains`.
- نموذج مرافق `recycle.driver.assignment` (نفس الملف) بالحقول `backend_driver_id, truck_id, shift_id` — **إلزامي لعقد `SYNC_FLEET`** بالباك إند (كان `fetchDriverAssignments()` يقرأ `recycle.driver.assignment`؛ غيابه يجعل مهمة مزامنة الأسطول تفشل وتُعيد للأبد). يبقى فارغاً حتى تُبنى دورة إسناد السائق لاحقاً — جدول فارغ هو الوضع الطبيعي الآن.
- كل `create/write/unlink` على الموديلين يستدعي `recycle.backend.sync.notify_fleet_changed()` (fire-and-forget، ملفوف بـ try/except، لا يعطّل العمل أبداً).

### ب) طبقة الربط (backend_sync.py)
- أُضيف مسار `fleet` لقاموس `BACKEND_ROUTES` بقيمة `/api/v1/odoo/webhooks/fleet` (نقطة **حيّة فعلاً** بالباك إند: `OdooWebhookController.fleetChanged` — تُرجع 202 وتجدول `SYNC_FLEET`).
- `notify_fleet_changed()`: نداء بلا حمولة (Odoo يبقى مصدر الحقيقة، والباك إند يُعيد قراءة الأسطول كاملاً عبر JSON-RPC) — يُرسل هيدر `x-odoo-webhook-secret = recycle.backend_webhook_secret` (يختلف عن بقية المسارات التي تستخدم `X-API-KEY`). أُضيف بارامتر `extra_headers` لدالة `_post` لدعم ذلك. إن لم يُضبط السر، تُتخطى العملية بصمت.

### ج) الأمان والقوائم
- 4 صفوف `ir.model.access.csv`: أدمن (CRUD كامل) ومدير (قراءة فقط) على `recycle.truck` و`recycle.driver.assignment`.
- `views/truck_views.xml` (مسجّل بالمانيفست): list/form/search كلاسيكية (للباك أوفيس). **فخ Odoo 19**: فلتر "Group By" لا يُلفّ بـ `<group expand="0">` (يكسر RelaxNG: "Invalid attribute expand for element group") — يوضع كـ `<filter context="{'group_by': ...}">` مباشرة تحت `<search>` (نفس نمط `shift_views.xml`).
- `views/menus.xml`: عميل أكشن `action_admin_nav_trucks` (`initial_view: 'trucks_list'`) + بند قائمة أعلى المستوى **"Trucks"** (sequence=9، بعد Warehouses مباشرة، للأدمن فقط) — بنفس نمط بند Warehouses.

### د) واجهة الأدمن (الداشبورد المُنسَّق)
- `recycle_admin_dashboard.js`: خيار `trucks` بـ `navSections` (أيقونة 🚛، single view)، حالة كاملة، ودوال `openTrucks/_refetchTrucks/filteredTrucks (بحث+فلترة مستودع+فلترة حالة على العميل — الأسطول محدود الحجم كالزونات/الورديات)/openTruckCreate/openTruckEdit/_truckVals (تحقق)/saveTruck/toggleTruckActive` + حالة `trucks_list` بالـ `initial_view`.
- `dashboard_admin.xml`: شاشتان جديدتان `trucks_list` (جدول سطح مكتب **و** بطاقات جوال — كلاهما إلزامي، انظر ملاحظة معمارية 14) و`truck_form` (إضافة/تعديل بنفس القالب). فلاتر: بحث + مستودع (يشمل "غير مسندة") + حالة الخدمة.
- `recycle_i18n_shared.js`: كل مفاتيح الترجمة العربية للشاشتين.

### تحقق فعلي (مُثبت)
- ترقية الموديول: **0 أخطاء** (بعد إصلاح فخ RelaxNG للـ search view). إعادة تشغيل الحاوية لتفعيل تعديلات Python.
- **12/12 اختبار أودو ناجح**.
- **تحقق حي عبر `odoo shell`**: حقول `recycle.truck` و`recycle.driver.assignment` تطابق العقد (`FIELDS_OK=True`, `ASSIGN_OK=True`)؛ إنشاء شاحنة يُطلق **نداء واحد** لـ `notify_fleet_changed`، والتعديل (إعادة الإسناد) يُطلق نداءً آخر؛ النداء الفعلي يذهب لـ `/api/v1/odoo/webhooks/fleet` بالهيدر الصحيح (Connection refused فقط لأن NestJS غير مشغّل الآن — سلوك fire-and-forget المقصود).
- **تحقق بصري بالمتصفح** (جلسة admin فعلية): بند "Trucks" بالنافبار → شاشة الأسطول (Hero أخضر + فلاتر + حالة فارغة) → "Add Truck" → تعبئة (Damascus Truck 1 / DAM 1234 / Hyundai HD65 / 2021 / 3500) → **"Truck created successfully!"** + ظهور البطاقة بشارة "In Service" → فتح البطاقة → نموذج **Edit Truck** معبّأ مسبقاً بزر "Save Changes". حُذفت الشاحنة التجريبية بعد الفحص (0 شاحنات متبقية).

### الجانب الآخر (مشروع الباك إند NestJS)
تعديلات مرافقة في `backend_dawrha` (انظر FIXES.md هناك جولة 2026-07-14): `syncFleet()` صار يُشعر حسابات الأدمن عند إضافة شاحنة أو تغيّر إسناد مستودعها (مفاتيح i18n جديدة ar/en) + `ODOO_WEBHOOK_SECRET` بالـ`.env` (يطابق `recycle.backend_webhook_secret` بالأودو).

---

## جلسة 2026-07-16 — نوع الوردية + قسم الشاحنات (أدمن/مدير) + طلبات السائقين (الدورة الكاملة)

**4 مهام رئيسية بطلب صريح من المستخدم، منفذة على المشروعين معاً:**

### أ) نوع الوردية (سائقين / موظفي مستودع)
- `recycle.shift.shift_type` (selection: warehouse افتراضي / driver، **عقد مع الباك إند**) + عرضه بالفيوهات الكلاسيكية وشاشات الداشبورد (إنشاء/تعديل/قائمة بشارة ملونة) وإخفاء منتقي الموظفين كلياً للورديات driver.
- **3 حواجز صلبة (مُثبتة بالشل)**: `action_set_employees` يرفض إسناد موظفين لوردية سائقين · `@api.constrains('shift_id')` على `res.users` يمنع موظفاً من أخذ وردية سائقين (يغطي كل مسارات الكتابة) · `@api.constrains('shift_type')` يمنع تحويل وردية عليها موظفون إلى driver · `recycle.driver.assignment` يقبل ورديات driver فقط.
- نقطتا المدير `/api/manager/warehouse-shifts` و`/api/manager/shift-assignment/warehouse-shifts` + منتقي ورديات الموظف بالأدمن يفلترون `shift_type='warehouse'`.
- `recycle.shift` صار يرسل ping أسطول للباك إند عند أي create/write/unlink (كان write فقط لا يرسل شيئاً).

### ب) قسم الشاحنات
- نافبار الأدمن: "Trucks" تحوّل لقسم بثلاثة بنود: **All Trucks / Add Truck / Drivers** + زر تبديل حالة (في الخدمة/خارج الخدمة) بجانب Edit بالجدول وبطاقات الجوال.
- **`action_toggle_service_state`**: أدمن = أي شاحنة؛ **المدير = شاحنات مستودعه فقط** (فحص ملكية صريح ثم sudo — المدير يبقى قراءة-فقط على البيانات) — مُثبت بالشل أن مستخدماً عادياً يُرفض.
- **record rules جديدة** على `recycle.truck`: أدمن الكل؛ المدير يرى شاحنات مستودعه فقط (`manager_user_id` أو `recycle_warehouse_id`).
- **داشبورد المدير**: بند "Trucks" جديد بالسايدبار + شاشة (جدول + بطاقات جوال + بحث + فلتر حالة) عرض وتبديل حالة فقط — بلا أي تعديل بيانات.

### ج) طلبات السائقين (الدورة الكاملة backend ⇄ Odoo)
- **نموذجان جديدان** `models/driver_request.py`: `recycle.driver.request` (backend_driver_id فريد، name/email/phone، state: pending/accepted/rejected/need_changes، warehouse_id عند القبول) + `recycle.driver.request.image` (backend_media_id/file_type/url/status).
- **create = upsert بالعقد**: الباك إند يستدعي `create` دائماً (بما فيها إعادة الدفع بعد إعادة رفع صورة) — سجل موجود يُحدَّث (تُستبدل صوره ويعود pending) بدل التكرار — مُثبت بالشل. إشعار أدمن أودو عند كل طلب جديد/محدَّث.
- **القرارات صارمة وليست fire-and-forget**: `notify_driver_decision` (route جديد `driver_decision` → `/api/v1/odoo/webhooks/driver-decision` بهيدر السر) يُستدعى **قبل** حفظ القرار؛ فشل الوصول = UserError ولا يُحفظ شيء — **مُثبت بالشل وبالمتصفح** (رسالة حمراء والطلب بقي pending والباك إند مطفأ).
- **شاشة "Driver Requests"** بقسم Recruitment بالسايدبار: تبويبات حالة، بطاقة لكل طلب (معلومات + صور المستندات كصور مصغرة قابلة للفتح بإطار ملون حسب الحالة)، **قبول** (مودال اختيار مستودع إلزامي)، **رفض** (مودال سبب إلزامي)، **رفض صورة واحدة** (مودال ملاحظة اختيارية → NEED_CHANGES + rejected_media_ids) — كلها مُتحقق منها بصرياً.
- **شاشة "Drivers"** بقسم Trucks: المقبولون فقط (اسم/إيميل/هاتف/مستودع/تاريخ القبول).
- التحديث الحي (polling 5s) يشمل شاشة الطلبات.

### د) الباك إند (NestJS)
- **Shift entity**: عمودان جديدان `shift_type` (enum DRIVER/WAREHOUSE، القديم = DRIVER) و`is_active` — هجرة `1783700000000-shiftTypeMigration.ts` (**مطلوب `npm run migration:run` بعد السحب**).
- `GET /shifts` (منتقي السائق بالـ onboarding) يعيد **ورديات DRIVER الفعالة فقط** · `getDriverShiftOrThrow` بالـ onboarding وطلب تغيير الوردية (وردية warehouse تبدو "غير موجودة").
- **حذف الورديات المحذوفة من أودو**: `syncFleet` يحذف المرآة؛ إن بقيت مراجع تاريخية (FK) يعطلها `is_active=false` فتختفي من قوائم السائقين — بعد تنظيف الإسنادات بنفس الدورة.
- **دفع طلب السائق صار يشمل صور المستندات** (media id/type/url من جدول media بمالكها profile.id) — `createDriverRequest` + حقن `mediaRepo` بالمعالج.
- **webhook `driver-decision` اتسع**: حقل اختياري `rejected_media_ids[]` (UUID، حد 20) → المعالج يعلّم تلك الصور REJECTED (بفحص ملكية `ownerId=profile.id`) فيقبلها مسار إعادة الرفع `PATCH /media/:id/reupload` الذي يعيد الدفع لأودو تلقائياً — **دورة مغلقة بالكامل**.

### التحقق (كله فعلي)
- أودو: ترقية 0 أخطاء ×2 + إعادة تشغيل + **12/12 اختبار** + فحوص شل شاملة (كل الحواجز BLOCKED، upsert يعمل، القرار الصارم يرفع خطأ ولا يحفظ) + **تحقق بصري بالمتصفح**: قسم Trucks بثلاثة بنوده، شاشة Drivers، شاشة Driver Requests ببطاقة تجريبية كاملة الصور والأزرار، مودال القبول باختيار المستودع، ورسالة الفشل الصارم الحمراء.
- باك إند: `tsc` نظيف + **154/154 اختبار** (أُصلح fixture واحد بالسبك يعكس العقد الجديد).
- **فخ تشخيصي مهم**: قاعدة الاختبار المحلية لا تحوي أي مستخدم بأدوار تشغيلية — أول فحص شل أعطى "ALLOWED (BUG!)" كاذبة لأن recordset الموظف كان فارغاً (`write` على recordset فارغ لا يفعل شيئاً بصمت). التحقق الصحيح أنشأ مستخدماً مؤقتاً.

---

## جلسة 2026-07-20 — إصلاحات UI الجذرية (زر التطبيقات/الدرج/Active/hover) + أسطول المستودع + إسناد سائق↔شاحنة (المشروعان معاً)

### أ) إصلاحات واجهة جذرية (مثبتة بالمتصفح قبل وبعد)
| البند | الجذر والإصلاح | الملفات |
|---|---|---|
| **زر المربعات التسعة "الخفيف" بالـ Light mode** | بقايا ستايل زجاجي (opacity 0.8 + خلفية surface + ظل) على حاوية اللونشر للأدمن + الشبح opacity 0.01 بحجمه الطبيعي كانا يظهران كمربع باهت. الآن: مخفي تماماً عن كل الموظفين (display:none)، وللأدمن شبح **1×1 بكسل** opacity 0.01 (لا يُرى إطلاقاً بالوضعين) يبقى لأن Odoo يتجاهل النقرة الموجهة إن كان العنصر غير قابل للإصابة. وصول الأدمن للتطبيقات حصراً من **كارد "All Apps" في الإعدادات** + fallback جديد في `openAppLauncher()` يوجه لـ `/odoo` إن لم يركّب Odoo الزر الأصلي بالـ DOM (يحدث فعلاً على بعض التحميلات) | `dashboard_navbar_fix.css`, `recycle_home.css` (كتلتا `o_navbar_apps_menu`), `recycle_admin_dashboard.js` |
| **القائمة الجانبية "الناقصة" على اللابتوب** | خللان منطقيان: (1) **عدم تطابق نقاط كسر** — الدرج يتفعل ≤900px لكن زر ☰ بالصفحة الرئيسية كان يظهر ≤768px فقط ⇒ أي نافذة 769–900 (لابتوب صغير/تكبير ويندوز) تفقد القائمة بلا زر لفتحها؛ (2) الدرج المفتوح كان `top:48px` (فراغ فوقه) وبـ z-index 999 **تحت** النافبار الثابت (z 1000) فيبدو مقصوصاً. الإصلاح: ☰ صار ≤900 (مطابق للدرج)، والدرج المفتوح `top:0` بارتفاع الشاشة كاملاً و**z 1200 فوق النافبار** وbackdrop z 1150 — طُبق على النظامين (`o_ra_sidebar` بكتلتَي 900/768 و`tw-sidebar` للموظفين). قياس فعلي بعد الإصلاح: y=0 وheight=viewport على 768 و850 و760 لكل الأدوار | `recycle_home.css`, `tailwind_theme.css` |
| **Active أخضر ثابت بكل النافبارات** | كان شرط التفعيل للأزرار المفردة ثابتاً بالخطأ على `state.view === 'dashboard'` (أدمن+مدير) وعناصر الأقسام بلا تفعيل إطلاقاً. الآن حالة `activeNavGo` موحدة بالداشبوردات الخمسة: تُضبط في `navClick` وتبقى خضراء حتى يُضغط خيار آخر (أزرار مفردة + عناصر أقسام + زر الإعدادات) + كلاسا `o_ra_sb_item_active`/`tw-sidebar-item-active` بالوضعين | JS+XML الداشبوردات الخمسة, `recycle_home.css`, `recycle_employee_theme.css` |
| **hover فلاتر طلبات السائقين يبتلع النص** | ثلاث قواعد `.o_recycle_back_btn:hover` بنفس التخصيص: الأخيرة تعطي **لون النص الأخضر** وقاعدة أقدم تعطي **الخلفية الخضراء** ⇒ أخضر-على-أخضر. وحّدت الأخيرة: خلفية خضراء + **نص أبيض**، مع استثناء للتبويب النشط (`o_ra_tab_active` نصه أخضر !important) يبقي خلفيته surface — مثبت من الحزمة المُقدَّمة (الكاسكيد الفائز bg=primary/color=#fff) | `recycle_home.css` |
| إزالة **Accepted Applicants** من نافبار الأدمن | أُزيل البند من قسم Recruitment فقط (الشاشة وكودها باقيان كنمط "طلبات الفرز المتضررة") | `recycle_admin_dashboard.js` |

### ب) أسطول المستودع + شاشة السائقين
- `recycle.warehouse`: حقلا `truck_count` و`driver_count` (سائقو الطلبات المقبولة) — كروت جديدة بشاشة تفاصيل المستودع (أدمن) + **قائمتا شاحنات وسائقي هذا المستودع حصراً** (مع الوردية) — مثبت ببيانات فعلية (2/2).
- شاشة **Drivers** (أدمن + جديدة للمدير): بحث بالاسم + فلتر وردية/بلا وردية + فلتر مربوط/غير مربوط بشاحنة + عمودا "الوردية" و"الشاحنة" (join حي مع `recycle.driver.assignment`). المدير يرى سائقي مستودعه فقط (record rule) — فُحصت الفلاتر وظيفياً (بحث Ahmad=1، unlinked=2...).

### ج) إسناد سائق ↔ شاحنة (الدورة الكاملة)
- **موديلات**: `recycle.driver.request.shift_id` (وردية onboarding تصل من الباك إند كـ `shift_odoo_id` وتُحل في create/upsert) · قيد `unique(truck_id, shift_id)` على الإسناد · `get_assignment_options(shift, warehouse?)` و`action_assign_driver(driver, truck, shift)` على `recycle.driver.assignment` مع `_assignment_actor_scope()` (أدمن كامل/مدير مقيد بمستودعه/غيرهما مرفوض؛ **env.su bypass** لفخ superuser المعروف).
- **القواعد المفروضة سيرفرياً**: الوردية أولاً (driver فقط) → الشاحنات الحرة **في تلك الوردية** (الحجز per-shift) → سائقو تلك الوردية **بلا شاحنة في أي وردية** · تطابق وردية السائق إلزامي · لا double-booking لنفس (شاحنة، وردية).
- **الواجهة** (أدمن بفلتر مستودع اختياري + مدير بلا فلتر): اختيار وردية → كروت شاحنات (تمييز أخضر للمختارة) → منتقي سائق → إسناد؛ رسالة **"All trucks are reserved for this shift / كل السيارات محجوزة"** عند نفادها. بند نافبار جديد "Assign Driver to Truck" للأدمن، وقسم Trucks للمدير صار ثلاثي: **Truck Management / Drivers / Assign Driver to Truck**.
- **صلاحيات**: ACL قراءة للمدير على `recycle.driver.request` + record rules (أدمن الكل؛ المدير: **accepted + مستودعه فقط** مع حارس `warehouse_id != False` كي لا تتسرب الطلبات المعلقة) — مثبت بـ `with_user(المدير الفعلي)`.
- خلل منطقي اكتُشف وأُصلح أثناء التحقق البصري: رسالة نجاح الإسناد كانت تُمسح فوراً لأن `_loadAssignOptions()` يصفّر الرسائل — صار الضبط بعد إعادة التحميل.

### د) الجانب الآخر (NestJS — تفاصيل بـ FIXES.md جولة 2026-07-20)
حذف كل راوتات طلبات تغيير الوردية (الإسناد صار بأودو) · دفع طلب السائق يشمل `shiftOdooId` · إحصائيات drivers جديدة + trucks. تأكيد بنيوي: لا راوت إضافة/تعديل وردية ولا إضافة شاحنة ولا عرض طلبات سائقين بالباك إند.

### التحقق (كله فعلي)
- ترقية الموديول 0 أخطاء (مرتين) + إعادة تشغيل + **12/12 اختبار أودو** + **15/15 فحص شل** لدورة الإسناد وقيودها + فحص صيغ (py/xml/js) لكل الملفات المعدلة.
- **تحقق بصري كامل بالمتصفح لثلاثة أدوار** (أدمن/مدير حقيقي/موظف إخراج): الدرج y=0 بكل المقاسات، Active يعمل، الفلاتر تعمل، دورة إسناد كاملة من واجهتي الأدمن والمدير (أحمد→شاحنة1 من الأدمن ظهر فوراً بشاشة المدير، خالد→شاحنة2 من المدير حتى ظهرت رسالة "كل السيارات محجوزة")، الحزمة المُقدَّمة تحوي قواعد hover الجديدة.
- بيانات ZDEMO أنشئت للفحص **ونُظفت بالكامل** (0 متبقٍ).
- باك إند: `tsc` نظيف + **148/148 اختبار** (23 suites — الفارق عن 154 = اختبارات خدمة طلبات تغيير الوردية المحذوفة عمداً).

**ملاحظات تشغيلية**: كلمة مرور admin أعيدت للقيمة الموثقة `admin` (كانت مغيّرة) · كلمتا مرور مؤقتتان `Test12345!` وُضعتا لـ `abdalaalwan100@gmail.com` (مدير دمشق) و`abodealwan32@gmail.com` (إخراج) للفحص — **غيّرهما** · التحقق البصري تم بفتح `http://localhost:8069` مباشرة (الحاوية شغالة) بدل launch.json.

---

## جلسة 2026-07-21 — دورة طلب تغيير الوردية (قرار المدير) + حظر/تعطيل + مشاكل الشاحنة + my-truck + PDF السائق

**السيناريو الكامل نُفِّذ على المشروعين معاً ومُثبت (اختبارات + متصفح).**

### أ) طلب تغيير الوردية (السائق ← المدير)
- **الباك ايند** (`shift-change-requests` v2): السائق **الفعّال** الذي **يملك شاحنة** يطلب الانتقال لوردية سائقين أخرى **من مستودعه** (ليست الحالية) مع **سبب إلزامي**؛ راوتات: `POST /` (بكل الشروط) · `GET /mine` (الأحدث أولاً) · `GET /available-shifts` · `DELETE /:id` (قيد الانتظار فقط → يحذف من النظامين). لا يستطيع حذف حسابه. الدفع فوري عبر الطابور لأودو.
- **أودو** `recycle.shift.change.request` (حالات pending/processing/accepted/rejected): شاشة المدير في نافبار **Trucks → Shift Change Requests** (فلترة الحالات، الأحدث أولاً). pending → **بدء المعالجة**؛ processing → **تغيير وردية** (يعرض شاحنات مستودعه **غير المحجوزة بتلك الوردية وغير المعطلة**، يختار شاحنة → موافقة → الإسناد ينتقل لـ (تلك الشاحنة، تلك الوردية)) أو **رفض** بسبب. كل انتقال **صارم**: يُرسل للباك ايند أولاً، فشلٌ = UserError ولا يُحفظ شيء (مُثبت بالمتصفح: الباك ايند مطفأ → رسالة حمراء والطلب بقي pending). إشعار السائق عند القبول/الرفض عبر الباك ايند.
- webhook `shift-change-decision` وسّع لـ `{status: PROCESSING|ACCEPTED(+truck_odoo_id)|REJECTED}` والمعالج يحرّك حالة الطلب وينقل الإسناد (المرآة) فوراً.

### ب) حظر/فك حظر + تعطيل شاحنة
- `recycle.driver.request.action_block/action_unblock` (أدمن + مدير مستودعه): يرسل BLOCKED/ACTIVE للباك ايند (صارم) + `is_blocked/blocked_reason` بأودو. **الباك ايند عند BLOCKED يمسح refresh+fcm لكل أجهزة السائق** → تسجيل خروج فوري، ومعالِج حالة BLOCKED يمنع الدخول حتى الرفع. **نفس المنطق لأي حساب** (مواطن/مؤسسة/معمل/جهة حرة) يحظره أدمن الباك ايند (`blockStatus` صار يمسح الأجهزة).
- **تعطيل الشاحنة (مدير)**: `action_toggle_service_state(reason)` — التعطيل **يتطلب سبباً** (مودال)، إعادة التشغيل تمسحه؛ يظهر السبب عند الأدمن في قائمة الشاحنات. الشاحنات المعطلة **لا تظهر في أي منتقي إسناد** (`get_shift_free_trucks`/خيارات الإسناد تفلتر `is_active=True`).

### ج) شاشات السائقين
- **الأدمن** Trucks → Drivers: كرت تفاصيل السائق (تغيير مستودع — يعالج الإسناد المتعارض + **تصدير PDF** عبر تقرير `action_report_driver`، مُثبت برندرة PDF فعلية 36KB) + حظر/فك حظر.
- **المدير** Trucks → Drivers: كرت تفاصيل السائق (حظر/فك حظر + **تغيير وردية**: يختار وردية → شاحنات مستودعه الحرة بتلك الوردية → نقل، ينعكس على النظامين) — مُثبت بالمتصفح (المودال، منتقي الوردية، ظهور الشاحنات الحرة).
- كروت **الشاحنات والسائقين** بشاشة تفاصيل المستودع (أدمن) صارت **كروت تنقل بنفس تصميم الشحنات/الطلبات** + كرتا إحصاء (عدد الشاحنات/السائقين) — مُثبت (Trucks:2 / Drivers:1، الكرتان يفتحان القوائم المنطاقة).

### د) my-truck + مشاكل الشاحنة + النافبار الليلي
- `GET /driver/my-truck`: يرجّع الشاحنة + **مستودعها (id + odoo id + اسم)** + الوردية بأوقاتها؛ وإن لا شاحنة → رسالة **"سيتم إسنادك لسيارة قريباً"**. وإشعار قبول السائق صار "تم قبول طلبك وسوف يتم إسنادك لسيارة قريباً".
- **مشاكل الشاحنة**: `POST /truck-problems` (سبب إلزامي + صور اختيارية عبر Cloudinary) → `recycle.truck.problem` بأودو (بنطاق المستودع) → شاشة المدير **Trucks → Truck Problems** **للقراءة فقط** (مُثبت: لا أزرار إجراء، تظهر الصورة).
- **فجوة النافبار بالوضع الليلي**: النافبار الأفقي كان يستخدم `--ra-glass` (شفافية 0.55) فيتسرب تدرّج الـHero ويبدو منفصلاً عن السايدبار؛ ثُبّت لأدمن/مدير الوضع الليلي على `rgba(15,23,42,0.96)` فصار سطحاً داكناً متصلاً واحداً (مُثبت بصرياً قبل/بعد).

### التحقق (كله فعلي)
- **الباك ايند**: `tsc` نظيف · **148/148 اختبار (23 suite)** · هجرة `1784500000000` نُفّذت (shifts.odoo_warehouse_id, collector_profiles.warehouse_id, shift_change_requests.reason + truck_id nullable, جدول truck_problems).
- **أودو**: ترقية 0 أخطاء · **12/12 اختبار** · **16/16 فحص شل** لدورة الطلب (إنشاء/معالجة/قبول-بنقل-الإسناد/رفض/إلغاء-idempotent/حظر/تغيير-مستودع/تعطيل-بسبب/مشكلة-شاحنة) · تقرير PDF السائق يرندر 36KB صالح · تحقق بصري بالمتصفح (مدير + أدمن): شاشات الطلبات/المشاكل/تفاصيل السائق + الصرامة + كروت أسطول المستودع + النافبار الليلي.
- بيانات ZDEMO أُنشئت للفحص ونُظّفت بالكامل (0 متبقٍ).

**ملاحظة تشغيلية**: كلمتا المرور المؤقتتان `Test12345!` لا تزالان على حسابَي مدير دمشق والموظف — غيّرهما. الدورة الحيّة الوحيدة التي تحتاج NestJS شغّالاً معاً هي إشعارات السائق الفعلية (الصرامة نفسها مُثبتة بأن الباك ايند المطفأ يمنع الحفظ).

---

## جلسة 2026-07-22 — استلام/تسليم السيارة (Handover) + حضور السائقين + إشعارات الوردية

**ميزة استلام/تسليم الشاحنة بأزرار بسيطة (بلا QR ولا إحداثيات) — منفّذة على النظامين ومُثبتة.**

### أ) الباك ايند (NestJS)
- كيان `truck_handovers` (جلسة حيازة لكل سائق/وردية/يوم): pickedUpAt, droppedOffAt, dropoffReason, lateDropoffMinutes, status (open/closed/missed_pickup)، + حارسا إشعار (missed/late) بصف فريد (driver, shift, workDate). هجرة `1784600000000` + عمود `tolerance` على `shifts` (مرآة من أودو عبر `fetchShifts`+`syncFleet`).
- `HandoverService` + راوتات COLLECTOR: `POST /driver/pickup` · `POST /driver/dropoff` (سبب إلزامي) · `GET /driver/handover-status`. القيود: **استلام** من بداية الوردية فقط (لا قبلها، ولا بعد نهايتها)، الحساب مقبول وغير محظور، مُسنَد لشاحنة، الشاحنة **غير معطّلة** وغير محجوزة بيد سائق آخر لم يُسلّمها؛ **تسليم** بعد نهاية الوردية فقط — **إلا إذا الشاحنة معطّلة فبأي وقت** — مع حساب التأخير من هامش الوردية. كل حدث يُدفع لأودو عبر الطابور (`PUSH_HANDOVER_PICKUP/DROPOFF`).
- **كرون** (`HandoverCronService` بالـ worker، كل 5د): بدء الوردية + الهامش بلا استلام → **إشعار السائق (FCM) + إشعار المدير (أودو)**؛ نهاية الوردية + الهامش وما يزال ماسكاً → إشعار الطرفين **مع دقائق التأخير**. مرة واحدة لكل حدث (حارس على صف الحيازة). مفاتيح i18n جديدة `handoverMissedPickup`/`handoverLateDropoff` (ar/en).

### ب) أودو
- موديل `recycle.truck.handover` (مرآة): create على الاستلام (يحل *_odoo_id) · `backend_close` على التسليم (idempotent) · `backend_alert_manager` يُنشئ إشعار مدير المستودع للتنبيهات (السائق يُشعَر بالـ FCM من الباك ايند). + ACL و record rules (المدير يرى مستودعه فقط).
- شاشة **"حضور السائقين"** تحت **الورديات** (أدمن + مدير) بجانب "حضور" الموظفين — **عرض فقط** (لا تسجيل دخول/خروج): سائق/شاحنة/وردية/تاريخ/وقت الاستلام/وقت التسليم/الحالة/التأخير + ملاحظة التسليم.
- **مشاكل الشاحنة** صارت **تُشعِر مدير المستودع** عند كل بلاغ جديد (كان ينقصها).

### التحقق (كله فعلي)
- الباك ايند: `tsc` نظيف · **148/148 اختبار** + سبك جديد `handover.service.spec` **6/6** (استلام قبل الوردية مرفوض، استلام شاحنة معطّلة مرفوض، إنشاء OPEN، سبب التسليم إلزامي، تسليم قبل النهاية مرفوض، المعطّلة تُسلَّم بأي وقت — بساعة مثبّتة). هجرة `1784600000000` نُفّذت.
- أودو: ترقية 0 أخطاء · **12/12 اختبار** · **5/5 فحص شل** (مرآة الاستلام+حل المعرّفات، إغلاق التسليم بالملاحظة والتأخير، idempotency، إشعار المدير للـ missed/late، إشعار مشكلة الشاحنة) · **تحقق بصري**: شاشة "حضور السائقين" عند المدير تحت الورديات بجانب "حضور" الموظفين، عرض فقط، بالبيانات الصحيحة.
- بيانات ZDEMO أُنشئت للفحص ونُظّفت بالكامل.

**ملاحظة**: الدورة الحيّة الوحيدة التي تحتاج NestJS شغّالاً هي ضغط السائق للأزرار فعلياً على الجوال وإشعارات FCM؛ منطق القيود والمزامنة والإشعارات مُثبت باختبارات الوحدة + شل أودو + المتصفح.

---

## جلسة 2026-07-24 — نطاق الورديات (عامة/خاصة) + وصل الشريط الجانبي بالنافبار

**ميزة نطاق الوردية على النظامين + قاعدة الوقت الجديدة + إصلاح CSS — منفّذة ومُثبتة.**

### أ) أودو — موديل الوردية (`models/shift.py`)
- حقول جديدة: `is_global` (Boolean, مفهرس) + `warehouse_ids` (Many2many عبر `recycle_shift_warehouse_rel`)؛ الحقل القديم `warehouse_id` بقي **خامداً** للهجرة فقط.
- `_normalize_scope`: اختيار **كل** المستودعات في وردية خاصة → تُرقّى تلقائياً إلى **عامة** (بلا مستودعات).
- قيد `_check_scope`: العامة بلا مستودعات، والخاصة تتطلب مستودعاً واحداً على الأقل.
- قيد `_check_no_duplicate_times`: يُمنع **فقط** تطابق (البداية والنهاية معاً) لورديتين من نفس النوع **إذا تشاركتا الجمهور** (عامة، أو تشترك بمستودع)؛ **التداخل الجزئي مسموح**.
- `write`: العامة **لا يمكن** أن تصير خاصة أبداً (UserError)؛ الخاصة يمكن ترقيتها لعامة. `create`/`write` يستدعيان `_normalize_scope` (محمي بـ context `_shift_norm`).
- هجرة `migrations/19.0.1.23.0/post-migrate.py`: `is_global = (warehouse_id IS NULL)` + تعبئة جدول الربط من `warehouse_id` القديم. (نُفّذت: الورديات 1,2,18 كلها خاصة بمستودع 1.)
- عرض أودو الأصلي `views/shift_views.xml` حُدّث لـ `is_global` + `warehouse_ids` (many2many_tags، يختفي عند العامة).

### ب) أودو — نموذج الأدمن (`recycle_admin_dashboard.js` + `dashboard_admin.xml` + `recycle_home.css`)
- الإنشاء: اختيار نطاق (عامة/خاصة) بالراديو + **قائمة مستودعات متعددة (checkboxes)** تظهر للخاصة فقط. حُذف اختيار المستودع المفرد ومنتقي الموظفين من النموذج (تبسيط — إسناد الموظفين يبقى من نموذج الموظف).
- التعديل: الوردية **العامة** تُظهر شارة "عامة" مقفلة (اسم/وقت/هامش فقط)؛ الوردية **الخاصة** تُظهر تبديل مستودعاتها + خيار "تحويل إلى عامة" (بلا رجعة). `shiftWasGlobal` يحرس القاعدة.
- قائمة الورديات: عمود **Scope** (شارة "عامة" أو عدد المستودعات) في الجدول وبطاقة الجوال.
- CSS جديد: `.o_ra_scope_options/.o_ra_scope_opt/.o_ra_wh_checklist/.o_ra_wh_check/.o_ra_badge_global` بدعم دارك/لايت.

### ج) الباك ايند (NestJS)
- كيان `Shift`: `isGlobal` + `odooWarehouseIds` (int[])؛ `odooWarehouseId` المفرد بقي خامداً. هجرة `1784700000000` (تعبئة من العمود القديم — نُفّذت).
- `odoo.service.fetchShifts` يقرأ `is_global`+`warehouse_ids`؛ `odoo-sync.processor.syncFleet` يعبّئ `isGlobal`+`odooWarehouseIds`.
- **Onboarding** (`GET /shifts` + `getDriverShiftOrThrow`): يعرض/يقبل **الورديات السائق العامة فقط** (السائق غير المقبول بلا مستودع).
- **تغيير الوردية** (`availableShifts`+`create`): مسموح إذا `isGlobal` **أو** مستودع السائق ضمن `odooWarehouseIds`.

### التحقق (كله فعلي)
- أودو: ترقية 0 أخطاء (v19.0.1.23.0) · post-migrate نُفّذت وتحقّقت (جدول الربط + is_global) · **11/11 فحص شل** (عامة بلا مستودعات، خاصة، ترقية "كل المستودعات"→عامة، رفض تطابق الوقت بنفس الجمهور، السماح بنفس الوقت لمستودع مختلف، السماح بالتداخل الجزئي، منع عامة→خاصة، السماح خاصة→عامة، رفض خاصة بلا مستودع). بيانات الفحص مؤقتة ورُوجعت بالكامل (0 تسريب ZZ).
- الباك ايند: `tsc` نظيف · **154/154 اختبار** · هجرة `1784700000000` نُفّذت.
- **بصري**: تعذّر التقاط لقطة (لوحة المتصفح غير معروضة في الجلسة)؛ تغيير الـ CSS تعديل تخطيط بحت (padding-top للجذر = ارتفاع النافبار 52px، والفراغ نُقل داخل عمود main فقط) مستقل عن الثيم → يصل الشريط الجانبي بالنافبار في الوضعين.

**ملاحظة**: الوردية السائق الوحيدة الحالية (18 "الوردية الصباحية") خاصة بمستودع 1 بعد الهجرة، لذا لن تظهر في onboarding حتى يحوّلها الأدمن إلى **عامة** — سلوك مقصود.

---

## جلسة 2026-07-24 (تكملة) — راوتات ورديات السائق + متانة الربط + تكرار طبق الأصل + مرآة السائقين فقط

### أ) باك ايند — راوتان جديدان للسائق (وحذف القديم)
- **حُذف** `GET /api/v1/shifts` القديم (كان فيه مشكلة).
- **`GET /api/v1/shifts/onboarding`**: الحساب `PENDING_PROFILE` + دور `COLLECTOR` → **الورديات العامة فقط**. الـ id يُستخدم في `POST /onboarding/collector/information`.
- **`GET /api/v1/shifts/home`**: الحساب `ACTIVE` + `COLLECTOR` → **العامة + الخاصة بمستودعه فقط**. الـ id يُستخدم في `POST /shift-change-requests`.
- ملفات: `shift.controller.ts` (حُرّاس per-route: Jwt+AccountStatus+Roles)، `shift.service.ts` (`listOnboardingShifts`/`listHomeShifts` + حقن `CollectorProfile`)، `shift.exceptions.ts` (`DriverProfileNotFoundException`)، `shift.module.ts`. تحقق: 401 بلا توكن، 404 للقديم، الراوتان مُعرّفان.

### ب) متانة الربط أودو↔باك ايند (السبب الجذري لاختفاء الورديات)
كانت 3 أعطال متراكبة: (1) بارامترا أودو `backend_base_url`/`backend_webhook_secret` غير مضبوطين → الجرس ما انبعت أبداً؛ (2) `ODOO_WEBHOOK_SECRET` ناقص من `.env` → الرد 503؛ (3) **`invalid input syntax for type time: "8"`** — أودو يخزن الوقت Float بينما العمود `time` → كل مزامنة تموت.
- **الحل (3 طبقات)**: الجرس الفوري (POST /odoo/webhooks/fleet) + **كرون تسوية كل 10د** (`fleet-reconcile.service.ts`, `@Cron EVERY_10_MINUTES`) + **مزامنة عند الإقلاع** (`OnModuleInit`). `enqueueSyncFleetReconcile()` بـ jobId مقسّم على الدقيقة فالمشغّلات المتزامنة تنهار على مهمة واحدة. `syncFleet` قراءة كاملة idempotent فأي فجوة تُغلق خلال دورة.
- **محوّل الوقت** `odooFloatToTime()` (8→08:00, 17.0333→17:02، تقريب للدقيقة، 0 صالحة).
- ضُبط بارامترا أودو + `ODOO_WEBHOOK_SECRET` (64 حرف). **إثبات حي**: أضفت وردية بأودو → ظهرت بالمرآة خلال ثوانٍ؛ حذفتها → انمسحت؛ 202 بالسرّ الصحيح و403 بالخطأ.

### ج) المرآة ورديات السائقين فقط
- `fetchShifts` صار بدومين `[('shift_type','=','driver')]` — ورديات موظفي المستودع ما تنعكس بالباك ايند. حلقة الإلغاء بـ syncFleet نظّفت ورديات الموظفين المنعكسة سابقاً تلقائياً.
- `shift-seed.ts` تحوّل من زرع Morning/Evening إلى **تنظيف** أي وردية يتيمة (odooShiftId=NULL) بلا مراجع — وحُذفت الصفوف الوهمية من DB.

### د) أودو — قاعدة التكرار = طبق الأصل
- `_check_no_duplicate_times` صار يرفض فقط **النسخة المطابقة تماماً** (نفس الاسم + البداية + النهاية + النوع + الهامش). أي اختلاف بحقل واحد (اسم مختلف بنفس الوقت، هامش مختلف…) **مسموح**. تحقق: **5/5 فحص شل**.

### هـ) Postman
- حُذف `GET /shifts` القديم، وأُضيف `GET /shifts/onboarding` و`GET /shifts/home` بوصف عربي كامل (JSON صالح).

### و) CSS — الشريط الجانبي بطول الصفحة كامل
- `.o_ra_has_unified_nav.o_recycle_home_dashboard { height:100vh; min-height:100vh; overflow:hidden }` + `.o_ra_sidebar { min-height:100%; align-self:stretch }` — يمنع انكماش الجذر لارتفاع المحتوى فيمتد الشريط من أسفل النافبار لأسفل الشاشة بلا فراغ. **لم يُتحقّق بصرياً** (الجلسة الحالية بالمتصفح ليست أدمن ولقطات الشاشة معطّلة في البيئة) — بحاجة تأكيد بصري من المستخدم.

### التحقق
- الباك ايند: `tsc` نظيف · **154/154 اختبار** · الراوتات مُعرّفة والحُرّاس فعّالة. أودو: ترقية سابقة + **5/5 فحص تكرار شل**. المرآة: 5 ورديات سائقين فقط، أوقاتها محوّلة صحيحة.

---

## جلسة 2026-07-24 (تكملة 2) — CSS شريط جانبي عام + إعادة تسمية راوت + حذف seed + دمج الحضور + نطاق المستودع

### 1) CSS — الشريط الجانبي بطول الشاشة (عام، كل الداشبوردات)
- **السبب الجذري** (فحص Dev-Tools/كود): عائلتان من القوالب — `.o_recycle_home_dashboard.o_recycle_admin_theme` (أدمن/مدير/Home → `.o_ra_sidebar`) كانت `height:100%` فتنكمش لارتفاع المحتوى؛ و`.tw-dashboard` (فرز/إخراج → `.tw-sidebar`) كانت `100vh` سليمة. الإصلاح السابق كان مقيّداً بـ `o_ra_has_unified_nav` (شاشة Home فقط) و`.o_ra_sidebar` فقط.
- **الإصلاح العام** (`recycle_home.css`): `@media (min-width:901px) and (min-height:501px)` → الجذران `100vh` + `min-height:100vh` + `overflow:hidden`، و`.o_ra_sidebar, .tw-sidebar { min-height:100%; align-self:stretch }`. يغطي كل الصفحات وكل الأدوار، لايت+دارك. (ديسكتوب فقط؛ الموبايل درج ثابت بطول كامل أصلاً.)

### 2) باك ايند — إعادة تسمية `/shifts/home` → `/shifts/available` + استثناء الوردية الحالية
- الاسم يعكس الغرض (الورديات المتاحة للتبديل). نفس الحارس (Jwt+AccountStatus ACTIVE+Roles COLLECTOR) ونفس المنطق (عامة + مستودعه) **+ استثناء `profile.shiftId`** (لا يعرض ورديته الحالية). حُدّث Postman. تحقق: القديم 404، الجديد 401، **154/154 اختبار**.

### 3) باك ايند — حذف seed الورديات نهائياً
- حُذف `seedShifts` من `run-seed.ts` و**حُذف الملف** `db/seeds/shift-seed.ts`. أودو المصدر الوحيد. DB: 0 وردية بـ odoo_shift_id=NULL (كلها 5 لها id حقيقي).

### 4) أودو — دمج الحضور بخيار واحد (أدمن + مدير)
- الشريط الجانبي صار يدعم **مستوى ثالث** (`subitems`): "الحضور" يفتح [حضور السائقين، حضور موظفي المستودع] بنفس التصميم. (JS: `navSubItem`+`toggleNavSubItem`؛ XML: كتلة subitems؛ CSS: `o_ra_sb_subitems/subitem/subchev`.)
- **الفلاتر**: أضيف لحضور السائقين فلتر **مستودع + تاريخ** عند الأدمن (مطابق لحضور الموظفين)، و**تاريخ فقط** عند المدير (مستودعه تلقائي).

### 5) أودو — نطاق المستودع للأدمن (المهمة الإضافية)
- كان `openWarehouseEmployees` يضبط `warehouseScope` (يخفي فلتر المستودع + ملاحظة "Showing items for")، لكن `openWarehouseTrucks/Drivers` لا. أُصلح: الاثنان يضبطان `warehouseScope`، وقوائم الشاحنات/السائقين تخفي فلتر المستودع تحت النطاق + ملاحظة. `navClick` يصفّر truckWHFilter/driverWHFilter أيضاً.

### التحقق
- الباك ايند: `tsc` نظيف · **154/154** · الراوت 401/404 حي. أودو: XML الملفين well-formed (python الحاوية)، JS `node --check` نظيف، CSS متوازن.
- ⚠️ **لم يُتحقّق بصرياً من واجهات أودو** — الويب-كلاينت OWL لا يُركَّب إطلاقاً في متصفح البيئة (حتى /odoo يظهر بلا نافبار/تطبيقات). كل تغييرات أودو تتبع أنماطاً قائمة ومثبتة ومُتحقّق منها نحوياً — **بحاجة تأكيد بصري من المستخدم**.

---

## جلسة 2026-07-24 (تكملة 3) — توحيد لون الشريط الجانبي + تحسين شاشات الحضور

### 1) لون الشريط الجانبي = لون الواجهة (كل الداشبوردات، الوضعين)
- كل خلفيات الشريط الجانبي صارت `var(--ra-bg)` (نفس خلفية المحتوى) بدل التدرّج الداكن/الأبيض — فالشريط والمحتوى يقرأان كسطح واحد موحّد، يفصلهما خط رفيع فقط.
- شمل العائلتين: `.o_ra_sidebar` (أدمن/مدير/Home — base + light + darkَي 8074/12611) و`.tw-sidebar` (فرز/إخراج — base + light). لايت=`#f8fafc`، دارك=`#0F172A` تلقائياً عبر المتغير.

### 2) شاشات الحضور
- **العنوان**: "الحضور" لشاشة الموظفين صارت **"حضور موظفي المستودع" / Warehouse Staff Attendance** (ترجمة جديدة بـ recycle_i18n_shared) — أدمن + مدير.
- **حضور السائقين بنفس تصميم حضور الموظفين**: أضيفت كروت ملخّص (حاضر/متأخر/لم يستلم/الإجمالي) — بالأدمن بنفس الكروت الملوّنة (أخضر/أحمر/عنبري/نيلي)، وبالمدير بنمط insight cards المطابق لحضور موظفيه. المقاييس للسائق: حاضر=استلم، متأخر=تأخّر تسليم، لم يستلم=missed_pickup، الإجمالي.
- **الفلتر حسب المستودع = قائمة منسدلة** (select) بدل الأزرار جنب بعض — في **حضور الموظفين وحضور السائقين عند الأدمن**. عُدّل `setAttendanceWHFilter`/`setDriverAttWHFilter` ليقرآ قيمة الـ select. (المدير بلا فلتر مستودع — مستودعه تلقائي، تاريخ فقط.)

### التحقق
- XML الملفين well-formed (python الحاوية)، JS `node --check` نظيف للثلاثة، CSS الثلاثة متوازن الأقواس. أصول أودو مُفرَّغة + إعادة تشغيل.
- ⚠️ **لم يُتحقّق بصرياً** — ويب-كلاينت أودو لا يُركَّب في متصفح البيئة. كل التغييرات تتبع أنماطاً قائمة ومُتحقّقة نحوياً — بحاجة تأكيد بصري من المستخدم.

---

## جلسة 2026-07-24 (تكملة 4) — إصلاح ضياع طلب السائق عند انقطاع أودو (تسوية طلبات السائقين)

### التشخيص (فعلي)
- سائق `mohamad` حالته PENDING_APPROVAL بالباك ايند لكن **صفر** طلبات بأودو. السبب: دفع الطلب (backend→Odoo, PUSH_DRIVER_REQUEST) كان **fire-once** بـ 3 محاولات فقط (~15ث)؛ لو أودو غير متصل بتلك اللحظة → يُستنفد ويضيع بلا استرجاع (نفس ثغرة الأسطول بالاتجاه المعاكس). أُثبت أن مسار الدفع سليم بإعادة دفع يدوية → ظهر الطلب فوراً.

### الحل — كرون تسوية لطلبات السائقين
- `odoo-sync/driver-request-reconcile.service.ts` (جديد): `@Cron EVERY_10_MINUTES` + `OnModuleInit`. يجلب كوليكتورز PENDING_APPROVAL، يسأل أودو أي backend_driver_ids موجودة (`odoo.fetchDriverRequestKeys`)، ويعيد دفع **الناقصين فقط** عبر `enqueuePushDriverRequestReconcile` (jobId مقسّم على الدقيقة/الحساب لمنع التكدّس). idempotent لأن أودو upsert بـ backend_driver_id.
- `odoo.service.fetchDriverRequestKeys()` جديد. مُسجّل بـ odoo-sync.module.

### الاتجاه المعاكس (قرار أودو → باك ايند) — كان محلولاً أصلاً
- `driver_request.py::_send_decision` **صارم/ذرّي**: ينادي webhook الباك ايند أولاً، وإذا الباك ايند غير متصل **يرفع UserError ولا يحفظ التغيير بأودو**. فلا يمكن أن توجد حالة بأودو بلا مقابلها بالباك ايند — لا انحراف ممكن.

### التحقق (فعلي end-to-end)
- `tsc` نظيف. حذفت طلب أودو (محاكاة ضياع) → أعدت تشغيل الباك ايند → لوق `Re-pushed 1 missing driver request(s) to Odoo (startup)` → الطلب رجع بأودو (id 13, pending). صفر تكرار (تحقق: 1 طلب/1 سائق مميّز).

---

## جلسة 2026-07-24 (تكملة 5) — مراجعة طلبات السائقين + تدقيق التكامل الشامل + محافظات

### 1) طلبات السائقين: جدول + تفاصيل بكروت منفصلة
- **الباك ايند يدفع بيانات كاملة**: `national_id` · الموقع (**اسم المحافظة** محلولاً من الـ UUID — أودو ما عنده جدول محافظات) · `address` · `location_note` · `latitude/longitude` (من PostGIS `[lng,lat]`).
- **أودو**: حقول جديدة (national_id, province_name, address, location_note, latitude, longitude) + related للوردية (shift_name/start/end) + `has_rejected_image` محسوب. الترقية 19.0.1.24.0.
- **الواجهة**: جدول (اسم/إيميل/جوال/رقم وطني/حالة) بالديسكتوب + بطاقات بالجوال؛ النقر يفتح **شاشة تفاصيل بثلاث كروت مستقلة**: معلومات الحساب (مع الوردية واسمها ووقتيها) · الموقع (المحافظة/العنوان/الوصف/رابط خرائط) · الملفات. مودالات القرار نُقلت لقالب مشترك `DriverDecisionModals`.

### 2) إعادة التفعيل + قفل زر القبول
- `action_reactivate`: الطلب المرفوض يعود `pending` والحساب `PENDING_APPROVAL` (بنفس الويبهوك الصارم). أُضيف `PENDING_APPROVAL` لـ DTO الباك ايند **و** لرسائل الإشعارات (كان يقع على رسالة "مرفوض" الافتراضية — خلل أُصلح).
- **زر القبول يختفي** طالما في صورة مرفوضة (واجهة + حارس بالموديل)، ويعود تلقائياً بعد إعادة رفع السائق (re-push يستبدل الصور ويعيد pending). **4/4 فحص شل**.

### 3) تدقيق التكامل الشامل + إصلاح الثغرات
- **ثغرة idempotency حرجة**: `create()` لـ shift.change.request / truck.problem / truck.handover **ما كانت upsert** — أي إعادة دفع كانت ترفع خطأ القيد الفريد، فالسجل الضائع **غير قابل للاسترجاع**. صارت الثلاثة **UPSERT بمفتاح الباك ايند**. **7/7 فحص شل** (لا تكرار، نفس الصف، تحديث البيانات).
- **`push-reconcile.service.ts` جديد**: كرون كل 10د + عند الإقلاع، يعيد دفع أي صف `odoo*Id IS NULL` أقدم من مهلة سماح 5 دقائق (حتى ما يسابق مهمة قيد التنفيذ)، بحد 50 صف/دورة. يغطي: طلبات تغيير الوردية · مشاكل الشاحنة · الحيازة (استلام + تسليم).
- **إشعار المدير مرة واحدة**: `truck.problem` يميّز الصفوف الجديدة فعلاً عن إعادة الدفع فلا يُشعَر المدير مرتين.

### 4) راوتات المحافظات (أدمن فقط)
`POST /api/v1/admin/provinces` · `PATCH /:id` · `DELETE /:id` — بحماية `JwtAuthGuard + RolesGuard + @Roles(ADMIN)`. منع التكرار (409)، منع حذف محافظة مستخدَمة (409 عبر التقاط FK — لا سباق)، 404 لغير الموجود.

### التحقق (فعلي)
- أودو: ترقية 0 أخطاء · **4/4** فحص قفل القبول · **7/7** فحص idempotency.
- الباك ايند: `tsc` نظيف · **154/154 اختبار** · دفع حي أثبت امتلاء الحقول (`دمشق`, `74123569874`, الوردية 08–18).
- **إثبات التسوية end-to-end**: أدخلت صف مشكلة شاحنة بلا `odoo_problem_id` ومؤرَّخ قبل 30 دقيقة → إعادة تشغيل الباك ايند → لوق `Re-pushed 1 record(s) missing in Odoo (startup) — truck-problems: 1` → الصف أخذ `odoo_problem_id=5` وظهر بأودو. نُظّف الطرفان.
- محافظات: create 201 · duplicate 409 · update 200 · delete 200 · delete-in-use 409 · 404 · بلا توكن 401.

---

## جلسة 2026-07-25 (تكملة) — إغلاق المستودع + شاشة الإدارة + تعديل المواد

### 1) سيناريو إغلاق المستودع (v19.0.1.24.0)
- حقل `state` على `recycle.warehouse`: **active / closing / inactive** (+ `closing_started_at`, `closed_at`) مع `tracking=True` (mail.thread موجود أصلاً فكل انتقال يُوثَّق تلقائياً).
- `action_start_closing` (**أدمن فقط**): يرفض البدء إن كانت هناك شحنات **قيد المعالجة** (كل ما ليس `sorted`/`rejected`)، ثم:
  - `_release_employees_on_closing`: يسجّل `assignment_end` بسجل `recycle.employee.history` ويفكّ `recycle_warehouse_id` — **الموظف يبقى نشطاً ويحتفظ بدوره**، والتعيين الجديد قرار يدوي.
  - `_release_trucks_on_closing`: الشاحنة غير المستلمة → تُفرَّغ فوراً؛ **المستلمة (handover مفتوح) تبقى مسنَدة** لأن السائق مسؤول عنها فعلياً، ويُنبَّه الأدمن، وتُحرَّر تلقائياً لحظة التسليم عبر `_unassign_if_warehouse_closing` المربوط بـ `backend_close`.
- `action_finalize_inactive`: من `closing` فقط، ويرفض إن بقي أي `recycle.stock` بكمية > 0 → `state=inactive` + `active=False` (أرشفة، لا حذف).
- `action_reopen`: تراجع عن إغلاق بُدئ بالخطأ (من `closing` فقط).
- `unlink` **ممنوع نهائياً** — الحذف يُلغى والتاريخ محفوظ.
- **الاستثناء من التخصيص**: `inactive` يختفي تلقائياً من كل `search` (لأن `active=False`)، و`closing` استُثني بإضافة `[['state','=','active']]` إلى **15** استعلام اختيار مستودع بداشبورد الأدمن (شبكة المستودعات تحتفظ باستعلامها فتبقى الموقوفة ظاهرة للإدارة).

### 2) شاشة "إدارة المستودع" مستقلة
- صارت **كرت/زر** ضمن شاشة المستودع يفتح شاشة `warehouse_manage` خاصة، مرتبطة تلقائياً بالمستودع المفتوح (**بلا اختيار مستودع**): بطاقة البيانات + بطاقة المناطق + بطاقة الإغلاق، والمودالات الثلاثة نُقلت معها. الأزرار تختفي تلقائياً حسب الحالة (لا تعديل/إضافة منطقة على مستودع مغلق).

### 3) تعديل المواد لكل رول يملكها
- `PATCH /onboarding/{institution|factory|external-partner}/materials` — PENDING_APPROVAL حصراً. DTO لكل نمط (مؤسسة=استجرار، معمل/جهة=طلب). استبدال التصنيفات يتحقق من **كل** المعرّفات أولاً فلا يمسح الاختيار السابق بمعرّف خاطئ. السائق بلا مواد → لا راوت ولا DTO (وحارس ثانٍ بالخدمة).

### 4) صور طلب السائق
- تظهر الآن **بكل الحالات** (معلّق/يحتاج تعديل/مقبول/مرفوض) مع شارة حالة لكل ملف، وحُصِّن العرض ضد `images` غير المعرّفة. الإجراء (رفض صورة) وحده مرتبط بالحالة — الدليل نفسه يبقى ظاهراً للسجل.

### التحقق
- أودو: ترقية 0 أخطاء · **11/11 فحص شل لدورة الإغلاق** (منع البدء مع شحنة قيد المعالجة، فكّ الموظف مع بقائه نشطاً، تفريغ الشاحنة الحرة، منع الإيقاف النهائي مع مخزون، الأرشفة، الاختفاء من قوائم الاختيار، منع الحذف) · **8/8 لإدارة المستودع** سابقاً · JS/XML صالحان.
- الباك ايند: `tsc` نظيف · **155/155 اختبار** · راوتات المواد الثلاثة + `GET/PATCH /admin/warehouses/:id`.
- ⚠️ لم يُتحقّق بصرياً (ويب-كلاينت أودو لا يُركَّب بمتصفح البيئة) — بحاجة تأكيد المستخدم.

---

## جلسة 2026-07-27 — جدول المحافظات + ربط الوحدات + شاشة الأسعار + نظافة الاستجابات (v19.0.1.27.0)

### 1) المحافظات صارت جدولاً حقيقياً بأودو بدل السيلكتور
- موديل جديد `recycle.province` (`backend_province_id` = uuid الباك ايند وهو **مفتاح المطابقة**، `name_en`, `name_ar`, `active`) + قيد فريد على المعرّف.
- `recycle.warehouse.governorate` (Selection) → **`province_id` (Many2one)**، و`governorate` بقي **حقلاً محسوباً مخزَّناً** يعكس اسم المحافظة، فكل القرّاء القدامى (dashboard_api، backend_sync، التقارير، JS) استمروا يعملون بلا تغيير.
- **حُذف المحوّل** `toOdooGovernorateKey` + `GOVERNORATE_KEYS` نهائياً من `odoo.service.ts`؛ الباك ايند صار يرسل الاسم كما هو (`province_name`) أو الـ uuid (`province_backend_id`) وأودو يحلّه بنفسه (`resolve_by_name` / `resolve_by_backend_id`) — واسم غير معروف يُرفض بوضوح بدل أن يُبتلع.
- **الهجرة** (`migrations/19.0.1.27.0`): pre-migrate يحفظ مفاتيح الـ Selection القديمة، post-migrate ينشئ صفوفاً مؤقتة `legacy:<key>` ويربط كل مستودع بها؛ ثم `backend_upsert` **يتبنّى** الصف المؤقت بالاسم عند أول دفعة حقيقية ويستبدل المفتاح بالـ uuid — فلا نسخة ثانية من "دمشق" ولا رابط مكسور.
- **المزامنة ثلاثية الطبقات** (نفس نمط الأسطول): وظيفة لكل صف (`SYNC_PROVINCE` / `DELETE_PROVINCE`) + مزامنة كاملة عند الإقلاع + كرون كل ساعة (`ProvinceReconcileService`, `SYNC_ALL_PROVINCES`) — فما ضاع وأودو مطفأ يعود وحده.
- **الحذف = أرشفة** بأودو لا حذفاً: مستودعات قديمة ما زالت تشير للمحافظة والتاريخ يجب أن يبقى.

### 2) وحدات القياس مربوطة بالباك ايند حصراً
- `recycle.product.uom_id`: `uom.uom` → **`recycle.measurement.unit`** (المرآة القادمة من الباك ايند)، ومعها الحقول المرتبطة المخزَّنة في `recycle.shipment.line` و`recycle.shipment.expected.line` و`recycle.stock.damage.report`.
- الهجرة تعيد تسمية العمود القديم، فيُنشئ أودو عموداً جديداً ويملؤه بالافتراضي (فيبقى NOT NULL ساري)، ثم post-migrate يعيد التخطيط بالاسم/الكود ويُسقط العمود القديم.
- `createProduct` صار يرسل **كود الوحدة** (`unit_code`) ويحلّه أودو — فلا تُعطى المادة وحدة لا يعرفها الباك ايند، وكود مجهول يُرفض.
- قائمة الوحدات في داشبورد الأدمن ومنيو الإعدادات تقرأ من المرآة (المؤرشفة لا تُعرض) → **تعديل أو حذف وحدة بالباك ايند ينعكس فوراً**.
- `dashboard_api` كان يقارن `uom_id.name == 'kg'` (اسم مترجَم) → صار يقارن الكود `KG`.

### 3) عرض الأسعار بدل عمودَي السعر
- حُذف عمودا "سعر المعامل" و"سعر الجهات الحرة" من جدول المواد (ومن بطاقة الموبايل)، وأضيف زر **"عرض الأسعار"** لكل مادة يفتح ورقة أسعارها: لكل فئة مشترٍ سعرٌ لكل حالة، **وإن لم يكن للمادة حالات يظهر السعر المباشر الذي أرسله الباك ايند**.
- `condition_code` صار اختيارياً بأودو (فارغ = لا حالات) مع `condition_name` محسوب يترجم الكود إلى اسم الحالة.
- الباك ايند كان **يُسقِط** سطر السعر بلا حالة (`.filter(r => r.conditionCode)`) فتبقى تلك المواد بلا سعر بأودو — أُزيل الفلتر، وصار `ConditionPriceDto.condition` اختيارياً مع منع الخلط (سعر مباشر + أسعار حالات لنفس الفئة مرفوض)، وتسعير السلة يتعامل مع السعر المباشر.
- زر "عرض الأسعار" أضيف أيضاً لواجهة أودو الأصلية (قائمة + استمارة المادة) مع تبويب أسعار.
- شاشات جديدة للقراءة فقط بمنيو الإعدادات: المحافظات، وحدات القياس، حالات المواد — الباك ايند هو المؤلّف الوحيد فالإنشاء/التعديل معطّل بدل إيهام المستخدم.

### 4) نظافة الاستجابات + تدقيق status code
- النمط `return { message: result.message, result }` كان يُكرّر الرسالة (مرة بالمغلّف ومرة داخل `data`) — أُصلح في **28 راوتاً** بإرجاع كائن الخدمة مباشرة، فالمغلّف يلتقط الرسالة و`data` يحمل الحمولة فقط. **المسارات داخل `data` لم تتغير**.
- تدقيق **181 راوتاً**: صُحِّحت 6 حالات — `POST /auth/refresh-token` → 200 (لا ينشئ مورداً، وبقية اللوغن 200)، `POST /admin/warehouses/:id/sync-manager` و`import-odoo` → 200، `POST /admin/warehouses/:id/sync-odoo` → **202** (يُدرَج بالطابور)، `POST /driver/dropoff` → 200 (يُغلق تسليماً قائماً)، `POST /admin/waste/products/:id/pricing` → 200 (استبدال قائمة أسعار موجودة). الباقي مطابق.

### التحقق
- أودو: ترقية بلا أخطاء + الهجرتان اشتغلتا · **28/28 فحص شل** (التبنّي، إعادة التسمية، الأرشفة، المزامنة الكاملة، حلّ الوحدة، ورقة الأسعار).
- حي بين النظامين: **12/12** لدورة المحافظة (إنشاء→تعديل→حذف) و**16/16** للوحدات والأسعار، مع إثبات أن حذف وحدة غير مستعملة يصل لأودو وأن المستعملة يرفضها الباك ايند.
- الهجرة الحقيقية: المستودع الموجود احتفظ بمحافظته، والصف المؤقت `legacy:damascus` تبنّاه الباك ايند وصار uuid حقيقي — **0 صفوف مؤقتة، 14 محافظة، بلا تكرار**.
- الباك ايند: `tsc` نظيف.
- ⚠️ لم يُتحقّق بصرياً من واجهات أودو (ويب-كلاينت أودو لا يُركَّب بمتصفح البيئة) — بحاجة تأكيد المستخدم.

### تخزين الملفات والصور بأودو (توصيف)
- كل مرفق يُسجَّل بجدول `ir_attachment` (الاسم، النوع، `res_model`/`res_id` أي لأي سجل يتبع، الحجم، `checksum`، `public`)، أما **المحتوى فيُكتب على القرص** لا بقاعدة البيانات.
- مسار المخزن: `data_dir/filestore/<اسم قاعدة البيانات>/` وهنا `/var/lib/odoo/filestore/odoo19/` داخل الحاوية، مربوط بـ docker volume باسم `odoo19-docker_odoo-web` (فالملفات تنجو من إعادة بناء الحاوية).
- التسمية **بالمحتوى**: الملف يُخزَّن باسم بصمته SHA1 داخل مجلد من أول محرفين — مثلاً `f8/f8de09133f0310eda63b5edd6b7c05581632bc5d` — والعمود `store_fname` بالجدول يشير إليه. نتيجتها: ملفان متطابقان يشغلان نسخة واحدة على القرص.
- `fields.Binary(attachment=True)` (مثل `recycle.stock.damage.report.image`) يمرّ بهذا المسار. أما `fields.Binary()` بلا `attachment` (مثل `barcode_image` بالويزرد) فيبقى base64 داخل عمود بالقاعدة — مناسب للمؤقت فقط.
- الحالة الفعلية الآن: `filestore/odoo19` ≈ 964MB، وملفات المتقدمين للتوظيف (`hr.applicant`) مخزَّنة هناك بـ `store_fname` و`db_datas` فارغ — أي على القرص لا بالقاعدة.

---
## جلسة 2026-07-28 — سيناريو الطلبيات: المرحلتان 0 و 1 (v19.0.1.28.0)

مرجع التصميم الكامل: [ORDER_FLOW_DESIGN.md](ORDER_FLOW_DESIGN.md)

### القرار المعماري المحوري
**`OrderPart` واحد بالباك ايند ⟷ `recycle.order` واحدة بأودو.**
لأن طلبية أودو مربوطة بمستودع واحد أصلاً (`warehouse_id` مطلوب)، فالطلبية المقسّمة على ٣ مستودعات = **٣ صفوف بأودو**، كلٌّ بمديرها وموظف إخراجها وفاتورتها — وتجتمع عند الزبون كطلبية واحدة. نتيجته المباشرة: **لا تغيير على بنية `recycle.order`** رغم أن التقسيم ميزة جديدة كلياً.

### المرحلة 0 — الأساس

**حجز المخزون — الحلقة المفقودة التي تجعل التوزيع صحيحاً:**
- `reserved_qty` + `available_qty` (محسوب ومخزَّن) على `recycle.stock`، و`_available_qty` صار يطرح المحجوز بدل أن يعيد الكمية الخام.
- `reserve_for_order` **الكل أو لا شيء**: حجز جزئي يحبس بضاعة لا تستطيع الطلبية استعمالها ويمنعها عمّن يستطيع.
- `release_for_order` لا يرمي خطأً عند تحرير مكرر، والرقم مقيَّد بالصفر من الأسفل.
- التحرير مربوط بدورة حياة الطلبية كاملة: **رفض المدير، الإلغاء، والخصم الفعلي** — وعلَم `stock_reserved` يضمن حدوثه **مرة واحدة بالضبط**.
- بدون هذه القطعة يبدو السيناريو سليماً ويفشل عند أول ضغط: مديران يوافقان على مخزون واحد، والعجز يظهر **بعد** أن وُعِد الزبون.

**فصل المنفِّذ عن المصادِق:** `action_finish` صار من صلاحية **المدير** لا موظف الإخراج. الموظف ينفّذ الحركة الفيزيائية، والمدير يشهد عليها. و`output_zone_id` + `finished_at` + الـ chatter + `recycle.order.zone.movement` هي السجل الزمني الذي طُلب.

**ثلاثة أعطال حقيقية في مرآة المخزون، كانت قائمة قبل اليوم:**
1. الباك ايند يقرأ `condition_code` بينما اسم الحقل بأودو `condition` → **كل صف كان يهبط تحت UNGRADED، وبُعد الحالة ضائع كلياً**.
2. يقرأ `reserved_quantity` بينما الحقل `reserved_qty` → العمود صفر دائماً.
3. أودو يخزّن صفاً لكل (مادة، حالة، **منطقة تخزين**)، والمرآة كانت تكتبها صفاً صفاً فيدهس الأخير سابقيه → **المرآة تُبلّغ جزءاً من المخزون الحقيقي**.
أُصلحت الثلاثة بالتجميع قبل الكتابة.

**ربط المحافظة والحالة:** `province_id` FK + `state` على `warehouses` بالباك ايند، مع حقل `province_backend_id` بأودو ينقل **uuid الباك ايند مباشرة** — فالربط بقراءة واحدة بلا أي مطابقة أسماء. والتوزيع لن يختار مستودعاً وضعه أودو في `closing`.

### المرحلة 1 — تعرفة التوصيل (**الأدمن في أودو هو المؤلّف** — قرار المستخدم)

- `recycle.delivery.tariff` بأودو: نطاق (مستودع / محافظة / عام) + رسم أساسي + سعر الكيلومتر + حدّ أدنى، مع قيدين صارمين: **لا تعرفتان لنفس النطاق**، و**لا نطاق بلا هدفه**.
- **مرآة للقراءة فقط** بالباك ايند (`delivery_tariffs`)، بنفس نمط الوحدات والمحافظات: نبضة بلا حمولة من أودو ← الباك ايند يعيد قراءة الجدول كاملاً. **استبدال كامل لا فرق**، فتعرفة حذفها الأدمن تختفي فعلاً بدل أن تبقى تسعّر بصمت.
- الأسبقية معبَّر عنها **كمفتاح ترتيب** (`SCOPE_SPECIFICITY`) لا كسلسلة شروط — إضافة نطاق لاحقاً = مدخل واحد بالخريطة.
- **لماذا مرآة لا استدعاء مباشر؟** سعر يراه الزبون قبل التزامه يجب ألّا يرتهن بتوفّر أودو تلك اللحظة. أودو يبقى المؤلّف الوحيد، والقراءة محلية.
- ثلاث طبقات كالمعتاد: نبضة حيّة + كرون كل ساعة + مزامنة عند الإقلاع.

### التحقق

- **16/16 فحص شل للحجز**، وأهمها الحالة الجوهرية: طلبية ثانية **تُرفَض** ولا تُمنح نفس المخزون؛ الرفض لا يترك حجزاً جزئياً؛ التحرير المكرر لا ينزل تحت الصفر؛ والحجز **لا يعبر الحالات** (طلبية `good` لا تمسّ مخزون `poor`).
- قيدا التعرفة مثبتان حياً: تكرار النطاق مرفوض، ونطاق بلا هدف مرفوض.
- **إثبات طبقة التسوية:** أنشأت التعرفات الثلاث بينما كان الباك ايند مطفأً، ففشلت النبضات الثلاث (`Connection refused`) — ثم عند الإقلاع: `Delivery tariffs mirrored: 3 kept, 0 removed`. النطاقات الثلاثة ارتبطت صحيحاً (المستودع بمعرّف أودو، والمحافظة بـ uuid الباك ايند).
- `tsc` نظيف، وهجرتان نُفّذتا بنجاح، والتعبئة الرجعية ربطت المستودع الذي يحمل محافظة.

### ملاحظة جانبية

مجلد `db/migartions` (خطأ إملائي في الاسم) يحوي هجرة مولّدة تلقائياً **لم تُنفَّذ قط**: `data-source.ts` لا يسجّل إلا `dist/db/migrations/*.js`، وجدول `migrations` يؤكد أنها غائبة. محتواها مجرد إعادة تسمية قيود إلى أسماء هاش، ومخرجها المترجم كان يُفشل كل `nest build` بـ `ENOTEMPTY`. **استُبعد من البناء فقط ولم يُحذف ملفك** — الحذف قرارك.

### الباقي من السيناريو (بالترتيب)

- **P2** كيانات الطلبية (`Order` / `OrderPart` / `OrderPartLine` / `OrderPartOffer`) + الحد الأدنى من قاعدة البيانات + آلة حالات معلَنة.
- **P3** المسافات (تصفية PostGIS → كاش → Google) + خوارزمية التوزيع كدالة نقية.
- **P4** العروض والموافقات وإعادة التوزيع + دفع الأجزاء لأودو + **مستقبِل `/webhooks/odoo/orders`** (غائب اليوم فتضيع كل طلبية تكتمل بأودو).
- **P5** التوصيل والاستلام + عرض الطلبية بحالتها وتقسيمها للزبون + التقييم والشكوى.

---

## جلسة 2026-07-28 (تتمة) — المرحلتان 2 و 3: نموذج الطلبية والخوارزمية

### المرحلة 2 — الكيانات وآلة الحالات

**خمسة جداول:** `orders` (الطلبية كما يراها الزبون) · `order_parts` (جزء لكل مستودع، **يقابل `recycle.order` واحدة بأودو**) · `order_part_lines` (بأسعار **مجمَّدة**) · `order_part_offers` (دفتر العروض) · `order_minimums`.

**قرارات تصميم مقصودة:**
- **لا حالة DRAFT**: السلة نفسها هي المسودّة، وصفّ `orders` لا يوجد إلا بعد التزام الزبون ونجاح فحص الحد الأدنى.
- **الأسعار تُجمَّد عند الإنشاء**: السلة تُعاد تسعيرها كلما غيّر الأدمن سعراً، أما الطلبية فعقد. اسم المادة ووحدتها وسعرها كلها لقطات، فتغيير السعر أو حتى حذف المادة لاحقاً لا يعيد كتابة ما دُفع.
- **`buyerRole` مخزَّن على الطلبية**: المستخدمون والمؤسسات سيطلبون من الجداول نفسها لاحقاً — بلا تغيير مخطط ولا إعادة كتابة للخوارزمية. (طلبك: الطلبية ليست حكراً على المعامل والجهات الحرة.)
- **الحد الأدنى صار سعراً لا كمية**: كلفة خدمة الطلبية تأتي من الرحلة والأوراق لا من عدد الكيلوغرامات، فـ ٥٠٠ كغ من مادة رخيصة و٥ كغ من غالية غير متقارنين أصلاً. ويُقارَن بقيمة **البضاعة وحدها** — احتساب التوصيل يجعل زبوناً بعيداً يتجاوز الحد بينما طلبية مطابقة قريبة تسقط، لمجرد بُعده.
- **آلة الحالات خريطة معلَنة لا سلسلة شروط** (`ORDER_TRANSITIONS`): دورة الحياة كلها مقروءة في مكان واحد، والانتقال غير القانوني يستحيل كتابته سهواً، وإضافة حالة = مدخل واحد. وكل الانتقالات تمر بحارس واحد يرفض بـ **409** يسمّي الحالتين — وهو بالضبط ما يحتاجه من خسر سباق «إلغاء مقابل موافقة».
- **حالة الطلبية مشتقّة من أجزائها لا مضبوطة يدوياً**: الطلبية عرضٌ على أجزائها، و**الجزء الأبطأ هو من يقرر**. طلبية مقسّمة «تتقدّم» بينما مستودع ما زال يعمل = كذب على الزبون.

### المرحلة 3 — المسافات والخوارزمية

**المسافات بثلاث طبقات — صفر استدعاء مدفوع في مسار الطلب:**
1. **PostGIS** يضيّق مستودعات المحافظة إلى الأقرب — مجاناً، داخل قاعدة البيانات، بإحداثيات مخزَّنة أصلاً (`LocationBase.coordinates`).
2. **الكاش** يجيب عن كل زوج سبقت رؤيته — والطرفان ثابتان عملياً، فبعد التسخين هذا يعني **كل زوج**.
3. **Google** يُسأل عن الناقص فقط، **بطلب واحد مجمَّع**.

**السقوط الآمن:** إذا كان Google معطّلاً أو نفدت الحصة أو لم يُضبط المفتاح أصلاً → تُستخدم المسافة الهوائية وتُسجَّل `source=HAVERSINE`. كل مسارات الفشل تهبط على التقدير بدل أن ترمي: طلبية بلا ترتيب أو بلا سعر نتيجة أسوأ بكثير من مسافة أقصر قليلاً — ويوم المناقشة، هذا الفرق بين نظام يعمل وشاشة ميتة.
**تسجيل المصدر مقصود:** التقدير الهوائي وطريق حقيقي ليسا قابلين للتبادل، والتوصيل يُسعَّر بالكيلومتر.

**الخوارزمية دالة نقية** (`planAllocation`): لا قاعدة بيانات ولا شبكة ولا ساعة — كل ما تحتاجه يصلها كوسائط، فالقرار قابل لإعادة الإنتاج والاختبار بلا أي تجهيزات.

تبني **خطتين اثنتين فقط** وتقارنهما:
1. أقرب مستودع **واحد** يغطي الطلبية كاملة.
2. تعبئة من الأقرب فالأقرب عبر عدة مستودعات.

مُحسِّن عام على كل التوليفات = أُسّي، يحتاج solver، وينتج أجوبة لا يستطيع أحد شرحها للزبون الذي انقسمت طلبيته. خطتان ومقارنة واحدة تلتقطان المقايضة الحقيقية وتُشرحان بجملة — **وهذه ميزة في المناقشة لا تنازل**.

**دالة الكلفة:** `مجموع المسافات + (عدد الأجزاء − 1) × غرامة التقسيم`. الغرامة هي ما يمنع تقسيم طلبية على ثلاثة مستودعات قريبة بينما مستودع أبعد قليلاً يغطيها كاملة — فكل جزء إضافي يعني مديراً آخر يوافق، وفرصة رفض أخرى، وفاتورة أخرى.

**والفرق بين النمطين مضبوط بالأرقام:** غرامة الاستلام الذاتي (٦٠ كم) أثقل بأربعة أضعاف من التوصيل (١٥ كم)، والسقف مستودعان مقابل ثلاثة — لأن **الزبون هو من يقود إلى كل موقع**، والجهة الحرة (لا توصيل لها أبداً) قد لا تملك أصلاً وسيلة نقل مناسبة.

**وقاعدة تسبق الكلفة كلها:** خطة تغطي الطلبية تتفوق دائماً على خطة أرخص تترك الزبون ناقصاً. خطة رخيصة تُبقيه ناقصاً ليست نتيجة أفضل، بل نتيجة **مختلفة وأسوأ**.

### التحقق

**12/12 اختبار وحدة للخوارزمية**، وكلها تُثبت قاعدة من التصميم لا مجرد «تعمل»:

| ما أُثبت |
|---|
| مستودع واحد يغطي → يُستخدم ولو كان أبعد |
| **مستودع أبعد واحد يفوز على تقسيم بين قريبين** (٤+٦ كم مقابل ١٨، والغرامة تحسم) |
| لكن يقسّم فعلاً حين يكون المنفرد بعيداً بما يفوق الغرامة (٩٠ كم) |
| نفس المخزون بالضبط: **التوصيل يقسّم والاستلام الذاتي لا يقسّم** |
| سقف الأجزاء لا يُتجاوَز أبداً |
| النقص يُبلَّغ ولا يُشحن ناقصاً بصمت |
| **حالة لا تُشبع حالة أخرى** (طلب EXCELLENT لا يأخذ GOOD) |
| خطة تغطي تفوز على أرخص ناقصة |

المجموع: **167/167** بالباك ايند · `tsc` نظيف · هجرتان إضافيتان.

---

## تصحيح جوهري 2026-07-28 — من يفعل ماذا داخل المستودع (v19.0.1.29.0)

كنت قد فهمت الأدوار خطأً، والمستخدم صحّحها. التصحيح مهم لأنه يمسّ **من يملك المسؤولية**، لا مجرد ترتيب أزرار.

### الفهم الخاطئ الذي أُزيل

نقلتُ `action_finish(output_zone_id)` إلى صلاحية المدير بفحص `_is_supervisor()`. **وهذا أدخل عطلاً فعلياً**: داشبورد موظف الإخراج هو من يستدعي هذا الراوت (`dashboard_api.py:2394`)، فكان التعديل سيمنع الموظف من إنهاء عمله أصلاً. أُزيل الفحص.

### الحدّ الفاصل الصحيح

**موظف الإخراج يملك التجهيز كاملاً، والمدير لا يتدخل في أي منه:**
`action_start_processing` (يأخذ الطلبية) → `action_complete(allocations)` (خصم من المناطق التي اختارها + الفاتورة + سطر `zone_movement` لكل خصم) → **`action_finish(output_zone_id)`** (إخراج البضاعة لمنطقة الإخراج).

**المدير له لحظتان فقط في عمر الطلبية:**
1. `action_manager_approve` / `action_manager_reject` — قبول الطلبية ابتداءً.
2. **`action_confirm_handover(carrier|buyer)`** — تأكيد أن البضاعة المجهَّزة **غادرت فعلاً**.

### لماذا حقل مستقل لا حالة إضافية في `state`

`state = completed` تعني اليوم «جُهِّزت وتنتظر بمنطقة الإخراج» في **كل** شاشة ودومين وتقرير قائم. توسيع الـ Selection كان سيغيّر معناها بصمت في كل مكان يقرؤها. لذلك المغادرة حقول مستقلة:
`handover_state` · `handover_type` · `handover_by` · `handover_at` · `handover_note`.

**والتمييز ليس شكلياً:** «جُهِّزت» و«غادرت» حدثان مختلفان بمسؤولين مختلفين، وبينهما تنتقل مسؤولية البضاعة خارج المستودع.

### أثره على حالة الطلبية عند الزبون

| تأكيد المدير | الجزء | الطلبية عند الزبون |
|---|---|---|
| `carrier` (توصيل) | `DISPATCHED` | **على الطريق** |
| `buyer` (استلام ذاتي) | `DELIVERED` | تم تسليم هذا الجزء |

و`IN_OUTPUT_ZONE` صارت تعني **«جُهِّزت، لم تغادر»**. لذلك حالة «على الطريق» لا تظهر للزبون إلا بعد أن يؤكد **كل** مدراء الأجزاء المغادرة — جزء ما زال بمنطقة الإخراج لم يغادر، وإخبار الزبون بغير ذلك كذبٌ قد يبني عليه تصرفاً.

**ولماذا المدير لا الموظف في لحظة المغادرة؟** لأن من جهّز البضاعة لا يصح أن يكون وحده السجل على أنها غادرت. وفي الطلبية المقسّمة، تأكيد **كل مستودع** هو ما تُبنى منه حالة الطلبية الواحدة التي يراها الزبون.

### التحقق — 13/13 بمستخدمين حقيقيين في مجموعاتهم الحقيقية

| |
|---|
| **موظف الإخراج** ينفّذ `start → complete → finish` كاملة بلا أي تدخل من المدير |
| «جُهِّزت» ≠ «غادرت»: بعد `finish` تبقى `handover_state = pending` |
| **موظف الإخراج يُرفَض** إن حاول تأكيد المغادرة |
| المدير يؤكد المغادرة ويُسجَّل **من ومتى** ونصّ حرّ (اسم الناقل/اللوحة/من وقّع) |
| تأكيد المغادرة **لا يمسّ** حالة التجهيز |
| تأكيد مكرر مرفوض · مغادرة قبل التجهيز مرفوضة · وجهة غير معروفة مرفوضة |
| الاستلام الذاتي: المدير يؤكد أن الزبون أخذها |

الباك ايند: **167/167** · `tsc` نظيف. ووثيقة التصميم صُحِّحت في المواضع الثلاثة التي حملت الفهم الخاطئ.

---

## جلسة 2026-07-28 (تتمة) — المرحلة 4: دفع الأجزاء لأودو وقناة العودة (v19.0.1.30.0)

### العطل الذي أُصلح أخيراً

`/webhooks/odoo/orders` كان **بلا مستقبِل**: أودو يرسل إليه منذ البداية بعد كل طلبية يُنهيها المستودع، ولا أحد يستمع — فكل طلبية تكتمل تضيع بصمت والزبون لا يُخبَر أبداً. ظهرت أخطاء 404 الخاصة به في سجلات اختباراتنا السابقة. الآن أصبح حياً.

### دفع الجزء إلى أودو

`recycle.order.backend_upsert_part(payload)` — **مفتاحه `backend_part_id`**، فالدفع **idempotent**: الباك ايند قد يعيد المحاولة بعد انقطاع دون أن يعرف هل وصلت الأولى، و**طلبية مكررة هنا تعني مستودعاً يجهّز البضاعة مرتين**.

يهبط الجزء دائماً بـ `manager_approval = 'pending'` — موافقة المدير هي ما تنتظره طلبية الزبون، فيجب أن تكون **قراراً صريحاً لا افتراضاً**.

**والحجز بعد الإنشاء لا قبله:** الحجز يعيش على سجل الطلبية بأودو، فحجزٌ قبل وجودها يترك بضاعة محبوسة لصالح لا شيء.

### قناة العودة: من الحدث إلى حالة الزبون

`ODOO_EVENT_TO_PART_STATUS` **جدول بحث لا سلسلة شروط** — كل حدث يرسله أودو مرئي في مكان واحد، وإضافة حدث = مدخل واحد، ولا فرع يُنسى.

| حدث أودو | حالة الجزء |
|---|---|
| `manager_approved` | ACCEPTED |
| `manager_rejected` | REJECTED |
| `processing` | PROCESSING |
| `stock_deducted` | STOCK_DEDUCTED |
| `completed` | IN_OUTPUT_ZONE |
| `handed_over` + `carrier` | **DISPATCHED** → الطلبية «على الطريق» |
| `handed_over` + `buyer` | **DELIVERED** لهذا الجزء |

**والحدث غير المعروف يُتجاهل ولا يُخمَّن**: اختراع حالة من حدث لا نفهمه هو كيف تنتهي طلبية وهي تدّعي أنها في مكان ليست فيه. و`handed_over` هو الحدث الوحيد الذي يعتمد معناه على حقل ثانٍ — لذلك خريطة صغيرة منفصلة له.

**التقدّم التلقائي بعد التجهيز:** طلبية الاستلام الذاتي لا يبقى لها ما يُرتَّب، فتصير جاهزة فور وصولها منطقة الإخراج. أما التوصيل فينتظر تأكيد المدير — ولهذا `PICKUP` وحدها تتقدّم تلقائياً.

**وحالة الطلبية مشتقّة لا مضبوطة** (`deriveOrderStatus`، دالة نقية يستخدمها الطرفان بلا دورة اعتماد بين الوحدات): «على الطريق» لا تظهر إلا بعد أن يؤكد **كل** المدراء المغادرة — جزء ما زال بمنطقة الإخراج **لم يغادر**.

### التحقق

**17/17 فحص شل لدفع الجزء:**

| |
|---|
| الدفع يُنشئ طلبية **تنتظر المدير**، لا مقبولة تلقائياً |
| **إعادة المحاولة تجد الطلبية القائمة ولا تُنشئ ثانية** — بقيت طلبية واحدة لهذا الجزء |
| الحجز يزيل البضاعة من متناول الآخرين قبل سؤال المدير (300 → 180) |
| جزء فارغ / بلا معرّف / بمستودع مجهول → **مرفوض ولا يُطبَّق نصفياً** |
| إلغاء الزبون يسحب الجزء **ويحرّر الحجز** (عاد 300 كاملاً) |
| إلغاء جزء غير موجود يُبلّغ `not_found` بدل أن يرمي |

**10/10 اختبار وحدة لخريطة الأحداث**، وأهمها: الحدث المجهول يُتجاهل · `handed_over` بلا وجهة يُتجاهل ولا يُخمَّن · **لا حدث واحد يقفز بالجزء إلى «جُهِّز وغادر»** معاً · واختبار يحرس أن الخريطة وآلة الحالات لا تفترقان.

المجموع: **177/177** بالباك ايند · `tsc` نظيف.

### الباقي

**P5**: عرض الطلبية بحالتها وتقسيمها للزبون · تأكيد الاستلام النهائي · التقييم لكل جزء · الشكوى الموجّهة · وخدمة التوزيع التي تربط الخوارزمية بالدفع (العروض، المهلة، إعادة التوزيع عند الرفض).

---

## جلسة 2026-07-28 (تتمة) — خدمة التوزيع والعروض

### `OrderAllocationService` — الغراء بين الخوارزمية والعالم

كل ما هو صعب في القرار يعيش في `planAllocation` النقية المختبَرة وحدها. هذه الخدمة تفعل ما يحتاج العالم فقط: قراءة المخزون، كتابة الأجزاء والعروض، والدفع لأودو.

**المتاح = الكمية − المحجوز** عند بناء العرض: القرار على الكمية الخام هو بالضبط كيف تُباع البضاعة نفسها لطلبيتين.

**مفتاح السطر يضمّ المادة وحالتها معاً** (`odooProductId:CONDITION`) — الحالة جزء من الهوية لا تفصيل: طلبية EXCELLENT يجب ألّا تُشبَع من مخزون GOOD أبداً، ودمجهما في مفتاح واحد هو تماماً كيف يحدث ذلك.

**إعادة التوزيع لا تحتاج جدولاً إضافياً**: المطلوب في الجولة التالية = **أسطر الأجزاء التي فشلت**، والأجزاء المقبولة تحتفظ بأسطرها. فيُبحَث عن الباقي غير المخدوم فقط. والأسطر المكررة عبر الجولات تُدمَج فيُبحَث عن المادة مرة واحدة بكامل الكمية المعلّقة.

**الإجماليات تتبع الأجزاء الحيّة** — فجزء رُفض يتوقف عن أن يُحاسَب عليه.

### إنهاء البحث — ثلاثة ضمانات مستقلة

1. **دفتر العروض**: مستودع رفض (أو صمت) يُستبعَد، فقائمة المرشحين **تصغر حتماً** كل جولة.
2. **سقف الجولات**: الضمان الذي لا يعتمد على صحة المنطق أعلاه في كل تعديل مستقبلي.
3. **مهلة العرض**: وهي الأهم عملياً.

### `OfferExpiryService` — الفشل الصامت

الفشل الصاخب (المدير يضغط «رفض») يعالج نفسه: الرفض يصل من أودو. **الصامت لا.** مدير في إجازة لا يضغط شيئاً، وبلا مهلة تنتظر طلبية الزبون إلى الأبد **ومخزونها محجوز يمنع طلبيات أخرى كان يمكن أن تستفيد منه**. عملياً، الصمت لا الرفض هو الطريق الأشيع لتجمّد طلبية.

- العرض المنتهي يُعامَل كالرفض تماماً (استبعاد المستودع) لكنه يُسجَّل `EXPIRED` لا `REJECTED` — «المدير رفض» و«لم ينظر أحد» مشكلتان مختلفتان، والأدمن الذي يراجع طلبية متعثّرة يحتاج التمييز بينهما.
- **قرار المدير يتفوّق على الساعة**: لا يُنتهى إلا الجزء الذي ما زال `OFFERED` فعلاً — قد يكون أجاب بين الاستعلام والكتابة.
- والانتهاء **يسحب الجزء من أودو أيضاً**، فمدير عائد من إجازة لا يقبل عرضاً تجاوزته الطلبية، والمخزون يُحرَّر هناك حقاً.

### إعادة التوزيع بعد الرفض — بلا دورة اعتماد بين الوحدات

رفض المدير يطبّقه معالج المزامنة، وهو **لا يستطيع مناداة المُوزِّع مباشرة** دون أن تعتمد وحدة الطلبيات ووحدة المزامنة كل على الأخرى. فبدل تمرير نداء، **الرفض يصير حالة**، وكنسة دورية تلتقطها: طلبية ما زالت `AWAITING_APPROVAL` ولا عرض مفتوح لها = طلبية لن يجيبها أحد.

**وهذا الترتيب أمتن أصلاً**: وظيفة ضائعة، أو انهيار في منتصف المعالج، أو قرار طُبِّق والعامل مطفأ — كلها تُشفى هنا، لأن الشرط يُقرأ **من البيانات** لا من حدث وقع. نفس فلسفة التسوية المستخدمة في المشروع كله.

### التحقق

`tsc` نظيف · **177/177** · والباك ايند يقلع سليماً — وهو الإثبات العملي أن **لا دورة اعتماد** بين وحدتي الطلبيات والمزامنة رغم أن كلتيهما تحتاج الأخرى منطقياً.

---

## تصحيح 2026-07-28 — Google Distance Matrix هو المصدر لا الاحتياط

نبّه المستخدم أن التصميم كان يكاد لا يستدعي Google أبداً، والملاحظة كشفت **عطلاً حقيقياً**.

### العطل

سطر الكاش الناتج عن السقوط الآمن كان **يُخزَّن بلا رجعة**. أول مرة يفشل فيها Google يُكتب صفّ `HAVERSINE`، وقراءة الكاش بعدها تُرجعه دائماً — **فالزوج لا يُسأل عن Google أبداً بعدها**.

النتيجة: **انقطاع عابر واحد كان يثبّت المسافة على تقدير هوائي للأبد**. والمسافة الهوائية تقلّ عن الطريق الحقيقي كثيراً داخل المدن، **والتوصيل يُسعَّر بالكيلومتر** — أي أن كل توصيل على ذلك المسار كان سيُحاسَب بأقلّ من كلفته، بصمت.

### التصحيح: مؤقّت لا نهائي

`HAVERSINE` صار يعني **«مؤقّت»** لا «بديل مقبول»: وعدٌ بالعودة لا جواب. و`PROVISIONAL_SOURCES` تُعرّف المعنى في مكان واحد.

- **مسار الطلب**: كاش أولاً؛ زوج جديد يُقاس فوراً بـ Google بمهلة **٣ ثوانٍ فقط** — الزبون ينتظر، وجوابٌ مؤقّت الآن تُصلحه الكنسة خلال دقائق أفضل من شاشة معلّقة.
- **كنسة الترقية** (كل ١٠ دقائق، مهلة ١٥ ثانية): تجد الصفوف المؤقتة وتعيد سؤال Google، **طلب مجمَّع واحد لكل زبون**، وبتراجع ٣٠ دقيقة كي لا يُسأل زوج غير قابل للتوجيه في كل جولة.
- **الصف النهائي (`GOOGLE`) لا يُسأل ثانية أبداً** — فالحالة المستقرة أن الطلب لا يكلّف استدعاءً إطلاقاً. وهذا هو الهدف فعلاً: **استخدم Google للدقّة، وادفع ثمنها مرة واحدة**.

### التعامل مع عدم الاستجابة — بتمييز لا بتعميم

| الحالة | المعالجة |
|---|---|
| `OVER_QUERY_LIMIT` / `UNKNOWN_ERROR` | عابرة → تُعاد المحاولة بالكنسة |
| `REQUEST_DENIED` / `INVALID_REQUEST` | المفتاح أو الطلب خطأ → **خطأ صريح بالسجل**، وإعادة المحاولة تحرق الحصة على مشكلة لا يحلّها إلا إنسان |
| `ZERO_RESULTS` / `NOT_FOUND` لعنصر | حقيقة عن **زوج واحد** لا فشل للطلب — ذلك المستودع يحتفظ بتقديره **وبقية الدفعة أرقام حقيقية** |
| مهلة / شبكة | تقدير مؤقّت + تحذير |
| **لا مفتاح** | تحذير **مرة واحدة لكل عملية** يقول صراحة إن كل توصيل يُسعَّر على خط مستقيم |

### تقليل الاستدعاءات — أربع طبقات

1. **PostGIS** يرتّب مستودعات المحافظة مجاناً ويُبقي الأقرب فقط → Google لا يُسأل عن أكثر من حفنة وجهات.
2. **طلب واحد مجمَّع**: أصل واحد × حتى ٢٥ وجهة. عشرة مستودعات فرادى تكلّف **نفس** العناصر لكن عشرة أضعاف زمن الانتظار وعشرة أضعاف فرص الفشل.
3. **الكاش** يجيب عن كل زوج سبق قياسه.
4. **إبطال عند الحركة فقط**: تغيّر إحداثيات مستودع بأودو → تُحذف مسافاته المخزَّنة. بقاؤها يعني محاسبة الزبون على رحلة إلى **مكان المستودع السابق**.

### التحقق — 9/9 اختبار وحدة

| |
|---|
| **مسافة Google تُستخدم لا الخط المستقيم** (12.4 لا 8) |
| ثلاثة مستودعات = **استدعاء واحد**، والوجهات الثلاث في طلب واحد |
| الزوج المقيس **لا يُسأل عنه ثانية أبداً** |
| فشل Google → تقدير **مؤقّت** ولا يُوقف الطلبية |
| **الصف المؤقّت يُرقّى فعلاً** حين يعود Google (8 → 12.4، والمصدر يصير GOOGLE) |
| الصف النهائي **لا يُعاد سؤاله** — صفر استدعاء |
| بلا مفتاح: صفر استدعاء وتحذير صريح |
| **زوج غير قابل للتوجيه لا يُفسد بقية الدفعة** |
| `REQUEST_DENIED` يُعامَل كفشل لا كمسافة |

المجموع **186/186** · `tsc` نظيف · و`GOOGLE_MAPS_API_KEY` موثّق في `.env` بسبب وجوده.

---

## جلسة 2026-07-28 (تتمة) — المرحلة 5: الواجهة التي يراها الزبون

### الراوتات السبعة (معمل وجهة حرة، **كلاهما ACTIVE حصراً**)

| الراوت | الكود | لماذا |
|---|---|---|
| `POST /orders/checkout` | **201** | يُنشئ مورداً فعلاً |
| `GET /orders` | 200 | قائمة بالبجينيشن، وفيها `is_split` و`warehouse_count` — **الانقسام معلوم من القائمة** |
| `GET /orders/:id` | 200 | كل جزء **مهمة مستقلة** بعنوان مستودعه وإحداثياته |
| `POST /orders/:id/cancel` | **200** | لا يُنشئ شيئاً · **409** إن بدأ التجهيز |
| `POST /orders/:id/confirm-receipt` | **200** | كلمة الزبون الأخيرة |
| `POST /orders/parts/:partId/rating` | **200** | إعادة التقييم **تستبدل** ولا تُراكم |
| `POST /orders/parts/:partId/complaints` | **201** | شكوى جديدة |

**ACTIVE حصراً** لأن حساباً ما زال بالأونبوردنغ بلا موقع مؤكَّد، **والموقع هو ما تُطابَق عليه المستودعات**.

### الـ checkout — لحظة الالتزام

- الحد الأدنى يُقاس على **الأسعار الحالية**: السلة تُعاد تسعيرها كلما غيّر الأدمن سعراً، فالرقم الذي يُلزَم به الزبون يجب أن يكون ما سيدفعه فعلاً.
- ثم **تُجمَّد** تلك الأسعار على الطلبية.
- **السلة تُفرَّغ بعد وجود الطلبية**: انهيار بين الاثنين يجب أن يُضيّع الطلبية لا سلة الزبون.
- **جهة حرة تطلب توصيلاً لا تُرفَض**: الخيار لا ينطبق عليها فيُحلّ إلى استلام ذاتي — إفشال checkout بسبب حقل قد لا تكون رأته أصلاً قسوة بلا سبب.

### الإلغاء — سباق حقيقي محسوم بقفل

الزبون يضغط «إلغاء» **اللحظة نفسها** التي يوافق فيها آخر مدير. الحل: معاملة واحدة بقفل `pessimistic_write` على صف الطلبية — **واحد فقط يفوز**، والخاسر يتلقى **409** يسمّي الحالة. والعروض المعلّقة **تُسحَب** (`WITHDRAWN`) فلا يوافق مدير على طلبية ميتة.
وتحرير المخزون بأودو يجري **خارج المعاملة**: نداء بعيد داخل قفل قاعدة بيانات يحجب مشترين آخرين.

### تأكيد الاستلام — كلمة الزبون وحده

كل مدير يؤكد أن **جزءه غادر**، لكن **الزبون وحده يقول إنه وصل**. نظامٌ يُغلق الطلبية بشهادة البائع لا يملك سجلاً للحقيقة الوحيدة التي تهمّ من دفع.

### التقييم والشكوى — **لكل جزء لا للطلبية**

بطلبية مقسّمة قد يكون مستودع ممتازاً وآخر سيئاً. **تقييم واحد للطلبية يجمعهما في رقم لا يُحاسب أحداً ولا يُعلّم شيئاً**، وشكوى ضد «الطلبية» لا تسمّي من يجيب. لكل جزء: التقييمات تتجمّع إلى **أداء حقيقي لكل مستودع**، والشكوى تصل الطاولة التي تملك الدليل.

**توجيه الشكوى بحسب نوعها** — وهذا ليس أوراقاً:
- **نقص / جودة → المستودع بأودو**، حيث `recycle.order.zone.movement` يسجّل بالضبط ما خرج ومن أي منطقة ومن خصمه ومتى.
- **توصيل / فاتورة → الأدمن**، فليست من صنع المستودع.

أرسل أياً منهما للطاولة الخطأ ولن يملك قارئها دليلاً يقرر عليه، فتتحول إلى تبادل ادّعاءات.
و**`route` يُخزَّن لا يُشتق عند القراءة**: تغيير قواعد التوجيه لاحقاً يجب ألّا ينقل شكاوى قيد المعالجة بصمت.

### تفصيلة أمنية

«غير موجودة» و«ليست لك» **تعطيان نفس الجواب (404)** — الـ403 هنا يؤكّد للمهاجم أن معرّف طلبية زبون آخر حقيقي.

### التحقق

- الراوتات السبعة **مُسجَّلة حيّاً**.
- الحرّاس مثبتون: **بلا توكن → 401** · **بتوكن أدمن (ليس معملاً) → 403** على القائمة وعلى الـ checkout.
- **186/186** · `tsc` نظيف · هجرة التقييمات والشكاوى نُفّذت.

### الباقي المعروف

- **دفع الشكوى إلى أودو** لتظهر عند المدير (بنمط `recycle.truck.problem` الجاهز) — الحقل `odoo_complaint_id` موجود ومنتظِر.
- شاشات الأدمن للشكاوى وأداء المستودعات.
- ضبط الحد الأدنى فعلياً: الصفّان مزروعان **معطَّلين وبصفر** عمداً — زرعُهما مفعَّلين برقم مُخمَّن كان سيمنع عمليات شراء لم يقرر أحد منعها.

---

## جلسة 2026-07-29 — الحالات ملك المادة + قاعدة الظهور حسب الدور (v19.0.1.33.0)

### أولاً: الحالات صارت خاصة بكل مادة

```
material_conditions.product_id  NOT NULL → FK CASCADE
UNIQUE (product_id, code)                ← بدل UNIQUE(code)
```

الكود يُعرّف الحالة **داخل مادتها**: مادتان قد تحمل كلٌّ منهما `GOOD` خاصتها، وهما درجتان مختلفتان لشيئين مختلفين. المادة تُنشأ **بلا حالات**، و«بلا حالات» جوابٌ نهائي مشروع.

- **الترتيب تلقائي** (`last + 1`) و`sort_order` **غير مقبول في البودي** — ترتيبٌ يختاره المُرسِل قد يتصادم عليه مُرسِلان فتتسلّل قيم مكرّرة لا تظهر حتى يُعرض المنتقي خطأً.
- **راوت إعادة ترتيب منفصل**: يعيد بناء القائمة كمصفوفة ثم يرقّمها ١..ن **داخل معاملة واحدة**. الإزاحة صفاً صفاً تترك القائمة لحظةً وفيها حالتان بنفس الرقم.
- **الراوتات العامة القديمة حُذفت** (`/admin/waste/conditions`) وحلّت محلها `/admin/waste/products/:productId/conditions`. وحُذفت خمس دوال من `AdminCatalogService` ولا شيء غيرها.
- `ConditionsService` صار **مقيَّداً بالمادة**: التحقق من كود بلا مادته هو بالضبط كيف تُقبَل طلبية بمادةٍ تحمل حالة مادةٍ أخرى. والتسميات مفتاحها `(مادة، كود)`.
- **أودو تبع**: `recycle.material.condition.product_id` مطلوب، والقيد `unique(product_id, code)`، وهجرة تحذف الصفوف العامة القديمة (لا سبيل صادق لإسنادها لمادة).

### قاعدة التسعير التي تتبع ذلك

| المادة | معامل / جهة حرة | مستخدم / مؤسسة |
|---|---|---|
| **لها حالات** | سعر **لكل حالة** | سعر واحد |
| **بلا حالات** | **سعر واحد** | سعر واحد |

والحالة الثانية هي التي كانت خطأً: **بلا شيء يُدرَّج، طلبُ سعر لكل حالة يطلب قيمة غير موجودة**. وأُضيف: السعر يجب أن يذكر حالةً **تملكها هذه المادة**، و**كل** حالاتها يجب أن تُسعَّر.

### ثانياً: مادة بلا سعر لدور لا تظهر لذلك الدور — إطلاقاً

**السبب ليس تجميلياً**: مادة مسعَّرة للمعامل فقط **غير موجودة** بالنسبة لمستخدم عادي. عرضُها له يعني أنه يضيفها لسلته، يصل الدفع، فتفشل الطلبية على سطر **لم يكن له سعر أصلاً** — والفشل يصل في أسوأ لحظة وبلا تفسير يستطيع التصرف بناءً عليه.

القاعدة في **مكان واحد** (`SellabilityService`) وتُستشار في كل نقطة تصل فيها المادة إلى مشترٍ:

1. **القائمة** — `EXISTS` داخل SQL لا ترشيح بعد الجلب، **فالبجينيشن والعدد الكلي يبقيان صادقين**، والأهم أن مادة لا يمكن محاسبته عليها لا تصل سلته أصلاً.
2. **السلة** — تُرفض عند الإضافة.
3. **الدفع** — كل سطر **يُعاد التحقق منه**: السلة ليست عقداً، والطلبية عقد. الأدمن قد يسحب لائحة الأسعار وسلةٌ مفتوحة — وهذه آخر نقطة يُلتقط فيها ذلك، فيتحوّل فشلٌ عميق داخل إنشاء الطلبية إلى **رفض واضح يسمّي المادة**.

**وعطل كنت سأُدخله وأغلقته:** مفتاح الكاش كان يجمع كل الأدوار تحت `'all'`. مع اختلاف القائمة بالدور، كان معملٌ سيرى قائمة مستخدم — **بمواد لا يستطيع شراءها**. صار المفتاح يحمل الـ tier.

**والسعر المعروض هو سعر دور القارئ** لا سعر غيره — مثبَّت باختبار مستقل.

### ثالثاً: حذف التسعيرة يوقف المادة

الحذف يؤرشف كل الفئات، **فتختفي المادة عن كل الأدوار تلقائياً** بقاعدة الظهور نفسها — لا حاجة لعلَم إضافي. والرسالة صارت صريحة: «سُحبت لائحة الأسعار — المادة موقوفة ومخفية عن كل الأدوار حتى تُضاف لائحة جديدة».

**وبأودو**: `pricing_suspended` **مشتقّ** من الأسعار المرآة نفسها لا مُزامَن منفصلاً — فلا يمكن أن يتعارض معها. ورقة الأسعار تعرض تنبيهاً صريحاً، و`assert_orderable()` ترفض المادة عند دفع الطلبية — لأن طلبية داخل أودو أيضاً ممكنة، ومادة بلا سعر **لا يمكن أن تُفوتَر**، فالفشل كان سيظهر عند الفاتورة بعد أن تكون البضاعة قد جُهّزت.

### التحقق

**8/8 اختبار لقاعدة الظهور**، وكلها تُثبت حكماً لا مجرد تشغيل:

| |
|---|
| المادة تظهر **فقط** للفئة المسعَّرة لها — والعكس بالعكس |
| كل فئة تأخذ **سعرها هي** لا سعر غيرها |
| **حالة بلا سعر غير قابلة للشراء** كمادة بلا سعر (حالة أُضيفت بعد اللائحة) |
| مادة بلا حالات تُسعَّر بلا حالة إطلاقاً |
| الرفض **يسمّي المادة** عند الدفع |
| مادة سُحبت لائحتها تُبلَّغ كذلك |

المجموع: **198/198** · `tsc` نظيف · والباك ايند وأودو يقلعان سليمين.

### الباقي

راوتات المخزون (بجينيشن + استعلام بالمادة) · اقتراح المادة من أودو بدل إضافتها · تدهور الحالة عند الفرز · تدقيق البجينيشن + كوليكشن الأدمن.

---

## جلسة 2026-07-29 (تتمة) — تعديل التسعيرة كجدول + تدقيق مجلد db

### تعديل السعر لا يمسّ طلبية قائمة — **مؤكَّد من الكود لا مفترَضاً**

خدمة التسعير تلمس أربعة مستودعات فقط: `productRepo` · `pricingRepo` · `historyRepo` · `cartItemRepo`.
**صفر إشارة** إلى `orders` أو `order_part_lines`.

فالتعديل والحذف يطالان **السلة وبداية الطلبية فقط**، أما الطلبية المنفَّذة فأسعارها لقطات مجمَّدة في `order_part_lines.unitPrice` — تبقى كما هي حتى لو حُذفت اللائحة كلها. الطلبية عقدٌ لحظةَ وُضِعت.

### `PATCH /admin/waste/products/:id/pricing` — تعديل كجدول

**الدور هو المفتاح لا حقل في البودي**: `{ "factory": [...] }` تقول أي فئة تُعدَّل، وتعديل فئتين يصير **نداءً ذرّياً واحداً** بدل نداءين قد ينجح أحدهما ويفشل الآخر.

**وهو تعديل لا استبدال**: فئة لم تُرسَل تحتفظ بأسعارها كما هي. رفعُ سعر المستخدم يجب ألّا يمسح بصمت حالات المعامل التي لم يذكرها أحد — و«استبدال كامل» يجعل هذا الخطأ على بُعد حقل منسيّ واحد.

**ودقّة انتبهت لها:** عند إعادة تسعير السلال بعد تعديل جزئي، الفئة غير المعدَّلة تأخذ **سعرها الحالي** لا صفراً — تمرير صفر كان سيصفّر كل سلال تلك الفئة بصمت.

والشكل يُفرَض من **المادة**: مُدرَّجة ← سعر لكل حالة تملكها هي؛ غير مُدرَّجة ← سعر واحد بلا حالة.

### `GET /admin/waste/products/pricing/:pricingId`

يرجع صف السعر كاملاً **ومعه آخر ١٠ من تاريخ فئته** — فسؤال «كم كان هذا قبلاً ولماذا تغيّر؟» يُجاب في النداء نفسه الذي تعمله الشاشة أصلاً. مُعرَّف **آخراً** عمداً: `:productId/pricing/...` كان سيبتلع المسار وإلا.

### كل تعديل وحذف يُسجَّل

`archiveCurrent` تنقل الصف إلى `product_pricing_history` بسبب صريح (`UPDATED` / `DELETED`) ومن نفّذه ومتى — قبل كتابة الجديد. فالمراجعة الزمنية قائمة على الحذف والتعديل معاً، و`getPricingById` تعرضها.

وكل تعديل يدفع فوراً إلى **أودو** (`enqueueUpdatePricing`) ويُبطل **كاش الكتالوج** ويُعيد تسعير **السلال** — الثلاثة معاً، فلا يبقى طرف متأخّراً.

### تدقيق مجلد `db` — ثلاث ملاحظات

| # | الملاحظة | الحكم |
|---|---|---|
| ١ | `db/migartions/` (خطأ إملائي) بداخله هجرة **مُعلَّقة بالكامل** — لا تصدّر صنفاً فلا يمكن أن تُنفَّذ | ميتة. مُستبعَدة من البناء بعد أن كانت تُفشل `nest build` بـ ENOTEMPTY |
| ٢ | `1777071613710-permissionMigration.ts` **مُعلَّق كله أيضاً**، ويظهر «غير منفَّذ» في أي تدقيق للأبد. والجداول الحقيقية (`permissions`, `role_permissions` — بالجمع) أنشأتها هجرة أخرى | غير ضار لكنه **يُضلّل كل تدقيق**. يُحذف |
| ٣ | صف `PerformanceIndexes1783400000000` في جدول `migrations` **بلا ملف مقابل** | **الأخطر**: الفهارس موجودة هنا، لكن **قاعدة بيانات جديدة لن تحصل عليها** — فبيئة الإنتاج ستختلف عن هذه بصمت، وتُكتشَف كبطء لا كخطأ |

الطوابع الزمنية بلا تكرار، وكل ملف يحمل `name`، و**44/44** هجرة حقيقية منفَّذة.

### التحقق

`tsc` نظيف · **198/198** · سبعة راوتات تسعير مُسجَّلة حيّاً.

---

## جلسة 2026-07-29 (تتمة ٢) — راوتات المخزون + الاقتراح بدل الإضافة

### المخزون: ثلاثة أسئلة، ثلاثة راوتات

| الراوت | يجيب عن |
|---|---|
| `GET /admin/warehouses/:id/inventory` | ماذا يوجد في هذا المستودع (مُصفَّح) |
| `GET /admin/inventory/warehouses/:wid/products/:pid` | هذه المادة في هذا المستودع + كل حالة |
| `GET /admin/inventory/products/:pid` | هذه المادة **في كل المستودعات** + أين هي |

**البجينيشن على المواد لا على صفوف المرآة.** الصفوف مخزَّنة لكل (مستودع، مادة، حالة)؛ قطعُ الصفحة عبرها يعيد **نصف حالات مادة**، فتظهر مجاميع خاطئة على البطاقة **بلا أن تبدو خاطئة**. فالصفحة تُقتطع من المواد، ثم تُجلب حالاتها كاملة.

**والملخّص يصف المستودع لا الصفحة** — استعلام تجميع مستقل في قاعدة البيانات. أدمن يقرأ «٣ مواد» في الصفحة الأولى من تسع كان سيقرأ كذبة.

**والحساب مطابق لأودو حرفياً:** `available = quantity − reserved` في كل مستوى، ولا ينزل تحت الصفر. المحجوز موعود لطلبية لم تخرج بعد؛ عدّه قابلاً للبيع هو بالضبط كيف يُباع الصندوق نفسه مرتين.

ومادة لم يرها أودو قط ترجع `synced_with_odoo: false` لا صفراً صامتاً — الصفر يُقرأ «نفدت»، والحقيقة «لم تُزامَن».

### أودو لم يعد يُنشئ مادة — بل يقترحها

**السبب:** المادة تظهر للمشتري **فقط** إذا كان لها تسعير لفئته، والتسعير يُؤلَّف في الباك ايند. فمادة تُنشأ في أودو تظهر **لا أحد** ويطلبها **لا أحد** — صفٌّ يبدو عملاً ولا يفعل شيئاً.

- شاشة **«Add Product»** في لوحة الأدمن (Owl) صارت **«Suggest a Material»**: اسم + تصنيف + وحدة + وصف، **وبلا حقول أسعار** — كانت ستُؤلَّف في الجهة الخطأ.
- نموذج جديد `recycle.product.suggestion` + قائمة + استمارة، وقوائم المواد والتصنيفات صارت `create="false" edit="false" delete="false"`.
- **الفشل يُسجَّل ولا يُرفَع استثناءً**: رفع `UserError` كان سيُرجِع المعاملة **ويأخذ رسالة الخطأ معها**، فيبقى الأدمن أمام سجل لا أثر فيه لأي عطل. الحالة تبقى قابلة لإعادة الإرسال.
- **`odoo_suggestion_id` مفتاح تفرُّد**: إعادة الدفع بعد timeout **تُحدِّث الصف نفسه** ولا تودع الاقتراح مرتين.
- اقتراح وصل الباك ايند **لا يُعدَّل في أودو** إلا بعد `Reset to Draft` — وإلا افترق الطرفان فيما أُرسِل.

### قبول الاقتراح **شكليٌّ بقرارك** — ولا يُنشئ منتجاً

`PATCH /admin/waste/suggestions/:id/review` يغيّر الحالة ويُشعر المقترِح **فقط**، والرد يقول صراحةً `product_created: false` كي لا يبني عميلٌ شاشةً حول معرّف مادة لن يأتي.

⚠️ ولهذا **نص الإشعار «وسيُدرَس لإضافته» لا «سيُضاف»** — الوعد بأكثر مما يفعله النظام هو كيف تصير الميزة تذكرة دعم.

ورفضٌ **بلا سبب مرفوض**: لا يفيد المقترِح ولا يمكن تصحيحه.
واقتراح أودو **لا يُشعَر أحد به** — لا حساب هناك.

### التحقق — حيّ لا مفترَض

اقتراح أُنشئ في أودو وأُرسِل فعلاً إلى الباك ايند العامل: عاد بمعرّف `7ec5ba9e…`، `source=ODOO`، `account_id=null`، والتصنيف «Plastic» طوبِق تلقائياً. ثم أُعيد الإرسال بعد تعديل الاسم → **صفٌّ واحد لا اثنان**، والاسم مُحدَّث.

**215/215** (كانت 198) · `tsc` نظيف · **6/6** اختبارات أودو للاقتراح · أودو `19.0.1.34.0` مُرقَّى ومُعاد التشغيل.

### الباقي

تدهور الحالة عند الفرز · واجهة الزائر · تدقيق البجينيشن · كوليكشن الأدمن.

---

## جلسة 2026-07-29 (تتمة ٣) — التلف مقابل التدهور

### الفرق الذي كان مفقوداً

| | ماذا يحدث للمخزون |
|---|---|
| **تلف** (`damage`) | المادة **راحت**. الكمية تخرج من المستودع |
| **تدهور** (`downgrade`) | المادة **موجودة**، لكنها لم تعد الحالة المسجَّلة بها. تنتقل كمية من حالة إلى **أدنى منها**، **والمجموع لا يتغيّر** |

تسجيل التدهور كتلف **يُتلِف مخزوناً حقيقياً على الورق**؛ وعدم تسجيله أسوأ: المستودع يبقى يبيع «ممتاز» لم يعد يملكه، **والمشتري يكتشفها عند التسليم**.

### ثلاثة أخطاء بيانات وجدتها وأصلحتها

**١ — التقرير لم يكن يحمل الحالة إطلاقاً.** الخصم كان يقع على أول حالة تُصادَف (`order='condition, id'`) — **لا الحالة التي كان موظف الفرز ينظر إليها**. الحقل صار مطلوباً.

**٢ — كان يمكن إتلاف مخزون محجوز لطلبية.** `_deduct_quantity` تخصم من `quantity` الخام لا من `available_qty`. أضفت `_assert_reportable` تقيس على **المتاح**: المحجوز موعود لطلبية قائمة وليس ملكاً لموظف الفرز. وتُعاد **عند الموافقة أيضاً** لا عند الرفع فقط — التقرير ينتظر المدير، وطلبية قد تُخصَّص في الأثناء.

**٣ — الباك ايند لم يكن يعلم أصلاً.** لا يوجد `inventory` في `BACKEND_ROUTES` ولا أوتوميتد أكشن — فالمرآة كانت تتحدَّث **فقط** عند ضغط الأدمن «مزامنة». والباك ايند **يخصّص الطلبيات من هذه المرآة**: خصمٌ مُوافَق عليه كان يترك المخصِّص يَعِد بحالة وكمية لم تعد موجودة، **فيظهر الخطأ كطلبية فاشلة لا كرقم على شاشة**. أضفت `notify_inventory_changed(warehouse)` — نبضة بلا حمولة كنبضة الأسطول، فالباك ايند يعيد قراءة المستودع كاملاً.

### الذرّية

التدهور **نصفان في معاملة واحدة**: خصم من الحالة الأعلى وإضافة إلى الأدنى. لو رُفع استثناء في النصف الثاني لعاد الأول معه — وهذه النتيجة **الوحيدة** المقبولة، لأن نقلة نصف مطبَّقة **تخلق مادة من العدم أو تُفنيها**.

والتدهور **لا يصعد**: `CONDITION_RANK` يفرض حالةً أدنى في الترتيب — «تدهور» إلى حالة أفضل كان سيصير ترقية جودة مجانية لم يفحصها أحد.

### الواجهات

- **موظف الفرز**: سؤال واحد في الأعلى «ماذا حدث؟» يفصل الحالتين قبل أي شيء، لأنهما تفعلان بالمجموع **عكس بعضهما**. ويرى **«المتاح في هذه الحالة»** — لا الكمية الخام.
- **مدير المستودع**: عمود «ماذا حدث؟» + النقلة تُعرض كنقلة `ممتاز ← جيد` في خانة واحدة. القرار بلا رؤية النوع كان قراراً أعمى.

### ملاحظة صريحة

`_add_quantity` تضيف إلى **منطقة التخزين الافتراضية** لا إلى المنطقة التي خُصم منها. مجاميع (مستودع، مادة، حالة) صحيحة — وهي ما يعتمده كل ما يلي — لكن توزيع المناطق قد ينزاح داخل المستودع الواحد.

### التحقق

**11/11** اختبار جديد · **29/29** لكل وحدة أودو · النبضة جُرِّبت **حيّة**: `notify_inventory_changed` → `PING_OK: True` من الباك ايند العامل · أودو `19.0.1.35.0`.

### الباقي

واجهة الزائر · تدقيق البجينيشن · كوليكشن الأدمن.

---

## جلسة 2026-07-29 (تتمة ٤) — واجهة الزائر + تدقيق البجينيشن + الكوليكشن

### الزائر — ولماذا **بلا سعر**، لا بسعرٍ خاص به

طرحتَ سعراً خاصاً بالزائر. رأيي أنه يضرّ لسببين:

**١** — السعر **دالّة على فئة المشتري**. فرقمٌ معلَّق على «لا أحد بعينه» هو رقمٌ **لن يُدفَع لأحد**. زائرٌ يرى ١٠ ثم يسجّل فيرى ٧ لا يقرأها نظام فئات، **يقرأها طُعماً**.
**٢** — لائحة المعامل **معلومة تجارية**. نشرها يسلّم منافساً كل أسعارك بنداء واحد.

| | الزائر يرى |
|---|---|
| التصنيفات | ✅ |
| المواد (اسم، صورة، وصف، وحدة) | ✅ |
| الأسعار | ❌ `price_hint: "سجّل لعرض أسعار فئتك"` |
| العروض | ✅ **وجودها** `has_offer: true` — بلا رقم ولا نسبة |
| السلة / الطلبية | ❌ |

**وثغرة كانت قائمة فعلاً:** راوتا العروض العامّان كانا يُرجعان `offer_price` و`discount_percentage` **لأي زائر**. القاعدة وُضعت **داخل `mapOffer` نفسها** لا في مُحوِّل منفصل: المُحوِّل المنفصل شيءٌ يمكن لموضع نداءٍ جديد أن **ينساه**؛ وقاعدةٌ في النقطة الوحيدة التي تصير فيها العروض JSON لا تُتجاوَز بالنسيان.

**ودقّتان:**
- استعلام الزائر **بلا `price_min/price_max`** — فلترة بالسعر طريقةٌ لقراءة الأسعار مجالاً مجالاً. وله **نوعه الخاص** لا نوع المشتري، وإلا صار التسريب على بُعد حقلٍ موروث واحد.
- الزائر يرى **فقط** المواد المسعَّرة لفئةٍ ما. مادة بلا سعر لأحد **موقوفة**: لن يشتريها أي حساب يسجّل، فعرضها وعدٌ لا يُوفى.

### تدقيق البجينيشن — على كامل النظام

فحصت **٧٧** راوت GET. النتيجة:

| | |
|---|---|
| **عطل حقيقي** | `GET /trucks/drivers` كان يُرجع **كل** السائقين بأربع وصلات على كلٍّ منهم. **عطل بطيء**: لا ينكسر شيء، الشاشة تثقُل شهراً بعد شهر حتى تنتهي مهلتها — يُكتشَف كـ«التطبيق بطيء» لا كخطأ يُشار إليه. **صُلِّح** |
| مقصود | مُنتقيات الورديات والوحدات والحالات: محدودة بطبيعتها، والتصفيح عليها ضجيج |
| ملاحظة | الإشعارات تُصفَّح لكنها ترجع `{items,total}` بدل بلوك `pagination` الموحَّد — تعمل، لكنها شاذّة عن البقية |

### الكوليكشن — **مُولَّد لا مكتوب بيد**

`node postman/build-admin-collection.js`

الكوليكشن القديم **كان متخلّفاً**: يعرض راوتات `/admin/waste/conditions` التي **حُذفت** حين صارت الحالات تابعة للمنتج — فمن يفتحه يجرّب راوتات غير موجودة **ويظن العطل في الباك ايند**؛ ولا يعرض جدول التسعير ولا المخزون ولا الاقتراحات أصلاً.

**والتحقق ثنائي الاتجاه بالكود لا بالعين:** **٨٠** طلباً في **١٦** مجلداً · **٧٧/٧٧** من راوتات الأدمن مغطّاة · و**صفر** مسار في الكوليكشن بلا راوت مقابل.

### التحقق

**221/221** (كانت 215) · `tsc` نظيف.

---

## جلسة 2026-07-31 — صفحة السائق + الترجمة + مرآة مدير المستودع (v19.0.1.39.0)

### واجهة السائقين: زر واحد بدل ستة

قائمة سائقي التوصيل كانت تحشر **ستة أزرار** في خلية جدول واحدة. على الجوال — وهو الاستخدام الأغلب — يتحوّل هذا إلى جدارٍ من النص الملتفّ. والأهمّ: **الخلية لا مكان فيها لعرض أي شيء**، لا صورتَي الرخصة اللتين جُعلتا إلزاميّتين، ولا العنوان، ولا الشاحنات التي استلمها.

فصارت القائمة تعرض **زر «عرض» واحداً** ينقل إلى صفحة السائق: معلوماته، شاحنته الحالية، **وجها رخصته**، و**كل شاحنة استلمها بتواريخها** — ثم الإجراءات (تعديل · إسناد/سحب شاحنة · إنشاء حساب · طباعة PDF · حظر/رفع حظر).

وطُبِّق نفس الشيء على **سائقي الجمع**: كانت تفاصيلهم **مودالاً** — والمودال لا يتّسع لسجلّ الشاحنات، وعلى الجوال يغطّي القائمة نفسها التي فُتح منها. صار صفحة، ومعه عمود «إجراءات» فيه زر «عرض» — لأن **إجراءً يجب اكتشافه هو إجراء لن يجده أغلب المستخدمين**.

**وعطلٌ صامت صُلِّح على الطريق:** كل إجراء كان ينادي `openDeliveryDrivers()` التي **تعيد الدخول إلى القائمة**. فمن يحظر سائقاً من صفحته يُقذف خارج السجلّ الذي كان يعمل عليه لحظةَ تغييره. فُصلت إعادة التحميل عن التنقّل (`_reloadDeliveryDrivers`)، وصار الإجراء يُحدِّث **ويبقى مكانه** — مع إعادة قراءة سجلّ الشاحنات، لأن الحظر يسحب الشاحنة، وصفحةٌ تعرض «بلا شاحنة» في أعلاها و«مستلَمة حالياً» في أسفلها تناقض نفسها.

وقائمة «سائق» صارت **مدخلاً واحداً** يتفرّع إلى جمع/توصيل — نفس شكل شريط المدير تماماً.

### تصدير PDF: كان يعمل ويكذب

الملف كان يُولَّد فعلاً (HTTP 200، `%PDF-1.4` سليم) — لكن جدول «الشاحنات المستلَمة» **فارغ**، وقد صُلّح ذلك بترحيل 1.38.0. غير أن الترحيل كتب صفوفه بـ **SQL خام**، وSQL لا يُشغِّل دوال الحساب — فخرجت ثلاثة أعمدة مخزَّنة فارغة:

```
truck_plate    NULL
truck_type     NULL
duration_days  0
```

**واللوحة هي الشيء الوحيد الذي يفرّق بين شاحنتين في أسطول**، وهي ما يُطبع الملف من أجله. مستندٌ يعرض شاحنة بلا لوحة و«0 يوم» **أسوأ من مستند ناقص**: يبدو كاملاً ويقول عن الشخص شيئاً غير صحيح.

فأُضيف إعادة الحساب داخل 1.38.0 (لمن يرقّي من أقدم منها)، و**ترحيل 19.0.1.39.0** يصل إلى قواعد البيانات التي شغّلت 1.38.0 بصيغتها الأولى — لأن ترحيلاً شُغِّل لا يُشغَّل ثانية. أُصلحت **3 صفوف**، وتحقّقت أن اللوحة تظهر **داخل نصّ المستند** لا أن المستند يُولَّد فحسب.

### الترجمة: 176 نصّاً كانت تصل الشاشة بالإنجليزية

`tr()` **ترجع النص الإنجليزي عند غياب المفتاح**. لا استثناء، ولا تحذير، ولا شيء يبدو مكسوراً لمطوّر يقرأ الإنجليزية — النصّ يظهر ببساطة إنجليزياً وسط شاشة عربية، **ولا يكتشفه إلا المستخدم**.

وُجد **176** نصّاً في هذه الحالة. تُرجمت كلّها.

**ومصيدةٌ داخل التصليح نفسه:** ستة من مفاتيحي كُتبت بصيغة `Confirm &amp; Store`. لكن **محلّل XML يفكّ الكيان قبل أن يرى Owl التعبير أصلاً** — فالنداء وقت التشغيل هو `tr('Confirm & Store')`، ومفتاحٌ مخزَّن بالكيان الخام **لا يُعثر عليه أبداً**. يبدو موجوداً في أي بحث نصّي ولا يُستعمل قط. حُذفت **10** مفاتيح ميّتة (منها اثنان كانا موجودَين من قبلي).

**حارسان دائمان:**
- `test_dashboard_translations.py` — يفشل البناء إذا وصل أي نصّ الشاشة بلا ترجمة، **بعد فكّ الكيانات** كما يفعل المتصفّح، ويرفض أي مفتاح يحمل كياناً خاماً.
- `test_qweb_branch_chains.py` — يمسك `t-elif` انقطعت سلسلته. هذا العطل **حدث هنا فعلاً**: مودال أُقحم بين فرعين في شاشة المدير، والنتيجة `OwlError` وقت الترجمة **في المتصفّح** — فالوحدة تُثبَّت، وXML يُحلَّل، وكل اختبارات الخادم تنجح، والشاشة **بيضاء عند المستخدم**.

وأُثبت أن الحارسَين **يفشلان فعلاً** على العطل الذي يدّعيان مسكه، لا أنهما يعملان فقط.

### الباك ايند: لماذا كان `manager: null`

سؤالٌ مطروح: لماذا يُرجع `GET /admin/warehouses` مديراً `null` لمستودعٍ له مدير، ولماذا يظهر **فقط** بعد نداء sync يدوياً؟

**ليس عطلاً في الاستعلام** — `list()` و`getOne()` يصلان العلاقة صحيحاً (`leftJoinAndSelect` / `relations: ['manager']`). المشكلة أن **لا صفّ في `warehouse_managers` ليُوصَل به**:

| | |
|---|---|
| ما يكتب الصفّ | `syncManager()` فقط — ولا يصلها إلا راوتان يدويّان: `:id/sync-manager` و`import-from-odoo` |
| المسار التلقائي | `POST /odoo/webhooks/warehouse` → مهمّة `SYNC_WAREHOUSE` — تُزامن الاسم والرمز والمحافظة والإحداثيات والحالة **والمخزون**، و**لا تمسّ المدير** |
| ما يدفعه أودو | `sync_warehouse()` في `backend_sync.py` — **شيفرة ميّتة بلا أي مُنادٍ**، وحمولتها أصلاً بلا حقل مدير |
| «تغيير المدير» في لوحة أودو | يكتب `manager_user_id` محلياً **ولا يُخبر أحداً** |

فالنتيجة أن المزامنة لم تكن مزامنة، بل **مهمّة يتذكّرها أحدهم**.

**صُلِّح من الطرفين:**
- أودو: `notify_warehouse_changed()` + نداؤها من `write()` عند تغيّر `manager_user_id`. والشرط صار `'manager_user_id' in vals` لا `vals.get(...)` — لأن `.get` **كاذبة عند الإزالة**، فحذف مدير كان يُتجاوَز بصمت. وهذا **الاتجاه الأسوأ**: الـAPI يبقى يسمّي شخصاً لم يعد مسؤولاً، والبيانات القديمة المعروضة كحقيقة أصعب اكتشافاً من البيانات الغائبة.
- الباك ايند: `mirrorWarehouseManager()` داخل مهمّة `SYNC_WAREHOUSE`. المطابقة على **`odooUserId`** لا على البريد — فتصحيح خطأ إملائي في عنوان أحدهم يجب ألّا يُنشئ مديراً ثانياً. وإزالة المدير في أودو **تُزال** هنا. والفشل يُسجَّل ولا يُرمى: خسارة تحديث مخزون كامل لأن استعلام مدير انتهت مهلته **مقايضةُ قِدَمٍ صغير بقِدَمٍ كبير**.

### التحقق

**أودو:** 123 اختباراً · 0 فشل · 0 خطأ (كانت 111)
**الباك ايند:** 290 اختباراً · 35 ملفاً · `tsc --noEmit` نظيف


---

## جلسة 2026-07-31 (تتمة) — المزامنة التلقائية + سجل الهوية + وحدة القياس كرابط (v19.0.1.40.0)

### القاعدة الذهبية: لا راوت مزامنة، أبداً

**السبب الجذري:** الإشعارات كانت معلَّقة على **ثلاثة مسارات فقط** — `order.py` و`shipment.py` و`stock_damage_report.py`، كلٌّ ينادي `notify_inventory_changed` **بيده**. وكل مسار آخر يحرّك المخزون **لا يخبر أحداً**: حجز، تحرير، تصحيح مباشر، خصم من أي مكان آخر، إنشاء صفّ أو حذفه. فالمرآة صحيحة بعد المسارات الثلاثة التي تذكّرها أحدهم، و**خاطئة بصمت بعد كل ما عداها** — وهذا بالضبط عَرَض «الـAPI يبقى على رقمه القديم حتى أنادي sync».

**الحلّ:** الإعلان انتقل إلى **`recycle.stock` نفسه** — الشيء الوحيد الذي **يجب** أن يمرّ منه كل تغيير كمية. والمُنادي لا يمكنه أن ينسى ما لا يُطلب منه تذكّره.

لكن هذا وحده يحوّل عمليةَ فرزٍ واحدة إلى **إشعار لكل صفّ**. فأُضيف `schedule_ping`: يجمع الإشعارات على مستوى **المعاملة**، ويرسل **واحداً لكل (مسار، مستودع)** — **بعد الـcommit**. والتوقيت ليس تفصيلاً: الإرسال قبل الـcommit يترك طريقين للخطأ — كتابةٌ تراجعت تُعلن عن نفسها، وباك ايند يعيد القراءة فوراً يقرأ الصفّ **كما كان قبل** التغيير الذي أُشعِر به.

**والمستودع:** الشرط صار يغطّي **كل حقل تُرآه المرآة** (الاسم، الرمز، المحافظة، الإحداثيات، **حالة الحياة**) لا المدير وحده. وحالة الحياة أهمّها: مستودعٌ وُضع في `closing` يتوقف عن الاستقبال، وباك ايند لم يُخبَر يستمرّ بتوزيع الطلبيات على موقعٍ يُغلق.

**وعطلٌ أمسكه الاختبار الحيّ:** `odoo.registry(db)` **حُذف في أودو 19**. أول تشغيل فعلي طبع «Backend ping flush could not open the registry» — أي أن كل شيء يبدو سليماً ولا يُزامَن شيء. صار الاستيراد `from odoo.modules.registry import Registry` صراحةً، ليفشل **وقت الاستيراد** لا داخل callback بعد الـcommit حيث العَرَض الوحيد سطرُ سجلٍّ لا يقرأه أحد.

**وشيفرة ميّتة حُذفت:** `sync_product` و`sync_category` كانا يرسلان إلى `/webhooks/odoo/products` — **مسار بلا مستمع**. وبما أن المادة لا تصل أودو إلا **مدفوعةً من الباك ايند**، كان الأثر الأشيع طلباً خارجياً محكوماً بالفشل في كل مزامنة: الباك ايند يخبر أودو بمادة، وأودو يخبر الباك ايند فوراً بالمادة التي أُعطيت له للتوّ.

**التحقق الحيّ:** كتابة مخزون → `[('inventory', 2)]` · تعديل مستودع → `[('warehouse', 2)]` · والراوتات الأربعة تُجيب **2xx** من الباك ايند الحيّ.

### المخزون: الكيلو لا يُجمع مع القطعة

الملخّص كان يجمع **كل** الكميات: 100 كغ ورق + 2 بطارية = **«102»**. رقمٌ **لا وحدة يمكن كتابتها بجانبه**، ويتغيّر إذا أُعيد قياس مادة بالطن **دون أن يتحرك كيلوغرام واحد**. من يقرأه يقرأ كميةً من لا شيء.

صار `totals_by_unit`: صفٌّ لكل وحدة (مُعرّفها واسمها) بمجاميعها. ولا مجموع كلّي — لأنه غير قابل للجمع أصلاً. والمواد التي لا تُحلّ وحدتها **تبقى** تحت رمزها بدل أن تُسقَط: مخزونها حقيقي سواء وُجد صفّ الوحدة أم لا.

وفي الاستجابة: **`condition_id`** بجانب الرمز، و`unit` صار **هويةً** `{id, code, name_en, name_ar}` — بلا `is_weight` ولا `allows_tolerance`: تلك تصف **كيف تتصرّف** الوحدة، ومكانها شاشة الوحدات لا قراءةُ مخزون لا تفعل بها شيئاً.

### وحدة القياس رابطاً لا نصّاً

المادة كانت تخزّن **رمز** الوحدة فقط — نصٌّ يُتحقَّق منه عند الكتابة ولا يُوصَل بشيء. صار `unit_id` (FK بـ`RESTRICT`) تماماً كـ`category_id`، والرمز يبقى بجانبه لأن أودو والسلة والاقتراح كلها تتكلم بالرموز.

و`unit_id` + `unit_type` **متعارضَين** → **رفض**، لا ترجيح: أيّهما كان قصد المُنادي، والاختيار الصامت هو كيف تُقاس مادة بالكيلو وتُسعَّر بالقطعة.

### التصنيف المعطَّل لم يكن يُعطِّل مواده

إيقاف تصنيف كان **يخفي العنوان فقط**: كل مواده تبقى معروضة ومبحوثة ومُشتراة. فأدمن سحب خطَّ موادٍ كاملاً يجده ما زال يُباع، ولا يكتشف ذلك إلا من طلبيةٍ لا يستطيع تلبيتها. الآن `c.isActive` شرطٌ في كل قراءات الكتالوج — القائمة والزائر والتفصيل والتوافر.

### سجل الهوية — **نُفِّذ**

`recycle.identity.guard` يبحث في أربعة جداول ثم يكتب، و**بحثٌ ثم كتابة ليس ذرّياً**: طلبان بنفس الرقم الوطني في اللحظة نفسها يبحثان قبل أن يكتب أيّهما، فلا يجدان شيئاً، فيمرّان معاً. لا خطأ في الشيفرة ولا أثر في السجلّ — فقط **شخصان هما شخص واحد**.

الآن `recycle.identity`: صفٌّ لكل هوية خلف **فهرس UNIQUE حقيقي**. الطبقتان لا تتكرران — الحارس يعطي **الرسالة القابلة للتصرّف** («هذا الرقم يخصّ سائق توصيل») وهو ما لا يستطيعه فهرس، والفهرس يجعل القاعدة **صحيحة** لا مُرجَّحة.

**وعطلان أمسكهما الاختبار قبل المستخدم:**
1. **`_sql_constraints` يُتجاهَل في أودو 19.** الجدول أُنشئ بلا أي قيد فريد — سجلٌّ لا يفرض شيئاً بينما كل فحوص بايثون تمرّ. الاختبار الذي **يكتب متجاوزاً كل الفحوص** هو ما كشفه، ولهذا كُتب. صار `models.Constraint`.
2. **السائق وحسابه شخصٌ واحد في جدولين** — بالتصميم. السجل كان سيرفض على سائقٍ حسابَ دخوله، لأن إنشاءه ينسخ رقمه الوطني إلى `res.users` والسائق يملك المطالبة. صار `same_person` يُمرَّر من الحارس نفسه، فلا تختلف الطبقتان على من هو من.

والترحيل عبّأ **17 مطالبة** ووجد تعارضات قائمة فعلاً — تُسجَّل مفصَّلةً ولا تُدمَج: اختيار أيّ التاريخين هو الشخص الحقيقي **حكمٌ على إنسان**، وترحيلٌ يتّخذه صامتاً يتّخذه خطأً وبلا أثر.

### تقرير السائق

كان يستعمل `web.external_layout` الذي يطبع ترويسة `res.company` — و**شعارها غير مضبوط** على هذه القاعدة، فكان كل ملف يخرج **بلا علامة**. ومستندٌ يسمّي شخصاً ولا يحمل أثر مُصدِره ليس دليلاً على شيء.

صار للملف تخطيطه الخاص: **شعار التطبيق** من `static/src/img/Logo.png` (تحقّقت أنه يُخدَم بـ200)، وترويسة بتاريخ الإصدار ومُصدِره، وشبكة حقائق label/value، وجدول سجلٍّ مخطّط، وحبّات حالة ملوّنة.

**والتنزيل تنزيل** لا علامة تبويب: `window.open` يترك الملف في تبويب باسم المسار — على الجوال عارضٌ بلا طريق واضح للعودة، وعلى الديسكتوب مستندٌ يُحفَظ يدوياً باسم `report_delivery_driver_file`. صار يُجلَب كـblob ويُحفَظ **باسم الشخص**.

**وصور الرخصة تُفتح فوق الصفحة** لا في تبويب: تبويبٌ يحمل صورةً عاريةً بلا سياق، وعلى الجوال بلا طريق عودة.

**وكرت «شاحنة التوصيل» حُذف** من الصفحتين: كان يقول الشيء نفسه مرتين — الشاحنة الحالية هي **الصفّ المفتوح** في «الشاحنات المستلَمة» موسوماً «مستلَمة حالياً». وموضعان يعرضان حقيقةً واحدة هما موضعان يمكن أن يختلفا بعد تسليم.

### رقم الجوال للمؤسسات والجهات الحرة

المعامل كانت تُسأل عن جوال؛ المؤسسات والجهات الحرة عن **أرضيّ فقط**. فكانت الطلبية نفسها قابلة للحلّ أو لا **حسب نوع المشتري وحده** — سائقٌ أمام بوابة مغلقة خارج الدوام معه رقمٌ يرنّ في غرفة فارغة. أُضيف `phoneNumber` (سوري، مُطبَّع، فريد) للاثنين، والعمود **nullable** لأن الصفوف السابقة لا جوال لها **يُخترَع**.

### ما كان سليماً وتحقّقت منه

- **قبول/رفض المؤسسات والمعامل والجهات الحرة**: رفض وثيقة → `REJECTED` + الحساب `NEED_CHANGES` + إشعار بالسبب. وإعادة الرفع → `PENDING` والحساب يعود `PENDING_APPROVAL` **فقط حين لا تبقى وثيقة مرفوضة** — تفصيلٌ دقيق ومغطّى باختبارات.
- **حالة المنتج مرتبطة بالمنتج** أصلاً (`material_conditions.product_id` + `UNIQUE(productId, code)`).
- **كلفة الكيلومتر عند أدمن الباك ايند**: `/api/v1/admin/delivery-rate` — GET · POST · PATCH · quote، وفي الكوليكشن.

### التحقق

**أودو:** 154 اختباراً · 0 فشل · 0 خطأ (كانت 138)
**الباك ايند:** 298 اختباراً · 35 ملفاً · `tsc --noEmit` نظيف
**حيّ:** كتابة مخزون وتعديل مستودع يجدولان إشعارَيهما، والراوتات الأربعة تُجيب 2xx


---

## جلسة 2026-07-31 (تتمة ٢) — الترحيلات لم تُشغَّل + تنظيف بيانات المرآة + الطلبية المجزّأة

### السبب الحقيقي لـ DATABASE_ERROR — عطلان في عملي أنا

**١. الترحيلات لم تُشغَّل أصلاً.** آخر ترحيل مُطبَّق كان `1785500000000`. فكل ما أضفته بعده — `unit_id`، جدول `delivery_rates`، `truck_type` — **موجود في الكيانات وغير موجود في القاعدة**. فأي راوت يقرأ منتجاً يطلب عموداً غير موجود → «Unexpected database error». وهذا هو خطأ إضافة المنتج وخطأ عرض المخزون معاً.

**٢. أسماء أعمدة خاطئة داخل الترحيلات.** المشروع يستعمل `SnakeNamingStrategy`، فـ`unitType` على القرص هو `unit_type`. كتبتُ اسم خاصية TypeScript في SQL — خطأ **لا يظهر إلا لحظة التشغيل**، وقد ظهر: `column "unitType" does not exist`. صُلّح في الترحيلَين، ثم شُغِّلت كلها.

### تخبيصات القاعدة — وجدتها وأصلحتها

فتحت قاعدتي الباك ايند وأودو وقارنتهما صفّاً صفّاً:

| ما وُجد | الأثر |
|---|---|
| **٨ مستودعات في الباك ايند مقابل ٤ في أودو** — زوجان يحملان **نفس `odoo_warehouse_id`** | مهمة `SYNC_WAREHOUSE` تكتب مخزون أودو في **كل** صفّ يحمل ذلك المعرّف، فكل كمية تُنسخ مرتين |
| **المخزون مضاعف تماماً**: 192 كغ في أودو تُقرأ **384**، و1812 تُقرأ **3624** | المُوزِّع كان يَعِد الزبائن بمخزون **غير موجود** |
| **كودان مكرّران** (`WH33`، `WHD1`) | الكود هو ما يُكتب على الأوراق ويُقال في الهاتف |
| **مستودعان يتبعان صفوف أودو محذوفة** | يظهران في القوائم ولا مصدر لهما |

**والسبب البنيوي: لا قيد فريد على `odoo_warehouse_id` ولا على `code`.** أضفت الاثنين، ومعهما ترحيل يدمج التكرارات: التبعيات (المدراء، الشاحنات، السائقون، التعرفات) **تُنقَل** إلى الصفّ الباقي، وصفوف المخزون المكرّرة **تُحذَف** لأنها نسخة ثانية من نفس سطور أودو — نقلها كان سيُبقي المضاعفة ويغيّر مكانها فقط.

**النتيجة بعد الإصلاح:** ٦ مستودعات، و`backend=192 odoo=192 OK` · `1812/1812 OK` · `15/15 OK`.

والمستودعات اليتيمة **لم تُحذف** بل يُوصى بتعطيلها: حذف موقع لأن صفّاً اختفى من الطرف الآخر ليس قراراً يتّخذه ترحيل بصمت.

### كود المستودع فريد — في الطرفين

**الباك ايند:** الفحص كان `findOne({code})` — **حسّاس لحالة الأحرف**، فـ«wh1» يمرّ فوق قاعدة تحمل «WH1» ثم يفشل عند الإدراج. صار `upper(btrim(...))` في الإنشاء **والتعديل**، والكود يُخزَّن مقصوصاً.
**أودو:** أُضيف `models.Constraint('unique(code)')` الحقيقي، والفحص صار `=ilike` ويشمل **المؤرشفة** — مستودع مؤرشف ما زال يملك كوده.

### الطلبية المجزّأة — الأدمن يقرّر، لا كل مدير

كان كل جزء يُوافَق عليه من **مدير مستودعه**. وهذا يفشل باتجاهين: مدير يوافق وآخر يرفض فتصير الطلبية **نصف موعودة** ولا أحد مسؤول عن كلّها؛ أو مدير يوافق والبقية لم ينظروا بعد فيرى الزبون حركةً على طلبية لا يمكن أن تكتمل.

الباك ايند صار يرسل `order_id` و`part_sequence` و`part_count`؛ وأودو صار يعرف أن الأجزاء **شيء واحد**. والقرار:
- جزء من طلبية مجزّأة → **الأدمن وحده**، ومدير المستودع يُرفَض برسالة تقول لماذا.
- والموافقة/الرفض تُطبَّق على **كل الأجزاء في معاملة واحدة**، والبحث عن الأشقاء بـ`sudo` عمداً: الأجزاء في مستودعات مختلفة، وقاعدة سجلّ تحصر القراءة بمستودع القارئ كانت ستعيد «كلاً» هو جزء واحد — وتوافق على قطعة بينما تقول إنها وافقت على الطلبية، وهذا أسوأ الاحتمالات لأنه **يبدو صحيحاً**.
- الطلبية أحادية المستودع **لم تتغيّر**: مديرها يقرّرها كما كان.

**١١ اختباراً** يثبّتون ذلك، منها أن الرفض يُحرّر مخزون **كل** الأجزاء.

### تسريب أمني في قوائم الطلبات

`GET` طلبات المعامل/الجهات كان يُرجع **كيان الحساب كاملاً** — أي `passwordHash` (بصمة argon2) لكل متقدّم، إلى متصفّح كل من يفتح شاشة المراجعة، ومعه `googleId` و`provider` وأعلام التحقق. سرٌّ **غير مستعمَل يبقى سرّاً تسرَّب**: هو في جسم الاستجابة، وفي كاش المتصفح، وفي أي سجلّ يحفظ استجابة.

صار **قائمة سماح** لا قائمة حذف: الاسم، البريد، الجوال، الصورة، حالة الحساب، الدور — وحقلٌ يُضاف للكيان لاحقاً يبقى **غير مكشوف** حتى يقرّر أحد كشفه. و`description` حُذف من الاستجابة كما طلبت.

### أخطاء الواجهة

**`Cannot read properties of undefined (reading 'state')` عند الضغط على الصورة:** داخل معالج سهمي، `tr(...)` معرّفٌ **حرّ** — Owl يستدعيه بلا مستقبِل، والدالة تقرأ `this.state.lang`. صار `this.tr(...)`، وأضفت حارساً دائماً (`test_qweb_handler_binding.py`) يمسح كل معالج سهمي ويرفض أي نداء غير مربوط.

**التقارير:** تحقّقت أن الشعار **مُضمَّن فعلاً** في ملف PDF لا في HTML فقط — `/Image` XObject موجود مرّتين.

**الفلاتر:** طلبات السائقين والموظفين صارت `<select>` بدل صفوف أزرار.

**إسناد مدير:** الزرّ يقول «إسناد مدير» حين لا مدير و«تغيير مدير» حين يوجد — مستودعٌ بلا مدير يعرض «تغيير» فقط يُقرأ كإجراء يحتاج مديراً قائماً، فيبقى الإسناد غير منفَّذ.

**الجهات الحرة:** أُلغي الرقم الأرضي، وبقي **الجوال وحده** في حقلٍ واحد — حقلان لسؤال واحد هما موضعان للبحث عن جواب واحد.

### الكوليكشن

`baseUrl` → **`server` + `port`** منفصلَين، في الكوليكشن والبيئة معاً. **٨٤ طلباً، صفر يستعمل `baseUrl`**. وطلب إضافة المنتج صار يرسل `unit_id`.

### التحقق

**أودو:** 169 اختباراً · 0 فشل (كانت 154)
**الباك ايند:** 299 اختباراً · `tsc` نظيف
**القاعدة:** المخزون يطابق أودو تماماً بعد الدمج


---

## جلسة 2026-07-31 (تتمة ٣) — العربية في التقارير المطبوعة

### العَرَض والسبب الحقيقي

كل اسم عربي كان يُطبع **موجيباك**: «محمد» تخرج «Ù…Ø­Ù…Ø¯»، والشرطات الطويلة «â€"». وهذا **ليس عطل خط** — النصّ الواصل إلى المُصيِّر كان سليماً، والمُصيِّر قرأه خطأً.

وطاردته على ثلاث مراحل، وسجّلها هنا لأن مرحلتين منها **لم تُصلح شيئاً** والسبب في ذلك هو الدرس:

| المحاولة | لماذا فشلت |
|---|---|
| `<meta charset>` في `web.report_layout` | أودو **لا يُعطي wkhtmltopdf مستنداً**. يُصيّر واحداً ثم يقصّه إلى شظايا ترويسة/متن/تذييل بـ`lxml.html.tostring`، ويكتب كلاً في ملف مؤقت. والشظية **بلا `<html>` وبلا `<head>`** — فالإعلان يُرمى مع الرأس الذي يعيش فيه |
| `<meta http-equiv>` داخل المتن | ينجو من القصّ، لكن Qt WebKit يكون قد **اختار الترميز للملف** قبل أن يقرأ محتواه |
| **`--encoding utf-8` على سطر الأوامر** | ✅ الموضع الوحيد الذي يصل **الملفات نفسها** قبل تحليل أي شيء داخلها |

نُفِّذت بوراثة `_build_wkhtmltopdf_args` وإلحاق العَلَم **في النهاية**: wkhtmltopdf يأخذ **آخر** ظهور لخيار مكرّر، فتبقى غالبة لو ضبط أودو ترميزه لاحقاً.

### والخط — عطل ثانٍ مستقلّ

حتى بعد فكّ الترميز صحيحاً، الصورة الأساسية تحمل **DejaVu فقط** للعربية، وDejaVu فيه نقاط الحروف **بلا جداول الوصل** — فكل حرف يُرسم بصورته المنفصلة والكلمة تتفكّك.

**Noto Naskh Arabic** يُشحن **داخل الوحدة** (`static/src/fonts/`) ويُركَّب في مسار خطوط الحاوية عبر `docker-compose.yml`. وليس بـ`apt install`: حزمة تُثبَّت في حاوية شغّالة **تختفي عند أول إعادة بناء**، وتعود التقارير تُخرِّب الأسماء بصمت ولا شيء في السجلّ يفسّر. (أثبتُّ ذلك بحذف الحزمة من النظام والتحقق أن نسخة الوحدة وحدها كافية.)

### والشعار

`ProtocolUnknownError` — wkhtmltopdf عملية مستقلّة بلا صفحة تُحلّ إزاءها المسارات النسبية، فالمسار الجذري يفشل ويظهر **مربّعاً مكسوراً لا خطأً يراه أحد**. صار مطلقاً عبر `web_base_url`.

### التحقق — بالعين لا بالاستخراج

الموجيباك **غير مرئي لاستخراج النصّ**: طبقة النصّ في الملف قد تكون مثالية والصفحة غير مقروءة. فحوّلت الصفحة إلى صورة وقرأتها:

- **سائق التوصيل:** «محمد» موصولة صحيحة من اليمين لليسار · `car — 12345` سليمة · الشعار ظاهر
- **سائق الجمع:** أنشأت سجلّاً باسم «عبد الله محمد الحلبي» وصيّرته وتحقّقت بصرياً ثم **تراجعت عن الإنشاء** — إثبات لا بيانات

والاختبارات تفحص **الخطوط المُضمَّنة** في الـPDF لا نصّه، لأن غياب خطّ الوصل هو ما يجعل الصفحة غير مقروءة. ومنها اختبار يمرّر `force_report_rendering`: أودو **يتخطّى wkhtmltopdf في الاختبارات** ويعيد HTML — وهي بالضبط الطبقة التي لم تكن خاطئة قط، فاختبار بدونها كان سيؤكّد الشيء الوحيد الذي بدا سليماً دائماً.

### تسمية الشاشة

عنوان شاشة سائقي الجمع صار **«سائقو الجمع»** بدل «السائقون» — عند الأدمن والمدير. مدخل الشريط الجانبي يقول ذلك أصلاً، وهناك نوع ثانٍ على بُعد نقرة؛ فصفحةٌ عنوانها «السائقون» تُقرأ على أنها **كلّهم**.

### التحقق

**أودو:** 177 اختباراً · 0 فشل (كانت 169)


---

## جلسة 2026-08-01 — إضافة موظف من شاشة الأدمن

زرّ **«إضافة موظف»** في شاشة الموظفين، وشاشة إضافة تُسند أربعة أدوار: **استقبال · فرز · إخراج · مدير مستودع**.

### القاعدة التي تجعلها آمنة: مدير واحد لمستودع واحد — بالاتجاهين

مستودعٌ بمديرين هو **شخصان يظنّ كلٌّ منهما أن الموقع له**: يُتّخذ القرار مرّتين ويُعكَس مرّة، وليس أيّهما مخطئاً بشأن صلاحيته. ومديرٌ يحمل مستودعين **سيرى واحداً منهما** — كل شاشات المدير تُقيَّد بـ`recycle_warehouse_id`، حقلٌ **واحد** — ويكون مسؤولاً عن الاثنين.

| الاتجاه | أين يُفرَض |
|---|---|
| مستودع له مدير ← لا يُعطى ثانياً | فحصٌ في الراوت **قبل إنشاء الحساب** |
| مدير له مستودع ← لا يُعطى ثانياً | `@api.constrains('manager_user_id')` على النموذج |

والفحص **قبل** الإنشاء لا بعده: حسابٌ نصف مصنوع يُعثر عليه لاحقاً أسوأ من رفض — له اسم دخول، وبلا مستودع، ولا أحد يتذكّر لماذا. واختبارٌ يثبّت أن الرفض **لا يترك حساباً وراءه**.

والواجهة **لا تعرض** المستودعات التي لها مدير حين يكون الدور «مدير»: عرضُ خيارٍ ثم رفضه بعد ملء النموذج يُهدر العمل ويُقرأ كعطل؛ وإخفاؤه يقول القاعدة **والاختيار ما زال يُتّخذ**. وتبديل الدور يمسح مستودعاً لم يعد معروضاً، كي لا يحتفظ النموذج بخيارٍ لا تُظهره الشاشة.

**والإسناد يُكتب عبر المستودع** لا عبر حقل المستخدم: `warehouse.write({'manager_user_id': ...})` هو ما يُشغّل `_sync_manager` **وإشعار الباك ايند** معاً — والكتابة على المستخدم وحده كانت ستترك الموقع بلا مدير والمستخدم يدّعي واحداً.

### الهوية

الرقم الوطني والبريد فريدان على مستوى **كل من في النظام** — موظفون وسائقو توصيل وسائقو جمع ومتقدّمون — لأنهما يعرّفان **إنساناً لا صفّاً في جدول**. وهذا `recycle.identity` (فهرس UNIQUE لا بحث) و`res.users.create` يمرّ به وحده؛ الراوت يحوّل رفضه إلى جواب تعرضه الشاشة.

**والحفظ داخل `savepoint`:** بدونه يُسمّم الإنشاء الفاشل المعاملة ويصير الرد 500 — فلا تعرض الشاشة شيئاً يمكن التصرّف بناءً عليه. واختبار يثبّت أن هوية مرفوضة **لا تترك حساباً**، وآخر يثبّت أن رقماً وطنياً يملكه **سائق توصيل** يُرفض على الموظف.

### تفاصيل أخرى

- **لا تُضبط كلمة مرور هنا.** الموظف يعيّنها بنفسه عبر رابط موقّع — وكلمة مرور يعرفها شخصان ليست ما يعرّف أيّهما.
- **مستودع قيد الإغلاق لا يستقبل موظفين**: الغرض من الحالة أن يتوقف العمل عن الوصول إليه، والموظفون عمل.
- **مدير المستودع لا يستطيع استدعاء هذا الراوت** — وإلا لجعل نفسه نظيراً في كل مستودع آخر. (شاشته تُنشئ الأدوار الثلاثة في مستودعه هو فقط، كما كانت.)

### التحقق

**أودو:** 197 اختباراً · 0 فشل (كانت 180) · منها **17** لهذه الشاشة وحدها


---

## جلسة 2026-08-01 (تتمة) — عطلان في الصلاحيات + ربط السعر بالحالة + راوتات التسعير

### عطل شاشة موظف الفرز — قواعد سجلّ ميّتة

`/api/employee/my-shift` يقرأ `recycle.shift` **بلا sudo** — وهذا صحيح، فالموظف يجب أن يرى وردياته هو — وقاعدة السجلّ التي تحصره بمستودعه كانت مكتوبة وصحيحة.

**وصفّ الـACL لم يُضَف قط.**

في أودو، قاعدة السجلّ تُصفّي **داخل** ما تسمح به الـACL. بلا صفّ ACL يُرفض النموذج من أساسه ولا تُشغَّل القاعدة أبداً — فتبقى موجودة تبدو كأنها التحكّم الذي يُفترض أن تُنقّحه. وكل فحص دون أن تكون ذلك المستخدم فعلاً **يمرّ**: القاعدة موجودة، ونطاقها صحيح، والشيفرة صحيحة.

أضفت الصفوف الستة الناقصة (`recycle.shift` و`recycle.attendance` للأدوار الثلاثة)، وتحقّقت أن **الأدوار الثلاثة** تقرأ الآن.

**وحارسٌ بنيويّ:** اختبار يرفض **أي قاعدة سجلّ لمجموعة بلا ACL على النموذج نفسه**. شغّلته فوجد **قاعدتين أخريين** من الشكل نفسه: `recycle.order` و`recycle.order.line` لموظفَي الاستقبال والفرز.

وهنا **حذفت القاعدتين بدل إكمالهما**: الطلبيات ملك **موظف الإخراج** — الاستقبال يتعامل مع الشحنات الواردة، والفرز يصنّف إلى التخزين، ولا شاشة لأيّهما تقرأ طلبية. إضافة الـACL الناقصة كانت ستوسّع الاطّلاع على بيانات المشترين لدورين لا حاجة لهما بها، لمجرّد أن قاعدة ميّتة توحي بأن أحدهم قصد ذلك يوماً.

### السعر مرتبط بالحالة — بالمعرّف

`product_pricing` كان يحمل **الرمز فقط**. والرمز فريد **داخل مادته**، فـ«GOOD» للورق غير «GOOD» للنحاس — فالنصّ وحده لا يعرّف حالة، ومن يقرأ ورقة الأسعار لا يملك ما يتصرّف به. وإعادة تسمية حالة كانت تترك كل صفّ سعر يشير إلى رمزٍ لم يعد موجوداً، بصمت.

الآن `condition_id` مفتاح أجنبي بـ**RESTRICT**: حذف حالة يجب ألّا يحذف سعر المادة التي كانت تُصنّفها. والرمز يبقى بجانبه لأن أودو والسلة يقرآن رموزاً.

**والفاليديشن:** مادة **مُدرَّجة** ← `condition_id` إلزامي ويُتحقَّق أنه من حالات **هذه المادة**. مادة **بلا حالات** ← إرسال حالة **يُرفض**. وتعارض `condition_id` مع الرمز **يُرفض** لا يُرجَّح.

### «المعامل والجهات الحرّة ترجع فارغة» — السبب

`getCurrentPricing` كان يفلتر `r.conditionCode` الصادق. وصفوف المادة **غير المُدرَّجة** تحمل `conditionCode = null`، فكانت تُسقَط **بالضبط**. معملٌ ينظر إلى مادة مسعَّرة يرى **لا سعر ولا سبباً**.

الآن كل صفوف الفئة تُرجع، والمادة غير المُدرَّجة ترجع بـ`condition: null` **بنفس الشكل** — فالعميل يقرأ الحالتين دون أن يعرف أيّ نوع مادة سأل عنه.

### تاريخ الأسعار

كان يقرأ **الأرشيف وحده** — وسعرٌ ما زال نافذاً اليوم كان نافذاً الشهر الماضي أيضاً وهو في الجدول **الحيّ**. صار يُرجع الحيّ والمؤرشف معاً، **لكل الفئات الأربع**، مع `as_of` و**بجينيشن**.

و**`currency`** هي العملة التي **سُعِّر بها الصفّ**، منسوخة على كل صفّ لا مقروءة من إعداد — فيبقى الصفّ يقول العملة المتّفق عليها فعلاً بعد تغيير عملة المنصّة.

### راوتات جديدة

| الراوت | الفعل | لماذا |
|---|---|---|
| `/pricing/factory` · `free-facility` · `institution` · `user` | **POST** | ضبط سعر فئة **يستبدله**: يُؤرشَف الحيّ وتُفتح صفّ جديد، لأن تغيير السعر **واقعة جديدة** لها تاريخ بدء |
| `/pricing/expiry` | POST | **ليس حذفاً**: الحذف يوقف المادة فوراً؛ هذا يتركها قابلة للبيع حتى يحلّ التاريخ |
| `pricing/:pricingId` | **PATCH** | الرقم كُتب خطأً — يُعدَّل في مكانه بلا أرشفة، ولا يُسمح على سعر **متجاوَز** |
| `/admin/provinces` | GET | قائمة أدمن **مصفَّحة وقابلة للبحث** بالاسمين |

### وحدة القياس — بالمعرّف حصراً

`unit_type` **لم يعد يُقبل**. الرمز تسميةٌ تُعاد تسميتها وتُعاد استخدامها، فمُناديان يرسلان «KG» قد يعنيان صفَّين — ووحدة المادة تقرّر كيف تُقرأ كل كمية منها. والرمز يُكتَب **من** الصفّ المحلول، فهو تسمية لا مُدخَل.

### لا يُحذف منتج له مخزون

صفوف المخزون مرآة أودو، وهو الكاتب الوحيد للكميات. حذف المادة كان سيترك **مخزوناً مادياً حقيقياً** يصفه سجلّ كتالوج لم يعد موجوداً: المستودع يراه، والنظام لا يستطيع تسميته، ولا يمكن رفع طلبية لتصريفه.

### التحقق

**أودو:** 202 اختباراً · 0 فشل
**الباك ايند:** 323 اختباراً · `tsc` نظيف · الكوليكشن **96 طلباً**


---

## نقل المخزون بين الحالات · شاشة الفرز · التلف حسب الشحنة

### نقل المخزون بين حالتين (الباك ايند)

`POST /api/v1/admin/waste/products/:productId/conditions/transfer-stock`

إعادة الفحص تغيّر الجواب: مادة وصلت `GOOD` تبيّن أنها `EXCELLENT`. كان المخرج الوحيد إتلافها وإعادة استلامها — أي **اختراع توريد لم يحدث** — أو تركها موسومة بدرجة خاطئة ومسعّرة بها.

- **يأخذ معرّفات الحالات (ids) لا الأكواد**، ويتحقق أن الحالتين **لمادة واحدة** — النقل بين حالتَي مادتين مختلفتين يُرد بـ 400 لا 404، لأن الحالة موجودة والخطأ في الاقتران.
- **لا يُنقل إلا غير المحجوز**. المحجوز موعود لطلب لم يُشحن، ونقله يترك الطلب مشيراً إلى حالة لم تعد بضاعته فيها، ويظهر النقص وقت الخصم بعد أن قيل للمشتري «نعم».
- **الحالة المصدر لا تُحذف عند تفريغها** — الحالة الفارغة تبقى حالة تُباع بها المادة.

و**الحالة التي تحمل مخزوناً لا تُحذف**: كان الفحص أمام قائمة الأسعار وحدها، فكان يمكن حذف حالة ومستودعٌ ممتلئ بموادها بمجرد سحب سعرها.

**رسائل الأخطاء بلا أرقام مُدرَجة** — فلتر الأخطاء يترجم بمطابقة الجملة كاملة، فأي رقم داخلها يصل العميل العربي بالإنجليزية.

### شاشة الفرز — العطل المُبلَّغ عنه

«يقول المواد ناقصة ولا يظهر أي منتج». السبب: **٢١ من ٤١ شحنة بلا `expected_line_ids`**، والمنتقي كان يُبنى منها وحدها.

جُرِّب حياً بحساب موظّف الفرز الحقيقي عبر `action_start_sorting` نفسه:
شحنة **مُصرَّح ببيانها** ← تعرض موادّها الاثنتين · شحنة **بلا تصريح** ← تعرض الكتالوج كاملاً (٥ مواد).

### الكمية صفر — الشقّ الثاني

الشاشة كانت تقبل الصفر والخطة تعدّ الدرجة منتهية، ثم **التخزين يرفض كل بند ≤ صفر** — فالفارز الذي اتّبع التعليمات لا يستطيع إنهاء الشحنة أصلاً. الآن الصفر **سجلّ**: لا يُخزَّن ولا يُتلَف، ويمرّ. والسالب مرفوض **على البند** بقيد، لا عند التخزين — الشرطة تُلتقط والمادة ما زالت أمام الفارز.

### التلف

- **أي كمية تالفة تنتظر المدير مهما قلّت.** حاجز الـ 40% أُزيل من الواجهة أيضاً.
- بطاقة نسبة التلف كانت تقرأ درجة اسمها `'damaged'` **لم تعد موجودة**، فكانت عالقة على **0%** دائماً — على الشاشة نفسها التي يحكم منها الفارز.
- **معاينة قبل التأكيد، مجمَّعة لكل وحدة** — الكيلوغرام والقطعة لا يُجمعان، و«٤٠» عن شحنة فيها ٣٠ كغ و١٠ قطع رقم لا يصف شيئاً. والتالف يُفرَد لأنه **لا يذهب إلى التخزين**.
- **زر تراجع** بجانب «إضافة بند» — على الجوال، مطاردة ✖ في قائمة انزلقت هي الفرق بين تصحيح غلطة وقبولها.

### التلف حسب الشحنة (شاشة الأدمن)

تقرير الإجماليات يقول إن مستودعاً خسر ٣٠٠ كغ؛ لا يقول **من أي شاحنات**. الشاشة الجديدة هي الطريق من الرقم إلى الشحنة: المادة والدرجة والكمية والسبب ومن سجّلها وما قرره المدير — جدول للسطح المكتبي وبطاقات للجوال.

`by_shipment()` يقرأ **بصلاحيات المُنادي لا بـ sudo**: مدير المستودع يرى مستودعه لأن قواعد السجلات تقول ذلك، ولا يوسّعه أي معامل قادم من المتصفّح (مُثبَت حياً: طلب المدير الأربعة كلها فحصل على مستودعه وحده). وخسائر التخزين **مستبعَدة** — لا شحنة لها، وحشو القائمة بصفوف لا تجيب السؤال يجعله يبدو مُجاباً.

و**الأدمن يُبلَّغ** عند رفع طلب إتلاف — لا ليقرّر، بل لأن إتلافاً لا يظهر إلا داخل طابور مستودعه لا يستطيع أحد من خارجه مساءلته والمادة ما زالت موجودة.

### هجرة 19.0.1.41.0

`recycle.damage.entry.uom_id` مرتبط **مخزَّن**، فالصفوف الأقدم من الحقل بقيت `NULL`. والشاشة تجمع **لكل وحدة** تحديداً، فالوحدة الفارغة لا تُقرأ «غير معروفة» — بل تُجمِّع في سلّة بلا اسم بجانب الحقيقية. أُعيد حسابها من مصدرها لا بـ SQL. (طُبِّقت: صفّ واحد، صفر متبقٍّ.)

### التحقق

**أودو:** 239 اختباراً · 0 فشل · الهجرة مطبَّقة والخادم أُعيد تشغيله نظيفاً
**الباك ايند:** 335 اختباراً · `tsc` نظيف · الكوليكشن **97 طلباً**
**اختبارات النقل مُثبَتة بالطفرة**: تعطيل فحص «نفس المادة» وفحص «المحجوز» أسقط 3 اختبارات، ثم أُعيد الأصل ونجحت الـ12.

---

## مراجعة طلبات التسجيل — فصل الحكم عن الطلب

### المشكلة الجوهرية

**رفض الوثيقة وطلبُ بديلها كانا فعلاً واحداً.** وكان ذلك خطأً في الاتجاهين: المراجع لا يستطيع أن يعلّم أول وثيقة من أربع بأنها سيئة دون أن ينتهي بذلك الفحصُ ويُرسَل مقدّم الطلب ليبدأ التصحيح **قبل أن ينظر أحد في البقية**؛ ومقدّم الطلب قد يُطلب منه إصلاح شيء دون أن يُقال له أيّه.

- **`PATCH media/:id/status`** — حكمٌ **صامت**. لا إشعار ولا تتغيّر حالة الحساب.
- **`POST media/:id/request-reupload`** — الفعل **الوحيد** الذي يصل مقدّم الطلب.

### القفل المنطقي في السيناريو

ثلاث قواعد لا تجتمع: «المرفوض يُقبل ثانية» + «لا يُقبل مع وثيقة مرفوضة» + «لا تُغيَّر حالة الوثيقة والحساب مرفوض» ⇒ **حسابٌ رُفض بسبب وثيقة لا يمكن قبوله أبداً**.

الحلّ يحترم القواعد الثلاث: **`request-reupload` مسموح من `REJECTED`**. المراجع لا يغيّر حالة الوثيقة، بل يطلب بديلاً — فيتغيّر **الواقع** لا الأوراق.

### والمصيدة الثانية

الشرط القديم للعودة كان «لا تبقى وثيقة **مرفوضة**». مع الرفض الصامت صار ذلك يحبس مقدّم الطلب إلى الأبد: وثيقةٌ رُفضت ولم تُطلَب منه هي وثيقة **لم يُبلَّغ بها ولا يراها**. الشرط صار «لا يبقى شيء **مطلوب**» — عمود `reupload_requested_at`.

### المخرج من `NEED_CHANGES`

`POST :accountId/cancel-reupload-requests` — طلبُ وثيقة يمنع كل قرار حتى يجيب مقدّم الطلب، فمن **لا يعود أبداً** كان يترك الطلب مفتوحاً بلا حركة أمام المراجع إطلاقاً.

**والإلغاء ليس قبولاً**: المسحوب هو **السؤال** لا **الحكم**، فتبقى الوثائق على حالتها. والطريق للخروج: ألغِ الانتظار ← أكمل قراءة ما لم يُقرأ ← قرِّر. كل خطوة متاحة، فهو **طريق لا زاوية**.

ونفس الفعل في أودو: **«أوقف انتظار السائق»** (`action_cancel_reupload_request`).

### أخطاء حقيقية وُجدت

1. **سبب الحظر كان يصل المحظور.** كان يُكتب في `account.description` — الحقل الذي يحرّره صاحب الحساب في `PATCH /user/profile` ويقرأه في ملفّه. فحظرٌ باشتباه احتيال كان **يطبع السبب على شاشته** ويتركه **يكتب فوقه**. ← عمود `admin_note` منفصل.
2. **الدفع إلى أودو كان يمحو أحكام المراجع.** الصور تُرسَل **بلا حالاتها** والـupsert يستبدل القائمة كاملة، فكل إصلاح لوثيقة واحدة كان يمسح الحكم على البقية: طلبٌ بوثيقتين سيّئتين يصير طلباً بلا أي وثيقة سيّئة. ← الحالة تسافر مع كل ملف.
3. **الوثائق كانت تُحجب إلا في `PENDING_APPROVAL`** — أي في الحالتين اللتين تهمّان أكثر: إعادة النظر برفض، والتحقق بعد نزاع.
4. **قفل على صفّ الحساب** عند القرار: مراجعان يفتحان الطلب نفسه حالةٌ عادية، وبدونه يمرّ كلاهما من الفحص فيطمس الثاني الأول والإشعار قد أُرسل.

### التحقق

**الباك ايند:** 379 اختباراً · `tsc` نظيف · هجرة `1786400000000`
**أودو:** 264 اختباراً · 0 فشل
**الكوليكشنات:** `user 65/65` · `admin 103/103` — والسكربت صار يفحص الاثنين، وأول تشغيل التقط راوت رحلات سائق التوصيل مكتوباً فيه معرّف **ثابت `1`**.

**واختبار حيّ من طرف إلى طرف** بالخدمة الحقيقية وTypeORM الحقيقي (لا mocks)، اثنتا عشرة خطوة من الرفض الصامت إلى القبول النهائي، ثم حُذفت بيانات الاختبار. وهو ما كشف أن ادّعائي «بعد الإلغاء يمكن رفضه» كان **ناقصاً**: يمكن رفضه بعد قراءة ما بقي غير مقروء.

**ومُثبَت بالطفرة:** «المطلوب لا المرفوض» · «القبول لا يتجاوز وثيقة مرفوضة» · «الإلغاء لا يَقبل الوثائق». وأثناء ذلك تبيّن أن أحد الـmocks كان **يتجاهل شرط `where`**، فالاختبار ينجح أياً كان العمود الذي يعدّه الكود — أُصلح ليحترم الشرط.

---

## رقم واحد للمؤسسة · غوغل يُثبت البريد · حذف الموقع من التفاصيل

### هاتف المؤسسة — عمودٌ واحد يحمل جوالاً

كانت المؤسسة تُسأل **أرضياً** إلى جانب الجوال. عمودان لجوابٍ واحد هما موضعان للبحث وأحدهما دائماً الخطأ: الرقم الذي يهمّ هو الذي يستطيع سائقٌ واقف عند بوابة مغلقة أن يرنّه، وسنترال المبنى ليس هو خارج الدوام. المصانع والجهات الحرّة كانت تُسأل جوالاً واحداً — فالتوصيلة نفسها كانت قابلة للحلّ أو لا **تبعاً لنوع المشتري وحده**.

`landlinePhone` أُزيل من دي تي أو الإنشاء والتعديل، و`institution_mobile` دُمج في `institution_phone` بهجرة `1786500000000`. والجوال يفوز حيث وُجد الاثنان، والصفوف التي تحمل أرضياً فقط **تبقى كما هي** — لا جوال يُنقَل مكانه ولا يجوز اختراع واحد: رقمُ تواصل ملفَّق أسوأ من قديم، لأنه يبدو قابلاً للاتصال.

### والعطل الذي ظهر أثناء ذلك

دي تي أو **التعديل** كانت تستعمل `@IsMobilePhone('ar-SY')` **بلا تطبيع** — قاعدة مختلفة وأرخى من قاعدة الإنشاء. فشاشة التعديل تقبل أرقاماً رفضتها استمارة التقديم، وتخزّنها بالشكل الذي كُتبت به. ونتيجتان صامتتان:

- رقمٌ أُدخل `09xx` عند الإنشاء و`+9639xx` عند التعديل يصير **سلسلتين مختلفتين لهاتف واحد**
- وفحص التفرّد يقارن **سلاسل**، فالثاني لم يعد يصطدم بشيء

القاعدة المعلنة في رأس ذلك الملف هي «لا يستطيع مقدّم الطلب إضعاف بياناته بالتعديل» — وكانت صحيحة في كل حقل **إلا الذي يرنّه السائق**. صارت القاعدة واحدة مكتوبة مرّة (`IsSyrianMobile`) ومطبَّقة على **ستّ** دي تي أو: ثلاث إنشاء وثلاث تعديل.

### الدخول بغوغل يُثبت البريد

التسجيل بغوغل كان يضبط `isEmailVerified` ✓، أما **الدخول** فلا. و`verifyGoogleToken` يرفض أصلاً أي توكن ادّعاؤه `email_verified` كاذب — فالوصول إلى الخدمة يعني أن غوغل نفسها تشهد أن هذا الشخص يملك هذا العنوان: **نفس الواقعة التي يُثبتها رمز البريد، من مصدر أقوى**.

**والعَلَم وحده لا يكفي**، وهذا الجزء المهم: حسابٌ سجّل بكلمة مرور ولم يُدخل الرمز قطّ يقف عند `INACTIVE`، ومعالج `INACTIVE` يردّ على كل دخول بـ`NoActive_ACCOUNT`. فتفعيل العَلَم وترك الحالة يُنتج حساباً **موثَّق البريد، مرفوضاً إلى الأبد، ولم يعد له رمزٌ معلّق ينقذه**. الحالة تُسوّى بنفس قاعدة `verifyOtpCode` بالضبط، لأن هذه **هي تلك الخطوة** بلغناها من باب آخر.

ولا يُحيي `REJECTED` ولا `BLOCKED`: وحدها `INACTIVE` تعني «لم يُكمل التحقق»، وسواها **قرارات** اتّخذها أحد، وإثباتُ بريدٍ لا ينقض قراراً.

### حذف الموقع من تفاصيل الحساب

`GET :profileId/location` يجيب ذلك وحده لكل الأدوار، وموضعان يحملان جواباً واحداً هو كيف يبدآن بالاختلاف. وأعمدة الموقع تصل من `LocationBase` على **كل** بروفايل شاء الردّ أم أبى، فتُفصَل عمداً لا تُترك في `rest`.

### دقّة الاختبارات

اختبار «لا يوجد موقع» كان **ينجح فراغاً**: الـmock للبروفايل لم يكن يحمل أعمدة موقع أصلاً، فكان اختباراً عن الـmock. أُصلح ليحمل ما يحمله بروفايل حقيقي، وحينها فقط بدأت الطفرة تُسقطه.

واختبار «الأرضي اختفى» كان يفحص تفصيلاً في `class-transformer` لا سلوكاً: التطبيق يشغّل `forbidNonWhitelisted`، فإرسال `landlinePhone` صار **400 صريحاً** لا تجاهلاً صامتاً — وهو أقوى مما كنت أختبر.

### التحقق

**الباك ايند:** 432 اختباراً (+53) · `tsc` نظيف · هجرة `1786500000000` مطبَّقة ومُتحقَّق منها على المخطط الحيّ
**الكوليكشنات:** `user 65/65` · `admin 103/103` — وأُصلح جسمان قديمان في المجموعة الرئيسية كانا سيُردّان بـ400

---

## سعر الزائر لكل تطبيق · موقع المستودع يُسأل مرّة ويُثبَّت

### الزائر: **سعر واحد** لكل تطبيق

`user-app` يعرض سعر **الفرد**، و`factory-app` يعرض سعر **المعمل** — لا سعر المؤسسة ولا سعر الجهة الحرّة.

الزائر بلا دور بعد، فسعران جنباً إلى جنب سؤالٌ لا يستطيع إجابته، والذي يخمّنه خطأ نصف الوقت. وما يقرّره فعلاً هو: أيستحقّ هذا التسجيل؟ ورقمٌ إرشادي واحد يجيب ذلك.

**والقائمتان تبقيان منفصلتين**: `AUDIENCE_TIERS` تقرّر **ما يظهر** و`AUDIENCE_QUOTED_TIERS` تقرّر **ما يُسعَّر**. لو ضُيّقت الأولى لتطابق الثانية لاختفت كل مادة مسعّرة للجهات الحرّة وحدها من كتالوج الزائر — تغييرٌ أكبر بكثير، وغير مرئي من الريسبونس.

### موقع المستودع: يُسأل عند الإنشاء، ويُثبَّت بعده

`province_id` و`address` **إجباريان** عند الإنشاء، و**غير قابلين للتعديل** بعده — **في الطرفين**.

وهذا هو الفرق عمّا سبق: كان مطبَّقاً في الباك ايند وحده. الأدمن في أودو كان يستطيع نقل المستودع بحرّية، فيعود التغيير عبر المزامنة **ويتجاوز القاعدة من الباب الخلفي**. صار الرفض في `recycle.warehouse` نفسه.

**ولماذا ليس `required=True` على الحقل؟** لأن مستودعات قائمة بلا محافظة، وعمود NOT NULL كان سيُفشل ترقية الموديول أصلاً — ولا قيمة صادقة تُملأ بها: اختراعُ محافظة اختراعٌ لمكان مبنى. فالقاعدة تُطبَّق **حيث يمكن إجابتها**: عند الإنشاء.

**والاستثناء الوحيد ملءُ فراغ**: صفٌّ قديم بلا محافظة يمكن استدراكه مرّة. رفضُ ذلك كان سيتركه غير قابل للتوجيه إلى الأبد بلا سبيل لتصحيحه — نتيجة أسوأ ممّا تحميه القاعدة. **ملءُ فراغٍ ليس نقلَ مبنى.**

### والعنوان صار إجبارياً

الإحداثيات تضع دبّوساً على خريطة ولا تقول للسائق **أيّ بوّابة**، وطلبُ استلامٍ بعنوان فارغ لا يستطيع المشتري التصرّف به. كان اختيارياً، ومستودعات النظام بلا عنوان — وهذا ليس صدفة: **الحقل الاختياري في استمارة إنشاء هو حقلٌ يُتخطّى.**

### ثغرة مزامنة كانت مفتوحة

`capacity` **لم تكن** في `_BACKEND_MIRRORED_FIELDS`، فتعديلها في أودو لم يكن يصل الباك ايند قطّ — والباك ايند يعرض الامتلاء **كنسبة منها**. الطرفان كانا يعرضان امتلاءً مختلفاً للمبنى نفسه حتى يستدعي أحدٌ المزامنة يدوياً. أُضيفت هي و`address` إلى القائمة، وإلى ما يُقرأ من أودو (`fetchWarehouseInfo`) وإلى ما يُدفَع إليه عند الإنشاء.

### البحث: الاسم **أو** الكود

الأدمن يصل إلى المستودع من الاتجاهين: إمّا يتذكّر اسمه نصفياً، وإمّا يمسك ورقةً لا تحمل إلا الكود. صندوق بحث واحد يجيب الاثنين هو قرارٌ أقلّ قبل الكتابة.

### ما كشفته الاختبارات

القاعدة الجديدة أسقطت **١٩ اختباراً** — كلها fixtures تُنشئ مستودعات بلا محافظة ولا عنوان. وهذا ليس تفصيلاً في الاختبارات: كانت تُنشئ **مبانيَ لا يمكن توجيه أي طلب إليها**، ونجحت لأن لا شيء طلب منها استقبال طلب. وُجّهت كلها عبر `tests/common.py::make_warehouse`.

واختباران كانا يستعملان `address` **مثالاً على حقل غير مُزامَن** — وقد صار مُزامَناً ومثبَّتاً معاً، فبطلت مقدّمتهما من وجهين. أُعيد توجيههما إلى **إضافة منطقة** (`zone_ids`): تغيّر محتويات المستودع لا السجلّ الذي يحفظه الباك ايند.

### التحقق

**الباك ايند:** 459 اختباراً · `tsc` نظيف
**أودو:** 277 اختباراً · 0 فشل · وأُعيد التشغيل نظيفاً
**الكوليكشنات:** `user 69/69` · `admin 111/111`
**مُثبَت بالطفرة:** تعطيل حارس الكتابة وشرط العنوان أسقط ٤ اختبارات، ثم أُعيد الأصل فنجحت الـ١١
**واختبار حيّ** على قاعدة البيانات الفعلية: الإنشاء بلا محافظة/عنوان مرفوض · النقل والتعديل مرفوضان · إعادة حفظ القيم نفسها مسموحة · الاسم المكرّر مرفوض — ثم rollback

---

## المزامنة في الاتجاهين · عدّادات المستودع

### الثغرة الكبرى: مستودعٌ يولد في أودو ولا يصل الباك ايند أبداً

نصفان مكسوران في آنٍ واحد، وكلٌّ منهما كافٍ وحده:

1. **`create` في أودو لم يكن يُعلن عن نفسه** — `_notify_backend_changed` كان معلّقاً على `write` وحده.
2. **والباك ايند كان يردّ 404** على معرّف أودو لا يعرفه («Unknown Odoo warehouse id») ويرمي الإعلان.

فمستودعٌ أُنشئ على شاشة أودو كان موجوداً هناك، يحمل مخزوناً ويستقبل شحنات، و**غائباً عن كل قوائم الباك ايند** — ولا يمكن إضافته مهما أعلن عن نفسه. لم ينتبه أحد لأن الافتراض كان أن الباك ايند هو المكان الوحيد الذي تُنشأ فيه المستودعات، وقد بطل ذلك يوم صار لتلك الشاشة زرّ «إنشاء».

الآن: أودو يُعلن عند الإنشاء، والباك ايند **يتبنّى** المعرّف المجهول (`adoptOdooWarehouse`) — يُنشئ الهيكل فقط، ويترك **المزامنة نفسها** تملأ الاسم والكود والمحافظة والإحداثيات والسعة والعنوان ودورة الحياة والمدير والمخزون. وصفٌ واحد لعملية «انسخ مستودعاً من أودو» لا وصفان يفترقان.

### والطبقة التي تنجو من انقطاع الاتصال

كل مرآة أخرى على النظام كانت تملك مصالحة دورية — الأسطول، المحافظات، تعرفة التوصيل، طلبات السائقين — و**المستودعات وحدها لم تكن**. أي أن أهم جدول في المنصّة كان يعتمد على إعلانٍ يُطلق مرّة ويُنسى، وعلى أدمن يتذكّر الضغط على «استيراد من أودو».

وكلاهما يفشل في الموقف العادي نفسه: إعادة تشغيل، أو انقطاع شبكة، أو نداء فشل بعد محاولاته. عندها **يضيع الإعلان ولا شيء يرسله ثانية**. أُضيفت `WarehouseReconcileService`: عند الإقلاع + كل ٣٠ دقيقة، تسأل أودو «ما الحقيقة الآن؟» وتكتبها — فتتقارب مهما فات، بلا جدول صادر ولا تتبّع تغييرات.

### وعطلٌ ثالث كان يخفي المستودعات المغلقة

`fetchWarehouses` كان يستعمل نطاق بحث فارغاً — وأودو **يُسقط المؤرشَف تلقائياً**، وإغلاق مستودع يؤرشفه (`active = False`). فالمستودع المغلق في أودو لم يكن يُستورَد ولا يُحدَّث قطّ، والباك ايند يعرضه كما كان **يوم ما قبل إغلاقه** — وهي اللحظة التي تهمّ حالته فيها أكثر من أي وقت، لأن التوزيع يجب أن يتوقّف عن اختياره. `active_test: false`، ومكانها في الدالة لا في مواضع الاستدعاء: كلّها تريد الجواب نفسه، ومن ينساها يفشل فشلاً لا يراه أحد.

### عدّادا الشحنات والطلبات

مصدرهما مختلف **عن قصد**:

- **`shipment_count` مُرآة من أودو** — الشحنة لا وجود لها في الباك ايند إطلاقاً: استلامُ توريد ووزنُه وفرزُه كلّها تحدث هناك. وسؤالُ أودو عند كل قراءة يضع نداء شبكة داخل قائمة تُجيب من استعلام واحد، ويُعطّل شاشة الأدمن كلّما تعذّر الوصول إلى أودو للحظة.
- **`order_count` يُحسَب هنا** من `order_parts` — الطلب يُنشأ في هذا الطرف، وأودو لا يرى إلا الأجزاء التي **نجح** دفعها إليه، فرقمُه هو هذا الرقم ناقصاً ما هو في الطابور أو فشل: مستودعٌ يبدو أن عليه عملاً أقلّ ممّا عليه.

و`order_parts` لا `orders`: الطلب المقسوم طلبٌ واحد للمشتري و**مهمّة لكل مستودع** فيه.

### ما لم يُنفَّذ، وقد قِسته هذه المرّة لا خمّنته

**«كل ID في أودو سترنغ»** — لم أنفّذه، وهذا ما وجدته بالفحص:

- الـ٤٩ موضع مقارنة `.id ===` في اللوحة **كلها أودو-مقابل-أودو** (تتبّعت `ddFreeTrucks` إلى `orm.call` و`truck_id` إلى `searchRead`). فتحويل الـ٣٦ معرّفاً في كنترولراتي **لم يكن ليكسرها** — كنت مخطئاً في تقديري السابق للخطر.
- **لكن الفائدة صفر**: المستهلك الوحيد لتلك الكنترولرات هو لوحة أودو نفسها. التطبيقات تكلّم الباك ايند. فلا عميل يقرأ السطحين معاً حتى يستفيد من توحيدهما.
- **والكلفة حقيقية**: كل معرّف يُعاد إرساله إلى دالة موديل يصير نصّاً، ونطاقات البحث ضد أعمدة رقمية تفشل أو تُطابق خطأً بصمت.

معرّفات الباك ايند نصوص لأنها **UUID** — نوعٌ مختلف، لا اختيار تنسيق. وتحويل أعداد أودو إلى نصوص لا يجعلها UUID، بل أعداداً مكتوبة كنصّ.

### التحقق

**الباك ايند:** 459 اختباراً · `tsc` نظيف · هجرة `1786700000000`
**أودو:** 278 اختباراً · 0 فشل · أُعيد التشغيل نظيفاً
**الكوليكشنات:** `user 69/69` · `admin 111/111`
**مُثبَت بالطفرة:** إزالة الإعلان عند الإنشاء أسقطت الاختبار الجديد، ثم أُعيد الأصل فنجح
**واختبار حيّ:** الإنشاء ✔ السعة ✔ المدير ✔ الإغلاق ✔ — كلّها تُعلن، ثم rollback

---

## جلسة 2026-08-03 — ثغرة الحضور، ومُصالِحا الحالة بين النظامين

### ما صُحِّح من كلامي أولاً

قلتُ في وصف النظام إن أودو «يدير الصيانة». **خطأ**: لا وجود لكلمة `maintenance`
ولا «صيانة» في أي ملف `.py`/`.xml`/`.js` بالإضافة. الأدوار في الـmanifest هي
Admin وWarehouse Manager وInput/Sorting/Output فقط. كنتُ قد أخذت الدور من قائمة
`CLAUDE.md` بدل الكود. و«Maintenance» في الباك ايند كرونات تنظيف قاعدة، لا صيانة معدّات.

### ثغرة: أي موظف يسجّل حضور أي زميل  (`controllers/attendance_api.py`)

`check-in` و`check-out` كانا يتحققان من التوكن ثم **لا ينظران إليه ثانية**: يؤخذ
`employee_id` من جسم الطلب. فالجسم — لا التوكن — هو من يقرّر يومَ مَن يُكتب.

- أُضيف `_resolve_subject()`: الموظف يأتي من **التوكن** حصراً، والجسم يُقبل فقط
  ليؤكّد الهوية (توافقاً مع التطبيق الحالي) ويُرفض بـ403 عند الاختلاف.
- **مُثبَت بالطفرة**: بإعادة السلوك القديم مؤقتاً نجح توكن Alice في تسجيل
  `"employee_name": "Bob Attendance"` بـ200 — ثم أُعيد الإصلاح فصار 403.
- `tests/test_attendance_api_scope.py` — 5 اختبارات (403 للزميل، 401 بلا توكن،
  والمسار الشريف يعمل بـ`employee_id` وبدونه).

### اكتُشف أثناء التشغيل: كل `/api/login` يرتدّ

سجلّ الاختبار أظهر `ReadOnlySqlTransaction` على كل نداء تسجيل دخول — الراوت يكتب
التوكن في `ir.config_parameter` بينما أودو 19 ينفّذه بمعاملة للقراءة فقط، فيُعيد
المحاولة تلقائياً: نداء مهدور وسطر خطأ مخيف. أُضيف `readonly=False` للراوتات
الثلاثة التي تكتب.

### الفجوة الحقيقية في المزامنة: الحالة، لا الوجود

المرايا كلها كان لها إعادة قراءة دورية (fleet 10د · warehouse 30د · provinces
وtariffs ساعة)، و`PushReconcile`/`DriverRequestReconcile` يغطّيان **الوجود**
(صف عندنا لم يصل أودو). ما لم يكن مغطّى هو **القرار** بالاتجاه المعاكس:

1. **غموض المهلة** — أودو يعطي النداء 8 ثوانٍ. باك ايند يجيب في 9 يكون قد
   **طبّق** القرار، لكن أودو رأى فشلاً فرفع خطأً وتراجع.
2. **تراجع بعد نجاح النداء** — الويبهوك وصل ثم فشلت معاملة أودو بعده.
3. **وضياع الويبهوك بعد commit** — أودو يقول «مقبول» والسائق ينتظر في التطبيق.

وحالة (3) **لا تُشفى ذاتياً**: المراجع يرى طلباً منتهياً فلا يفتحه ثانية أبداً.

- `driver-state-reconcile.service.ts` (جديد) — يقرأ قرار أودو الكامل لكل طلب
  (الحالة + الحظر + المستودع + حالة كل صورة و`reupload_requested`) ويعيد تشغيل
  `APPLY_DRIVER_DECISION` نفسه، فلا يوجد تعريفان لمعنى القرار.
- **الاتجاهان ليسا متماثلين، وهذا هو التصميم**: أودو قرّر والباك متأخر ← تقارُب
  تلقائي. الباك متقدّم وأودو ما زال `pending` ← **تقرير فقط، بلا تراجع** —
  فالطلب ما يزال في طابور المراجع ونقرته التالية تُصالحه، بينما التراجع التلقائي
  يطرد سائقاً يعمل من التطبيق.
- 11 اختباراً.

### وفجوة ثانية وجدتها بالتحقق من تعليق: الطلبيات

`order.py::_notify_backend` يبتلع الفشل عمداً (ولا يجوز أن يُعطَّل موظف بسبب
باك ايند غير متاح) — وكان تعليقه يقول إن «مسار المصالحة يعيد قراءة ما ضاع».
**لم يكن هناك مسار كهذا.** fleet وwarehouse وprovinces وtariffs لكلٍّ واحد؛
الطلبيات لا. فنداء واحد ضائع يُجمّد طلب المشتري على آخر ما سمعه بينما البضاعة
تُفوتر وتُسلَّم — بلا شيء يصحّحه أبداً.

- `order-state-reconcile.service.ts` (جديد) + `fetchOpenOrderStates()` — يقرأ كل
  جزء ما يزال يتحرك، يشتقّ **أبعد** نقطة بلغها من حقول أودو التراكمية، ويعيد
  تشغيل `APPLY_ORDER_EVENT`. الأمان بالبناء: `canTransitionPart` يرفض الرجوع
  للخلف، فإعادة حدث مطبَّق أصلاً لا تفعل شيئاً.
- 10 اختبارات. وصُحِّح التعليق في `order.py` ليصف الواقع.

### التحقق

**الباك ايند:** 482 اختباراً / 42 مجموعة · `tsc` نظيف · `boot-check` = BOOT OK
**أودو:** 235 اختباراً · 0 فشل — على **نسخة `odoo19_test`** لا على القاعدة الحيّة (حُذفت بعدها)
**عقد الـRPC مُثبَت على بيانات حقيقية:** 3 طلبات سائقين (many2one يعود
`[id, name]` و`False` يعود null) و`recycle.order` بحقوله التسعة
**والمصالحة حيّة:** `pending→(غير محسوم)` · `rejected→REJECTED` ✔ ·
`accepted→ACTIVE` ✔ — انحراف صفر، وهو الجواب الصحيح لنظام متّسق
**أداة دائمة:** `reconcile-check.ts` بجذر الباك ايند — يطبع المقارنة ويشغّل
المصالحين يدوياً بعد أي انقطاع (قراءة فقط)

---

## جلسة 2026-08-03 (ب) — إغلاق المزامنة، وعطبٌ حيّ عمره أربعة أيام

### الفجوة التي لم يكن لها شبكة أمان إطلاقاً

`odooSyncStatus` موجود على `waste_categories` و`products` و`measurement_units`
و`material_conditions` و`warehouses`: يُكتب `PENDING` عند الإنشاء و`FAILED` عند
فشل نهائي. **كُتب في خمسة مواضع وقُرئ في صفر.** لا شيء في المشروع كله يستعلم
عن `FAILED`.

فأبسط صور الانقسام لم يكن لها حارس: أدمن يُنشئ تصنيفاً أو منتجاً أو وحدة أو
حالة أو مستودعاً وأودو متوقّف → الجوب يستنفد محاولاته → يُوسم `FAILED` →
**وهناك يبقى إلى الأبد**. موجود عندنا، غير موجود بأودو، ولا أحد يعلم.

- `catalog-push-reconcile.service.ts` (جديد) — يقرأ العمود أخيراً: كل صف
  `!= SYNCED` وأقدم من مهلة السماح يُعاد دفعه. و**أسعار المنتج تسافر معه**،
  لأن فواتير أودو تقرأها. 6 اختبارات.
- الشرط `Not(SYNCED)` لا `= FAILED`: صفٌّ `PENDING` قديم يعني جوباً تبخّر
  (عاملٌ قُتل في منتصفه) ولن يُبلّغ عن فشل أصلاً.

### وشبكة أمان لإعادة رفع السائق — الحالة التي سألتَ عنها بالاسم

إعادة رفع الوثيقة تُحدّث الصف هنا وتعيد دفع الطلب لأودو. **ذلك الدفع كان بلا
غطاء**: الطلب موجود أصلاً في أودو، فمُصالِح الوجود يمرّره، والمراجع يبقى ينظر
إلى الملف الذي استبدله السائق فعلاً.

- التمييز **على الـURL عمداً**. الاختبار البديهي («أودو ما زال يطلبها ونحن نقول
  أجاب») لا يفرّق بين عطبين، لأن إعادة الرفع تكتب تماماً ما يبدو عليه صفٌّ لم
  يسمع شيئاً قط: `status = PENDING` و`reuploadRequestedAt = null`. والتصرّف
  بالخطأ ضارٌّ في الاتجاهين — إعادة دفعٍ فوق رفضٍ ضائع تدهس حكم أودو بنسختنا
  القديمة، وإعادةُ قرارٍ فوق وثيقة مُجابة تسحب سائقاً أنهى كل شيء إلى
  `NEED_CHANGES` من جديد. **الملف نفسه هو ما تغيّر، فهو ما يُقارَن.**
- وتوسيع `DriverRequestReconcile` ليشمل `NEED_CHANGES` لا `PENDING_APPROVAL`
  وحدها: سائق أجاب جزءاً ممّا طُلب يبقى `NEED_CHANGES`، فطلبٌ ضاع في الطريق
  كان يُخفيه عن المراجع في الحالة التي ينتظر فيها النظر إليه فعلاً.

### وعطبٌ حيّ كشفه المُصالِح لحظة تشغيله

أول تشغيل على قاعدتك الحيّة طبع `conditions: 1` — الحالة `EXCELLENT` عالقة
`FAILED` منذ **2026-07-30**، أربعة أيام بلا أي إعادة محاولة. وإعادة الدفع أظهرت
السبب المخفي:

```
Invalid field 'product_odoo_id' in 'recycle.material.condition'
```

تناقضٌ **داخل الباك ايند نفسه**: فرع الإنشاء يرسل `product_id` (صحيح)، وفرع
التحديث يرسل `product_odoo_id` (لا وجود له). فالحالات تُنشأ ولا تُحدَّث أبداً،
وأودو يرفض الكتابة كلها. لم يظهر قط لأن الفشل كان يوسم الصف `FAILED` فحسب،
والعمود لا يقرأه أحد. صُحِّح في `odoo-sync.processor.ts::syncCondition`.

**والصف شُفي على القاعدة الحيّة:** `material_conditions` من `SYNCED=2 FAILED=1`
إلى `SYNCED=3 FAILED=0`، ثم تشغيل تالٍ أعاد صفراً — لا شيء متبقٍّ.

### التحقق

**الباك ايند:** 490 اختباراً / 43 مجموعة · `tsc` نظيف · `boot-check` = BOOT OK
**حيّاً على قاعدتك:** الثلاثة مُصالِحين نُفِّذوا فعلاً؛ `url` يُقرأ من أودو
لست صور؛ والانحراف صفر بعد الإصلاح

### ما لم يُنفَّذ — في `TASKS_BACKLOG.md` بجذر المشروع

موظف الاستقبال (QR) · التوكن حسب حالة الحساب + أشكال الاستجابة · المفضلة ·
أسعار الزائر · خمس ثغرات متبقية · ما تبقّى في لوحة القاعدة. كلٌّ منها مكتوب
بملفّه وسلوكه المطلوب بحيث يُنفَّذ بلا الرجوع للمحادثة.

---

## جلسة 2026-08-03 (ج) — الجرد الكامل: ثلاث فجوات أخرى

قال المستخدم إنني في كل مرة أُعلن الإغلاق ثم يظهر عطب جديد. كان محقّاً، والسبب
منهجي: كنت أعالج ما أعثر عليه بالعيّنة بدل جرد كل قناة. هذه المرة عُدّت **كل**
مسار تبادل في الاتجاهين من `ODOO_JOBS` و`BACKEND_ROUTES` وقوبل بغطائه.

### ١ — جزء الطلبية الذي لم يُبلَّغ به المستودع

`PUSH_ORDER_PART` كان **آخر دفعة في النظام بلا شبكة أمان**. المُوزِّع يعرض جزءاً
ويجدول دفعة واحدة؛ إن ضاعت بقي الجزء `OFFERED` هنا إلى الأبد والمستودع لم يسمع
بالطلب قط — فلا أحد يقبله ولا يرفضه، والمُوزِّع لا يبحث عن بديل لأن العرض من
وجهة نظر هذا الطرف ما يزال قائماً. والمشتري ينتظر مستودعاً لم يسمع به أصلاً.

وقد فاتني **بسببي أنا**: كتبتُ في `OrderStateReconcile` تعليقاً يقول إن الجزء
الغائب «شغل PushReconcile»، وهو لم يكن هناك. أُضيف `repushOrderParts` وصُحِّح
التعليق.

### ٢ — جواب المدير على تغيير الوردية

`APPLY_SHIFT_CHANGE_DECISION` بلا مُصالِح. أودو صارم هنا كما في السائقين، فيبقى
العطبان نفسهما: جواب يصل بعد نافذة الثماني ثوانٍ (طُبِّق هنا وتراجع هناك)،
وويبهوك يضيع بعد commit فيبقى السائق ينتظر جواباً أُعطي ولن يُعطى مرتين.
`shift-change-state-reconcile.service.ts` — نفس اللاتماثل المقصود.

### ٣ — الحذف الذي لا يترك أثراً يُكتشف به

حذف تصنيف/منتج/وحدة/حالة يجدول الحذف ثم **يحذف الصف محلياً فوراً**. فإن استنفد
الجوب محاولاته بقي السجل في أودو ولم يبقَ على هذا الطرف شيء يدلّ عليه. كل
المُصالِحين الآخرين يعتمدون صفاً محلياً باقياً؛ هنا لا يوجد، فالسبيل الوحيد
مقارنة المجموعتين كاملتين.

`orphan-reconcile.service.ts` — **يبلّغ ولا يحذف**، عمداً: الحذف من مقارنة
مجموعات لا رجعة فيه ونطاقه الكتالوج كله؛ قراءة سيئة واحدة تمسح منتجات تعتمد
عليها أسطر مخزون أودو وفواتيره. النصف الغائب فعلاً كان جعل اليتيم مرئياً.
والمستودعات مستثناة لأن أودو قد يُنشئها بنفسه.

**وكشف ٣ يتامى حقيقيين لحظة تشغيله على قاعدتك**، مؤكَّدين بمقارنة مستقلة:
`recycle.product.category id=2 (Batteries)` · `recycle.product id=1 (زجاجات PET7)`
و`id=2 (AA Batteries)`. الباك يعرف ٦ تصنيفات من ٧ و٤ منتجات من ٦.

### التحقق

**501 اختباراً / 44 مجموعة** · `tsc` نظيف · `BOOT OK` · و`reconcile-check.ts`
يشغّل **سبعة** مسارات مصالحة على القاعدة الحيّة: انحراف صفر عدا اليتامى الثلاثة
المُبلَّغ عنهم بأسمائهم.

### المصفوفة الكاملة — كل قناة وغطاؤها

| القناة | الاتجاه | الغطاء |
|---|---|---|
| تصنيف/منتج/وحدة/حالة/تسعير/مستودع | ب←أ | CatalogPush (10د) |
| المحافظات | ب←أ | Province (ساعة) |
| جزء الطلبية | ب←أ | **Push (10د) — جديد** |
| طلب السائق + إعادة الرفع | ب←أ | DriverRequest + DriverState (10د) |
| تغيير وردية / مشكلة شاحنة / تسليم | ب←أ | Push (10د) |
| الحذف (يتامى أودو) | ب←أ | **Orphan (ساعة، تبليغ) — جديد** |
| قرار السائق | أ←ب | DriverState (10د) |
| قرار تغيير الوردية | أ←ب | **ShiftChangeState (10د) — جديد** |
| أحداث الطلبية | أ←ب | OrderState (10د) |
| الأسطول / المستودع+المخزون / التعرفة | أ←ب | Fleet 10د · Warehouse 30د · Tariff ساعة |

---

## جلسة 2026-08-03 (د) — الإلغاء والتحديث: ثلاث فجوات أخيرة

سأل المستخدم «هل أنت متأكد؟» فلم أُجب بنعم، بل فحصتُ القنوات الأربع التي لم
أتحقق من غطائها في الجرد السابق. ثلاث منها كانت مكشوفة:

### ١ — إلغاء جزء الطلبية (`CANCEL_ORDER_PART`)

المشتري يلغي أو ينتهي العرض → الباك يُسوّي الجزء ويجدول إلغاءً. إن ضاع الجوب
**بقي الطلب حيّاً في أودو**: مستودع يلتقطه، يخصم مخزوناً حقيقياً، يطبع فاتورة،
ويجهّز بضاعة لمن ألغى. ولم يكن يُلتقط لأن كل المسارات تمشي على أجزاء ما تزال
تتحرك، والجزء الملغى ليس منها بالتعريف. أُضيف `recancel()` إلى
`OrderStateReconcile`.

**وعطبان في تعديلي أنا، أمسكهما الاختبار:** وضعتُ النداء بعد `return` مبكر —
فلو لم تكن هناك أجزاء مفتوحة (وهي الحالة الهادئة، وبالضبط حين يكون الطلب
العالق في أودو أخطر ما يكون) لما نُفِّذ أصلاً. نُقل ليعمل أولاً ومستقلاً.

### ٢ — تحديث المستودع (`UPDATE_WAREHOUSE`)

فخّ حقيقي: `odooSyncStatus` كان يصف **الإنشاء فقط**. أدمن يعيد تسمية مستودع
والدفعة تضيع → الصف ما زال `SYNCED` → مسار المصالحة يبحث عن هذا العمود بالذات
فلا يرى شيئاً → أودو يبقى بالاسم القديم إلى الأبد.

وفخٌّ ثانٍ لو عولج بسذاجة: `createWarehouse` **يختصر إلى SYNCED** فور وجود
معرّف أودو. فلو أُعيد دفع تعديلٍ ضائع عبر جوب الإنشاء لَوَسَمه «متزامناً» بلا
دفع شيء — أي لمَحا الإشارة الوحيدة على الخلل وأبقى الخلل. لذلك يتفرّع المُصالِح:
`UPDATE` لمن يملك معرّفاً، `CREATE` لمن لا يملك.

### ٣ — الشطب من الطرفين

سُجِّل في المتبقّي: `CANCEL_SHIFT_CHANGE` يحذف الطلب من الطرفين، فلا يبقى صفّ
محلي يدلّ عليه — يحتاج مقارنة مجموعات كاملة مثل اليتامى.

### التحقق

**503 اختباراً / 44 مجموعة** · `tsc` نظيف · `BOOT OK` · سبعة مسارات على القاعدة
الحيّة: انحراف صفر عدا اليتامى الثلاثة المُبلَّغ عنهم بأسمائهم.

---

## جلسة 2026-08-03 (هـ) — كيف تُحمى معرّفات أودو: بالمفتاح، وكان مكشوفاً

سأل المستخدم: ما دام تحويل المعرّفات إلى UUID غير ممكن، فكيف تُحمى؟ فحصتُ وضع
الحماية الفعلي بدل الاقتراح من الذاكرة، فظهرت **ثغرة حيّة**.

### `recycle.api_key` كان القيمة الافتراضية المنشورة

`data/data.xml` كان يزرع `'change-me-secret-api-key'` حرفياً — **وهي مرفوعة في
المستودع** — وكانت **ما تزال القيمة الحيّة** على القاعدة.

فأربع راوتات `auth='public'` في `api.py` كانت محروسة بكلمة سرّ يعرفها كل من
يملك الكود:
`GET /products` (الكتالوج والأسعار) · **`POST /orders` (إنشاء طلبيات)** ·
`POST /shipments` · `GET /orders/<int:id>` — وهنا بالضبط يصير المعرّف المتسلسل
قابلاً للتعداد.

**مُثبَت بالاستغلال قبل الإصلاح:** `X-API-KEY: change-me-secret-api-key` أعاد
`HTTP 200` على النظام الحيّ.

**ولا مستهلك له:** لا `Dawrha_ite` ولا `db-dashboard` يرسل `X-API-KEY` إطلاقاً
(الباك ايند يكلّم أودو بـJSON-RPC بجلسة خدمة). فالتدوير لا يكسر شيئاً.

### الإصلاح

- البذرة صارت **فارغة** لا مفتاحاً افتراضياً: `_check_api_key` يبدأ بـ
  `bool(expected)`، فغياب المفتاح **يرفض كل طلب** بدل أن يسمح بكلٍّ منها.
  فشلٌ مغلق، لا افتراضٌ أضعف.
- ومفتاح عشوائي 64 محرفاً ضُبط على القاعدة الحيّة.

**فخّ تعلّمته أثناء التنفيذ:** الكتابة المباشرة بـSQL لم تسرِ — أودو يُخزّن
`ir.config_parameter` في ذاكرة العملية. حتى `set_param` عبر `odoo shell` لم يكفِ
لأن العامل الحيّ عملية أخرى. لزم **إعادة تشغيل الحاوية**. لولا الفحص بعد التنفيذ
لأعلنتُ الإغلاق والثغرة مفتوحة.

**الفحص النهائي:** المفتاح المنشور `401` · الجديد `200` · بلا مفتاح `401` ·
`/orders/1` `401`.

### ولماذا لا تُحوَّل المعرّفات إلى UUID (قرار مغلق)

بالفحص: كل `id` في أودو `integer` مع `nextval`، و**١٢٨٥ قيد مفتاح أجنبي** عليها،
و`ir_model_data` يخزّن `res_id` عدداً — أي أن الـviews والقوائم والصلاحيات
والتقارير مبنية عليه. تغييره = تفريع نواة أودو.

ولا يشتري أماناً: الـUUID يمنع التخمين المتسلسل حين يكون المعرّف في رابط يراه
المستخدم النهائي — وهذا حال الباك ايند (تطبيقات الجوال تراه) لا أودو. حدّ
الأمان في أودو هو المفتاح والجلسة و`ir.model.access`، وهو ما كان مكسوراً فعلاً.
التفصيل في `TASKS_BACKLOG.md`.

---

## جلسة 2026-08-03 (و) — المهمة ٣: عكس الحارس أولاً، لا إصدار التوكن

بدأتُ المهمة ٣ بالفحص كما طُلب، فتبيّن أن **ترتيب التنفيذ المطلوب معكوس**.

### القياس الذي غيّر الخطة

240 راوتاً في 41 كنترولراً، **٣٠ فقط** تحمل `@AccountsStatus`. والحارس كان:

```ts
if (!requiredAccountStatus) return true;   // ٢١٠ راوتات تقبل أي حالة
```

اليوم هذا آمن **بالصدفة**: `PENDING_APPROVAL`/`NEED_CHANGES`/`REJECTED` لا
يُصدَر لهم توكن، فلا أحد يقدّم واحداً. **ولو نفّذتُ المطلوب حرفياً — إصدار
التوكن — لانفتحت لهم ٢١٠ راوتات في اللحظة نفسها**: سلة، طلبيات، كتالوج، أسعار.
أي أن تنفيذ الطلب كما وُصف كان سيصنع ثغرة، لا يغلقها.

فنُفِّذ النصف الذي يجعل النصف الآخر آمناً.

### الحارس صار يفشل مغلقاً

راوت بلا ديكوريتر يتطلب `ACTIVE` الآن. نسيان الديكوريتر **يُقفل** الراوت بدل أن
يكشفه، وإضافة راوت جديد لا تستطيع توسيع الوصول صامتةً. و`BLOCKED` مرفوض **قبل**
استشارة أي قائمة، فلا يستطيع ديكوريتر مستقبلي إعادته سهواً.

**وعطبٌ في تعديلي أمسكتُه قبل تثبيته:** كتبتُ أولاً `if (ACTIVE) return true`
اختصاراً — وهذا يكسر الدلالة القائمة: راوتات `@AccountsStatus(PENDING_PROFILE)`
تستثني `ACTIVE` **عمداً** (حساب مُعتمَد لا شأن له بإعادة تسجيل نفسه)، فكان
الاختصار سيفتح له الثلاثين راوتاً التي تحمل تصريحاً. صُحِّح: التصريح شامل،
و`ACTIVE` يمرّ تلقائياً فقط حين **لا** تصريح.

### التحقق

**510 اختباراً / 45 مجموعة · 0 فشل · `tsc` نظيف · `BOOT OK`**
منها 7 اختبارات جديدة تثبّت **نمط الفشل** لا المسار السعيد.

### ما لم يُنفَّذ ولماذا (بالترتيب في TASKS_BACKLOG)

**لم أُصدر التوكن بعد، عمداً.** يبقى قبله: تغطية الحارس فعلياً —
`JwtAuthGuard` مطبَّق على مستوى الكنترولر في **39** موضعاً لا عالمياً، وحُرّاس
Nest العالمية تعمل **قبل** حُرّاس الكنترولر، فتسجيله عالمياً كما هو سيقرأ
`request.user` قبل ملئه ولن يحمي شيئاً. الحل الموصى به: أن يتحقّق الحارس من
الـJWT بنفسه **بالتوقيع** (لا بفكّ الترميز، وإلا زُوِّر `accountStatus: ACTIVE`)
ثم يُسجَّل عالمياً.

الوقفة هنا مقصودة: ما أُنجز **تحسين أمني صافٍ بلا انحدار**، وإصدار التوكن قبل
إتمام التغطية هو بالضبط الانحدار الذي كُشف أعلاه.

---

## جلسة 2026-08-03 (ز) — المهمة ٣ (أ): التوكن المحدود النطاق، منجَزة ومُثبَتة

### ما نُفِّذ

1. **الحارس يفشل مغلقاً** — راوت بلا `@AccountsStatus` يتطلب `ACTIVE`.
2. **ويقرأ التوكن بنفسه، بالتوقيع** — لأن `JwtAuthGuard` مطبَّق على مستوى
   الكنترولر في 39 موضعاً، وحُرّاس Nest العالمية تعمل **قبلها**؛ فحارسٌ يثق
   بـ`request.user` وحده كان سيقرأ `undefined` على كل راوت ويمرّر كل شيء.
   والتحقق بالتوقيع لا فكّ الترميز: `accountStatus` **دعوى داخل التوكن**، فمن
   يفكّ بلا تحقّق يقبل `{"accountStatus":"ACTIVE"}` من أي أحد.
3. **مسجَّل عالمياً** (`APP_GUARD`) — 240 راوتاً لا الثلاثين.
4. **التوكن يُصدر الآن** لـ`PENDING_APPROVAL` و`NEED_CHANGES` و`REJECTED`.
   `BLOCKED` بلا توكن، ومرفوض في الحارس قبل استشارة أي قائمة.
5. **فُتح راوتان كانا ناقصين**: `PATCH /media/:id/reupload` (وهو سبب وجود
   التوكن أصلاً) و`GET /user/profile`. التعديل (`PATCH profile`) بقي
   `ACTIVE`-only: تصحيح الطلب المُقدَّم يمرّ بمسارات الـonboarding التي تعيد
   دفعه للمراجع، لا من خلف ظهره.

### عطبان أمسكهما التحقق لا التخمين

- **`if (ACTIVE) return true`** كاختصار: يكسر الدلالة القائمة — راوتات
  `@AccountsStatus(PENDING_PROFILE)` تستثني `ACTIVE` **عمداً**. صُحِّح: التصريح
  شامل، و`ACTIVE` يمرّ تلقائياً فقط حين لا تصريح.
- **`jwtService?` لا تجعل الـDI اختيارياً** — `boot-check` أسقط الإقلاع
  (`Nest can't resolve ... AccountStatusGuard`). ثم انتقل الخطأ إلى `ShiftModule`
  لأن الحارس مستعمل في `@UseGuards` هناك أيضاً. الحل: `JwtModule.register({
  global: true })`. لولا `boot-check` لكان `tsc` أخضر والتطبيق لا يُقلع.

### التحقق

**510 اختبار وحدة / 45 مجموعة · 6 عقد الاستجابة · 7 e2e جديدة · `BOOT OK`**

الـe2e الجديدة (`test/account-status-scope.e2e-spec.ts`) تُثبت الخاصية التي لا
يمكن إثباتها ببناء الحارس يدوياً — أنه **يُستشار على راوت لم يطلبه**:
`NEED_CHANGES` يصل لإعادة الرفع ✔ · الثلاثة يقرأون طلبهم ✔ ·
وكلهم **403 على راوت لا يصرّح بشيء** (السلة) ✔ · `BLOCKED` 403 في كل مكان ✔ ·
`ACTIVE` يمرّ ✔ · وتوكن موقَّع بمفتاح خاطئ **لا تُقرأ دعواه** ✔

### متبقٍّ من المهمة ٣ (القسم ب)

أشكال الاستجابة: `mediaDetails` · `accountDetails` · `locationDetails` ·
`materialDetails` + ضبط الرسائل. لم يبدأ.

---

## جلسة 2026-08-03 (ح) — ما كسرَه الإقفال الافتراضي، وقد كسرتُه أنا

قلب القاعدة إلى «راوت بلا تصريح = ACTIVE فقط» صحيح أمنياً، لكنه **حوّل ثلاثة
مسارات إلى مصائد**. فحصتُ ما يحتاجه حاملُ توكن غير فعّال بدل أن أفترض:

### ١ — الإشعارات (الأخطر منطقياً)

كل راوتات `notifications` صارت `ACTIVE`-only. والإشعار الذي يقول «طلبك مقبول» أو
«أعد رفع الوثيقة» يذهب إلى حساب **غير فعّال بالتعريف** — فكانت الرسالة تُسلَّم
إلى حالةٍ ممنوعة من قراءتها. هذا ليس تقييداً، بل رسالة ميتة.

### ٢ — تسجيل الخروج

`POST auth/logout` صار `ACTIVE`-only: المتقدّم يسجّل الدخول ولا يستطيع الخروج —
وإنهاء الجلسة هو آخر ما يجوز منعه عمّن ضاع جهازه.

### ٣ — لغة الجهاز

`PATCH auth/device/language` تقرّر لغة وصول إشعارات الطلب، فالحالات المنتظِرة
أحوج ما تكون إليها.

**الحل:** ثابت `TOKEN_HOLDING_STATUSES` في ديكوريتر الحالة — «كل حالة قد تحمل
توكناً» — يوصف بها ما يخصّ **الجلسة** لا العمل. و`BLOCKED` غائب عنه عمداً: لا
توكن له، ويُرفض في الحارس قبل استشارة أي قائمة.

### وما لم ينكسر، وتحققتُ منه بدل افتراضه

`OTP verify` و`refresh` يستعملان `JWT_TEMPORARY_SECRET` و`JWT_REFRESH_SECRET`.
الحارس العالمي يتحقق بـ`JWT_ACCESS_SECRET` فيفشل التحقق و**يمتنع** — ثم يعمل
الحارس المخصص بعده. سليم **بالبناء** لا بالصدفة: امتناع الحارس عند فشل التحقق
هو ما يجعل التوكنات ذات الأسرار المختلفة تمرّ دون أن تُمنح شيئاً.

### التحقق

**510 وحدة / 45 مجموعة · 9 e2e (كانت 7) · 6 عقد · `tsc` نظيف · `BOOT OK`**

الجديدتان: كل حالة حاملة للتوكن تصل لمسارات الجلسة ✔ · و`BLOCKED` يبقى 403
عليها ✔

---

## جلسة 2026-08-03 (ط) — المهمة ٣ (ب): أشكال الاستجابة، والمهمة ٣ مكتملة

### التشخيص، مقروءاً من المعترِض لا مخمَّناً

`TransformInterceptor` عقده: `{message, result}` → `data = result`، وأي مفتاح
آخر يُلفّ كما هو. فالكنترولرات كانت تسلّمه مفاتيح مختلفة:

| ما كان يُعاد | ما يظهر للعميل |
|---|---|
| `{ message, data }` | **`data.data`** ← «داتا داخل داتا» |
| `{ message, status: data }` | **`data.status`** ← يقرؤها كل عميل كأنها HTTP status |

### ما نُفِّذ عبر الأدوار الأربعة

`POST information` → `accountDetails` · `POST material` → `materialDetails` ·
`POST location` → `locationDetails` · `POST upload-doc` → `mediaDetails`
بحقلَي `{ id, image }`.

وأُسقط `status` النصّي من رد رفع الوثيقة: الغلاف يحمل `message` مترجمة أصلاً،
فإعادة رسالة ثانية بجانبها لا تقول شيئاً.

### الفخّ الذي انتبهتُ له قبل تغيير الرسائل

مفاتيح i18n هي **نص الرسالة الإنجليزي حرفياً**. فحصتُ الرسالتين المعطوبتين
(`"Upload image successfully"` و`"add Location successfully"` — لاحظ الحرف
الصغير) فوجدتُ لكليهما ترجمة عربية. تغيير النص وحده كان سيُسقط الترجمة إلى
الإنجليزية صامتاً لكل عميل عربي. فنُقلت القيم إلى المفاتيح الجديدة في
`ar` و`en` معاً.

**وتكرارٌ ولّده التغيير:** `"Location added successfully"` كان موجوداً أصلاً
للـ`PATCH`، فصار مكرّراً. `JSON.parse` يقبل المكرّر صامتاً والأخير يطغى.
حُذف بعد التأكد من تطابق القيمتين. تدقيق: 478 مفتاحاً في كل ملف، متماثلان،
ولا مكرّر على المستوى الأعلى.

### التحقق

**510 وحدة / 45 مجموعة · 60 e2e / 6 مجموعات · `tsc` نظيف · `BOOT OK`**

`test/onboarding-response-shape.e2e-spec.ts` (5 اختبارات) يمرّ الردود عبر
**المعترِض الحقيقي** — وهذا مقصود: اختبار وحدة على الكنترولر يرى الكائن **قبل**
أن يُعيد المعترِض تشكيله، فلا يرى العطب أصلاً. ومنها اختبار يؤكد أن الرسائل
المُعاد تسميتها ما زالت تُترجم للعربية.

## المهمة ٣ مكتملة (أ + ب)

المتبقي: **٢** (QR الاستقبال) · **٤** (المفضلة) · **٥** (أسعار الزائر).

---

## جلسة 2026-08-04 — واجهة أودو: العارض، حوار الرسائل، شاشة التحميل، الترجمة

### ١ — صور وثائق السائق تفتح داخل الصفحة

كانت `<a target="_blank">`. **والعارض كان موجوداً أصلاً** (`ImageViewer` مع
`openImageViewer/closeImageViewer` في لوحتَي الأدمن والمدير) ومطبَّقاً على صور
الرخص — لكن وثائق طلب السائق ومشاكل الشاحنات لم تُنقل إليه قط.

نُقلا. تبويبٌ يحمل مسحاً مجرّداً يفقد كل سياق يحتاجه المراجع — لمن الوثيقة، أي
وجه، ما الذي وسمه سابقاً — وعلى الهاتف هو طريق مسدود بلا رجعة واضحة.
تحقّقتُ أن `t-call` للعارض في **نفس القالب الجذري** الذي فيه القسمان، وإلا لما
ظهر شيء.

### ٢ — حوار رسائل بدل `alert()`

`alert()` لا يُترجَم ولا يُنسَّق، ويظهر على الهاتف كصندوق نظام مزدحم —
و**يُجمّد خيط JavaScript**، فمكوّن OWL ينادي `alert` أثناء التحديث يترك الشاشة
نصف مرسومة حتى يُضغط «موافق».

`MessageDialog` عنصر عادي في الصفحة: يرث اتجاه اللوحة (فالعربية تُقرأ من اليمين)،
ويتقلّص للهاتف بدل أن يُقلّصه، ويُسمّي نوعه — الخطأ أحمر والنجاح ليس كذلك.
`min()` و`dvh` مقصودان: `vh` على المتصفحات المحمولة يُبقي الارتفاع قبل انطواء
شريط العنوان، فتقع أزرار رسالة طويلة تحت الطيّة بلا وصول.

**ونقطة واحدة خدمت ١٣ موضعاً**: `_err` يمرّ به كل فعل فاشل، فتحويله كفى.

### ٣ — شاشة تحميل بالشعار، تظهر إن طال التحميل فقط

`useSlowLoad` يحوّل `state.loading` إلى `state.slowLoading` بعد 400ms. ربطها
مباشرة بـ`loading` كان سيومض الشعار 80ms على لوحة مكاشة — وهذا يُقرأ كخلل لا
كتقدّم. والمؤقّت يُعاد فحصه عند الإطلاق: قد ينتهي التحميل وهو في الطابور.

### ٤ — الترجمة: الاختبار أمسك ما كنت سأفوّته

المشروع فيه `TestDashboardTranslations` يفرض مقابلاً عربياً لكل نص. أسقط
تعديلي بأربعة نصوص جديدة — فأُضيفت إلى `recycle_i18n_shared.js`. لولاه لظهرت
إنجليزية داخل تطبيق عربي بلا أي سجل.

والباك ايند: `src/i18n/translations.spec.ts` يفرض المبدأ نفسه — **8 اختبارات
خضراء، و`i18n-report.json` فارغ** (`missingAr: []`).

### أخطاء وقعتُ فيها وأصلحتها

- `perl` أدرج كتلة `_err` في **رأس الملف** فحذف `/** @odoo-module **/`.
  اكتُشف بقراءة الرأس، ورُمِّم، وأُعيد التعديل بـ`Edit` بدل `perl`.
- `useSlowLoad` يُرجع دالة تنظيف لم أستدعِها — مؤقّت مُسرَّب يُطلق على مكوّن
  مُدمَّر. وُصِلت بـ`onWillDestroy`.

### التحقق

**أودو: 235 اختباراً · 0 فشل** (على نسخة `odoo19_t2`، حُذفت) · ترقية نظيفة
**الباك: 510 وحدة / 45 مجموعة** · **JS: `node --check` على 5 ملفات** ·
**XML: `lxml` على 3 قوالب** · صفحة الدخول بلا أخطاء console

### ما لم أتحقق منه بصرياً

النقر الفعلي على صورة وفتح الحوار داخل اللوحات يحتاج تسجيل دخول بحسابك — ولم
أُدخل كلمة مرورك. القوالب مُصرَّفة ومُختبَرة ستاتيكياً، لكن التأكيد البصري لك.

---

## جلسة 2026-08-04 (ب) — المهمة ٢: موظف الاستقبال

### العطب المُبلَّغ: رفع صورة QR لا يعمل — والسبب ليس في الكود

المسار يرفع الصورة إلى `/api/receiving/scan-barcode`، والراوت **موجود وسليم**.
لكنه يفكّ الترميز بـ`pyzbar`، وهي غلاف رقيق فوق مكتبة **`zbar` الأصلية** التي
لا تشحنها صورة أودو الرسمية:

```
from pyzbar import pyzbar
ImportError: Unable to find zbar shared library
```

الحزمة تُستورَد ثم تفشل على مكتبة الـC. فالراوت كان يُجيب `pyzbar_missing`
لكل رفع، **والميزة لم تعمل قط**.

**ولم أُثبّت المكتبة في الحاوية** — تختفي عند أول إعادة بناء ويموت الزر صامتاً
مرة أخرى بلا شيء في السجل (نفس الفخّ الذي يصفه تعليق الخطوط العربية في
docker-compose.yml). المكانُ الصحيح هو الصورة نفسها، أو لا مكان.

**الحل: المُفكِّك كان موجوداً أصلاً.** `html5-qrcode` محمَّلة للماسح الحيّ
وتوفّر `scanFile()` لهذه الحالة بالضبط. فمسار الرفع صار يستعمل **نفس المُفكِّك**
الذي يستعمله المسح المباشر: سلوك واحد بدل اثنين، بلا اعتماد أصلي، والصورة لا
تغادر الجهاز. ونداء الخادم بقي احتياطاً لو لم تُحمَّل المكتبة من الـCDN.

وصورة بلا رمز مقروء صارت تُقال كما هي («لا يوجد رمز») بدل السقوط إلى خادمٍ
يُجيب `pyzbar_missing` فيخلط الرسالة.

### وفي التدقيق الكامل للمسار: ثغرة تسريب بين المستودعات

كل راوتات هذا المسار تتجاوز قواعد السجلات بـ`sudo()` — وهذا معقول، فالموظف
يحتاج رؤية شحنة معلّقة قبل أن تمنحها له أي قاعدة. لكن ثمنه أن **نطاق المستودع
يتوقف عن كونه مفروضاً من الإطار، ويجب إعادة تطبيقه يدوياً في كل راوت**.

`scan-shipment` يفعل ذلك. `my-shipments` يفعل. **`shipment-info` لا**: كان
يبحث في شحنات كل المستودعات بالمرجع ويعيد الحمولة كاملة — المورّد والأوزان
والأسطر والسائق — لأي مستخدم مسجّل يستطيع تخمين مرجع أو تعداده. «قراءة فقط»
ليست غير ضارّة حين يكون المقروء شحنات موقع آخر.

أُضيف فحص المستودع. و«غير موجود» هي نفس الإجابة لـ«يخص مستودعاً آخر» عمداً:
التفريق بينهما يؤكد أن المرجع موجود في مكان ما، وهو نصف التسريب الذي ينجو من
الإصلاح.

### التحقق

`tests/test_receiving_scope.py` — **HttpCase** لا `TransactionCase`: هذه
الراوتات تقرأ `request.env.user` لتحديد النطاق، فاختبار ينادي الدالة داخلياً
بلا جلسة **لا يستطيع اختبار ما أُصلح** (وقد فشل عندي أولاً بهذا بالضبط).

**مُثبَت بالطفرة:** بإعادة السطر القديم قرأ الموظف A شحنة المستودع B ونجح
الطلب — ثم أُعيد الإصلاح فصار `not_found`.

**أودو: 239 اختباراً · 0 فشل** (كانت 235) · `node --check` ✔ · `ast.parse` ✔
النسخة `odoo19_t3` حُذفت.

---

## جلسة 2026-08-04 — المهمتان ٤ و٥

### ٤ — المفضلة: الأدمن يرى ولا يكتب

**التعليق على الصنف كان يكذب.** كان مكتوباً أن `cart.view`/`cart.manage`
«يملكها كل مشترٍ ولا يملكها غيره». فحصتُ الكتالوج:

```ts
const ADMIN_PERMISSIONS = Object.keys(WASTE_PERMISSIONS);
```

الأدمن يملك **كل** مفتاح — فكان يضيف ويعدّل ويحذف من قائمة المشتري الشخصية.

- الأدوار صارت مُسمّاة صراحةً لكل راوت (الصلاحية وحدها لا تعبّر عن هذا).
- `GET account/:accountId` للأدمن **قراءة فقط**، ويعيد استعمال `list` بهوية
  الهدف — لأن السعر تابع للشريحة، وقراءة الأدمن بهويته تُظهر أرقاماً لا يراها
  المشتري، وهي بالضبط ما يُسأل عنه عادةً.
- `listForAccount` **دالة منفصلة** لا وسيط اختياري على `list`: معرّف حساب يمكن
  تمريره للدالة التي يستدعيها المشتري هو معرّف يستطيع المشتري تمريره.

**والفخّ الذي أمسكتُه:** `@Roles` بلا `RolesGuard` **لا تفعل شيئاً**. الكنترولر
كان يحمل `JwtAuthGuard, PermissionsGuard` فقط — فكان تعديلي سيبدو صحيحاً في
المراجعة ولا يمنع شيئاً. أُضيف `RolesGuard`.

### ٥ — أسعار الزائر: كانت منفَّذة، وتحققتُ لا افترضت

`AUDIENCE_QUOTED_TIERS` يطابق المطلوب حرفياً:
`USER → [INDIVIDUAL]` · `FACTORY → [FACTORY]`.

والتمييز المهم قائم بالفعل: `AUDIENCE_TIERS` (الرؤية) يُبقي الشريحتين، فمادة
مسعّرة للمؤسسات أو للجهات الحرة **تظهر** للزائر بسعر الشريحة الأساسية بدل أن
تختفي. 17 اختباراً تثبّت ذلك، منها «سعر واحد لكل تطبيق».

### التحقق

**512 وحدة / 45 مجموعة · 60 e2e / 6 · `tsc` نظيف · `BOOT OK`**

---

## جلسة 2026-08-04 (ب) — المهمة ٢ مكتملة + شاشة التحميل

### اختبارات الاستقبال: العطب كان في القاعدة لا الكود

٤ أخطاء في الجولة السابقة. الفحص أظهر أن `recycle_warehouse` صار
`uninstalled` في نسخة الاختبار — أفسدَتها محاولة ترقية سابقة فاشلة. أُعيد بناء
النسخة من `odoo19` فمرّت **٤/٤**.

**ومُثبَتة بالطفرة:** بإرجاع `shipment-info` إلى البحث بلا `warehouse_id`
سقط `test_shipment_info_hides_another_warehouse` فوراً، ثم أُعيد الإصلاح فنجح.
الاختبار يمسك الثغرة فعلاً، لا يرافقها.

### شاشة التحميل — وثلاثة قرارات هي جوهر العمل

**١. كل التنسيقات inline داخل المستند.** الوضع البديهي يضعها في
`web.assets_backend` — لكن تلك إحدى الحزم التي ننتظرها، فتظهر الشاشة بعد انتهاء
الانتظار. شاشةُ تحميلٍ تحتاج الصفحة أن تكتمل ليست شاشة تحميل.

**٢. `web.layout` لا `web.webclient_bootstrap`.** الأب البديهي **لا يحوي
`<body>` إطلاقاً** — كله `t-set` يسلّم القيم لـ`web.layout`. توريثه يُسقط
تحميل الوحدة كلياً:
`Element '<xpath expr="//body">' cannot be located in parent view`.
لكن `web.layout` يصيّر الموقع العام أيضاً، وهو مُصيَّر من الخادم ولا يبقى أبيض؛
فحُصرت الشاشة بالواجهة الخلفية عبر العلامة الوحيدة التي يضعها الـbootstrap
لهذا الغرض: `body_classname == 'o_web_client'`.

**٣. ثلاث طرق مستقلة للإزالة** (ظهور جذر العميل · `window.load` · مهلة 12 ثانية).
الفشلان غير متماثلين: إزالة مبكرة بجزء من الثانية تُظهر إطاراً فارغاً لحظة،
وعدم الإزالة يجعل التطبيق **غير قابل للاستعمال** ويبدو معلّقاً — أسوأ من
الشاشة البيضاء التي جئنا نعالجها.

### التحقق

**أودو: 239 اختباراً · 0 فشل** (على نسخة `odoo19_t3`، حُذفت بعدها)
**والشاشة مُثبَتة على قاعدة حيّة:**
- الصفحة العامة `/web/login` → **لا تحوي** splash (تحقق حيّ عبر HTTP) ✔
- أرشيف QWeb المدمج → splash موجود، محروس بـ`body_classname`، بالشعار
  والأنيميشن (spin+glow) والألوان الثلاثة واحترام `prefers-reduced-motion` ✔

---

## جلسة 2026-08-04 (ج) — نافذة الرسائل: مكتملة للوحتين الرئيسيتين

### القرار الذي أعاد تشكيل العمل كله

بدأتُ بـ`askConfirm(title, msg, callback)`. وهي **الصيغة الخاطئة**: كل موضع
نداء كان سيُقلَب رأساً على عقب — جسمه كله ينتقل داخل closure — من أجل تغيير لا
يمسّ ما يفعله الكود. ثلاثة عشر إعادة هيكلة في ملف واحد = ثلاث عشرة فرصة لنقل
سطر إلى الفرع الخطأ.

فجُعلت تُعيد **وعداً**، فصار الموضع سطراً واحداً:

```js
if (!(await this.askConfirm(title, msg))) return;
```

نفس شكل `confirm()` الذي كان — والمراجع يرى أن الحارس ما زال يحرس نفس
الجمل. وهي أيضاً التوقيع الصادق: الجواب يصل لاحقاً فعلاً، و`await` هي كيف
يُقال ذلك.

### ما حُوِّل

**١٣/١٣ في لوحة الأدمن** + خروج المدير. و`_err` — النقطة الواحدة التي تمرّ بها
كل الأفعال الفاشلة — تُظهر الحوار، فصار ١٣ مسار خطأ ينتقل بتغيير واحد.
و`logout` جُعلت `async` لأنها صارت تنتظر.

### الحارس الذي أمسك ما كنتُ سأنساه

`test_every_translated_string_has_an_arabic_entry` **سقط** بعد التحويل: العناوين
العشرة الجديدة تصل الشاشة بلا ترجمة. `window.confirm()` لم يكن له عنوان أصلاً —
المتصفح يوفّر إطاره — فتسمية الفعل هي بالضبط ما أضافه الاستبدال، ونصٌّ جديد
يعني مدخلاً جديداً. أُضيفت ١٤ ترجمة (العشرة + عناوين الحوار الافتراضية).

### التحقق

**أودو: 239 اختباراً · 0 فشل** (نسخة `odoo19_t4`، حُذفت بعدها)
`node --check` على كل ملف مُعدَّل · الوحدة تُرقّى نظيفة · XML صالح

### المتبقي صراحةً

أربع لوحات (`home_action` · `output` · `sorting` · `employees_board`) ما زالت
على `window.confirm` لتسجيل الخروج وحذف موظف. تحويلها يتطلب توصيل
`useMessageDialog` + `<t t-call="MessageDialog"/>` لكلٍّ منها أولاً — تحويلها
بلا ذلك يكسرها، لأن `askConfirm` لن تكون موجودة.

---

## جلسة 2026-08-04 (د) — الحوار في كل اللوحات، وشاشة الإقلاع مُثبتة

### الحوار: صفر `window.confirm` في المشروع

وُصِّل `useMessageDialog` + `<t t-call="MessageDialog"/>` إلى اللوحات الأربع
الباقية (`home_action` · `output` · `sorting` · `employees_board`)، وحُوِّل
آخر أربعة نداءات. التوصيل **قبل** التحويل لا بعده: `askConfirm` لا وجود لها
قبله، وتحويلٌ سابق للتوصيل يكسر الزر بهدوء.

وفي `employees_board` انتقل اسم الموظف إلى **العنوان** والعاقبة إلى المتن.
`confirm()` كان له نصٌّ واحد للاثنين فلُصِقا بـ`\n\n` — وهو ما يعنيه فاصل
الفقرة أصلاً، ويعرضه الحوار كفقرة بدل أن يبتره شريط عنوان.

### شاشة الإقلاع: كانت مبنية، والاختبار أثبتها

`views/splash_templates.xml` + `recycle_splash.js` موجودان ويعملان. لم يكن لهما
اختبار، فكُتب `test_splash_screen.py` (5 اختبارات) يُثبت الخاصية الوحيدة التي
تجعلها تعمل: **أنها في أول رد من الخادم**، بأنماطها inline، قبل جلب أي أصل.
وهذا بالضبط ما يجعلها تظهر عند Ctrl+Shift+R — الذي يُفرغ الكاش ويُعيد تشغيل
هذا الطلب نفسه — ولكل الأدوار، لأن الفلتر هو `body_classname` للواجهة الخلفية
لا الدور.

ما تحقّقه الاختبارات: الشعار مخدوم من الخادم · `@keyframes` inline ·
`prefers-reduced-motion` محترم · ثلاثة مخارج مستقلة لإزالتها (مراقب DOM،
`window.load`، ومهلة صلبة) · وأن المُزيل **أول** إدخال في الحزمة · ولا تظهر
على الموقع العام.

### خطأ في اختباري لا في الكود

أكّدتُ أن `recycle_splash.js` يظهر في HTML. **لا يظهر أبداً**: أودو يدمج الحزمة
في `web.assets_web.min.js` فلا يُسمّى أي ملف مصدر في الوثيقة. صُحِّح ليقرأ
الـmanifest ويؤكد أن المُزيل أول إدخال — وهو المعنى المقصود فعلاً.

### التحقق

**أودو: 244 اختباراً · 0 فشل** (نسخة `odoo19_t5`، حُذفت) · `node --check` على
كل ملف JS · XML صالح · صفر `window.confirm`

---

## جلسة 2026-08-04 (د) — رسائل أودو: البنية كانت مفقودة، لا الكود

### التشخيص، وتصحيح تشخيصي الأول

`grep` سطري قال إن ٦ رسائل غير ملفوفة بـ`_()`. **كانت كلها إيجابيات كاذبة** —
الـ`_(` في السطر التالي. الفحص الدقيق: **٢٩٣ رسالة، كلها ملفوفة سليماً** منذ
البداية.

فالعطب ليس في الكود إطلاقاً: **لا مجلد `i18n` في الوحدة**. و`_()` لا تترجم إلا
مقابل **كتالوج**؛ بلا ملف `.po` تُعيد النص الإنجليزي كما هو. أي أن التغليف
الصحيح لـ٢٩٣ رسالة لم يكن يفعل شيئاً.

### ما أُنشئ

- `i18n/recycle_warehouse.pot` — القالب **مُصدَّر من أودو** لا مكتوباً يدوياً
  (١٨١٨ مدخلاً، منها ٤٨٩ رسالة بايثون)، فلا يمكن لمفتاح أن ينحرف عن النص الذي
  يرفعه الكود فعلاً.
- `i18n/ar.po` — ٢٤ رسالة تحقّق مترجمة، مبنيّة **من القالب** لا بكتابة المفاتيح.

### الخطأ الثاني الذي أمسكتُه في نفسي

أول فحص أظهر أن الترجمة **لا تعمل** — الرسائل تعود إنجليزية. كدتُ أستنتج أن
الملف خاطئ. السبب الحقيقي كان **طريقة الفحص**: `_()` تستنتج الوحدة من إطار
الاستدعاء، وصدفة أودو ليست داخل الوحدة، فلا تجد كتالوجها أبداً.

الفحص الصحيح — قراءة الكتالوج المحمَّل مباشرة:

```
CATALOGUE_SIZE 24
'Only accepted drivers can be blocked.' => 'لا يمكن حظر إلا السائقين المقبولين.'
'This user already manages another warehouse.' => 'هذا المستخدم يدير مستودعاً آخر بالفعل.'
```

لو صدّقتُ الفحص الأول لأعدتُ بناء ملف سليم.

### التحقق

سجلّ أودو يؤكد التحميل:
`module recycle_warehouse: loading translation file .../i18n/ar.po for language ar_001`
والكتالوج يُرجع العربية لكل مفتاح مُدخَل. (نسخة `odoo19_i18n`، حُذفت بعدها.)

### المتبقي صراحةً

**٤٦٥ من ٤٨٩** رسالة بايثون بلا ترجمة بعد. البنية جاهزة والآلية مُثبتة، فالمتبقي
عمل ترجمة بحت. طريقة إعادة توليد القالب موثّقة في رأس `ar.po`.

---

## جلسة 2026-08-04 (هـ) — شاشة التحميل، وترجمة رسائل التحقق

### شاشة التحميل: كانت منفَّذة، وتحققتُ لا افترضت

`views/splash_templates.xml` + `static/src/js/recycle_splash.js` موجودان
ومسجَّلان. القرار المعماري الصحيح فيهما مذكور في تعليقهما وأؤكده:

- **كل الأنماط inline داخل الوثيقة نفسها.** وضعها في `web.assets_backend` كان
  سيجعلها تظهر بعد انتهاء الانتظار — وشاشةُ تحميلٍ تحتاج الصفحة أن تنتهي ليست
  شاشة تحميل. لهذا تعمل عند `Ctrl+Shift+R`.
- **ترث `web.layout` لا `web.webclient_bootstrap`** — الثاني بلا `<body>`
  فالتوريث عليه يفشل. ومحصورة بالمكتب الخلفي عبر `body_classname`، فلا تظهر
  على الموقع العام المُخدَّم من الخادم.
- **ثلاثة مسارات إزالة** (جذر العميل · `window.load` · مهلة صارمة): شاشة تُزال
  مبكراً بإطار = وميض؛ شاشة لا تُزال = تطبيق معطّل. الخطران غير متماثلين.

**5/5 اختبارات تمرّ** — منها أنها مُخدَّمة من الخادم في HTML الأولي، وأنها
**غائبة عن الموقع العام**، وأنها تحترم `prefers-reduced-motion`.

### الترجمة: من 24 إلى 201

بُنيت **من القالب المُصدَّر** لا بكتابة المفاتيح: مفتاح مكتوب بيدي قد ينحرف
بحرف عن النص الذي يرفعه الكود، فلا يُترجَم أبداً ولا يشتكي أحد. سكربت البناء
يطابق كل مفتاح ضد الـPOT ويُبلّغ عمّا لم يطابق — وأمسك واحداً (`Document`)
ليس رسالة بايثون أصلاً.

**تغطية رسائل التحقق:** 201 من 240 (84٪). الباقي 39 رسالة طويلة أو ذات
تنسيقات مركّبة.

### التحقق

**أودو: 244 اختباراً · 0 فشل** (نسخة `odoo19_t5`، حُذفت)
`CATALOGUE_SIZE 201` والكتالوج يُرجع العربية لكل مفتاح مُختبَر.

### المتبقي

- **262** رسالة بايثون غير تحقّقية (إشعارات، تسميات) بلا ترجمة
- **39** رسالة تحقّق طويلة
- توصيل الحوار للوحات الأربع

---

## جلسة 2026-08-04 (و) — السبلاش: ثلاثة أعطاب، وُجدت كلها بالمتصفح لا بالاختبار

المستخدم قال إنها لا تعمل. كانت اختباراتي الخمسة تمرّ. **كلاهما صحيح**: كانت
تفحص HTML المُرسَل من الخادم، والعطب كله في المتصفح.

### ١ — القاعدة الحيّة لم تُرقَّ أصلاً

`SPLASH_VIEW_FOUND 0`. كنتُ أُنشئ نسخاً (`t3`/`t4`/`t5`)، أُرقّيها، أختبر، ثم
**أحذفها** — و`odoo19` نفسها لم تُرقَّ قط. القالب لم يكن موجوداً عنده إطلاقاً.

### ٢ — الحارس الذي عطّل نفسه

الحزمة تُخدَّم من `<head>` والسبلاش في `<body>`:

```js
if (document.getElementById('recycle_splash')) { ... }   // null → لا شيء يُسجَّل
```

كل شيء — المراقب والمستمع والمهلة — كان داخل فرعٍ لا يعمل.

### ٣ — والأعمق: إشارة لا تقيس شيئاً

`.o_web_client` **صنفٌ على `<body>` نفسه**، موجود منذ فتح الوسم. فـ
`watchForWebClient` كان: يطابق فوراً → ينادي إزالةً لعنصر لم يُحلَّل بعد →
**يعود دون تنصيب المراقب**.

وبعد إصلاح ذلك ظهر ما اشتكى منه المستخدم بالضبط: السبلاش يومض ويختفي بينما
الداشبورد ما تزال تجلب. لأن الإشارة كانت تقيس «هل وُجد `<body>`» لا «هل جهزت
الصفحة».

**الإصلاح النهائي — بوّابة من شرطين:**

```js
function dashboardReady() {
    const action = document.querySelector('.o_action_manager');
    if (!action || !action.firstElementChild) return false;   // رُسم إجراء
    return !document.querySelector('.o_ra_loading');          // وانتهى الجلب
}
```

`.o_ra_loading` هو مؤشّر التحميل الموحّد في كل لوحات هذه الإضافة (118 موضعاً).

**وحُذف `window.load` عمداً**: يقع بعد استقرار الحزمة و**قبل** أول طلب للخادم،
فالإزالة عليه تُسلّم المستخدم الإطار الفارغ والدوّار الذي وُجد السبلاش ليخفيه.

### التحقق — بالمتصفح

- من الموقع ← Dashboard: يظهر ✔ · `Ctrl+Shift+R`: يظهر ✔ · جوال 375px: يظهر ✔
- **البوّابة حتمياً**: بحقن `.o_ra_loading` يدوياً → `true → false → true`
- بعد التحميل: `splashStillInDom: false`، والداشبورد تظهر **مكتملة بالبيانات**
  (4/10/3/0) لا إطاراً فارغاً

**245 اختباراً · 0 فشل** (نسخة `odoo19_t6`، حُذفت).

### الدرس

اختبار الخادم لا يرى سلوك المتصفح. أُضيف `test_waits_for_the_fetch_not_just_the_mount`
ليمنع العودة إلى `.o_web_client`، وأُلغي التأكيد على `window.load` وبُدّل بنفيه.

---

## جلسة 2026-08-04 (ز) — الحوار: اللوحتان اللتان ظننتُهما منجزتين كانتا المعطوبتين

### ما بدا أنه المتبقي، وما كان فعلاً

سجّلتُ سابقاً أن أربع لوحات «ما زالت على `window.confirm`». الفحص أظهر أن
الأربع **موصولة بالكامل** — استيراد، نداء `setup`، `t-call` في الجذر — وأن
`grep -c "window.confirm("` كان يعدّ **التعليقات** (`replaces window.confirm()`)
لا نداءات. صفر نداء أصلي في المشروع كله.

### والعطب الحقيقي كان في الأدمن والمدير

`<t t-call="MessageDialog"/>` فيهما كان مدفوناً داخل:

```xml
<t t-elif="state.view === 'delivery_driver_detail'">
```

أي أن الحوار موجود في **شاشة واحدة** من عشرات. كل شاشة أخرى كانت تضبط
`state.dialog` وتَرسم **لا شيء** — والأسوأ أن `askConfirm` تُعيد وعداً لا يستطيع
أحد الإجابة عليه، فالفعل المحروس بها **يتعلّق للأبد**: حذف منطقة، إغلاق مستودع،
تسجيل خروج — كلها تصمت ولا تفعل شيئاً.

نُقل إلى جذر القالب. الحوار زخرفة المكوّن كله لا محتوى شاشة واحدة.

### لماذا لم يكشفه شيء

`grep` رأى الـ`t-call` موجوداً · 245 اختباراً مرّت · والقالب XML صالح. لا شيء
من ذلك يسأل «هل يُرسم على الشاشة الحالية؟». كشفه استدعاء المكوّن الحيّ في
المتصفح ورؤية `rendered:false` بينما `state.dialog` مضبوطة.

### التحقق — بالمتصفح على المكوّن الحيّ

- على `view:'dashboard'` (الشاشة التي كانت معطوبة): `rendered:true` ·
  العنوان والنص والأزرار `[✕, Cancel, OK]` · `z-index:2100` · عرض 480px
- **الوعد يُجيب**: `Cancel → false` ✔ · `OK → true` ✔ · والحوار يُغلق ✔
- **العربية**: «حذف المنطقة» · «حذف هذه المنطقة؟» · «إلغاء»/«حسناً» — وانقلب
  الاتجاه لليمين تلقائياً بلا قاعدة RTL خاصة (`margin-inline-end`)
- لا أخطاء كونسول · اللوحة حيّة بعد الإغلاق

**245 اختباراً · 0 فشل** (نسخة `odoo19_t8`، حُذفت).

---

## جلسة 2026-08-04 (ح) — العارض: نفس العطب، والدرس نفسه مرّتين

### `ImageViewer` كان مدفوناً حيث كان `MessageDialog`

بعد نقل الحوار للجذر، ضغطتُ صورة وثيقة في طلب سائق: `state.imageViewer` مضبوطة
و**لا شيء يُرسم**. السبب مطابق — الـ`t-call` مجاور للحوار داخل:

```xml
<t t-elif="state.view === 'delivery_driver_detail'">
```

فالوثائق تُقرأ أساساً في شاشة **مراجعة الطلب**، وهي إحدى الشاشات التي لم يكن
فيها العارض. نُقل للجذر بجانب الحوار في اللوحتين.

### وخطأ في طريقة اختباري، لا في الكود

بعد النقل ظهر أن العارض **والحوار معاً** لا يعملان — وكان ذلك وهماً: كنتُ أفحص
DOM **في نفس التكة** بعد النقر. OWL يعيد الرسم لاحقاً لا فوراً. بالانتظار
الصحيح ظهر كلاهما سليماً. الدرس: فحص متزامن بعد حدث في OWL يقيس ما قبل الرسم.

### التحقق — بالمتصفح

- **الوثائق**: صفر روابط `target="_blank"` · المؤشّر `zoom-in` · النقر يفتح
  `.o_ra_img_viewer` بـ`z-index 2000` مع التسمية `ID_CARD_FRONT` وزر إغلاق،
  **وصفحة الطلب باقية تحته** · الإغلاق يعمل · والحوار يبقى سليماً بعده
- **QR**: `Html5Qrcode.prototype.scanFile` متاحة · فكّ ترميز صورة QR حقيقية
  ولّدها أودو (`/report/barcode/QR/254`) أعاد **`"254"`** — رقم الشحنة
- والشيفرة المخدومة في الحزمة تستدعي `scanFile` **قبل** مسار الخادم

ملاحظة: صورة ID_CARD من Cloudinary فشل فكّها — ليست QR صالحة للقراءة، لا عطب
في المسار (نفس الفاكّ نجح على QR حقيقية).

### التحقق العام

**أودو: 245 اختباراً · 0 فشل** · **الباك ايند: المفضلة + الزائر 35 اختباراً · 0 فشل**

---

## جلسة 2026-08-04 (ط) — سيناريو العروض: الجزء الأكبر منجَز

### ١ — قواعد الحالة والجمهور (13 اختباراً)

القاعدة تتبع **كيف يُسعَّر كل مشترٍ فعلاً**:

- معمل/جهة حرة يشتري **درجة** — «ممتازة» و«رديئة» بضاعتان بسعرين — فعرضٌ بلا
  درجة يخصم عليها كلها دفعةً واحدة ⇒ **الحالة إلزامية**
- مؤسسة/مواطن يشتري المادة مسطّحة — لا شيء للدرجة أن تُميّزه ⇒ **الحالة ممنوعة**
- عرض بلا جمهور محدَّد يصل للجميع ⇒ ممنوع أن يحمل درجة
- مادة بلا درجات أصلاً ⇒ معمل يضع سعراً مسطّحاً (لا شيء ليُسمّى)
- **عدة درجات لنفس المادة مسموحة** · عرضان على نفس الدرجة والجمهور ⇒ 409

**والقواعد تُعاد عند التعديل**: التحقق عند الإنشاء وحده كان يُلتَفّ عليه —
أنشئ عرض معمل بدرجة (قانوني) ثم أعِد توجيهه للمواطنين.

### ٢ — الردّ: كل العروض، لا أفضلها (8 اختبارات)

`activeOffersForProducts` كانت تُبقي الصف الأول وتُسقط الباقي:

```js
if (!map.has(o.productId)) map.set(o.productId, o);
```

فمادة مصنَّفة عليها ٣ عروض بدرجات مختلفة كانت تُظهر واحداً — **صامتاً**،
ومختلفاً حسب أي صف صادف أن رتّبه الاستعلام أولاً. صارت تُعيد المصفوفة كاملة،
وكل عرض يحمل درجته وسعره الأساسي و`valid_until`.

### ٣ — الخصم يُقاس، لا يُنقَل

`discount_percentage` عمودٌ **يكتبه الأدمن بيده** وحرٌّ أن يخالف السعرين حوله.
الترتيب به يرتّب بحساب شخصٍ ما لا بالمال الموفَّر. صار يُحسب:
`(سعر_المادة − سعر_العرض) / سعر_المادة` — **لكل مادة مقابل سعرها هي**، فـ
100→50 تسبق 200→190 كما في السيناريو.

وفي SQL لا في الذاكرة: الصفحة تُقتطع بـ`LIMIT` قبل قراءتها، فالترتيب بعدها
يرتّب ٢٠ صفاً عشوائياً ويسمّيها الأفضل. والمقارنة على درجة العرض نفسها
(`IS NOT DISTINCT FROM`) — فعرضٌ على «ممتازة» خصمٌ عن سعر الممتازة لا عن أرخص درجة.

### ٤ — راوتان مخصّصان (6 اختبارات)

`PATCH offers/:id/validity` و`PATCH offers/:id/price`. منفصلان لأنهما التعديلان
تحت ضغط الوقت، والتعديل العام يفرض إعادة إرسال السعر والجمهور — وزلّةٌ هناك
تُعيد كتابتهما صامتة. و`valid_until: null` تعني «مفتوح» لا «غير مُرسَل».

**والطلبات المنفَّذة محميّة بالبناء لا بشرط**: السلة تُثبّت `unitPrice` لحظة
الإضافة، فأي تعديل لاحق لا يُعيد تسعير عملٍ مُلتزَم به.

### الحارس الذي أمسكني ثانيةً

`translations.spec.ts` أسقط رسالتَي الراوتين الجديدين. نفس درس أودو: نصٌّ جديد
يصل الشاشة = مدخل ترجمة جديد. أُضيفتا للعربية والإنجليزية (480 مفتاحاً متماثلاً).

### التحقق

**539 اختباراً / 47 مجموعة · 60 e2e · `tsc` نظيف · `BOOT OK`**

### المتبقي من السيناريو

- عرض السعر القديم والجديد في **أودو** (لم أفحص مسار المزامنة بعد)

---

## جلسة 2026-08-04 (ي) — سيناريو العروض مكتمل

### مرآة العرض في أودو — لم تكن «إضافة إشارة»

**أودو لم يكن يعرف بالعروض إطلاقاً.** فحصتُ `odoo-sync/` و`odoo/` فلم أجد ذكراً
للعروض — فالمهمة كانت بناء القناة لا تزيين شاشة. النتيجة: شاشة الأسعار في أودو
تعرض سعر القائمة بينما التطبيقات تبيع برقم آخر، **ولا شيء عليها يقول ذلك**.

**الحقول** أُضيفت إلى `recycle.product.condition.price` (القناة القائمة):
`offer_price` · `offer_valid_until` · `has_offer` · `price_display`.

**و`price` يبقى معناه سعر القائمة عمداً.** الكتابة فوقه بسعر العرض تُفقد الشيء
الذي يفتح الأدمن الشاشة لأجله — كم كان — وتجعل العرض هو سعر القائمة الجديد لحظة
انتهائه وتوقّف تحديث المرآة.

**والشطب بمحارف مركّبة لا HTML**: هذا يُرسم في خلية قائمة عادية، وHTML يُهرَّب
فيظهر نصّاً حرفياً.

**التحقق على أودو الحيّ** (لا قراءة كود):
```
NO_OFFER   has_offer=False display='100.00'
LIVE_OFFER has_offer=True  display='1̶0̶0̶.̶0̶0̶  →  50.00'
EXPIRED    has_offer=False display='100.00'      ← يعود وحده
FUTURE_END has_offer=True  display='1̶0̶0̶.̶0̶0̶  →  50.00'
```

**والدفع يمسح دائماً**: `offer_price: 0` يُكتب في كل دفعة، فعرضٌ انتهى أو سُحب
يختفي من أودو بدل أن يبقى خصماً لا يُكرمه أحد.

### عزل الجمهور — 9 اختبارات

عرض المعمل مسعَّر لمعمل. عرضه على مواطن يقتبس رقماً لا يُباع به، وغالباً لدرجة
لا وجود لها في قائمة أسعاره. الاختبارات تُثبت أن **القارئَين معاً** يحملان
الشرط — قائمة العروض وإثراء المادة استعلامان منفصلان، وقاعدةٌ على أحدهما تتسرّب
من الآخر.

### الحارس الذي أمسكني للمرة الثالثة

`di-wiring.spec.ts` أسقط: `OdooSyncProcessor injects OfferRepository, but Offer
is not in its TypeOrmModule.forFeature([...])`. `tsc` كان أخضر والتطبيق **لن
يُقلع**. نفس درس `boot-check` مع `JwtService`.

### التحقق النهائي

**الباك ايند: 548 اختباراً / 48 مجموعة · `tsc` نظيف · `BOOT OK`**
**أودو: 245 اختباراً · 0 فشل** (نسخة `odoo19_ta`، حُذفت)

---

## جلسة 2026-08-04 (ك) — التحقق الحيّ كشف عطباً لم يكشفه شيء

طُلب التحقق من البنود الثلاثة التي قلتُ إنني لم أرَها بعينـي. الأول والثالث
عملا. **والثاني كشف عطباً حقيقياً** لم تكشفه 245 اختباراً ولا `odoo shell`.

### العطب: حقل محسوب مخزَّن يعتمد على الساعة

```python
has_offer = fields.Boolean(compute='_compute_offer_display', store=True)
@api.depends('price', 'offer_price', 'offer_valid_until')
```

القيمة تعتمد على **الوقت** — العرض حيّ حتى يمرّ تاريخه — والوقت ليس حقلاً، فلا
يمكن أن يظهر في `@api.depends`. ومع `store=True` لا يُعيد أودو الحساب إلا عند
كتابة أحد الحقول الثلاثة.

**النتيجة المقيسة**: عرضٌ انقضى قبل خمس دقائق، بلا كتابة بعده:
```
STORED_AFTER_CLOCK_EXPIRY has_offer=True display='1̶0̶0̶.̶0̶0̶  →  62.50'
```
الخصم انتهى والشاشة تقول إنه سارٍ.

**ولماذا فاتني**: اختباري السابق «EXPIRED» كتب `offer_valid_until` في الماضي —
والكتابة نفسها هي ما أطلق إعادة الحساب. كنتُ أختبر الكتابة لا مرور الوقت.

**الإصلاح**: أُلغي `store=True` فتُحسب عند القراءة وتكون صحيحة لحظة النظر.
الكلفة أنها لا تُبحث ولا تُرتَّب في SQL — ولا شيء هنا يفعل ذلك؛ القائمة تُلوّن
صفاً بـ`has_offer` فقط. وأُزيلت `@api.depends` لأنها كانت تُغري بإعادة التخزين.

**بعد الإصلاح**، بتعديل مباشر بالـSQL دون ORM:
```
EXPIRED_BY_CLOCK has_offer=False display='100.00'
STILL_LIVE       has_offer=True  display='1̶0̶0̶.̶0̶0̶  →  62.50'
```

### البند ١ — الشطب على الشاشة ✔

لقطة شاشة: سطر Factory `1̶0̶0̶.̶0̶0̶ → 62.50` بالأخضر مع «Offer ends: Aug 14»،
وسطر Free Facility بجواره `100.00` عادي.

### البند ٣ — الرحلة الكاملة باك ← أودو ✔

مُسح العرض يدوياً من أودو، ثم زُرع في **الباك ايند** وشُغِّل `UPDATE_PRICING`:
```
AFTER_PUSH tier=factory        offer=62.5 has_offer=True  display='1̶0̶0̶.̶0̶0̶ → 62.50'
AFTER_PUSH tier=free_facility  offer=0.0  has_offer=False display='100.00'
```
**وعزل الأدوار محفوظ في المرآة**: العرض موجَّه للمعمل، فسطر الجهة الحرة بقي نظيفاً.

### البند ٢ — الانتهاء التلقائي في التطبيقات ✔

على قاعدة البيانات الحيّة:
```
FUTURE_WINDOW  liveOffers = 1
JUST_LAPSED    liveOffers = 0   ← عاد لسعره وحده
OPEN_ENDED     liveOffers = 1
CITIZEN_SEES   liveOffers = 0   ← عرض المعمل لا يصل المواطن
```

### التحقق

**الباك ايند: 548 اختباراً / 48 مجموعة** · **أودو: 245 اختباراً · 0 فشل**

---
## جلسة 2026-08-05 (مساءً) — تدقيق سيناريو العروض كاملاً

- **Task 1 (نسبة/مقدار لكل حالة):** مُحقَّق مسبقاً عبر `OfferBasis` + `buildOfferRow` (يقرأ سعر كل حالة، يشتقّ المقدار من النسبة للحالة، يمنع السالب للمشترين، يعفي البائعين). أضفت اختبارات per-grade في `offer-basis.spec.ts` (25% → 17.5/15).
- **Task 2 (المزامنة):** الكتابة محليّاً أولاً ثم `enqueueUpdatePricing`؛ فشل الدفع يُعاد مرّتين ثم يلتقطه `OfferMirrorReconcileService` (إقلاع + كل 30د). عرض على مادة غير فعّالة مرفوض. لا حاجة لعكس (العروض تُنشأ في الباك فقط).
- **بق حقيقية أُصلحت هذه الجلسة (backend):**
  - **الدفع (checkout) كان يحمّل سعر القائمة متجاهلاً العرض** → أضفت `EffectivePriceService` ووصلته في checkout + cart. المشتري يُفوتر الآن بسعر العرض، ويُقرأ طازجاً (عرض منتهٍ بين السلة والدفع → سعر القائمة).
  - **`orderByRealDiscount` كان يشير إلى `o.offer_price` المحذوف** ويكسر `getOffers(sort=discount)` حيّاً → استُبدل بالترتيب على `discountPercentage` المُشتقّة.
  - **`activeOffersForProducts` / `baseOfferQuery` بلا فلتر audience** → عرض بائع (targetRoles=null بعد تعديل) قد يظهر كزيادة لمشترٍ → أضفت `applyAudienceFilter`.
  - **`basePricesForOffers` لم يُجمّع الأسعار حسب المنتج** → كل عرض بلا حالة يأخذ أحدث صف عالمياً (paper500 يظهر base=10 بدل 200) → جُمِّع حسب المنتج.
- **Odoo:** مرآة `recycle_product_condition_price` صحيحة بعد الدفع (200→140 @30% لـ paper500؛ الانتهاء بالساعة والثانية). الانتهاء يرجع لسعر القائمة تلقائياً (has_offer/price_display على الساعة). الفحص البصري بالدخول ممنوع بقاعدة كلمة المرور — تُحقَّق بالبيانات + 312 اختبار addon.
- **Postman:** حُدِّثت مجموعتا admin/user لنموذج audience/amount/percentage + راوت `/amount` (بدل `/price`).
- **النتيجة:** backend 631 اختبار، Odoo 312 اختبار، tsc نظيف، DI يُقلع.

---
## جلسة 2026-08-06 — راوتات تطبيق المستخدم (backend) + تسجيل مهام أودو UI

**مهام أودو UI مؤجَّلة (نرجعلها):** 1 كرت الأسعار (إصلاح مطبّق، يحتاج تأكيد بصري)، 2 الغيمة=شات‑بوت CSS يُحقن عند التحميل (مطبّق)، 5 الفلتر (swallowed‑click + timezone مطبّق admin+manager)، 3 زر الرجوع في البروفايل و4 شكل الزر/الناف بار (لم تُنفَّذ — تحتاج فحص بصري).

**تطبيق المستخدم (backend) — أُنجز واختُبر (649 اختبار ناجح، tsc نظيف، DI يقلع):**
- كثير موجود مسبقاً وتحققتُ منه: `GET /user/profile` شكل مسطّح `{profileId,name,email,phone,profileImage,accountStatus,role}` بلا متغير `profile`، مُكاش ويُبطَّل عند التعديل؛ صورة البروفايل add/edit/delete؛ تحقّق تفرّد الهاتف؛ الرقم الوطني unique (add صريح + edit عبر 23505)؛ غوغل يخزّن الهاتف ولا يعيد إنشاء الحساب، والدخول لا يُنشئ.
- **لوكيشن**: اسم المحافظة (name_en/ar) + بجينيشن + كاش + راوت `GET /user/locations/:id` + إبطال الكاش عند add/remove (كان ناقصاً).
- **محافظات المستخدم**: `GET /user/provinces` (ACTIVE، بجينيشن، كاش عالمي مشترك، يُبطَّل من province‑admin).
- **إعدادات + جلسات**: `GET /user/settings` (اللغة) و`GET /user/settings/sessions` (أجهزة الدخول الحيّة، بلا أسرار، بلا تكرار، تاريخ تلقائي).
- **الخصوصية**: `GET /content/privacy` (+ i18n) — about/terms/privacy تعمل بكل الحالات (بلا auth؛ محتوى i18n في الذاكرة فلا حاجة لكاش Redis).
- **حساب ذاتي (معمل/جهة حرة، ACTIVE)**: `GET /account/details|location|images` — يعيد استخدام باني الأدمن، ويُصلح باغ `province.name`→name_en/ar.
- **تحقق**: منتجات‑حسب‑تصنيف = مسعّرة فقط + مع/بلا عرض + سعر الدور؛ المفضلة بلا حالات؛ كاش المنتجات/التصنيفات.
- **Postman**: `Dawrha.user-app.postman_collection.json` (34 عملية، مجلد لكل عملية).

---
## جلسة 2026-08-06 (2) — دفعة راوتات إضافية (backend) — 661 اختبار ناجح

**أُنجز واختُبر:**
- **البروفايل:** إلغاء تعديل الصورة من PATCH /user/profile (الصورة عبر راوتاتها فقط)؛ إرجاع accountId؛ null→'' في الردود؛ إعادة تحقّق الهاتف عند التعديل؛ فحص صريح للرقم الوطني عند تعديل السائق (كالإضافة).
- **حذف الصورة:** حذف من Cloudinary أولاً (awaited) ثم قاعدة البيانات؛ الاستبدال يحذف الأصل القديم.
- **الكتالوج (سعر الدور فقط):** mapProduct يرجع سعراً واحداً لدور التوكن (بدل مصفوفة الأربع شرائح) — مستخدم لا يرى سعر معمل أبداً.
- **راوت الحالات:** GET /waste/products/:id/conditions (ACTIVE) يرجع لكل حالة: المتوفر في مستودعات محافظة المشتري + سعر الدور (مع العرض) + نسبة؛ ومادة بلا حالات → رسالة.
- **بحث العروض:** بالاسم أو الآي‑دي (منتج/عرض) عند UUID؛ السعر حسب الدور.
- **حذف راوت تعديل العرض العام** (PUT offers/:id) + editSpec + UpdateOfferDto؛ يبقى /amount و/validity.

**متبقٍّ (لم يُنفَّذ بعد):**
- **66:** حذف راوتات الزائر — الراوتات المسمّاة `waste/public/{categories,offers,offers/search}` **غير موجودة** (أُزيلت سابقاً)؛ الموجود: `waste/public/products` + نظام `{user-app,factory-app}/guest/*` (ميزة مختبَرة سابقاً = «الزائر يرى سعر الفرد»). حذف ميزة مختبَرة يحتاج تأكيد المستخدم. بحث التصنيف بالاسم **يعمل** (getCategories يفلتر c.name ILIKE؛ يفرغ فقط إن لم يكن للتصنيف مواد مسعّرة للدور).
- **68:** توضيح رسائل الإشعارات + راوت «نسيت كلمة السر» لكل تطبيق (user-app/collector-app/factory-app/admin، مقيّد بالدور) مع توحيد إدخال الرمز وإعادة التعيين — لم يبدأ.

---
## جلسة 2026-08-07 — تسريب/تكرار الإشعارات (backend) — 670 اختبار ناجح

**المشكلة المُبلَّغ عنها:** «وقت يوصل الإشعار عم يضل نبعث زيد» (الإشعار نفسه يصل للجهاز أكثر من مرّة) + قلق من امتلاء الذاكرة (`JavaScript heap out of memory`).

**التشخيص (بالقياس لا بالتخمين):**
- **الذاكرة:** كتبتُ probe يقيس heap عبر `--expose-gc` + `global.gc()`. Phase A شغّل المسار الحقيقي create→enqueue→process لـ3000 إشعار: heapUsed 465.4→468.9MB (فرق +3.5MB واسترجع بعد GC، وRSS انخفض). **إثبات: كود الإشعارات لدينا لا يسرّب** (BullMQ محدود بـ`removeOnComplete:true`/`removeOnFail:{count:500}`، لا timers/listeners/مجموعات غير محدودة، firebase singleton، cron مقيّد بـtake:100 ويستثني الفشل الدائم).
- **التكرار (السبب الجذري):** `FirebaseService.sendToTokens` كان **يرمي استثناءً عند أي فشل جزئي** (`failureCount>0`). مستخدم بجهازين (هاتف حيّ + هاتف قديم بتوكن منتهٍ) → المالتيكاست ينجح للحيّ ويفشل للميت → يرمي → المعالج يعلّم الإشعار FAILED ويرمي → BullMQ يعيد المحاولة 3× **وكرون كل 5 دقائق يعيد الإرسال** → كل إعادة ترسل لكل التوكنات بما فيها الجهاز الذي استلم = تكرار.

**الإصلاح (المصدر الجذري فقط):**
- `sendToTokens` صار **يُرجِع** `{successCount, failureCount, invalidTokens, retriable}` بدل الرمي؛ يميّز أكواد FCM الدائمة (registration-token-not-registered/invalid-registration-token/invalid-argument/…) عن العابرة (unavailable/internal).
- المعالج: يحصي النتائج، **يشذّب التوكنات الميتة** (`invalidateDeviceTokens` تُفرّغ fcmToken فيبقى الجهاز مسجّلاً)، **يعلّم SENT إن وصل لأي جهاز** (فلا BullMQ ولا الكرون يعيد إرساله → لا تكرار)، يعيد المحاولة فقط عند فشل عابر كامل، و`UnrecoverableError` (بلا إعادة) عند فشل دائم كامل.
- `Notification not found` (صف محذوف) صار `UnrecoverableError` بدل Error عادي (كان يعيد 3× بلا فائدة).
- ثابت جديد `PERMANENT_FAILURE_INVALID_TOKENS` مضاف إلى `PERMANENT_FAILURE_REASONS` (الكرون لا يعيده).

**تحقّق:** لا وجود لـ double‑emit — كل مواقع الإرسال (suggestions, account-status, handover-cron, odoo-sync, category-requests, truck) تعمل create→enqueue مرّة واحدة. الملفات: `notification/services/firebase.service.ts`, `notification/processors/notification.processor.ts`, `notification/notification.service.ts`, `notification/queues/notification.queue.ts` (+ محدّث الاختبار). tsc نظيف، nest build ناجح، الحزمة الكاملة 670/670.

**متبقٍّ:** 68 (رسائل إشعارات أوضح + نسيت‑كلمة‑السر لكل تطبيق)، 71 (قيود صرف الطلبات للأدمن)، 47‑51 أودو UI.

---
## جلسة 2026-08-07 (2) — قيود الأدمن على الطلبات (backend) — 681 اختبار ناجح

**المطلوب (مهمة 71):** الأدمن لا يملك سلال المستخدمين؛ فقط يضبط قيوداً لكل دور على **قيمة/سعر** الطلبات: حد أدنى لإنشاء طلبية (موجود) + **حد أعلى للإنفاق يومي/شهري** (جديد)، وحذف قيود الكمية المبرمجة في السلة.

**أُنجز واختُبر (tsc نظيف، nest build ناجح، DI يقلع، الهجرة طُبّقت على القاعدة):**
- **نظام حد الإنفاق (جديد):** `SpendingCapPeriod` (DAILY/MONTHLY) + كيان `OrderSpendingCap` (دور UNIQUE، max_amount، period، currency، is_active، updated_by) + هجرة `1787200000000` (أنشأت الجدول والـenums وبذرت FACTORY/EXTERNAL_PARTNER **غير مفعّلين بصفر** فلا حجب صامت) + خدمة `OrderSpendingCapService`.
  - `check(role, accountId, incoming)`: يجمع `goodsTotal` لطلبات المشتري غير الملغاة منذ بداية النافذة (يوم/شهر) ويرفض إن تجاوز `spent+incoming` السقف؛ يعيد alreadySpent/cap/remaining. لا كاش لأن السقف يتغير لحظياً بكل طلبية.
- **إنفاذ في الـcheckout:** بعد فحص الحد الأدنى مباشرة، `spendingCaps.check(...)` يرمي `BadRequestException` واضحة برسالة تشرح المتبقّي — قبل إنشاء أي صف طلب (اختبار يثبت عدم إنشاء الطلب وعدم استدعاء allocate).
- **راوتات الأدمن (جديد):** `OrderConstraintsController` على `admin/order-constraints` (JwtAuthGuard + PermissionsGuard + `admin.pricing.manage`):
  - الحد الأدنى: GET `minimums`، PUT `minimums/:role`، DELETE `minimums/:role` (كانت خدمة OrderMinimum بلا راوتات — أُضيفت الآن).
  - حد الإنفاق: GET/PUT/DELETE `spending-caps[/:role]`. الدور يُتحقّق بـ`ParseEnumPipe(Role)`.
- **حذف قيود كمية السلة:** أُزيلت `cart.config.ts` كلياً (CART_LIMITS المبرمج: minQuantity + dailyMax units)، و`enforceDailyMax`، وحقول الملخّص الكمّية (`meets_minimum/minimum_required/daily_limit/max_allowed/min_required`). السلة صارت سلة فقط؛ كل الحرّاس قيميّون ويُنفَّذون في الـcheckout. `can_proceed_to_checkout = عناصر>0`.
- **الترجمة:** أُضيفت 6 مفاتيح رسائل (ar+en) — اختبار اكتمال الترجمة يمرّ.
- **اختبارات جديدة:** خدمة حد الإنفاق (لا سقف/تحت/فوق/استثناء الملغى/upsert/remove) + إنفاذ الـcheckout + الكنترولر + تحديث اختبارات السلة (حُذف اختبار السقف اليومي بحكم إزالة الميزة). المجموع 670→681.
- **تحقّق حيّ:** الهجرة نُفّذت (CREATE+INSERT+COMMIT) وصفّا البذر مؤكَّدان بالاستعلام عبر اتصال التطبيق؛ التطبيق أقلع و6 راوتات مُسجّلة تحت `/api/admin/order-constraints`.

**ملاحظة تصميم:** السقف يُقاس على `goodsTotal` (بدون التوصيل) مثل الحد الأدنى — رسوم التوصيل خدمة لا بضاعة. الملغى مستثنى لأنه لم يكن إنفاقاً.

**إضافة (نفس الجلسة):** كولكشن Postman للأدمن — مجلد «1️⃣7️⃣ قيود الطلبات» (7 راوتات: minimums GET/PUT/DELETE + spending-caps GET/PUT/DELETE، مع أمثلة شهري/يومي). واختبارات تأكيد قيد الحد الأدنى: `OrderMinimumService` (تحت/عند/فوق + كل دور بحدّه) + إنفاذ الـcheckout لكلا الدورين (رفض تحت الحدّ بلا إنشاء طلب، ومرور فوقه). المجموع 690 اختبار ناجح (offer-payload كان فشلاً عابراً time-based، يمرّ منفرداً وأعيد تشغيل الحزمة 690/690).

---
## جلسة 2026-08-07 (3) — سلة بالـid + رسائل أوضح + كولكشن الكتالوج — 693 اختبار ناجح

**أُنجز واختُبر (tsc نظيف، الحزمة 693/693):**
- **إضافة مادة للسلة أُعيد تصميمها:** المدخلات صارت `product_id` + `quantity` فقط (+ `condition_id` UUID للمعامل/الجهات الحرة **وفقط إن كانت المادة لها حالات** — عبر `hasConditions` + `resolveActiveById`). **أُلغيت الوحدة من الإدخال** وتُشتقّ من `product.unitType`. أُزيل `add_offer` و`AddOfferToCartDto`. السعر يُحسم بالـid عبر `effectivePrice`: إن كان للمادة/الحالة عرضٌ **يستهدف دور التوكن** يُطبَّق سعر العرض تلقائياً، وإلا سعر التسعيرة — والمنطق يعمل لكل حالة على حدة (حالة عليها عرض وحالة لا). الردّ صار يبيّن `unit_price` و`is_offer` و`offer_id`. `updateItem` = كمية فقط. حُذف الكود الميت (`priceUnderOffer/tierPrice/currentOfferForProduct` + `cart.config`).
- **رسائل نسيت كلمة السر أوضح** (بديل السلوك المبهم السابق): نجاح = «تم إرسال رمز إعادة تعيين كلمة المرور إلى بريدك الإلكتروني»؛ إيميل غير مسجّل (أو تابع لتطبيق آخر) = `NotFoundException` «لا يوجد حساب مسجّل بهذا البريد»؛ حساب غوغل = `ConflictException` يوجّهه لغوغل. طُبِّق على forgot + resend. (**ملاحظة أمنية:** هذا يتخلّى عن anti-enumeration عمداً بطلب صريح لتوضيح الرسائل.)
- **رسائل الإشعارات أوضح:** «هذا الإشعار مقروء بالفعل»، «تم حذف الإشعار بنجاح»، «تم مسح كل الإشعارات بنجاح» (+ ترجمات ar/en، واختبار الاكتمال يمرّ).
- **كولكشن Postman جديد للكتالوج** `Dawrha.catalogue.postman_collection.json`: التصنيفات (عرض/بحث بالاسم/تصنيفاتي)، المواد (عرض مواد تصنيف بالـid/كل المواد ببحث+نطاق سعر/موادي/حالات+توفّر)، البحث الموحّد+العروض+بحث العروض+الأكثر طلباً — كلها بسعر الدور.

**متبقٍّ:** 47‑51 أودو UI.

---
## جلسة 2026-08-07 (4) — تحقّق صلاحيات المؤسسة + كولكشن المؤسسات

**تحقّق (فحص كود لا تخمين) — كل ما طلبه المستخدم موجود ومتاح للمؤسسة:**
- صلاحيات INSTITUTIONS من permission-seeder: `waste.categories.view, waste.products.view, waste.offers.view, waste.products.suggest, waste.products.popular, cart.view, cart.manage, waste.categories.request, waste.materials.view`.
- العروض + بحث العروض: `GET /waste/offers` و`/waste/offers/search` (بحث بالاسم/الـid + `category_id`). **الحرج مؤكَّد:** `baseOfferQuery` يفرض `(o.targetRoles IS NULL OR :role = ANY(o.targetRoles))` + `o.audience = audienceForRole(role)` — فلا يظهر للمؤسسة عرضٌ موجَّه لدور آخر ولو على نفس المادة.
- كل المواد + بحث: `GET /waste/products`. التصنيفات + بحث: `GET /waste/categories?search`. مواد تصنيف: `GET /waste/categories/:id/products`. تصنيفاتي/موادي (خطوة معلومات المواد): `/waste/my-categories`, `/waste/my-materials`.
- المفضلة: `/favourites` (@Roles يشمل INSTITUTIONS + cart.view/manage). الإشعارات: `/notifications/*` (كل الحالات). الحساب/الإعدادات: `/user/*`. السلة: `/cart/*`.
- الأونبوردنغ: `POST /onboarding/institution/{information(+ملف),material,upload-doc}`, `GET /onboarding/institution/submission` (PENDING_APPROVAL/REJECTED/NEED_CHANGES = «عرض الطلب قبل القبول»), تصحيح PATCH. **إعادة رفع صورة بطلب الأدمن:** `PATCH /media/:id/reupload` (يعمل لصورة REJECTED والحساب NEED_CHANGES).
- إنشاء+تحقيق: `POST /auth/register/institution(+/google)` + `otp/verify`؛ ونفس النمط للمعامل/الجهات الحرة عبر `register/{factory,external-partner}/google` + `onboarding/{factory,external-partner}/*`.
- **ملاحظتان مهمّتان:** (1) المؤسسة **لا تعمل checkout** — الطلبات محصورة بـ FACTORY/EXTERNAL_PARTNER (@Roles). (2) راوت التوفّر `/waste/products/:id/availability` **غير متاح** للمؤسسة (يحتاج waste.products.availability = معامل/جهات حرة فقط).

**تسليم:** كولكشن `Dawrha.institution.postman_collection.json` (9 مجلدات/56 راوت) يغطّي الرحلة كاملة + مجلد إنشاء حساب المعامل/الجهات الحرة. لا تغييرات كود هذه الجلسة (كله كان موجوداً وصحيحاً).

---
## جلسة 2026-08-07 (5) — سلة (تكرار) + تسجيل معامل/جهات + إعادة تصميم الاقتراحات — 697 اختبار ناجح

**أُنجز واختُبر (tsc نظيف، الحزمة 697/697، الهجرة طُبّقت، التطبيق أقلع والراوتات مُسجّلة):**
- **منع تكرار عنصر السلة:** عند إضافة نفس المادة: المواطن/المؤسسة (flat) → المادة نفسها = رفض `ConflictException` «موجودة بالسلة، عدّل الكمية». المعمل/الجهة الحرة → الهوية = (مادة+حالة): نفس المادة بحالة **مختلفة** = سطر جديد مسموح، ونفس المادة+الحالة = رفض. (`IsNull()` لمطابقة الـflat).
- **تسجيل بالإيميل للمعامل والجهات الحرة:** `POST /auth/register/factory` و`/auth/register/external-partner` (كلٌّ روت مستقل مثل `register/institution`).
- **إعادة تصميم الاقتراحات (كبير):**
  - الاقتراح = اسم مادة + `category_id` (تصنيف موجود) + **صورة أو أكثر (ملفات → Cloudinary، حقل `images`)**. أُزيل: الوحدة، السعر، الوصف، الحالات.
  - عند الإضافة: **يُشعَر المقدِّم** ويرجع «طلبك قيد الدراسة — شكراً على مشاركتك». المقدِّم لا يملك راوت عرض اقتراحاته.
  - **أُلغي approve/reject** — الأدمن لا يعدّل حالة. بدله راوت **رد**: `POST /admin/waste/suggestions/:id/reply` يرسل رسالة تصل المقدِّم كإشعار (يرفض اقتراح أودو بلا حساب).
  - قائمة الأدمن: **الأقدم أولاً** + فلترة `submitted_by` (CITIZEN/INSTITUTIONS/FACTORY/EXTERNAL_PARTNER/ODOO).
  - أودو: أُزيلت الوحدة من `OdooSuggestionDto` و`ingestFromOdoo`، وأُضيف `image_urls` اختياري.
  - كيان + هجرة `1787300000000`: DROP `unit_type`/`estimated_price`، `image_url`→`image_urls jsonb` (مع ترحيل القيمة القديمة). أُعيد استخدام أعمدة المراجعة كحقول رد (adminReply/repliedBy/repliedAt). حُذف كود ميت (notifyAdmins/accountRepo/units).
  - ترجمتان جديدتان (ar/en) لرسالتي الاقتراح/الرد.

**تحقّق حيّ:** الراوتات مُسجّلة (`register/factory`, `register/external-partner`, `waste/products/suggest`, `suggestions/:id/reply`)، DI سليم، الهجرة نُفّذت.

---
## جلسة 2026-08-07 (6) — الاقتراحات: وصف + إزالة الحالة نهائياً — 697 اختبار ناجح

**أُنجز واختُبر (tsc نظيف، الحزمة 697/697، هجرتان طُبّقتا، التطبيق أقلع):**
- **حقل الوصف** أُضيف لإنشاء الاقتراح (`description` اختياري) — تطبيق وأودو كلاهما يأخذان: اسم + تصنيف + صور + وصف (نفس الشكل).
- **حُذفت حالة الاقتراح نهائياً** (`status` + enum): الكيان + الخدمة + الاستجابات + `OdooSuggestionDto` (كانت أُزيلت سابقاً). أودو صار يُحدّث الصف الموجود دائماً (لا حارس حالة). إحصائية التقارير `pending_suggestions` صارت «بلا رد» (`adminReply IS NULL`). هجرة `1787400000000`: DROP `status` + DROP enum + تنظيف enum الوحدة اليتيم. حُذف ملف `suggestion-status.enum.ts`.
- **التصنيف بدور المقدِّم** مؤكَّد: قائمة الأدمن `submitted_by=CITIZEN|INSTITUTIONS|FACTORY|EXTERNAL_PARTNER|ODOO`، والأقدم أولاً، وshape يرجع دور المقدِّم.
- **روت رد الأدمن موجود ومؤكَّد**: `POST /admin/waste/suggestions/:id/reply` (يصل المقدِّم كإشعار). حُدّث كولكشن الأدمن (فلترة submitted_by بدل status/source، ورد بدل قبول/رفض)، وأُضيف راوت اقتراح multipart للكولكشن المؤسسة.

**تحقّق حيّ:** أعمدة `product_suggestions` النهائية: id, account_id, product_name, description, category_id, admin_notes(reply), reviewed_at, reviewed_by, created_at, source, odoo_suggestion_id, suggested_by_name, suggested_category_name, image_urls. لا status/unit_type/estimated_price/image_url. التطبيق أقلع بلا أخطاء والراوتات مُسجّلة.

---
## جلسة 2026-08-07 (7) — منطق الفرز: الإتلاف/الضائع + حارس الأرشفة (Odoo) — 13/13 اختبار للميزة

**قرار المستخدم المؤكَّد:** كمية الإتلاف **لا تمنع** إنهاء الفرز (يكمل الموظف ويخزّن السليم، والمدير يقرّر لاحقاً). المنطق أولاً ثم الواجهات.

**فهم مؤكَّد من الكود (كان ~90% منفّذاً مسبقاً):** الضائعة=`expected−entered` لكل مادة ولكل وحدة؛ الإتلاف=أسطر `is_damaged`+سبب؛ قواعد التسامح الثلاث (1: لا تتجاوز المتوقع لكل وحدة دائماً؛ 2: وحدات `allows_tolerance` ضمن نسبتي الأدمن؛ 3: غير القابلة للهامش تطابق تام) + التصعيد للمدير. قائمتا المدير موجودتان (Damaged sorting requests + Damage Reports).

**التعديلات (models/shipment.py + order.py):**
- **`action_finish_sorting`:** أُزيل حجب الإتلاف. الأسطر التالفة تُحجَز (لا تُخزَّن ولا تُتلَف)؛ يُطلب سبب الإتلاف قبل الإنهاء؛ عند إنهاء الموظف تُرفع طلب قرار للمدير (pending + إشعار) وتظهر في قائمته؛ إن أنهى **مشرف** فهو المُوافِق (تُسجَّل للسجل فوراً بلا طلب).
- **`action_approve_damage`:** يُسجّل الإتلاف المحجوز إلى سجل الخسائر (`record_from_sorting`) ولا يُخزَّن — يبقى ظاهراً «تالف» في معلومات الشحنة.
- **`action_reject_damage(reason, grades, storage_zone_id)`:** إن كانت الشحنة `sorted` فالمدير **يخزّنها بنفسه** مختاراً المنطقة (+الحالة إن كانت مُدرَّجة)؛ إن ما زالت `sorting` يُلغى العلم ويخزّنها الموظف عند الإنهاء.
- **حارس الأرشفة:** `action_archive_recycle` (شحنة) يمنع الأرشفة ما لم تكن `sorted` وبلا قرار إتلاف/تصعيد معلّق؛ و(طلب) يمنع إلا `completed`/`cancelled`.
- استُخرج `_notify_damage_request`.

**تحقّق حيّ:** `test_damage_approval.py` أُعيد كتابته (13 اختباراً) ويمرّ كاملاً في حاوية Odoo (`0 failed, 0 errors of 13`). ملاحظة: 4 إخفاقات موجودة مسبقاً في `test_product_suggestion` (عقد التزامن مع الباك‑إند: unit_type/backend ref) **غير متعلقة** بتعديلات الشحنة/الطلب، +خطأ بيئة wkhtmltopdf شبكي.

**التالي (واجهات):** قائمة «مواد تلف» في نافبار المدير (قائمتان: أثناء الفرز / ضمن المخزون، الأقدم أولاً) + تجاوب الجوال لواجهات الموظفين (سكرول أفقي/عمودي، عرض كامل).

---
## جلسة 2026-08-07 (8) — واجهات الفرز: نافبار «مواد تلف» + تجاوب الجوال (Odoo)

**أُنجز:**
- **قسم نافبار جديد للمدير «مواد تلف» (Damaged Materials)** ببندين: «تالف أثناء الفرز» (openDamagedRequests) و«تالف ضمن المخزون» (openDamageReports)، ونُقل خيار الإتلاف من قسم Operations. القائمتان صارتا **من الأقدم للأحدث** (`id asc` / `create_date asc`). أُضيفت ترجمات ar (مواد تلف / تالف أثناء الفرز / تالف ضمن المخزون).
- **تجاوب الجوال لواجهات المستودع** (`recycle_employee_theme.css`، محمّل في `web.assets_backend` لكل اللوحات): جداول `o_recycle_data_table` تتحوّل إلى **سكرول أفقي داخل صندوقها** (`display:block; overflow-x:auto; white-space:nowrap`) فتُقرأ كل الأعمدة بلا اقتطاع مع بقاء محاذاة الرأس/الجسم؛ حاويات `o_recycle_view_container` بعرض كامل؛ صفوف الأزرار/الفلاتر `flex-wrap`؛ النصوص الطويلة `overflow-wrap:anywhere`. يغطّي شاشة عرض الشحنة (تستخدم نفس صنف الجدول).

**تحقّق حيّ:** الموديول يُحمّل بلا أخطاء (Registry loaded)، واختبارات QWeb/handler-binding/vocabulary/translations تمرّ (`0 failed, 0 of 8`) — أي أن روابط أزرار النافبار الجديدة والترجمات صحيحة. (التحقق البصري الحيّ يتطلّب دخول مدير/موظف بكلمة مرور، وهو محظور عليّ؛ اكتفيت بالاختبارات الآلية وتحميل الموديول.)

**متبقٍّ من طلب سابق لم يُنفَّذ بعد:** تعديل العرض لتغيير نسبة/مقدار + راوت السجل الزمني لعروض مادة بفلترة تاريخ (كان طلباً منفصلاً قبل سيناريو الفرز).

---
## جلسة 2026-08-14 — تحويل حالة المخزون (re-grade) ينفَّذ في أودو — إصلاح عبر النظامين

**الطلب:** روت الباك لتحويل كمية مادة من حالة إلى أخرى (`transfer-stock`) كان يعدّل مرآة الباك فقط، فتعكسه المزامنة. المطلوب أن **يتعدّل في أودو** (المالك الوحيد للكميات) ويتزامن الطرفان، **مع بقاء إجمالي كمية المستودع ثابتاً** (إعادة تصنيف لا إضافة/حذف). خاص بالمعامل والجهات الحرة.

**التشخيص (تتبّع كود عبر المشروعين):** لا يوجد أصلاً أي action/endpoint لإعادة التصنيف في `recycle.stock`؛ الباك كان ينقل المرآة ثم يطلق `SYNC_WAREHOUSE` (قراءة) فيدهس النقل بقيم أودو القديمة → **التحويل يُعكَس بصمت خلال ثوانٍ**.

**أُنجز في أودو:**
- **`recycle.stock.transfer_grade(warehouse_id, product_id, from_condition, to_condition, quantity)`** (`@api.model`): ينقل **الكمية غير المحجوزة فقط** بين حالتين لنفس المادة داخل **نفس منطقة التخزين** (المادة لا تنتقل فيزيائياً، تتغير حالتها فقط) → **الإجمالي ثابت بالبناء**. يتحقق أن الحالتين تخصّان المادة (`material.condition.normalize`)، ويترك صف المصدر عند تصفيره (حالة فارغة تبقى حالة تُباع). يُرجع `{transferred:False, movable}` عند العجز بدل الرمي. `write` على `recycle.stock` يطلق ping المخزون تلقائياً → مرآة الباك تتحدّث عبر `SYNC_WAREHOUSE` القائمة (لا مُصالِح جديد).

**أُنجز في الباك (NestJS):**
- `odoo.service.transferStockGrade` (callKw إلى `recycle.stock.transfer_grade`) + job كتابة `TRANSFER_STOCK_GRADE` (constants/service/processor، retry 3) — الكتابة لأودو عبر الطابور حصراً. الروت `transfer-stock` أُعيد بناؤه: تحقّق + pre-check ضد المرآة + audit للنيّة + إدراج للطابور، **بلا لمس المرآة إطلاقاً**. المعالج يُشعر الأدمن الطالب عند رفض أودو (سباق نادر).

**تحقّق حيّ:**
- **أودو:** `tests/test_grade_transfer.py` جديد — **9/9 ناجح** على DB معزولة نظيفة (`0 failed, 0 error(s) of 9`): حفظ الإجمالي، نقل غير المحجوز فقط، البقاء بنفس المنطقة، رفض حالة مادة أخرى/نفس الحالة، تطابق رمز بلا حساسية حالة، بقاء صف المصدر عند التصفير. DB الاختبار حُذفت و`odoo19` أُعيد تحميله (دالة بايثون جديدة).
- **الباك:** `tsc` نظيف · **754/754 اختبار** · اختبار الروت أُعيد كتابته ليثبت أن المرآة لا تُكتب وأن الكتابة تُدرَج بالحمولة الصحيحة (حارس ضد الثقة الزائفة السابقة التي كانت تـ mock الـsync).
- **عقد جديد (backend→odoo RPC):** `recycle.stock.transfer_grade` — أُضيف لـ FIXES.md #125–127.

---
## جلسة 2026-08-15 — سيناريو طلبات المعامل/الجهات الحرة (تقسيم + رفض التقسيم + تعديل الأدمن)

بعد فحص عميق لـ`src/order`: التوزيع والمسافات (Google Distance Matrix + كاش لكل زوج buyer×warehouse) والحجز (reserve/release عبر reserved_qty) والحدود (أدنى/أعلى لكل حساب) **مبنيّة سابقاً وتطابق السيناريو**. نُفّذت الفجوات:

**الباك (NestJS):**
- خوارزمية التقسيم أُعيد بناؤها: أولوية صارمة — مستودع واحد يغطّي (الأقرب) → أقل عدد مستودعات → أقل مسافة عند التعادل → أفضل جزئي يُعرض على المشتري. (17/17)
- رفض التقسيم: حالة طلبية جديدة `REJECTED_AWAITING_BUYER` (لاصقة، لا إعادة توزيع)، تمييز التقسيم من دفتر الجولات، endpoint تأكيد للمشتري يُغلق الطلبية. رفض المستودع المنفرد يبقى يُعيد التوزيع.

**أودو (recycle_warehouse):**
- **`recycle.order.action_admin_reassign_warehouse(new_warehouse_id)`**: يبدّل مستودع جزء من تقسيم — أدمن فقط، جزء تقسيم فقط، قبل الموافقة، **لا يضيف مستودعاً** (الجديد ليس لأحد الأشقّاء)، الكمية متوفرة (غير المحجوز)، والحجز ينتقل (release ثم reserve). يُشعر الباك `reassigned` (مع `warehouse_odoo_id`) فيُعيد الباك النقطة والمسافة وسعر التوصيل والإجماليات.
- endpoint `/api/admin/order/reassign` (JSON-RPC، أدمن فقط).

**تحقّق حيّ:**
- أودو: DB نظيفة معزولة — **36/36 ناجح** (`test_order_reassign` 6 جديد + `test_split_order_approval` + `test_order_workflow` + `test_grade_transfer` 9). أُصلح `uom_id` مفقود في فكستشرَي workflow/split (عطل سابق مستقل على تنصيب نظيف). أُعيد تحميل `odoo19`.
- الباك: `tsc` نظيف · **782/782 اختبار**.
- **متبقٍّ صراحةً:** زر «إعادة التوزيع» في لوحة الأدمن OWL — المنطق/الـendpoint جاهزان؛ الزر المرئي لم يُضَف.

**تكملة — زر إعادة التوزيع في لوحة الأدمن (OWL):** أُضيف قسم «Reassign This Part» في تفاصيل الطلبية (`dashboard_admin.xml`) + منطقه (`recycle_admin_dashboard.js`: `canReassignOrder`, `_loadReassignCandidates`, `reassignOrderPart`). يظهر فقط لجزء تقسيم قابل للتعديل، قائمة المستودعات تستثني الحالي والأشقّاء، ويستدعي `action_admin_reassign_warehouse` عبر `orm.call`. تحقّق: قوالب OWL 10/10 (`TestQweb*`) + `node --check` + XML parse. أُعيد تحميل `odoo19`. (النقر البصري يتطلّب دخول أدمن المحظور عليّ.)

---
## جلسة 2026-08-15 (تكملة 2) — سيناريو التوصيل: تكامل أودو الكامل (Phase 2)

بعد بناء محرّك التوصيل في الباك (سكور الشاحنات + تقسيم بالوزن + المحطة القادمة + الماب)، أُكمل التكامل مع أودو:

**أودو (recycle_warehouse):**
- **`recycle.delivery.trip` + `.stop`** (`models/delivery_trip.py`): مرآة الرحلة التي يعمل عليها السائق/الأدمن. `backend_upsert` idempotent (يحفظ الاستلامات المؤكَّدة عبر إعادة الدفع)، `next_stop`، `action_driver_confirm_pickup` (حارس التسلسل «الأبعد أولاً» + يُشعر الباك)، `action_driver_complete`، وإشعار السائق عند وصول الرحلة. + `recycle.delivery.driver.backend_driver_for_truck`.
- **لوحة سائق التوصيل**: تبويب «My Trips» يعرض **المحطة القادمة فقط** + رابط غوغل ماب + زر تأكيد الاستلام؛ وعند اكتمال المحطات زر التسليم للمعمل. Endpoints في `dashboard_api` (`/api/recycle/my-delivery-trips|delivery-confirm-pickup|delivery-complete`).
- **واجهة الأدمن**: `views/delivery_trip_views.xml` (قائمة + استمارة تعرض كل محطة: التسلسل/المستودع/البضاعة/الحالة/وقت الاستلام/رابط الماب) + قائمة «Delivery Trips».
- `backend_sync.sync_delivery` + مسار `delivery` لإرجاع أحداث الاستلام/الإكمال للباك.
- ACLs للموديلين الجديدين، وترجمات عربية لكل نصوص اللوحات الجديدة.

**الباك (NestJS):**
- `odoo.service`: `fetchDeliveryDriverForTruck` + `pushDeliveryTrip`. job `PUSH_DELIVERY_TRIP`. `DeliveryTripService.dispatchTrip` (يحلّ السائق من أودو → ASSIGNED → دفع)، وإرسال تلقائي بعد التخطيط. `DeliveryWebhookController` (يستقبل تأكيدات أودو ويستدعي confirmPickup/completeTrip، بنفس حارس السرّ، في موديول الطلبات لتفادي دورة الموديولات).

**تحقّق حيّ:**
- أودو: **119/119** على DB معزولة نظيفة (توصيل 9 جديد + QWeb/OWL + ترجمات اللوحات + إعادة توزيع + فرز + ضرر…). أُصلحت ثغرة `uom_id` مفقودة في فكستشرات قديمة (عطل سابق مستقل على تنصيب نظيف). رُقّيت `odoo19` الحيّة (جداول/عروض/قوائم) وأُعيد تحميلها.
- الباك: `tsc` نظيف · **804/804 اختبار**.
- عطل سابق وحيد خارج النطاق ولم يُلمَس: `TestProductSuggestion.test_cannot_submit_twice` (صفر ملفات suggestion غُيّرت).
- التأكيد النهائي عند المعمل (المشتري) — مبنيّ سابقاً وموافَق عليه. لم أسجّل دخولاً يدوياً (كلمة المرور محظورة عليّ)؛ الاعتماد على الاختبارات الآلية.
