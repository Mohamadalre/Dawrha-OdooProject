# Recycle Warehouse Management (Odoo 19)

موديول واحد شامل: إدارة المستودعات + الشحنات + المخزون + الطلبات (Next.js API) + التوظيف عبر الموقع.

## التثبيت

1. ضع المجلد `recycle_warehouse` في مجلد addons (موجود بالفعل).
2. أعد تشغيل أودو: `docker compose restart`
3. فعّل وضع المطور → Apps → Update Apps List → ابحث عن **Recycle Warehouse Management** → Install.

## الإعدادات (Settings → Technical → System Parameters)

| المفتاح | القيمة الافتراضية | الوصف |
|---|---|---|
| `recycle.allowed_email_domain` | `gmail.com` | نطاق البريد المسموح للتقديم |
| `recycle.api_key` | `change-me-secret-api-key` | **غيّره فوراً** — مفتاح API لـ Next.js |

## الأدوار (Settings → Users → اختر المستخدم → Recycle Warehouse)

- **Administrator**: كل النظام + إدارة التوظيف + المنتجات.
- **Warehouse Manager**: مستودعه فقط — شحنات، مخزون، طلبات، إنشاء حسابات الموظفين المقبولين.
- **Input / Sorting / Output Employee**: مستودعهم فقط حسب الدور.

أعطِ نفسك مجموعة **Recycle Warehouse / Administrator** بعد التثبيت.

## سير العمل

1. **Admin**: ينشئ المنتجات والتصنيفات (Recycle Warehouse → Inventory → Products).
2. **Admin**: ينشئ وظيفة (Recruitment → Jobs) ويحدد `Recycle Job Type` ويفعّل `Publish on Recycle Website`.
3. **المتقدم**: ينشئ حساباً من الموقع (/web/signup) ببريد `@gmail.com` → يفتح `/jobs` → يقدّم (هاتف + رقم وطني + ملفات). لا تكرار للتقديم، الرقم الوطني فريد.
4. **Admin**: يتابع الطلب من نموذج المتقدم (Set Interview / Accept / Reject).
5. **Admin**: لوظيفة مدير → زر **Create Manager Account** ثم ينشئ Warehouse ويربط المدير (المناطق الأربع تُنشأ تلقائياً).
6. **Manager**: من Recycle Warehouse → Recruitment → Accepted Applicants → يحدد الدور → **Create Employee Account** (يُنشأ User + hr.employee ويُربط بمستودعه).
7. **Manager**: ينشئ شحنة (السائق + الوزن المعلن) → حالة Pending.
8. **Input**: يدخل الوزن الفعلي → **Validate Weight** (فرق > 2% = رفض، وإلا قبول وقفل).
9. **Sorting**: **Start Sorting** (حجز) → يدخل المنتجات (جيد/تالف) → **Finish Sorting** (الجيد يُضاف للمخزون).
10. **Output**: يستقبل طلبات Next.js → Processing → Ready → **Complete** (خصم المخزون + فاتورة PDF).

## REST API لـ Next.js

كل الطلبات تحتاج Header: `X-API-KEY: <recycle.api_key>`

```bash
# المنتجات
curl -H "X-API-KEY: KEY" http://localhost:8069/api/recycle/products

# إنشاء طلب
curl -X POST -H "X-API-KEY: KEY" -H "Content-Type: application/json" \
  -d '{"warehouse_code":"WH1","customer_name":"Ali","customer_email":"a@b.com","lines":[{"product_id":1,"quantity":3}]}' \
  http://localhost:8069/api/recycle/orders

# حالة الطلب
curl -H "X-API-KEY: KEY" http://localhost:8069/api/recycle/orders/1
```

## التقارير

- فاتورة PDF: زر Print Invoice على الطلب المكتمل.
- تحليلات Graph/Pivot للشحنات والمخزون + تصدير Excel من أي قائمة (زر ⚙ → Export).

## ملاحظات

- قائمة الموقع: أُضيفت Jobs و My Applications تلقائياً؛ احذف القوائم غير المرغوبة من Website → Site → Menu Editor.
- بريد تعيين كلمة المرور للمستخدمين الجدد يتطلب إعداد خادم بريد صادر؛ بدونه عيّن كلمة المرور يدوياً من بطاقة المستخدم.
