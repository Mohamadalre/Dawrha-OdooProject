# 🔌 BACKEND_INTEGRATION — دليل ربط مشروع "دورها" (Odoo 19) مع باك إند NestJS

> **الغرض**: هذا الملف هو المرجع الكامل والوحيد لربط النظام مع الباك إند.
> عندما تبني الـ NestJS، اقرأ هذا الملف فقط — كل نقطة ربط موثقة هنا مع مكانها في الكود.
>
> **آخر تحديث**: 2026-07-12

---

## 1) نظرة عامة على المعمارية

```
┌─────────────────┐   Odoo → Backend (Webhooks)   ┌──────────────────┐
│                 │ ────────────────────────────► │                  │
│   Odoo 19       │                                │  NestJS Backend  │
│ (هذا المشروع)   │ ◄──────────────────────────── │  (ستبنيه لاحقاً)  │
│                 │   Backend → Odoo (REST API)    │                  │
└─────────────────┘                                └──────────────────┘
```

قناتا اتصال منفصلتان تماماً:

| الاتجاه | الآلية | ملف الكود | متى تُستخدم |
|---|---|---|---|
| **Odoo → Backend** | Webhooks (POST JSON) | `addons/recycle_warehouse/models/backend_sync.py` | Odoo يُعلم الباك إند بالأحداث (تخزين شحنة، إتمام طلبية، منتج جديد...) |
| **Backend → Odoo** | REST API (X-API-KEY) | `addons/recycle_warehouse/controllers/api.py` | الباك إند ينشئ شحنات/طلبات في Odoo ويقرأ الحالة |

**المبدأ**: إنشاء المستودعات، المنتجات، التصنيفات، الشحنات، والطلبات يتم من الباك إند
عبر هذه الراوتات — Odoo هو نظام التشغيل الداخلي (استقبال/فرز/إخراج) وليس مصدر الإدخال.

---

## 2) خطوات الربط (عند جهوز الـ NestJS) — لا تعديل كود

### الخطوة 1 — بارامتران فقط
من Odoo: **Settings → Technical → Parameters → System Parameters** أضف:

| Key | Value (مثال) |
|---|---|
| `recycle.backend_base_url` | `https://api.dawrha.com` |
| `recycle.backend_api_key` | السر المشترك (يُرسل كهيدر `X-API-KEY` بالاتجاهين) |

> بدون `recycle.backend_base_url` كل مزامنة صادرة تُتجاهل بصمت (fire-and-forget) —
> النظام يعمل بشكل كامل بدون باك إند.

### الخطوة 2 — عدّل مسارات الراوتات إن اختلفت
كل المسارات الصادرة معرفة في **قاموس واحد** أعلى `models/backend_sync.py`:

```python
BACKEND_ROUTES = {
    'shipments':  '/webhooks/odoo/shipments',
    'orders':     '/webhooks/odoo/orders',
    'products':   '/webhooks/odoo/products',
    'categories': '/webhooks/odoo/categories',
    'warehouses': '/webhooks/odoo/warehouses',
}
```

- **الطريقة أ (كود)**: عدّل القاموس مباشرة.
- **الطريقة ب (بدون كود — الأفضل للإنتاج)**: أضف System Parameter باسم
  `recycle.backend_route_<key>` — مثال: `recycle.backend_route_orders = /v2/hooks/orders`
  وهو يتجاوز قيمة القاموس تلقائياً.

بعد أي تعديل كود: `docker restart odoo19`.

---

## 3) Odoo → Backend (Webhooks الصادرة)

كلها `POST {base_url}{path}` بهيدر `X-API-KEY` و`Content-Type: application/json`.
كل payload يحمل حقل `event` يحدد نوع الحدث. الفشل الشبكي يسجَّل تحذيراً فقط
**ولا يوقف العمل أبداً**.

### 3.1 الشحنات — `shipments`
تُستدعى عند: **تخزين الشحنة** (انتهاء الفرز).
```json
{
  "event": "stored",
  "odoo_id": 41,
  "name": "SHP00041",
  "backend_shipment_id": "BK-1042",
  "state": "sorted",
  "warehouse": "warehouse-damascus",
  "actual_weight": 95.5,
  "lines": [
    { "product": "PET bottles", "quantity": 35, "condition": "excellent" }
  ]
}
```
`condition` ∈ `excellent | good | poor | damaged`.

### 3.2 الطلبات — `orders`
تُستدعى مرتين لكل طلبية (حدثان منفصلان — راقب `event`):
- `stock_deducted` — عند اختيار موظف الإخراج لمناطق التخزين وضغط "إكمال" (خُصم المخزون
  فعلياً وتوَّلدت الفاتورة، لكن الطلبية لم تنتهِ بعد — بانتظار اختيار منطقة الإخراج).
- `completed` — عند ضغط "إنهاء" واختيار منطقة الإخراج (نهاية دورة حياة الطلبية).
```json
{
  "event": "completed",
  "odoo_id": 12,
  "name": "ORD00012",
  "state": "completed",
  "factory_id": "FAC-2091",
  "priority": 5,
  "warehouse": "warehouse-damascus",
  "invoice_number": "INV00007",
  "output_zone": "Output Zone A",
  "stock_deducted_at": "2026-07-12 10:15:00",
  "finished_at": "2026-07-12 10:20:00",
  "lines": [
    { "product": "PET bottles", "quantity": 20, "condition": "excellent" }
  ]
}
```

### 3.3 المنتجات — `products` / التصنيفات — `categories` / المستودعات — `warehouses`
تُستدعى عند الإنشاء/تحديث الأسعار. payload بسيط بنفس النمط (`event`, `odoo_id`, `name`, ...).
انظر `sync_product / sync_category / sync_warehouse` في `backend_sync.py`.

### 3.4 الأسطول (الشاحنات) — `fleet` ⚠️ مصادقة مختلفة
- **المسار الافتراضي**: `POST /api/v1/odoo/webhooks/fleet` (نقطة **حيّة فعلاً** بالباك إند — `OdooWebhookController.fleetChanged`).
- **المصادقة**: هيدر `x-odoo-webhook-secret = recycle.backend_webhook_secret` (**ليس** `X-API-KEY` كبقية المسارات؛ يطابق `ODOO_WEBHOOK_SECRET` في `.env` بالباك إند).
- **الحمولة**: فارغة `{}`. الباك إند يرد `202` ويجدول مهمة `SYNC_FLEET` التي **تُعيد قراءة الأسطول كاملاً** من الأودو عبر JSON-RPC (Odoo هو السيّد). فبدل حمل البيانات في كل حدث، يكفي إشعار أن الأسطول تغيّر — وتنهار دفعات التغييرات في إعادات قراءة متكافئة (idempotent).
- **متى يُطلق**: أي `create/write/unlink` على `recycle.truck` أو `recycle.driver.assignment` (عبر `notify_fleet_changed()` — fire-and-forget). إن لم يُضبط السر، يُتخطى النداء بصمت.
- **ما يقرؤه الباك إند بعد الإشعار** (أسماء حقول = عقد، لا تُعاد تسميتها):
  - `recycle.truck`: `model, year, plate_number, max_payload_kg, warehouse_id, is_active`.
  - `recycle.shift`: `name, start_time, end_time, shift_type` (**driver/warehouse** — السائق يرى ورديات driver فقط).
  - `recycle.driver.assignment`: `backend_driver_id, truck_id, shift_id` (الوردية يجب أن تكون driver — قيد بالموديل).

### 3.5 قرار طلب السائق — `driver_decision` ⚠️ صارم (ليس fire-and-forget)
- **المسار**: `POST /api/v1/odoo/webhooks/driver-decision` بهيدر `x-odoo-webhook-secret`.
- **الحمولة**: `{backend_driver_id, status: ACTIVE|REJECTED|NEED_CHANGES, rejection_reason?, rejected_media_ids?[]}`.
- **صارم**: أزرار القرار في شاشة "Driver Requests" ترسل الـ webhook **قبل** حفظ القرار؛ فشل الوصول = UserError ولا يُحفظ شيء — لا يمكن أن يختلف الأودو عن الباك إند في حالة السائق.
- **الاتجاه المعاكس**: الباك إند يدفع الطلب بـ`recycle.driver.request.create` (upsert بـ `backend_driver_id`) مع `image_ids[backend_media_id, file_type, url]` — رفض صورة واحدة يرسل NEED_CHANGES + `rejected_media_ids=[...]` فيعلّمها الباك إند REJECTED ويعيد السائق رفعها ويُعاد دفع الطلب تلقائياً.

---

## 4) Backend → Odoo (REST API الواردة)

**المصادقة**: هيدر `X-API-KEY` يطابق البارامتر `recycle.api_key`
(بارامتر منفصل عن مفتاح الاتجاه الصادر — يمكن توحيدهما بنفس القيمة).

**Rate limiting**: كل الراوتات الواردة محدودة بـ **120 طلب/دقيقة** افتراضياً
(نافذة عالمية واحدة لكل النظام، وليست لكل عنوان IP). عند التجاوز تُعاد `429`
مع `{"success": false, "error": "Rate limit exceeded..."}`. للتعديل: System
Parameter باسم `recycle.api_rate_limit_per_minute`.

Base URL = عنوان أودو، مثال محلي: `http://localhost:8069`

### 4.1 إنشاء شحنة (الأهم — معرّف الباركود)
```
POST /api/recycle/shipments
X-API-KEY: <recycle.api_key>
```
```json
{
  "warehouse_code": "WHD1",
  "driver_name": "Ahmad Khaled",
  "backend_shipment_id": "BK-1042",
  "truck_info": "DAM 1234",
  "truck_serial_number": "SN-99",
  "dispatch_date": "2026-07-12 08:00:00",
  "priority": 5,
  "expected_materials": [
    { "product_id": 1, "quantity": 40 },
    { "product_id": 2, "quantity": 15 }
  ]
}
```
الاستجابة `201`:
```json
{
  "success": true,
  "shipment_id": 42,          ← ⭐ هذا هو الرقم الذي يُطبع كباركود ويُمسح في الاستقبال
  "name": "SHP00042",
  "state": "pending",
  "backend_shipment_id": "BK-1042",
  "expected_weight": 55.0
}
```
> موظف الاستقبال يمسح `shipment_id` (رقم أودو) — راوت المسح الداخلي:
> `/api/receiving/scan-shipment` في `controllers/dashboard_api.py`.

### 4.2 إنشاء طلبية
```
POST /api/recycle/orders
```
```json
{
  "warehouse_id": 3,
  "warehouse_code": "WHD1",
  "customer_name": "مصنع الأمل",
  "customer_email": "factory@example.com",
  "order_type": "factory",
  "factory_id": "FAC-2091",
  "priority": 5,
  "lines": [
    { "product_id": 1, "quantity": 20, "condition": "excellent" }
  ]
}
```
- `warehouse_id` (رقم أودو للمستودع) و`warehouse_code` — **أحدهما مطلوب على الأقل**.
  إن أُرسل الاثنان يجب أن يتطابقا (وإلا رفض الطلب برسالة صريحة) — أرسلهما معاً
  دائماً إذا كانا متوفرين لديك لتفادي أي التباس بين نسخة قديمة من الكود ومعرّف
  المستودع الفعلي. الاستجابة تعيد كليهما دوماً (`warehouse_id` و`warehouse_code`)
  حتى لو أرسلت واحداً منهما فقط.
- `condition` اختياري (افتراضي `good`) ∈ `excellent | good | poor | damaged`.
- `factory_id` اختياري — معرّف المعمل/العميل في الباك إند، يُحفظ فقط للربط ويُعاد
  كما هو (Odoo لا يولّد له معنى، ولا يُستخدم كمفتاح داخلي).
- `priority` اختياري (افتراضي `10`) — **رقم أصغر = أولوية أعلى**. سعر كل سطر
  (`price_unit`) يُحسب **دائماً من طرف Odoo** تلقائياً من `price_factory` أو
  `price_free_facility` في المنتج حسب `order_type` — لا تُرسله أبداً من الباك إند.
- **الاستجابة (201)** تتضمن `priority` و `factory_id` و `warehouse_id` و
  `warehouse_code` و`amount_total` المحسوب.
- **قاعدة الخصم**: عند إتمام الطلبية يُخصم المخزون **من نفس الحالة فقط** —
  سطر بحالة "ممتازة" لا يستهلك أبداً مخزوناً بحالة "جيدة".
- **قاعدة ترتيب الأولوية (مُطبّقة داخل Odoo، لا حاجة لأي منطق من الباك إند)**:
  لا يمكن لموظف الإخراج بدء معالجة طلبية طالما توجد طلبية أخرى بنفس المستودع
  أولويتها أعلى (رقم أصغر) وما زالت `pending` **ولديها مخزون كافٍ لإتمامها** —
  إن كانت الطلبية الأعلى أولوية تفتقر للمخزون الكافي يُسمح بتجاوزها.
- **قاعدة خصم المخزون بعدة مناطق**: عند إتمام الطلبية يختار موظف الإخراج منطقة
  تخزين واحدة أو أكثر لكل مادة (لتغطية الكمية المطلوبة)، فيُسجَّل توقيت الخصم
  الفعلي في `stock_deducted_at`، ثم يختار منطقة الإخراج لإنهاء الطلبية
  (`finished_at`). راجع `recycle.order.zone.movement` لسجل الخصم التفصيلي
  لكل (منطقة × مادة × حالة × توقيت).

### 4.3 قراءة حالة طلبية
```
GET /api/recycle/orders/<order_id>
```
تعيد الحالة + `factory_id` + `priority` + الأسطر (مع `condition`) + رقم الفاتورة +
`output_zone` + `stock_deducted_at` + `finished_at` إن وُجدت.

### 4.4 كتالوج المنتجات
```
GET /api/recycle/products
```
تعيد كل المنتجات (id, name, category, السعرين) — استعملها لمزامنة الـ IDs عند إنشاء
الشحنات/الطلبات.

---

## 5) قاموس الحالات (مصدر واحد للحقيقة)

معرّف في `models/stock.py`:

```python
STOCK_CONDITIONS = [
    ('excellent', 'Excellent'),   # ممتازة
    ('good', 'Good'),             # جيدة
    ('poor', 'Poor'),             # رديئة
    ('damaged', 'Damaged'),       # تالفة
]
```

يُستخدم في: مخزون (`recycle.stock`)، أسطر الفرز (`recycle.shipment.line`)،
أسطر الطلبات (`recycle.order.line`). **أي تعديل عليه يسري تلقائياً على الجميع.**

### منطق المخزون
- كل سجل مخزون = (مستودع × منطقة تخزين × منتج × حالة).
- الفرز يضيف للمخزون بحسب حالة كل سطر.
- الطلبية تخصم **حصراً** من الحالة المطلوبة في السطر (`_deduct_quantity(condition=...)`
  في `models/stock.py`) — عدم كفاية الحالة المطلوبة = رفض العملية برسالة واضحة
  حتى لو توفرت كميات بحالات أخرى.

---

## 6) خريطة ملفات التكامل

| الملف | الدور |
|---|---|
| `models/backend_sync.py` | كل النداءات الصادرة + قاموس `BACKEND_ROUTES` (المكان الوحيد للمسارات) |
| `controllers/api.py` | كل الراوتات الواردة من الباك إند (X-API-KEY) |
| `controllers/dashboard_api.py` | راوتات داخلية للداشبوردات (جلسة مستخدم — ليست للباك إند) |
| `models/shipment.py` | `backend_shipment_id` للربط + hooks المزامنة عند التخزين |
| `models/order.py` | hook المزامنة عند الإتمام + خصم بحسب الحالة |
| `models/stock.py` | `STOCK_CONDITIONS` + `_add_quantity` / `_deduct_quantity` / `_available_qty` |

## 7) قائمة فحص الربط النهائية

1. ☐ ضبط `recycle.backend_base_url` و `recycle.backend_api_key` (الصادر).
2. ☐ ضبط `recycle.api_key` (الوارد) وتمريره من NestJS كهيدر `X-API-KEY`.
3. ☐ مطابقة مسارات `BACKEND_ROUTES` مع Controllers الـ NestJS (أو override بالبارامترات).
4. ☐ بناء endpoints الـ NestJS الخمسة المستقبِلة للـ webhooks (ترد `2xx`).
5. ☐ اختبار: إنشاء شحنة من الباك إند → طباعة باركود بـ `shipment_id` → مسحها في
   واجهة الاستقبال → فرزها → التأكد من وصول webhook `stored` للباك إند.
6. ☐ اختبار: إنشاء طلبية بحالة `excellent` → إتمامها من موظف الإخراج → التأكد من
   خصم مخزون `excellent` فقط + وصول webhook `completed`.
