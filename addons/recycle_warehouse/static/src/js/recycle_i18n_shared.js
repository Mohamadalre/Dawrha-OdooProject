/** @odoo-module **/
// @version 202606301146

var LANG_KEY = 'recycle_wms_lang';

var T = { en: {}, ar: {} };

// Normalise whitespace so multiline template strings (which keep
// newlines + indentation) still match single-line registry keys.
function normKey(s) {
    return String(s).replace(/\s+/g, ' ').trim();
}

export function reg(en, ar) {
    var k = normKey(en);
    T.en[k] = en;
    T.ar[k] = ar;
}

export function tr(key) {
    var v = localStorage.getItem(LANG_KEY);
    var lang = v === 'ar' ? 'ar' : 'en';
    var k = normKey(key);
    return (T[lang] && T[lang][k]) || key;
}

export function getLang() {
    var v = localStorage.getItem(LANG_KEY);
    return v === 'ar' ? 'ar' : 'en';
}

// ─── Employee Dashboard strings ───
reg('Recycle Warehouse', 'مستودع إعادة التدوير');
reg('Welcome,', 'مرحبًا،');
reg('Choose an action to get started.', 'اختر إجراءً للبدء.');
reg('Process Shipment', 'معالجة شحنة');
reg('Enter a shipment ID manually or upload a barcode image to load, weigh, and receive an incoming shipment.', 'أدخل معرف الشحنة يدوياً أو حمّل صورة باركود لتحميل الشحنة الواردة ووزنها واستلامها.');
reg('My Processed Shipments', 'شحناتي المعالجة');
reg('View all shipments you have received — including timestamps, actual weights, differences, and current status.', 'عرض جميع الشحنات التي استلمتها — بما في ذلك الطوابع الزمنية والأوزان الفعلية والفروقات والحالة الحالية.');
reg('Sorting & Classification', 'الفرز والتصنيف');
reg('Sort Shipment', 'فرز شحنة');
reg('View all shipments ready for sorting. Select one to reserve it, enter product quantities and conditions, then finish sorting to update stock.', 'عرض جميع الشحنات الجاهزة للفرز. اختر واحدة لحجزها، أدخل كميات المنتجات والظروف، ثم أنهِ الفرز لتحديث المخزون.');
reg('My Shipments', 'شحناتي');
reg('View all shipments you are currently sorting or have already sorted — with timestamps, quantities by condition, and status.', 'عرض جميع الشحنات التي تفرزها حالياً أو فرزتها بالفعل — مع الطوابع الزمنية والكميات حسب الحالة والحالة.');
reg('Order Processing', 'معالجة الطلبات');
reg('Process Order', 'معالجة طلب');
reg('View all pending orders assigned to your warehouse. Select an order to reserve it, prepare items, and generate the invoice.', 'عرض جميع الطلبات المعلقة المخصصة لمستودعك. اختر طلباً لحجزه وتجهيز العناصر وإنشاء الفاتورة.');
reg('My Orders', 'طلباتي');
reg('View all orders you are currently processing or have already completed — with invoice numbers, totals, and status.', 'عرض جميع الطلبات التي تعالجها حالياً أو أكملتها بالفعل — مع أرقام الفواتير والإجماليات والحالة.');
reg('Total Orders', 'إجمالي الطلبات');
reg('View Orders', 'عرض الطلبات');
reg('active orders', 'طلبات نشطة');
reg('My Invoices', 'فواتيري');
reg('Browse all invoices you have generated. View full details or export any invoice as a PDF file.', 'تصفح جميع الفواتير التي أنشأتها. عرض التفاصيل الكاملة أو تصدير أي فاتورة كملف PDF.');
reg('Warehouse Control Center', 'مركز التحكم بالمستودع');
reg('Welcome back,', 'مرحبًا بعودتك،');
reg('Core Operations', 'العمليات الأساسية');
reg('Quick access to shipments, orders, and stock.', 'وصول سريع إلى الشحنات والطلبات والمخزون.');
reg('My Warehouse', 'مستودعي');
reg('View warehouse details, zones, and employee assignments.', 'عرض تفاصيل المستودع والمناطق وتعيينات الموظفين.');
reg('Shipments', 'الشحنات');
reg('Manage incoming shipments, sorting, and tracking.', 'إدارة الشحنات الواردة والفرز والتتبع.');
reg('Orders', 'الطلبات');
reg('Requests', 'الطلبات');
reg('Manage customer orders, processing, and invoices.', 'إدارة طلبات العملاء والمعالجة والفواتير.');
reg('Employees', 'الموظفون');
reg('View and manage warehouse employee assignments and roles.', 'عرض وإدارة تعيينات وأدوار موظفي المستودع.');
reg('Working', 'يعمل');
reg('Out of Service', 'خارج الخدمة');
reg('Retired', 'متقاعد');
reg('Transferred', 'منقول');
reg('View Details', 'عرض التفاصيل');
reg('Available Requests', 'الطلبات المتاحة');
reg('My Requests', 'طلباتي');
reg('Job Applications', 'طلبات التوظيف');
reg('application(s) to review', 'طلب (طلبات) للمراجعة');
reg('No applications', 'لا توجد طلبات');
reg('There are no applications to process right now.', 'لا توجد طلبات للمعالجة حالياً.');
reg('No position', 'بدون وظيفة');
reg('Stage:', 'المرحلة:');
reg('Back to Dashboard', 'العودة إلى لوحة التحكم');
reg('Employees List', 'قائمة الموظفين');
reg('employee(s). Deleting removes the account, job applications and warehouse role. Shipment records are kept.', 'موظف. الحذف يزيل الحساب وطلبات التوظيف ودور المستودع. يتم الاحتفاظ بسجلات الشحنات.');
reg('No employees', 'لا يوجد موظفون');
reg('There are no employees to manage yet.', 'لا يوجد موظفون للإدارة بعد.');
reg('Delete Employee', 'حذف الموظف');
reg('Work Shifts', 'ورديات العمل');
reg('Create and manage work shifts for employees.', 'إنشاء وإدارة ورديات العمل للموظفين.');
reg('Create Shift', 'إنشاء وردية');
reg('Define a new work shift with its schedule and attendance tolerance.', 'تحديد وردية عمل جديدة بجدولها الزمني وهامش الحضور.');
reg('View All Shifts', 'عرض كل الورديات');
reg('Browse all defined work shifts, view hours, tolerance periods, and employee assignments.', 'تصفح جميع ورديات العمل المعرّفة، وعرض الساعات وفترات السماح وتعيينات الموظفين.');
reg('Shift Name', 'اسم الوردية');
reg('Start Time', 'وقت البداية');
reg('End Time', 'وقت النهاية');
reg('Tolerance (minutes)', 'الهامش (دقائق)');
reg('Grace period allowed for late check-in', 'فترة السماح المسموح بها للحضور المتأخر');
reg('Create New Shift', 'إنشاء وردية جديدة');
reg('Back', 'رجوع');
reg('Shift created successfully!', 'تم إنشاء الوردية بنجاح!');
reg('Create Another', 'إنشاء وردية أخرى');
reg('Today\'s Attendance', 'حضور اليوم');
reg('Present', 'حاضر');
reg('Late', 'متأخر');
reg('Left Early', 'غادر مبكراً');
reg('Late & Early', 'متأخر وغادر مبكراً');
reg('Total', 'الإجمالي');
reg('Employee', 'الموظف');
reg('Check In', 'تسجيل الدخول');
reg('Check Out', 'تسجيل الخروج');
reg('Hours', 'الساعات');
reg('Status', 'الحالة');
reg('No attendance records found for today.', 'لم يتم العثور على سجلات حضور لليوم.');
reg('Refresh', 'تحديث');
reg('Full List View', 'عرض القائمة الكاملة');
reg('Attended', 'حضر');
reg('Unattended', 'لم يحضر');
reg('Pending', 'قيد الانتظار');
reg('Approved', 'مقبول');
reg('Rejected', 'مرفوض');
reg('Warehouse Manager', 'مدير المستودع');
reg('Input Employee', 'موظف استقبال');
reg('Sorting Employee', 'موظف فرز وتخزين');
reg('Output Employee', 'موظف إخراج');
// Raw `recycle_role` technical values (as returned by the backend, e.g.
// user.recycle_role = 'sorting') — profileRoleLabel getters across every
// dashboard call tr(rawRole), so these lowercase keys must resolve too,
// not just the human-readable "X Employee" labels above.
reg('admin', 'إدارة');
reg('manager', 'مدير المستودع');
reg('input', 'موظف استقبال');
reg('sorting', 'موظف فرز وتخزين');
reg('output', 'موظف إخراج');
reg('Applicant', 'مقدم طلب');
reg('h', 'س');
reg('m', 'د');
reg('All Warehouses', 'جميع المستودعات');
reg('Manage incoming shipments', 'إدارة الشحنات الواردة');
reg('Process incoming shipments', 'معالجة الشحنات الواردة');
reg('View dashboards', 'عرض لوحات التحكم');

// ─── Admin Dashboard missing strings ───
reg('Dashboard', 'لوحة التحكم');
reg('Overview', 'نظرة عامة');
reg('Shipment States', 'حالات الشحنات');
reg('Order States', 'حالات الطلبات');
reg('Applicant States', 'حالات المتقدمين');
reg('Role Labels', 'تسميات الأدوار');
reg('Zone Types', 'أنواع المناطق');
reg('Reports', 'التقارير');
reg('Export', 'تصدير');
reg('Print', 'طباعة');
reg('Filter by warehouse', 'تصفية حسب المستودع');
reg('Search shipments', 'بحث في الشحنات');
reg('Search orders', 'بحث في الطلبات');
reg('Search employees', 'بحث في الموظفين');
reg('Name', 'الاسم');
reg('Login', 'اسم المستخدم');
reg('Role', 'الدور');
reg('Warehouse', 'المستودع');
reg('Date Created', 'تاريخ الإنشاء');
reg('Actions', 'الإجراءات');
reg('Edit', 'تعديل');
reg('Save', 'حفظ');
reg('Cancel', 'إلغاء');
reg('Delete', 'حذف');
reg('Create', 'إنشاء');
reg('loading', 'جارٍ التحميل…');
reg('No data found.', 'لا توجد بيانات.');
reg('Loading…', 'جارٍ التحميل…');
reg('Loading profile…', 'جارٍ تحميل الملف الشخصي…');
reg('Loading notifications…', 'جارٍ تحميل الإشعارات…');
reg('Loading shifts…', 'جارٍ تحميل الورديات…');
reg('Loading warehouses…', 'جارٍ تحميل المستودعات…');
reg('Loading shipments…', 'جارٍ تحميل الشحنات…');
reg('Loading lines…', 'جارٍ تحميل البنود…');
reg('Loading orders…', 'جارٍ تحميل الطلبات…');
reg('Loading more…', 'جارٍ تحميل المزيد…');
reg('End of list.', 'نهاية القائمة.');
reg('Loading reports…', 'جارٍ تحميل التقارير…');
reg('Loading jobs…', 'جارٍ تحميل الوظائف…');
reg('Loading applicants…', 'جارٍ تحميل المتقدمين…');
reg('Loading employees…', 'جارٍ تحميل الموظفين…');
reg('Loading deleted employees…', 'جارٍ تحميل الموظفين المحذوفين…');
reg('Loading accepted applicants…', 'جارٍ تحميل المتقدمين المقبولين…');
reg('Loading rejected applicants…', 'جارٍ تحميل المتقدمين المرفوضين…');
reg('Yes', 'نعم');
reg('No', 'لا');
reg('Close', 'إغلاق');

// ─── Admin Dashboard full translations ───
reg('System Control Center', 'مركز التحكم');
reg('Welcome back', 'مرحباً بعودتك');
reg('live system overview', 'إليك نظرة عامة على النظام.');
reg('WMS', 'نظام إدارة المستودع');
reg('this month', 'هذا الشهر');
reg('v19.0', 'الإصدار 19.0');
reg('System Overview', 'نظرة عامة على النظام');
reg('Distribution', 'التوزيع');
reg('Recent Shipments', 'أحدث الشحنات');
reg('Recent Orders', 'أحدث الطلبات');
reg('Recent Requests', 'أحدث الطلبات');
reg('View All', 'عرض الكل ←');
reg('My Profile', 'ملفي الشخصي');
reg('Your account details, role, and system access information.', 'تفاصيل حسابك، دورك، وصلاحيات الوصول إلى النظام.');
reg('Administrator', 'مدير النظام');
reg('Settings', 'الإعدادات');
reg('Customize your dashboard appearance and system preferences.', 'خصص مظهر لوحة التحكم وتفضيلات النظام.');
reg('Appearance', 'المظهر');
reg('Dark Mode', 'الوضع الليلي');
reg('Toggle between light and dark theme', 'التبديل بين الوضع الفاتح والداكن');
reg('Language', 'اللغة');
reg('Privacy & Security', 'الخصوصية والأمان');
reg('Change Password', 'تغيير كلمة السر');
reg('Update your account password', 'تحديث كلمة مرور حسابك');
reg('Active Sessions', 'الجلسات النشطة');
reg('Manage your active sessions', 'إدارة جلساتك النشطة');
reg('Devices currently signed in to your account.', 'الأجهزة المسجلة دخولاً حالياً إلى حسابك.');
reg('Device', 'الجهاز');
reg('IP Address', 'عنوان IP');
reg('Location', 'الموقع');
reg('Last Activity', 'آخر نشاط');
reg('Last Action', 'آخر عملية');
reg('Approval', 'الموافقة');
reg('Rejection Reason', 'سبب الرفض');
reg('Reject Order', 'رفض الطلبية');
reg('Optional reason…', 'السبب (اختياري)…');
reg('Order approved and released to output employees.', 'تمت الموافقة على الطلبية وأصبحت متاحة لموظفي الإخراج.');
reg('Order rejected.', 'تم رفض الطلبية.');
reg('Awaiting your approval', 'بانتظار موافقتك');
reg('Add Warehouse', 'إضافة مستودع');
reg('Create a new warehouse with its location and storage zones.', 'إنشاء مستودع جديد مع موقعه ومناطق التخزين الخاصة به.');
reg('Warehouse Name', 'اسم المستودع');
reg('Warehouse Code', 'كود المستودع');
reg('Latitude', 'خط العرض');
reg('Longitude', 'خط الطول');
reg('Select a governorate…', 'اختر محافظة…');
reg('Zones (optional)', 'المناطق (اختياري)');
reg('Leave empty to auto-create the 4 standard zones (Receiving, Sorting, Storage, Output). Any zone you add here is kept, and the remaining standard types are still created automatically.', 'اتركه فارغاً لإنشاء المناطق الأربعة القياسية تلقائياً (الاستلام، الفرز، التخزين، الإخراج). أي منطقة تضيفها هنا تبقى كما هي، وباقي الأنواع القياسية تُنشأ تلقائياً أيضاً.');
reg('Add Zone', 'إضافة منطقة');
reg('Save Warehouse', 'حفظ المستودع');
reg('Warehouse name is required.', 'اسم المستودع مطلوب.');
reg('Warehouse code is required.', 'كود المستودع مطلوب.');
reg('Latitude must be between -90 and 90.', 'خط العرض يجب أن يكون بين -90 و90.');
reg('Longitude must be between -180 and 180.', 'خط الطول يجب أن يكون بين -180 و180.');
reg('Each zone needs both a name and a type — remove incomplete rows.', 'كل منطقة تحتاج اسماً ونوعاً معاً — احذف الصفوف غير المكتملة.');
reg('Warehouse created successfully!', 'تم إنشاء المستودع بنجاح!');
// Governorate display labels (the DB stores the technical code, e.g.
// "damascus" — these are what govLabel() in dashboard_shared.js maps it
// through before handing it to tr()).
reg('Damascus', 'دمشق');
reg('Rif Dimashq', 'ريف دمشق');
reg('Aleppo', 'حلب');
reg('Homs', 'حمص');
reg('Hama', 'حماة');
reg('Latakia', 'اللاذقية');
reg('Tartus', 'طرطوس');
reg('Idlib', 'إدلب');
reg('Deir ez-Zor', 'دير الزور');
reg('Raqqa', 'الرقة');
reg('Al-Hasakah', 'الحسكة');
reg('Daraa', 'درعا');
reg('As-Suwayda', 'السويداء');
reg('Quneitra', 'القنيطرة');
reg('Login', 'تسجيل دخول');
reg('Logout', 'تسجيل خروج');
reg('First Seen', 'أول ظهور');
reg('This device', 'هذا الجهاز');
reg('No active sessions found.', 'لا توجد جلسات نشطة.');
reg('Sign out of your account', 'تسجيل الخروج من حسابك');
reg('Reception Employee', 'موظف الاستقبال');
reg('Switch theme', 'التبديل بين الوضع الفاتح والداكن');
reg('Language / اللغة', 'اللغة / Language');
reg('Select the display language for the system', 'اختر لغة عرض النظام');
reg('System Information', 'معلومات النظام');
reg('Platform', 'المنصة');
reg('Module', 'الوحدة');
reg('User', 'المستخدم');
reg('Save Settings', 'حفظ الإعدادات');
reg('Settings saved successfully!', 'تم حفظ الإعدادات بنجاح!');
reg('Notifications', 'الإشعارات');
reg('Recent activity across shipments and orders in the system.', 'النشاط الأخير في الشحنات والطلبات.');
reg('No recent notifications.', 'لا توجد إشعارات حديثة.');
reg('Shift Management', 'إدارة الوردیات');
reg('Create and manage work shifts, or browse all existing shifts and their assigned employees.', 'إنشاء وإدارة الورديات أو تصفح جميع الورديات المعرّفة والموظفين المعينين.');
reg('Add a new work shift with custom start time, end time, and attendance tolerance settings.', 'أضف وردية عمل جديدة بوقت بداية ونهاية وهامش حضور مخصص.');
reg('Browse all defined work shifts, view hours, tolerance periods, and employee assignments.', 'تصفح جميع الورديات المعرّفة، واطلع على الأوقات وعدد الموظفين.');
reg('Define a new work shift with its schedule and attendance tolerance.', 'حدد جدول وردية عمل جديدة وهامش الحضور.');
reg('Grace period allowed for late check-in', 'فترة السماح للحضور المتأخر');
reg('Save Shift', 'حفظ الوردية');
reg('Saving…', 'جارٍ الحفظ…');
reg('No shifts defined.', 'لا توجد ورديات محددة.');
reg('Active', 'نشط');
reg('Inactive', 'غير نشط');
reg('employee(s)', 'موظف');
reg('Work Shifts', 'ورديات العمل');
reg('All defined work shifts — view shift hours, tolerance, and assigned employee counts.', 'جميع الورديات المعرّفة — الأوقات والهامش وعدد الموظفين.');
reg('Shift Name', 'اسم الوردية');
reg('Tolerance', 'الهامش');
reg('Shift Name *', 'اسم الوردية *');
reg('Start Time *', 'وقت البداية *');
reg('End Time *', 'وقت النهاية *');
reg('My Warehouse', 'مستودعي');
reg('View your warehouse details, zones, employees, and settings.', 'عرض تفاصيل المستودع والمناطق والموظفين والإعدادات.');
reg('Monitor incoming shipments, approve escalations, and track delivery status.', 'مراقبة الشحنات الواردة والموافقة على التصعيد وتتبع حالة التسليم.');
reg('Track outgoing orders, review invoices, and manage customer requests.', 'تتبع الطلبات الصادرة ومراجعة الفواتير وإدارة طلبات العملاء.');
reg("View today's attendance: who is present, who is late, check-in/out times and hours.", 'عرض حضور اليوم: من حاضر ومن متأخر وأوقات تسجيل الدخول/الخروج والساعات.');
reg('Core Operations', 'العمليات الأساسية');
reg('Damage Requests', 'طلبات التلف');
reg('Replacement Requests', 'طلبات الاستبدال');
reg('General Information', 'معلومات عامة');
reg('Product Lines', 'بنود المنتجات');
reg('Shipment details — driver, weight, product lines, and current status.', 'تفاصيل الشحنة — السائق والوزن وبنود المنتجات والحالة الحالية.');
reg('Reference', 'المرجع');
reg('Driver', 'السائق');
reg('Priority', 'الأولوية');
reg('Expected Weight', 'الوزن المتوقع');
reg('Actual Weight', 'الوزن الفعلي');
reg('Weight Diff %', 'نسبة فرق الوزن');
reg('Received At', 'تاريخ الاستلام');
reg('Received By', 'المستلم');
reg('Loading lines…', 'جارٍ تحميل البنود…');
reg('Track all incoming shipments across warehouses — filter by warehouse or search by reference.', 'تتبع جميع الشحنات الواردة عبر المستودعات — تصفية حسب المستودع أو البحث حسب المرجع.');
reg('Search by reference, driver…', 'بحث حسب المرجع أو السائق…');
reg('ID', 'الرقم');
reg('Quantity', 'الكمية');
reg('Condition', 'الحالة');
reg('No shipments found.', 'لم يتم العثور على شحنات.');
reg('No orders found.', 'لم يتم العثور على طلبات.');
reg('Browse and manage all recycling orders. Click any row to view details and print a PDF invoice.', 'تصفح وإدارة جميع طلبات إعادة التدوير. انقر على أي صف لعرض التفاصيل وطباعة فاتورة PDF.');
reg('Search by reference, warehouse, customer…', 'بحث حسب المرجع أو المستودع أو العميل…');
reg('Loading orders…', 'جارٍ تحميل الطلبات…');
reg('Order details — product lines, weight breakdown, and PDF invoice for completed orders.', 'تفاصيل الطلب — بنود المنتجات و Breakdown الوزن و فاتورة PDF للطلبات المكتملة.');
reg('Order Completed', 'الطلب مكتمل');
reg('Export PDF Invoice', 'تصدير فاتورة PDF');
reg('Order Information', 'معلومات الطلب');
reg('Customer', 'العميل');
reg('Owner', 'المالك');
reg('Source', 'المصدر');
reg('Invoice #', 'رقم الفاتورة');
reg('Total Weight', 'الوزن الإجمالي');
reg('Amount Total', 'المبلغ الإجمالي');
reg('Processed By', 'تمت المعالجة بواسطة');
reg('Order Lines', 'بنود الطلب');
reg('Qty', 'الكمية');
reg('Unit Price', 'سعر الوحدة');
reg('Subtotal', 'المجموع الفرعي');
reg('Loading lines…', 'جارٍ تحميل البنود…');
reg('Warehouses', 'المستودعات');
reg('Registered Users', 'المستخدمون المسجلون');
// ── Deleted employees / Users management ──
reg('Users', 'المستخدمون');
reg('Website Users', 'مستخدمو الموقع');
reg('Accounts registered on the website. Ban, unban or delete accounts.', 'الحسابات المسجلة على الموقع. حظر أو فك حظر أو حذف الحسابات.');
reg('Search by name or email…', 'ابحث بالاسم أو البريد الإلكتروني…');
reg('Deleted On', 'تاريخ الحذف');
reg('Reason', 'السبب');
reg('Actions', 'الإجراءات');
reg('View', 'عرض');
reg('Restore', 'استعادة');
reg('Delete Permanently', 'حذف نهائي');
reg('Ban', 'حظر');
reg('Unban', 'فك الحظر');
reg('Delete', 'حذف');
reg('Banned', 'محظور');
reg('Active', 'نشط');
reg('Status', 'الحالة');
reg('Registered', 'تاريخ التسجيل');
reg('No users found.', 'لم يتم العثور على مستخدمين.');
reg('Loading users…', 'جارٍ تحميل المستخدمين…');
reg('Login', 'اسم الدخول');
reg('National ID', 'الرقم الوطني');
// Prompts / notifications
reg('Delete this employee? The account will be archived and can be restored later.\n\nOptional reason:', 'حذف هذا الموظف؟ سيتم أرشفة الحساب ويمكن استعادته لاحقاً.\n\nسبب اختياري:');
reg('Employee deleted (archived).', 'تم حذف الموظف (أرشفة).');
reg('Employee restored.', 'تمت استعادة الموظف.');
reg('Permanently delete this account? This cannot be undone. Shipment records are kept.', 'حذف هذا الحساب نهائياً؟ لا يمكن التراجع. يتم الاحتفاظ بسجلات الشحنات.');
reg('Account permanently deleted.', 'تم حذف الحساب نهائياً.');
reg('Ban this user? They will be signed out and blocked from logging in.\n\nOptional reason:', 'حظر هذا المستخدم؟ سيتم تسجيل خروجه ومنعه من الدخول.\n\nسبب اختياري:');
reg('User banned.', 'تم حظر المستخدم.');
reg('User unbanned.', 'تم فك حظر المستخدم.');
reg('Permanently delete this account? This cannot be undone.', 'حذف هذا الحساب نهائياً؟ لا يمكن التراجع.');
reg('Account deleted.', 'تم حذف الحساب.');
// ── Applicant processing (Admin Home design) ──
reg('Loading application…', 'جارٍ تحميل الطلب…');
reg('Could not load the application.', 'تعذّر تحميل الطلب.');
reg('Position Type', 'نوع الوظيفة');
reg('Manager', 'مدير');
reg('Employee', 'موظف');
reg('Profile Link', 'رابط الملف الشخصي');
reg('Attachments (CV, documents)', 'المرفقات (السيرة الذاتية، المستندات)');
reg('No documents were attached to this application.', 'لا توجد مستندات مرفقة بهذا الطلب.');
reg('Download', 'تنزيل');
reg('Schedule Interview', 'جدولة مقابلة');
reg('Currently scheduled:', 'المجدولة حالياً:');
reg('Date & Time', 'التاريخ والوقت');
reg('Location / Video Link', 'الموقع / رابط الفيديو');
reg('Office address or meeting link', 'عنوان المكتب أو رابط الاجتماع');
reg('Message to Applicant', 'رسالة إلى المتقدم');
reg('Schedule & Email Applicant', 'جدولة وإرسال بريد للمتقدم');
reg('Create Account', 'إنشاء حساب');
reg('Account already created:', 'تم إنشاء الحساب بالفعل:');
reg('Assign to Warehouse', 'تعيين إلى مستودع');
reg('Select a warehouse', 'اختر مستودعاً');
reg('Role (optional)', 'الدور (اختياري)');
reg('Assigned later by manager', 'يُعيَّن لاحقاً من قبل المدير');
reg('Create Manager Account', 'إنشاء حساب مدير');
reg('Create Employee Account', 'إنشاء حساب موظف');
reg('Please pick an interview date and time.', 'يرجى اختيار تاريخ ووقت المقابلة.');
reg('Please select a warehouse.', 'يرجى اختيار مستودع.');
reg('Interview scheduled.', 'تمت جدولة المقابلة.');
reg('Interview saved, but the email could not be sent (configure a mail server).', 'تم حفظ المقابلة، لكن تعذّر إرسال البريد (قم بإعداد خادم بريد).');
reg('Account created successfully.', 'تم إنشاء الحساب بنجاح.');
reg('Stage approved.', 'تمت الموافقة على المرحلة.');
reg('Stage rejected.', 'تم رفض المرحلة.');
reg('Moved to the next stage.', 'تم الانتقال إلى المرحلة التالية.');
reg('Status updated.', 'تم تحديث الحالة.');
reg('Applied For', 'تقدم لـ');
reg('Cover Letter:', 'الرسالة التعريفية:');
// ── Advanced Shift Management ──
reg('Shift name is required.', 'اسم الوردية مطلوب.');
reg('Start and end time cannot be the same.', 'لا يمكن أن يكون وقت البداية والنهاية متطابقين.');
reg('A shift must last at least 4 hours.', 'يجب أن تستمر الوردية 4 ساعات على الأقل.');
reg('A shift cannot exceed 12 hours.', 'لا يمكن أن تتجاوز الوردية 12 ساعة.');
reg('A shift must last at least 6 hours.', 'يجب أن تستمر الوردية 6 ساعات على الأقل.');
reg('A shift cannot exceed 9 hours.', 'لا يمكن أن تتجاوز الوردية 9 ساعات.');
reg('(allowed 6–9h)', '(المسموح 6–9 ساعات)');
reg('Tolerance cannot be negative.', 'لا يمكن أن تكون فترة السماح سالبة.');
reg('Duration:', 'المدة:');
reg('hours', 'ساعات');
reg('(allowed 4–12h)', '(المسموح 4–12 ساعة)');
reg('Warehouse', 'المستودع');
reg('All warehouses', 'جميع المستودعات');
reg('Available Employees', 'الموظفون المتاحون');
reg('Loading employees…', 'جارٍ تحميل الموظفين…');
reg('No employees found for this warehouse.', 'لا يوجد موظفون لهذا المستودع.');
reg('currently on:', 'حالياً على:');
reg('Unusual Shift Times', 'أوقات وردية غير معتادة');
reg('These times are outside the usual shift hours. Do you want to continue?', 'هذه الأوقات خارج الأوقات المعتادة. هل تريد المتابعة؟');
reg('Yes, continue', 'نعم، تابع');
reg('No', 'لا');
reg('Cannot Delete Shift', 'لا يمكن حذف الوردية');
reg('Cannot delete this shift as it is assigned to employees:', 'لا يمكن حذف هذه الوردية لأنها مسندة للموظفين:');
reg('Unassign them from the shift first, then delete it.', 'قم بإلغاء إسناد الموظفين من الوردية أولاً ثم احذفها.');
reg('OK', 'حسناً');
reg('Delete Shift', 'حذف الوردية');
reg('Delete this shift?', 'حذف هذه الوردية؟');
reg('Shift deleted successfully.', 'تم حذف الوردية بنجاح.');
reg('Failed to delete shift.', 'فشل حذف الوردية.');
reg('Assigned to employees — cannot delete', 'مسندة لموظفين — لا يمكن الحذف');
reg('Shift created successfully.', 'تم إنشاء الوردية بنجاح.');
reg('Shift updated successfully.', 'تم تحديث الوردية بنجاح.');
reg('Shift updated and times synchronized for all employees.', 'تم تحديث الوردية ومزامنة الأوقات لجميع الموظفين.');
reg('Failed to save shift.', 'فشل حفظ الوردية.');
reg('Failed to update shift.', 'فشل تحديث الوردية.');
reg('No shift selected.', 'لم يتم اختيار وردية.');
// ── Stage pipeline / talent pool / stage management ──
reg('Hiring Pipeline', 'مسار التوظيف');
reg('Current stage:', 'المرحلة الحالية:');
reg('Status:', 'الحالة:');
reg('Approve Stage', 'اعتماد المرحلة');
reg('Reject Stage', 'رفض المرحلة');
reg('Advance to Next Stage →', 'الانتقال للمرحلة التالية →');
reg('Stages only move forward — you cannot return to a previous stage.', 'المراحل تتقدم للأمام فقط — لا يمكنك العودة لمرحلة سابقة.');
reg('★ Add to Talent Pool', '★ إضافة إلى تجمّع المرشحين');
reg('Remove from Talent Pool', 'إزالة من تجمّع المرشحين');
reg('In Talent Pool', 'في تجمّع المرشحين');
reg('Added to the talent pool.', 'تمت الإضافة إلى تجمّع المرشحين.');
reg('Removed from the talent pool.', 'تمت الإزالة من تجمّع المرشحين.');
reg('Talent Pool', 'تجمّع المرشحين');
reg('Retained candidates kept for future positions.', 'مرشحون محتَفَظ بهم لوظائف مستقبلية.');
reg('The talent pool is empty.', 'تجمّع المرشحين فارغ.');
reg('Added to Pool', 'تاريخ الإضافة');
reg('Remove', 'إزالة');
reg('Action failed.', 'فشل الإجراء.');
reg('Hiring Stages', 'مراحل التوظيف');
reg('Add, reorder or remove the stages of the hiring pipeline.', 'إضافة أو ترتيب أو حذف مراحل مسار التوظيف.');
reg('New Stage Name', 'اسم المرحلة الجديدة');
reg('e.g. Contract Signing', 'مثال: توقيع العقد');
reg('Order', 'الترتيب');
reg('Add Stage', 'إضافة مرحلة');
reg('Stage Name', 'اسم المرحلة');
reg('No stages defined.', 'لا توجد مراحل معرّفة.');
reg('Stage name is required.', 'اسم المرحلة مطلوب.');
reg('Stage added.', 'تمت إضافة المرحلة.');
reg('Failed to add stage.', 'فشل إضافة المرحلة.');
reg('Delete this stage? Applications in it may be affected.', 'حذف هذه المرحلة؟ قد تتأثر الطلبات الموجودة فيها.');
reg('Stage deleted.', 'تم حذف المرحلة.');
reg('Failed to delete stage.', 'فشل حذف المرحلة.');
reg('Failed to reorder stages.', 'فشل إعادة ترتيب المراحل.');
reg('Logout', 'تسجيل الخروج');
reg('Sign out of your account.', 'تسجيل الخروج من حسابك.');
reg('Orders', 'الطلبات');
reg('No assign', 'بدون إسناد');
reg('Long Shift', 'وردية طويلة');
reg('This shift is longer than the recommended 9 hours (up to 12h). Do you want to continue?', 'هذه الوردية أطول من الـ9 ساعات الموصى بها (حتى 12 ساعة). هل تريد المتابعة؟');
reg('A shift cannot exceed 12 hours.', 'لا يمكن أن تتجاوز الوردية 12 ساعة.');
reg('Other (type below)', 'أخرى (اكتب أدناه)');
reg('Interview stage (enables interview scheduling)', 'مرحلة مقابلة (تفعّل جدولة المقابلة)');
reg('Description (optional)', 'الوصف (اختياري)');
reg('Optional description for this stage…', 'وصف اختياري لهذه المرحلة…');
reg('Interview', 'مقابلة');
reg('Normal', 'عادية');
reg('Set interview', 'تعيين كمقابلة');
reg('Unset interview', 'إلغاء المقابلة');
reg('Type', 'النوع');
reg('Reject Application', 'رفض الطلب');
reg('Please provide a reason for rejection:', 'يرجى تقديم سبب الرفض:');
reg('Reason…', 'السبب…');
reg('Confirm Reject', 'تأكيد الرفض');
reg('Cancel', 'إلغاء');
reg('Rejection reason:', 'سبب الرفض:');
reg('⚠ This is an interview stage — schedule the interview below before advancing.', '⚠ هذه مرحلة مقابلة — قم بجدولة المقابلة أدناه قبل الانتقال.');
// ── Archiving + notifications + warehouse detail ──
reg('Archived Employees', 'الموظفون المؤرشفون');
reg('Archived On', 'تاريخ الأرشفة');
reg('Previous Warehouse', 'المستودع السابق');
reg('was manager', 'كان مديراً');
reg('No archived employees found.', 'لا يوجد موظفون مؤرشفون.');
reg('Loading archived employees…', 'جارٍ تحميل الموظفين المؤرشفين…');
reg('Reactivate', 'إعادة تفعيل');
reg('Account reactivated.', 'تم إعادة تفعيل الحساب.');
reg('Request declined.', 'تم رفض الطلب.');
reg('Action failed.', 'فشل الإجراء.');
reg('View the team of', 'عرض فريق');
reg('Archived staff who were assigned to', 'الموظفون المؤرشفون الذين كانوا مسندين إلى');
reg('Showing items for:', 'عرض عناصر:');
reg('Message / Details (include the meeting link here)', 'الرسالة / التفاصيل (ضع رابط الاجتماع هنا)');
reg('Write the interview details and paste the meeting link here…', 'اكتب تفاصيل المقابلة وألصق رابط الاجتماع هنا…');
reg('No recent notifications.', 'لا توجد إشعارات حديثة.');
reg('Select a warehouse to view its details, shipments, orders, and team members.', 'اختر مستودعاً لعرض تفاصيله وشحناته وطلباته وأعضاء فريقه.');
reg('Loading warehouses…', 'جارٍ تحميل المستودعات…');
reg('No warehouses found.', 'لم يتم العثور على مستودعات.');
reg('Manager:', 'المدير:');
reg('View all shipments for', 'عرض جميع الشحنات لـ');
reg('View all orders for', 'عرض جميع الطلبات لـ');
reg('Member Since', 'عضو منذ');
reg('Showing shipments for:', 'عرض الشحنات لـ:');
reg('Showing orders for:', 'عرض الطلبات لـ:');
reg('Jobs & HR', 'الوظائف والموارد البشرية');
reg('Manage job postings, review applicants, and track the hiring pipeline from one place.', 'إدارة إعلانات الوظائف ومراجعة المتقدمين وتتبع خط التوظيف من مكان واحد.');
reg('View Jobs', 'عرض الوظائف');
reg('Browse all job postings. View details, publish or unpublish, and edit job information.', 'تصفح جميع إعلانات الوظائف. عرض التفاصيل والنشر أو إلغاء النشر وتحرير معلومات الوظيفة.');
reg('Create Job', 'إنشاء وظيفة');
reg('Add a new job position to the recruitment pipeline for this recycle system.', 'إضافة وظيفة جديدة إلى خط التوظيف لنظام إعادة التدوير هذا.');
reg('Job Applicants', 'المتقدمون للوظائف');
reg('Browse all applicants across every job position and review their application status.', 'تصفح جميع المتقدمين عبر كل وظيفة ومراجعة حالة طلباتهم.');
reg('Accepted', 'مقبول');
reg('View all applicants who have been accepted into the hiring pipeline.', 'عرض جميع المتقدمين الذين تم قبولهم في خط التوظيف.');
reg('Rejected', 'مرفوض');
reg('View all applicants who were rejected, along with their final stage and reason.', 'عرض جميع المتقدمين الذين تم رفضهم، مع مرحلتهم النهائية والسبب.');
reg('Job Positions', 'الوظائف');
reg('All active and draft job postings — publish, edit, and view applicants for each position.', 'جميع إعلانات الوظائف النشطة والمسودة — النشر والتحرير وعرض المتقدمين لكل وظيفة.');
reg('Loading jobs…', 'جارٍ تحميل الوظائف…');
reg('Job Title', 'المسمى الوظيفي');
reg('Type', 'النوع');
reg('To Hire', 'المطلوب');
reg('Hired', 'تم التعيين');
reg('Published', 'منشور');
reg('Draft', 'مسودة');
reg('View', 'عرض');
reg('Unpublish', 'إلغاء النشر');
reg('Publish', 'نشر');
reg('Applicants', 'المتقدمون');
reg('No jobs found.', 'لم يتم العثور على وظائف.');
reg('Create Job', 'إنشاء وظيفة');
reg('Job position details — edit, publish, and review applicants for this role.', 'تفاصيل الوظيفة — التحرير والنشر ومراجعة المتقدمين لهذا الدور.');
reg('Job Type', 'نوع الوظيفة');
reg('Positions to Hire', 'عدد الوظائف المطلوبة');
reg('Hired', 'تم التعيين');
reg('Publish on Recycle Website', 'نشر على موقع إعادة التدوير');
reg('Save Changes', 'حفظ التغييرات');
reg('Creating…', 'جارٍ الإنشاء…');
reg('Create Job', 'إنشاء وظيفة');
reg('Publish on Recycle Website', 'نشر على موقع إعادة التدوير');
reg('Create New Job', 'إنشاء وظيفة جديدة');
reg('Define a new job position — set its title, type, and number of positions to fill.', 'تحديد وظيفة جديدة — تعيين المسمى والنوع وعدد الوظائف المطلوبة.');
reg('Job Title *', 'المسمى الوظيفي *');
reg('e.g. Sorting Specialist', 'مثال: أخصائي فرز');
reg('Warehouse Employee', 'موظف مستودع');
reg('General Employee', 'موظف عام');
reg('Description', 'الوصف');
reg('Describe the position…', 'صف الوظيفة…');
reg('General: any of the four employee roles is assigned later. A specific role locks every hire from this job to that role only.', 'عام: يتم تعيين أي من الأدوار الأربعة لاحقًا. اختيار دور محدد يقصر كل من يُوظَّف من هذه الوظيفة على هذا الدور فقط.');
reg('Assign role now:', 'تعيين الدور الآن:');
reg('This job is specialized — only this role can be assigned. Leave unchecked to let the warehouse manager assign it.', 'هذه الوظيفة متخصصة — لا يمكن تعيين إلا هذا الدور. اتركه غير محدد ليقوم مدير المستودع بتعيينه.');
reg('This job is specialized — only this role can be assigned.', 'هذه الوظيفة متخصصة — لا يمكن تعيين إلا هذا الدور.');
reg('Review candidates by stage — each stage shows its approval status.', 'مراجعة المرشحين حسب المرحلة — كل مرحلة تظهر حالة الموافقة.');
reg('Applicant Name', 'اسم المتقدم');
reg('Email', 'البريد الإلكتروني');
reg('Phone', 'الهاتف');
reg('Applied For', 'متقدم لـ');
reg('Stage', 'المرحلة');
reg('Stage Status', 'حالة المرحلة');
reg('No applicants found.', 'لم يتم العثور على متقدمين.');
reg('Review application, update hiring stage, and manage interview details.', 'مراجعة الطلب وتحديث مرحلة التوظيف وإدارة تفاصيل المقابلة.');
reg('Applied', 'متقدم');
reg('Interview', 'مقابلة');
reg('Full Name', 'الاسم الكامل');
reg('National ID', 'الهوية الوطنية');
reg('Interview Date', 'تاريخ المقابلة');
reg('Current Status', 'الحالة الحالية');
reg('Cover Letter:', 'خطاب التقديم:');
reg('Interview Notes:', 'ملاحظات المقابلة:');
reg('Manage current employees and review deleted accounts.', 'إدارة الموظفين الحاليين ومراجعة الحسابات المحذوفة.');
reg('Active Employees', 'الموظفون النشطون');
reg('Deleted Employees', 'الموظفون المحذوفون');
reg('Filter by Warehouse:', 'تصفية حسب المستودع:');
reg('Loading employees…', 'جارٍ تحميل الموظفين…');
reg('Login / Email', 'اسم المستخدم / البريد');
reg('No employees found.', 'لم يتم العثور على موظفين.');
reg('Delete employee', 'حذف الموظف');
reg('This removes their account, job applications and warehouse role. Shipment records are kept.', 'هذا يزيل الحساب وطلبات التوظيف ودور المستودع. يتم الاحتفاظ بسجلات الشحنات.');
reg('Employee deleted successfully.', 'تم حذف الموظف بنجاح.');
reg('Failed to delete employee:', 'فشل حذف الموظف:');
reg('Stock', 'المخزون');
reg('View stock quantities across warehouses — filter by warehouse to narrow results.', 'عرض كميات المخزون عبر المستودعات — تصفية حسب المستودع لتضييق النتائج.');
reg('Filter by Warehouse:', 'تصفية حسب المستودع:');

// ─── Admin state labels ───
reg('In Reception', 'قيد الاستقبال');
reg('Transferred', 'محول');
reg('Sorted', 'تم الفرز');
reg('Processing', 'قيد المعالجة');
reg('Ready', 'جاهز');
reg('Completed', 'مكتمل');
reg('Cancelled', 'ملغي');
reg('In Progress', 'قيد التقدم');
reg('Resolved', 'تم الحل');
reg('Storage', 'تخزين');
reg('Output', 'إخراج');
reg('Interview', 'مقابلة');

// ─── Placeholders ───
reg('Search by reference, driver…', 'بحث حسب المرجع أو السائق…');
reg('Search by reference, warehouse, customer…', 'بحث حسب المرجع أو المستودع أو العميل…');
reg('Search by product name…', 'بحث باسم المنتج…');
reg('Search by name, warehouse, driver…', 'بحث بالاسم أو المستودع أو السائق…');
reg('Search by name, email, or job…', 'بحث بالاسم أو البريد أو الوظيفة…');
reg('e.g. Morning Shift', 'مثال: الوردية الصباحية');
reg('e.g. Sorting Specialist', 'مثال: أخصائي فرز');
reg('Full name', 'الاسم الكامل');
reg('Username / Email', 'اسم المستخدم / البريد الإلكتروني');
reg('Email address', 'عنوان البريد الإلكتروني');
reg('e.g. Receiving Area A', 'مثال: منطقة الاستقبال أ');

reg('Filter by Warehouse:', 'تصفية حسب المستودع:');
reg('Loading stock…', 'جارٍ تحميل المخزون…');
reg('Product', 'المنتج');
reg('No stock records found.', 'لم يتم العثور على سجلات مخزون.');
reg('Products', 'المنتجات');
reg('View all products — search by name to quickly find what you need.', 'عرض جميع المنتجات — بحث بالاسم للعثور بسرعة على ما تحتاجه.');
reg('Search by product name…', 'بحث باسم المنتج…');
reg('Loading products…', 'جارٍ تحميل المنتجات…');
reg('Category', 'الفئة');
reg('Price', 'السعر');
reg('Factory Price', 'سعر المصنع');
reg('Free Facility Price', 'سعر المنشأة الحرة');
reg('Weight (kg)', 'الوزن (كجم)');
reg('No products found.', 'لم يتم العثور على منتجات.');
reg('Product Categories', 'تصنيفات المنتجات');
reg('View all product categories.', 'عرض جميع تصنيفات المنتجات.');
reg('Loading categories…', 'جارٍ تحميل التصنيفات…');
reg('No categories found.', 'لم يتم العثور على تصنيفات.');
reg('Description:', 'الوصف:');
reg('Notes:', 'ملاحظات:');
reg('Serial Number', 'الرقم التسلسلي');
reg('Date Added', 'تاريخ الإضافة');
reg('Loading reports…', 'جارٍ تحميل التقارير…');
reg('Title', 'العنوان');
reg('Reported By', 'تم الإبلاغ بواسطة');
reg('Shift name is required.', 'اسم الوردية مطلوب.');
reg('End time must be after start time.', 'يجب أن يكون وقت النهاية بعد وقت البداية.');
reg('Tolerance cannot be negative.', 'لا يمكن أن يكون الهامش سالباً.');
reg('An error occurred while saving.', 'حدث خطأ أثناء الحفظ.');
reg('Success', 'نجاح');
reg('Error', 'خطأ');
reg('Filter by Warehouse:', 'تصفية حسب المستودع:');
reg('Zone Type *', 'نوع المنطقة *');
reg('Zone Name *', 'اسم المنطقة *');
reg('Create Zone', 'إنشاء منطقة');
reg('Zone created successfully!', 'تم إنشاء المنطقة بنجاح!');
reg('Zone name is required.', 'اسم المنطقة مطلوب.');
reg('Receiving', 'استقبال');
reg('Zone Details', 'تفاصيل المنطقة');
reg('No documents yet.', 'لا توجد مستندات بعد.');
reg('Accepted Applicants', 'المتقدمون المقبولون');
reg('Rejected Applicants', 'المتقدمون المرفوضون');
reg('No accepted applicants found.', 'لم يتم العثور على متقدمين مقبولين.');
reg('No rejected applicants found.', 'لم يتم العثور على متقدمين مرفوضين.');
reg('Add Employee', 'إضافة موظف');
reg('Create Employee', 'إنشاء موظف');
reg('Employee created successfully!', 'تم إنشاء الموظف بنجاح!');
reg('Name *', 'الاسم *');
reg('Login *', 'اسم المستخدم *');
reg('Email *', 'البريد الإلكتروني *');
reg('Password', 'كلمة المرور');
reg('Confirm Password', 'تأكيد كلمة المرور');
reg('Passwords do not match.', 'كلمتا المرور غير متطابقتين.');
reg('Save & Add Another', 'حفظ وإضافة آخر');
reg('Welcome', 'مرحباً');
reg('You have no pending tasks.', 'لا توجد مهام معلقة.');
reg('All tasks completed!', 'جميع المهام مكتملة!');
reg('View all', 'عرض الكل');
reg('Clear All', 'مسح الكل');
reg('Mark all as read', 'تحديد الكل كمقروء');
reg('English', 'English');
reg('Phone', 'الهاتف');
reg('lang desc', 'اختر لغة عرض النظام');
reg('Odoo 19.0', 'أودو 19.0');
reg('Recycle WMS v1.0', 'نظام إدارة المستودع v1.0');
reg('View All →', 'عرض الكل ←');
reg('Code:', 'الرمز:');

// ─── Dashboard table headers ───
reg('#', '#');
reg('Shipment', 'الشحنة');
reg('Date', 'التاريخ');
reg('Invoice', 'الفاتورة');
reg('No shipments yet.', 'لا توجد شحنات بعد.');
reg('No orders yet.', 'لا توجد طلبات بعد.');
reg('Expected Wt', 'الوزن المتوقع');
reg('Actual Wt', 'الوزن الفعلي');
reg('Ref', 'المرجع');
reg('Exp. Weight', 'الوزن المتوقع');
reg('Act. Weight', 'الوزن الفعلي');
reg('Received', 'مستلم');
reg('Serial', 'الرقم التسلسلي');
reg('State', 'الحالة');
reg('Job', 'الوظيفة');
reg('min', 'د');

// ─── Transferred Shipments ───
reg('Transferred Shipments', 'الشحنات المحولة');
reg('Receiving Zone', 'منطقة الاستقبال');
reg('Scan the QR code on the shipment to begin processing.',
    'امسح رمز QR على الشحنة لبدء المعالجة.');
reg('Scan the QR code on the shipment or upload an image to start processing.',
    'امسح رمز QR على الشحنة أو ارفع صورة لبدء المعالجة.');
reg('Point your camera at the QR code on the shipment label.',
    'وجّه الكاميرا نحو رمز QR على ملصق الشحنة.');
reg('Start Camera', 'تشغيل الكاميرا');
reg('Or upload an image', 'أو ارفع صورة');
reg('My Warehouse Dashboard', 'لوحة تحكم مستودعي');
reg('Avg Time', 'متوسط الوقت');
reg('Shipments you have received, accepted, or transferred.',
    'الشحنات التي استلمتها أو قبلتها أو حوّلتها أنت.');
reg('Select a receiving zone…', 'اختر منطقة استقبال…');
reg('Select a receiving zone of your warehouse before accepting the shipment.',
    'اختر منطقة استقبال من مستودعك قبل قبول الشحنة.');
reg('Select a receiving zone of your warehouse before approving the transferred shipment.',
    'اختر منطقة استقبال من مستودعك قبل اعتماد الشحنة المحولة.');
reg('Archive', 'الأرشيف');
reg('Archived Shipments', 'الشحنات المؤرشفة');
reg('Archived Orders', 'الطلبات المؤرشفة');
reg('All shipments that have been transferred between warehouses — track movement and weight reconciliation.', 'جميع الشحنات التي تم تحويلها بين المستودعات — تتبع الحركة ومطابقة الأوزان.');
reg('Loading transferred shipments…', 'جارٍ تحميل الشحنات المحولة…');
reg('No transferred shipments found.', 'لم يتم العثور على شحنات محولة.');

// ─── Zones ───
reg('Warehouse Zones', 'مناطق المستودع');
reg('Manage all zones across warehouses — receiving, sorting, storage, and output areas. Click a zone to view details.', 'إدارة جميع المناطق عبر المستودعات — مناطق الاستقبال والفرز والتخزين والإخراج. انقر على منطقة لعرض التفاصيل.');
reg('Loading zones…', 'جارٍ تحميل المناطق…');
reg('No zones found.', 'لم يتم العثور على مناطق.');
reg('Zone Name', 'اسم المنطقة');
reg('Zone Type', 'نوع المنطقة');
reg('Assigned Warehouse', 'المستودع المخصص');
reg('Zone ID', 'معرف المنطقة');
reg('Zone Purpose', 'الغرض من المنطقة');
reg('Zone Information', 'معلومات المنطقة');
reg('Zone details — type, assigned warehouse, and current configuration.', 'تفاصيل المنطقة — النوع والمستودع المخصص والإعداد الحالي.');
reg('Create New Zone', 'إنشاء منطقة جديدة');
reg('Define a new zone — choose its type (receiving, sorting, storage, or output) and assign it to a warehouse.', 'تعريف منطقة جديدة — اختر نوعها (استقبال أو فرز أو تخزين أو إخراج) وخصصها لمستودع.');
reg('Save Zone', 'حفظ المنطقة');
reg('— Select Warehouse —', '— اختر المستودع —');
reg('This is a', 'هذه');
reg('This is an', 'هذه');
reg('Receiving Zone', 'منطقة استقبال');
reg('Sorting Zone', 'منطقة فرز');
reg('Storage Zone', 'منطقة تخزين');
reg('Output Zone', 'منطقة إخراج');
reg('handles incoming materials and goods from suppliers or external sources. Items are checked, logged, and prepared for further processing.', 'تستقبل المواد والبضائع الواردة من الموردين أو المصادر الخارجية. يتم فحص العناصر وتسجيلها وإعدادها للمعالجة.');
reg('materials are separated and categorized by type, condition, or destination. Sorted items are then routed to the appropriate storage or output zones.', 'يتم فصل المواد وتصنيفها حسب النوع والحالة والوجهة. توجّه العناصر المفرزة إلى مناطق التخزين أو الإخراج المناسبة.');
reg('processed and sorted materials are held here until they are ready for dispatch or further use. Inventory is tracked and managed in this area.', 'تُحفظ هنا المواد المعالجة والمفرزة حتى تصبح جاهزة للشحن أو الاستخدام. يتم تتبع المخزون وإدارته في هذه المنطقة.');
reg('final materials ready for shipping or distribution are staged here. Orders are fulfilled and dispatched from this zone.', 'تُجهز هنا المواد النهائية الجاهزة للشحن أو التوزيع. تُنفَّذ الطلبات وتُشحن من هذه المنطقة.');

// ─── Attendance ───
reg('Attendance', 'الحضور');
reg('Warehouse Staff Attendance', 'حضور موظفي المستودع');
reg('Attendance records for', 'سجلات الحضور لـ');
reg('All attendance records — enter a date or leave empty to show all.', 'جميع سجلات الحضور — أدخل تاريخاً أو اتركه فارغاً لعرض الكل.');
reg('Date:', 'التاريخ:');
reg('Warehouse:', 'المستودع:');
reg('Shift', 'ورديتي');
reg('Loading attendance records…', 'جارٍ تحميل سجلات الحضور…');
reg('No attendance records found.', 'لم يتم العثور على سجلات حضور.');


// ─── Accepted/Rejected applicants ───
reg('All applicants who passed the hiring process — view their profile and final stage details.', 'جميع المتقدمين الذين اجتازوا عملية التوظيف — عرض ملفاتهم وتفاصيل المرحلة النهائية.');
reg('All applicants who were rejected, along with their final stage and reason.', 'جميع المتقدمين المرفوضين مع مرحلتهم النهائية والسبب.');
reg('Deleted Account', 'حساب محذوف');
reg('No deleted-account applications found.', 'لم يتم العثور على طلبات لحسابات محذوفة.');

// ─── General UI ───
reg('Recycle WMS', 'نظام إدارة التدوير');
reg('v19.0', 'الإصدار 19.0');
reg('WMS', 'نظام المستودع');
reg('live system overview', 'إليك نظرة عامة على النظام.');
reg('Your account details, role, and system access information.', 'تفاصيل حسابك ودورك ومعلومات صلاحيات الوصول.');
reg('Loading categories…', 'جارٍ تحميل التصنيفات…');
reg('No categories found.', 'لم يتم العثور على تصنيفات.');
reg('View all products — search by name to quickly find what you need.', 'عرض جميع المنتجات — ابحث بالاسم للعثور على ما تحتاجه بسرعة.');
reg('Loading products…', 'جارٍ تحميل المنتجات…');
reg('No products found.', 'لم يتم العثور على منتجات.');
reg('Customize your dashboard appearance and system preferences.', 'خصص مظهر لوحة التحكم وتفضيلات النظام.');
reg('Recent activity across shipments and orders in the system.', 'النشاط الأخير في الشحنات والطلبات عبر النظام.');

// ─── Missing keys (employees, shifts, applicants) ───
reg('All applicants who were not selected — review the rejection stage and status details.', 'جميع المتقدمين غير المختارين — مراجعة مرحلة الرفض وتفاصيل الحالة.');
reg('Applicant Information', 'معلومات المتقدم');
reg('Applications of employees whose accounts were permanently deleted. Read-only archive for administrators.', 'طلبات الموظفين الذين حُذفت حساباتهم. أرشيف للقراءة فقط.');
reg('Back to Menu', 'العودة إلى القائمة');
reg('Browse, edit, or deactivate existing work shifts. See how many employees use each shift.', 'تصفح ورديات العمل وتعديلها أو إلغاء تفعيلها.');
reg('Define a new work shift with start time, end time, and tolerance period.', 'حدد وردية عمل جديدة بوقت البداية والنهاية وفترة التسامح.');
reg('Deleted', 'محذوف');
reg('Deleted Account Applications', 'طلبات الحسابات المحذوفة');
reg('Deleted Employee', 'موظف محذوف');
reg('Deleted On', 'تاريخ الحذف');
reg('Deleting removes the account, job applications and warehouse role — shipment records are kept.', 'يؤدي الحذف إلى إزالة الحساب وطلبات التوظيف ودور المستودع. يتم الاحتفاظ بسجلات الشحنات.');
reg('Employee details — edit information and generate PDF reports.', 'تفاصيل الموظف — تعديل المعلومات وإنشاء تقارير PDF.');
reg('Grace period allowed before marking an employee as late.', 'فترة التسامح قبل تسجيل الموظف كمتأخر.');
reg('Language', 'اللغة');
reg('Loading attendance data', 'جارٍِ تحميل بيانات الحضور');
reg('Loading deleted account applications…', 'جارٍِ تحميل طلبات الحسابات المحذوفة…');
reg('Loading employee details…', 'جارٍِ تحميل تفاصيل الموظف…');
reg('Manage work shifts and assign them to employees.', 'إدارة ورديات العمل وتعيينها للموظفين.');
reg('New Work Shift', 'وردية عمل جديدة');
reg('No deleted employees found.', 'لم يتم العثور على موظفين محذوفين.');
reg('Not assigned', 'غير مخصص');
reg('PDF Report', 'تقرير PDF');
reg('Rejected At', 'تم الرفض في');
reg('Review candidates by stage — each stage shows its approval status. Accepted at the final stage moves to Accepted.', 'مراجعة المرشحين حسب المرحلة. القبول في المرحلة النهائية ينتقل إلى المقبولين.');
reg('Shift Created!', 'تم إنشاء الوردية!');
reg('Sorting', 'الفرز');
reg('This employee account has been deleted. Information is read-only.', 'تم حذف حساب هذا الموظف. المعلومات للقراءة فقط.');
reg('Total:', 'الإجمالي:');
reg('Warehouse *', 'المستودع *');
reg('Work Shift', 'وردية العمل');
reg('application(s)', 'طلب (طلبات)');
reg('has been saved successfully.', 'تم الحفظ بنجاح.');
reg('to review — click any card to open and process it through the hiring stages.', 'للمراجعة — انقر على أي بطاقة لفتحها ومعالجتها عبر مراحل التوظيف.');

reg('Forklift', 'رافعة شوكية');
reg('Conveyor', 'سير ناقل');
reg('Baler', 'كبّاسة');
reg('Crusher', 'كسّارة');
reg('Scale', 'ميزان');
reg('Vehicle', 'مركبة');

// ── Shift Edit ──
reg('Edit Shift', 'تعديل الوردية');
reg('Update shift name, times, and tolerance settings.', 'تحديث اسم الوردية والأوقات وإعدادات الهامش.');

// ── Stats ──
reg('This Month', 'هذا الشهر');
reg('All Time', 'الإجمالي');

// ─── Odoo Backend Menu translations ───
reg('Recycle Warehouse', 'مستودع التدوير');
reg('Home', 'الرئيسية');
reg('Operations', 'العمليات');
reg('Damaged Materials', 'مواد تلف');
reg('Damaged during sorting', 'تالف أثناء الفرز');
reg('Damaged in inventory', 'تالف ضمن المخزون');
reg('Archived', 'المؤرشفة');
reg('Process Shipments', 'معالجة الشحنات');
reg('Sort Shipments', 'فرز الشحنات');
reg('My Sorted Shipments', 'شحناتي المفرزة');
reg('My Processed Shipments', 'شحناتي المعالجة');
reg('Transferred Shipments', 'الشحنات المحولة');
reg('Process Order', 'معالجة طلب');
reg('My Orders', 'طلباتي');
reg('My Invoices', 'فواتيري');
reg('Orders', 'الطلبات');
reg('Inventory', 'المخزون');
reg('My Reports', 'تقاريري');
reg('Recruitment', 'التوظيف');
reg('Job Applications', 'طلبات التوظيف');
reg('Shifts', 'الورديات');
reg('Manage Shifts', 'إدارة الورديات');
reg('All Shifts', 'جميع الورديات');
reg('Configuration', 'الإعدادات');
reg('Recycle Warehouse Home', 'الصفحة الرئيسية');
reg('Sorting Dashboard', 'لوحة الفرز');
reg('Output Dashboard', 'لوحة الإخراج');
reg('Manager Dashboard', 'لوحة المدير');
reg('Job Applicants', 'المتقدمون للوظائف');

/* Dashboard i18n additions */
reg('Period', 'الفترة');
reg('Today', 'اليوم');
reg('days ago', 'أيام مضت');
reg('Week', 'الأسبوع');
reg('Month', 'الشهر');
reg('today', 'اليوم');
reg('this week', 'هذا الأسبوع');
reg('this month', 'هذا الشهر');
// Added for the per-card "added this period" badge and the warehouse-edit hint.
reg('added', 'أُضيف');
reg('Governorate and address are fixed at creation and cannot be changed here.',
    'المحافظة والعنوان يُحدّدان عند الإنشاء ولا يمكن تغييرهما هنا.');
// Material-suggestion form (dashboard): images instead of a unit.
reg('Images', 'الصور');
reg('image(s) selected', 'صورة/صور محدَّدة');
reg('Most Active', 'الأكثر نشاطاً');
reg('Growth', 'النمو');
reg('Highest count across all categories', 'أعلى عدد بين جميع الفئات');
reg('Overall change vs previous period', 'التغير الإجمالي مقارنة بالفترة السابقة');
reg('No data yet', 'لا توجد بيانات بعد');
reg('Add records to see the donut chart', 'أضف سجلات لرؤية المخطط الدائري');
reg('Add records to see the bar chart', 'أضف سجلات لرؤية المخطط الشريطي');

/* Coverage gap fixes (project-wide translation audit) */
reg('No requests yet.', 'لا توجد طلبات بعد.');
reg('Notes', 'ملاحظات');
reg('Price (SAR)', 'السعر (ريال)');
reg('Statistics Breakdown', 'تفصيل الإحصائيات');
reg('Toggle Theme', 'تبديل المظهر');
reg('View requests you are currently working on or have completed. Mark in-progress requests as done or failed.', 'عرض الطلبات التي تعمل عليها حالياً أو أنجزتها. حدّد الطلبات الجارية كمكتملة أو فاشلة.');
reg("View today's attendance: who is present, who is late, check-in/out times and hours.", 'عرض حضور اليوم: من الحاضر، من المتأخر، أوقات الدخول والخروج وساعات العمل.');
reg('e.g. Forklift 001', 'مثال: رافعة 001');
reg('e.g. SN-12345', 'مثال: SN-12345');
reg('Start and end time cannot be the same.', 'لا يمكن أن يكون وقت البداية والنهاية متطابقين.');

/* Sidebar navigation */
reg('Menu', 'القائمة');
reg('Jobs', 'الوظائف');
reg('Zones', 'المناطق');
reg('Other', 'أخرى');

reg('Add Another', 'إضافة معدة أخرى');
reg('Please select a warehouse.', 'يرجى اختيار مستودع.');
reg('Select a warehouse…', 'اختر مستودعاً…');
reg('Back to Home', 'العودة للرئيسية');

/* Manager Dashboard */
reg('Manager Dashboard', 'لوحة تحكم المدير');
reg('Manager', 'مدير');
reg('Manager WMS', 'نظام إدارة المستودع');
reg('Warehouse Control Center', 'مركز التحكم بالمستودع');
reg('live overview', 'نظرة عامة حية');
reg('live warehouse overview', 'نظرة عامة حية على المستودع');
reg('Name required', 'الاسم مطلوب');
reg('No notifications', 'لا توجد إشعارات');
reg('System alerts and pending requests', 'تنبيهات النظام والطلبات المعلقة');
reg('You\'re all caught up!', 'لقد تابعت كل شيء!');
reg('Account reactivated.', 'تم إعادة تنشيط الحساب.');
reg('Action failed.', 'فشلت العملية.');
reg('Request declined.', 'تم رفض الطلب.');
reg('Customize your dashboard appearance and preferences.', 'تخصيص مظهر لوحة التحكم والتفضيلات.');
reg('Customize your dashboard appearance and preferences', 'تخصيص مظهر لوحة التحكم والتفضيلات');
reg('Sign out of your account.', 'تسجيل الخروج من حسابك.');
reg('Your account details, role and warehouse assignment.', 'تفاصيل حسابك ودورك وتعيين المستودع.');
reg('Employees', 'الموظفين');
reg('Today Shipments', 'شحنات اليوم');
reg('Week Shipments', 'شحنات الأسبوع');
reg('Today Orders', 'طلبات اليوم');
reg('Week Orders', 'طلبات الأسبوع');
reg('Stock Items', 'أصناف المخزون');
reg('Avg Processing (h)', 'متوسط المعالجة (ساعة)');
reg('Completion Rate', 'نسبة الإنجاز');
reg('Shipment Status', 'حالة الشحنات');
reg('Order Status', 'حالة الطلبات');
reg('Daily Activity', 'النشاط اليومي');
reg('Zone Utilization', 'استخدام المناطق');
reg('Quick Actions', 'إجراءات سريعة');
reg('Shipments', 'الشحنات');
reg('Orders', 'الطلبات');
reg('Stock', 'المخزون');
reg('Attendance', 'الحضور');
reg('Pending', 'معلق');
reg('In Reception', 'قيد الاستلام');
reg('Escalated', 'محول للمدير');
reg('Accepted', 'مقبول');
reg('Sorting', 'فرز وتنظيف');
reg('Sorted', 'مفرز');
reg('Processing', 'قيد المعالجة');
reg('Ready', 'جاهز');
reg('Completed', 'مكتمل');
reg('Cancelled', 'ملغي');
reg('Receiving', 'استلام');
reg('Storage', 'تخزين');
reg('Output', 'إخراج');
reg('Account', 'حساب');

/* Manager Dashboard — warehouse-scoped sections */
reg('All', 'الكل');
reg('All Roles', 'كل الأدوار');
reg('My Employees', 'موظفو مستودعي');
reg('Employees assigned to your warehouse. Search, review, edit or deactivate accounts.', 'الموظفون المسندون لمستودعك. ابحث، راجع، عدّل أو عطّل الحسابات.');
reg('Employee details. Only the phone and account status can be edited by a manager.', 'بيانات الموظف. يمكن للمدير تعديل الهاتف وحالة الحساب فقط.');
reg('Create a new employee account in your warehouse. The warehouse is assigned automatically.', 'إنشاء حساب موظف جديد في مستودعك. يتم إسناد المستودع تلقائياً.');
reg('New employees are always created in your own warehouse.', 'يتم إنشاء الموظفين الجدد دائماً في مستودعك.');
reg('Employee updated successfully!', 'تم تحديث بيانات الموظف بنجاح!');
reg('Employee created successfully!', 'تم إنشاء الموظف بنجاح!');
reg('Update failed. Please try again.', 'فشل التحديث. حاول مرة أخرى.');
reg('Creation failed. Please check the fields.', 'فشل الإنشاء. يرجى التحقق من الحقول.');
reg('This login is already in use.', 'اسم الدخول مستخدم بالفعل.');
reg('Login / email is required.', 'اسم الدخول / البريد مطلوب.');
reg('Disable', 'تعطيل');
reg('Enable', 'تفعيل');
reg('Joined', 'تاريخ الانضمام');
reg('Loading employees…', 'جارٍ تحميل الموظفين…');
reg('Search name or email…', 'ابحث بالاسم أو البريد…');
reg('Create Employee', 'إنشاء موظف');
reg('All incoming shipments of your warehouse. Click a row for full details.', 'جميع الشحنات الواردة لمستودعك. اضغط على أي صف لعرض التفاصيل الكاملة.');
reg('All customer orders of your warehouse. Click a row for full details.', 'جميع طلبات عملاء مستودعك. اضغط على أي صف لعرض التفاصيل الكاملة.');
reg('Shipment details — contents, weights, timing and processing employees.', 'تفاصيل الشحنة — المحتويات والأوزان والتوقيت وموظفو المعالجة.');
reg('Order details — customer, lines, totals and processing employee.', 'تفاصيل الطلب — العميل والبنود والإجماليات وموظف المعالجة.');
reg('Search shipment or driver…', 'ابحث بالشحنة أو السائق…');
reg('Search order, customer or invoice…', 'ابحث بالطلب أو العميل أو الفاتورة…');
reg('Contents', 'المحتويات');
reg('No lines.', 'لا توجد بنود.');
reg('Sorted By', 'تم الفرز بواسطة');
reg('Weight (kg)', 'الوزن (كجم)');
reg('Current inventory of your warehouse by product.', 'المخزون الحالي لمستودعك حسب المنتج.');
reg('Total Quantity', 'الكمية الإجمالية');
reg('No stock found.', 'لا يوجد مخزون.');
reg('Empty', 'فارغ');
reg('Normal', 'طبيعي');
reg('kg', 'كجم');
reg('Daily attendance of your warehouse employees: check-in, check-out and delays.', 'الحضور اليومي لموظفي مستودعك: الدخول والخروج والتأخير.');
reg('Loading attendance…', 'جارٍ تحميل الحضور…');
reg('No attendance records for this date.', 'لا توجد سجلات حضور لهذا التاريخ.');
reg('No Record', 'بدون تسجيل');
reg('Late (min)', 'التأخير (دقيقة)');
reg('Hours', 'الساعات');
reg('Shifts available for your warehouse employees.', 'الورديات المتاحة لموظفي مستودعك.');
reg('No shifts found.', 'لا توجد ورديات.');
reg('Reject', 'رفض');
reg('Saving.', 'جارٍ الحفظ…');

reg('Your assigned warehouse — details and live counters.', 'مستودعك المسند — التفاصيل والعدادات الحية.');
reg('No warehouse assigned', 'لا يوجد مستودع مسند');
reg('Ask the administrator to assign you to a warehouse.', 'اطلب من المسؤول إسنادك إلى مستودع.');
reg('Code', 'الرمز');
reg('Governorate', 'المحافظة');
reg('Manager', 'المدير');
reg('Job Applications', 'طلبات التوظيف');
reg('Applicants accepted by the administrator and assigned to your warehouse. You can only assign their role and shift.', 'المتقدمون الذين قبلهم المسؤول وأسندهم إلى مستودعك. يمكنك فقط إسناد الدور والوردية لهم.');
reg('The application itself is read-only. You can only assign the role and work shift.', 'طلب التوظيف للقراءة فقط ولا يمكن تعديله. يمكنك فقط إسناد الدور ووردية العمل.');
reg('Assign Role', 'إسناد الدور');
reg('Assign Role & Shift', 'إسناد الدور والوردية');
reg('Role and shift assigned successfully!', 'تم إسناد الدور والوردية بنجاح!');
reg('Assignment failed. Make sure the employee account exists.', 'فشل الإسناد. تأكد من وجود حساب للموظف.');
reg('Please select a role.', 'يرجى اختيار الدور.');
reg('Current Role', 'الدور الحالي');
reg('Not assigned', 'غير مسند');
reg('Applied On', 'تاريخ التقديم');
reg('Account', 'الحساب');
reg('Created', 'مُنشأ');
reg('No shift', 'بدون وردية');
reg('No accepted applications for your warehouse yet.', 'لا توجد طلبات مقبولة لمستودعك بعد.');
reg('Full report details as submitted by the sorting employee.', 'تفاصيل التقرير كاملة كما قدمها موظف الفرز.');
reg('Report', 'التقرير');
reg('Problem Description', 'وصف المشكلة');
reg('New', 'جديد');
reg('Transferred Shipments', 'الشحنات المحوّلة');
reg('Shipments transferred by reception because the actual weight differs from the expected weight by more than 5%. Review each one and approve it to send it to sorting.', 'الشحنات المحوّلة من موظف الاستقبال لأن الوزن الفعلي يختلف عن الوزن المتوقع بأكثر من 5%. راجع كل شحنة ووافق عليها لإرسالها إلى الفرز.');
reg('Approve & Send to Sorting', 'موافقة وإرسال للفرز');
reg('Shipment approved and sent to sorting.', 'تمت الموافقة على الشحنة وإرسالها إلى الفرز.');
reg('No transferred shipments. Everything is on track!', 'لا توجد شحنات محوّلة. كل شيء على ما يرام!');
reg('Difference', 'الفرق');
reg('Transferred By', 'حُوّلت بواسطة');
reg('Export PDF', 'تصدير PDF');
reg('PDF', 'PDF');

/* Archive (manager + admin) */
reg('Archive', 'أرشفة');
reg('Restore', 'استعادة');
reg('Archived Shipments', 'الشحنات المؤرشفة');
reg('Archived Orders', 'الطلبات المؤرشفة');
reg('Shipments you archived. Hidden from employees — only you and the administrator can see them.', 'الشحنات التي أرشفتها. مخفية عن الموظفين — تظهر لك وللمسؤول فقط.');
reg('Orders you archived. Hidden from employees — only you and the administrator can see them.', 'الطلبات التي أرشفتها. مخفية عن الموظفين — تظهر لك وللمسؤول فقط.');
reg('No archived shipments.', 'لا توجد شحنات مؤرشفة.');
reg('No archived orders.', 'لا توجد طلبات مؤرشفة.');
reg('Shipment archived.', 'تمت أرشفة الشحنة.');
reg('Order archived.', 'تمت أرشفة الطلب.');
reg('Shipment restored.', 'تمت استعادة الشحنة.');
reg('Order restored.', 'تمت استعادة الطلب.');

/* Input Employee Dashboard */
reg('Reception', 'الاستقبال');
reg('View Shipments', 'عرض الشحنات');
reg('Process New Shipment', 'معالجة شحنة جديدة');
reg('Processed Shipments', 'الشحنات المعالجة');
reg('Acceptance Rate', 'معدل القبول');
reg('Direct acceptance', 'القبول المباشر');
reg('Avg Processing Time', 'متوسط وقت المعالجة');
reg('Per shipment', 'لكل شحنة');
reg('hrs', 'ساعة');
reg('Working Hours', 'ساعات العمل');
reg('Processed', 'تمت معالجتها');
reg('All shipments you have received — weights, differences and current status.', 'جميع الشحنات التي استلمتها — الأوزان والفروقات والحالة الحالية.');
reg("You haven't processed any shipments yet.", 'لم تقم بمعالجة أي شحنات بعد.');
reg('Enter the shipment ID, weigh it, then accept it or transfer it to the manager.', 'أدخل معرف الشحنة، قم بوزنها، ثم اقبلها أو حوّلها إلى المدير.');
reg('Shipment ID', 'معرف الشحنة');
reg('e.g. SHIP001', 'مثال: SHIP001');
reg('Type the shipment ID printed on the delivery note, or scan its barcode with a USB scanner into this field.', 'اكتب معرف الشحنة المطبوع على إشعار التسليم، أو امسح الباركود بقارئ USB داخل هذا الحقل.');
reg('Search', 'بحث');
reg('Enter the shipment ID first.', 'أدخل معرف الشحنة أولاً.');
reg('Shipment not found. It may not exist, belong to another warehouse, or be reserved by a colleague.', 'الشحنة غير موجودة. قد لا تكون موجودة، أو تتبع مستودعاً آخر، أو محجوزة من زميل.');
reg('This shipment is currently reserved by %s. Please wait or ask them to release it.', 'هذه الشحنة محجوزة حالياً من %s. يرجى الانتظار أو طلب منها الإلغاء.');
reg('This shipment has already been processed and cannot be received again.', 'تمت معالجة هذه الشحنة مسبقاً ولا يمكن استلامها مرة أخرى.');
reg('Shipment reserved successfully by %s.', 'تم حجز الشحنة بنجاح من قِبل %s.');
reg('Welcome back! Shipment %s is still reserved for you.', 'مرحباً بعودتك! الشحنة %s لا تزال محجوزة لك.');
reg('another employee', 'موظف آخر');
reg('Loading failed. Please try again.', 'فشل التحميل. حاول مرة أخرى.');
reg('Failed to load shipments. Please try again.', 'فشل تحميل الشحنات. حاول مرة أخرى.');
reg('Failed to load shipment for processing.', 'فشل تحميل الشحنة للمعالجة.');
reg('This shipment was processed by another employee.', 'هذه الشحنة تمت معالجتها من موظف آخر.');
reg('Shipment released. Scan the QR code again to reserve it.', 'تم إلغاء حجز الشحنة. امسح رمز QR مرة أخرى لحجزها.');
reg('Actual Weight (kg)', 'الوزن الفعلي (كجم)');
reg('Expected weight:', 'الوزن المتوقع:');
reg('Variance', 'نسبة التباين');
reg('Acceptable — you can accept directly.', 'مقبول — يمكنك القبول مباشرة.');
reg('Between 5% and 10% — acceptance requires confirmation.', 'بين 5% و10% — القبول يتطلب تأكيداً.');
reg('More than 10% — must be transferred to the manager.', 'أكثر من 10% — يجب تحويلها إلى المدير.');
reg('Do you want to accept this shipment?', 'هل تريد قبول هذه الشحنة؟');
reg('Warning: the variance is between 5% and 10%. Are you sure you want to accept this shipment?', 'تحذير: نسبة التباين بين 5% و10%. هل أنت متأكد من قبول هذه الشحنة؟');
reg('Yes, Accept', 'نعم، قبول');
reg('Accept Shipment', 'قبول الشحنة');
reg('Accept with Warning', 'قبول مع تحذير');
reg('Transfer to Manager', 'تحويل إلى المدير');
reg('The variance exceeds 10%. This shipment cannot be accepted and must be transferred to the warehouse manager.', 'نسبة التباين تتجاوز 10%. لا يمكن قبول هذه الشحنة ويجب تحويلها إلى مدير المستودع.');
reg('Transfer Reason', 'سبب التحويل');
reg('Transfer reason', 'سبب التحويل');
reg('Release Reservation', 'إلغاء الحجز');
reg('Shipment accepted successfully!', 'تم قبول الشحنة بنجاح!');
reg('Shipment transferred to the manager!', 'تم تحويل الشحنة إلى المدير!');
reg('Moved to the receiving zone and sent to sorting.', 'نُقلت إلى منطقة الاستقبال وأُرسلت إلى الفرز.');
reg('The warehouse manager will review it in the Transferred Shipments screen.', 'سيراجعها مدير المستودع في شاشة الشحنات المحوّلة.');
reg('Process Another', 'معالجة شحنة أخرى');
reg('Priority', 'الأولوية');

/* Employee create: password + national ID */
reg('Password', 'كلمة المرور');
reg('Password is required (at least 6 characters).', 'كلمة المرور مطلوبة (6 أحرف على الأقل).');
reg('At least 6 characters. The employee uses it to log in.', '6 أحرف على الأقل. يستخدمها الموظف لتسجيل الدخول.');
reg('This national ID is already registered for another employee.', 'هذا الرقم الوطني مسجل بالفعل لموظف آخر.');
reg('A password setup link will be sent to the employee email after creation.', 'سيتم إرسال رابط تعيين كلمة المرور إلى بريد الموظف بعد الإنشاء.');
reg('Employee created successfully! A password setup email has been sent.', 'تم إنشاء الموظف بنجاح! تم إرسال بريد إعداد كلمة المرور.');
reg('e.g. Ahmad Mohammed', 'مثال: أحمد محمد');
reg('e.g. ahmad@dawrha.com', 'مثال: ahmad@dawrha.com');
reg('e.g. 0551234567', 'مثال: 0551234567');
reg('e.g. 1234567890', 'مثال: 1234567890');
reg('Email is required for login and password reset.', 'البريد الإلكتروني مطلوب لتسجيل الدخول وإعادة تعيين كلمة المرور.');
reg('The national ID %s already belongs to %s.', 'الرقم الوطني %s يعود بالفعل إلى %s.');
reg('The email %s is already used by %s.', 'البريد الإلكتروني %s مستخدم بالفعل من قبل %s.');
reg('An account with this email already exists.', 'يوجد حساب بهذا البريد الإلكتروني بالفعل.');
reg('Email cannot be changed.', 'لا يمكن تغيير البريد الإلكتروني.');
reg('Used as login and password reset.', 'يُستخدم كبيانات دخول ولمعاينة كلمة المرور.');
reg('Employee Created!', 'تم إنشاء الموظف!');
reg('A password setup link has been sent to the employee email.', 'تم إرسال رابط تعيين كلمة المرور إلى بريد الموظف.');
reg('View Employees', 'عرض الموظفين');
reg('Add Another', 'إضافة موظف آخر');

/* Zone filtering */
reg('All Zones', 'كل المناطق');
reg('Zone', 'المنطقة');

/* Admin archive views */
reg('All archived shipments across warehouses, with the employee who archived each one.', 'جميع الشحنات المؤرشفة في كل المستودعات، مع الموظف الذي أرشف كل واحدة.');
reg('All archived orders across warehouses, with the employee who archived each one.', 'جميع الطلبات المؤرشفة في كل المستودعات، مع الموظف الذي أرشف كل واحد.');
reg('Archived By', 'أُرشفت بواسطة');

/* Admin: add product */
reg('Add Product', 'إضافة منتج');
reg('Create a new recyclable product with its category and the price for each buyer tier.', 'إنشاء منتج جديد قابل لإعادة التدوير مع تصنيفه وسعر كل فئة من المشترين.');
reg('Product Name', 'اسم المنتج');
reg('Category', 'التصنيف');
reg('Base Price', 'السعر الأساسي');
reg('Factory Price', 'سعر المصانع');
reg('Free Facility Price', 'سعر الجهات الحرة');
reg('Weight per Unit (kg)', 'الوزن لكل وحدة (كجم)');
reg('Save Product', 'حفظ المنتج');
reg('Product created successfully!', 'تم إنشاء المنتج بنجاح!');
reg('Product name is required.', 'اسم المنتج مطلوب.');
reg('Please select a category.', 'يرجى اختيار التصنيف.');
reg('Select a category…', 'اختر تصنيفاً…');

/* Pre-existing gaps caught by the audit */
reg('Done.', 'تم.');
reg('Failed to ban user:', 'فشل حظر المستخدم:');
reg('Failed to unban user:', 'فشل إلغاء حظر المستخدم:');
reg('Failed to delete account:', 'فشل حذف الحساب:');
reg('Failed to restore employee:', 'فشلت استعادة الموظف:');

/* Barcode image scanning for receiving employees */
reg('OR', 'أو');
reg('Tap to take a photo or choose an image', 'اضغط لالتقاط صورة أو اختيار صورة');
reg('The barcode on the shipment label will be decoded automatically.', 'سيتم فك تشفير الباركود على ملصق الشحنة تلقائياً.');
reg('Scanning barcode...', 'جاري مسح الباركود...');
reg('No image received. Please try again.', 'لم يتم استلام صورة. يرجى المحاولة مرة أخرى.');
reg('Barcode library not installed on the server. Contact the administrator.', 'مكتبة الباركود غير مثبتة على الخادم. تواصل مع المسؤول.');
reg('Image library not installed on the server. Contact the administrator.', 'مكتبة الصور غير مثبتة على الخادم. تواصل مع المسؤول.');
reg('Invalid image data. Please take a clearer photo.', 'بيانات الصورة غير صالحة. يرجى التقاط صورة أوضح.');
reg('Cannot read the file as an image. Upload a valid PNG or JPG.', 'لا يمكن قراءة الملف كصورة. ارفع ملف PNG أو JPG صالح.');
reg('No barcode found in the image. Try a clearer, well-lit photo taken straight-on.', 'لم يتم العثور على باركود في الصورة. جرّب صورة أوضح ومضاءة جيداً ومأخوذة من الأمام.');
reg('Network error. Please check your connection and try again.', 'خطأ في الشبكة. تحقق من اتصالك وحاول مرة أخرى.');
reg('Barcode scan failed. Please try again.', 'فشل مسح الباركود. يرجى المحاولة مرة أخرى.');

/* QR Scan Cards (Receive Shipment) */
reg('Upload Image', 'رفع صورة');
reg('Choose a photo with a QR code from your gallery', 'اختر صورة تحتوي على رمز QR من معرض الصور');
reg('Scan QR Code', 'مسح رمز QR');
reg('Open camera and scan the shipment label directly', 'افتح الكاميرا وامسح ملصق الشحنة مباشرة');
reg('Scanning...', 'جاري المسح...');
reg('Switch Camera', 'تبديل الكاميرا');
reg('Stop', 'إيقاف');

/* Sorting Employee Dashboard */
reg('My Shift', 'ورديتي');
reg('Your assigned work shift and its timing.', 'وردية العمل المسندة إليك وتوقيتها.');
reg('No shift assigned', 'لا توجد وردية مسندة');
reg('Ask your warehouse manager to assign you a work shift.', 'اطلب من مدير مستودعك إسناد وردية عمل لك.');
reg('Shipments I Sorted', 'الشحنات التي فرزتها');
reg('Waiting for Sorting', 'بانتظار الفرز');
reg('In your warehouse', 'في مستودعك');
reg('Work Hours', 'ساعات العمل');
reg('Damaged Requests', 'طلبات التالف');
reg('Total', 'الإجمالي');
reg('Process Sorting', 'معالجة عمليات الفرز والتخزين');
reg('Sorting & Storage', 'فرز وتخزين');
reg('In Sorting', 'قيد الفرز');
reg('Poor', 'رديئة');
reg('Actual Weight (kg)', 'الوزن الفعلي (كغ)');
reg('Please select a storage zone.', 'الرجاء اختيار منطقة تخزين.');
reg('Start Storage', 'بدء التخزين');
reg('End Storage', 'إنهاء التخزين');
reg('First choose the storage zone where the sorted materials will be placed.', 'اختر أولاً منطقة التخزين التي ستوضع فيها المواد المفروزة.');
reg('The quantities you entered are more than the actual weight of the shipment. Please review the quantities.', 'الكميات التي أدخلتها أكبر من الوزن الفعلي للشحنة. يرجى مراجعة الكميات.');
reg('Quantity Shortage Reason', 'سبب نقص الكمية');
reg('There is a difference between the entered quantities and the actual weight. Please describe the reason.', 'هناك فرق بين الكميات المدخلة والوزن الفعلي. يرجى وصف السبب.');
reg('Confirm', 'تأكيد');
reg('Make sure you entered the quantities correctly. Do you want to transfer this shipment to the warehouse manager?', 'تأكد من أنك أدخلت الكميات بشكل صحيح. هل تريد تحويل هذه الشحنة إلى مدير المستودع؟');
reg('Yes, transfer to manager', 'نعم، تحويل إلى المدير');
reg('No', 'لا');
reg('Shipment transferred to the warehouse manager.', 'تم تحويل الشحنة إلى مدير المستودع.');
reg('This shipment was transferred to the warehouse manager and is awaiting review.', 'تم تحويل هذه الشحنة إلى مدير المستودع وهي بانتظار المراجعة.');
reg('Sorting Escalations', 'تحويلات الفرز');
reg('Shipments transferred by sorting employees due to a quantity shortfall.', 'شحنات تم تحويلها من موظفي الفرز بسبب نقص في الكميات.');
reg('Transferred By', 'تم التحويل بواسطة');
reg('Quantity Shortfall (%)', 'نسبة نقص الكمية (%)');
reg('Accepted shipments waiting to be sorted, in priority order.', 'الشحنات المقبولة بانتظار الفرز، مرتبة حسب الأولوية.');
reg('Resolve', 'إنهاء المراجعة');
reg('No escalated shipments.', 'لا توجد شحنات محولة.');
reg('High', 'عالية');
reg('Medium', 'متوسطة');
reg('Low', 'قليلة');
reg('Shipments you are sorting or have already sorted, with damage requests.', 'الشحنات التي تفرزها أو فرزتها، مع طلبات التالف.');
reg('Stored (Sorted)', 'مخزنة (مفروزة)');
reg('Sorted At', 'تاريخ الفرز');
reg('Damaged (%)', 'نسبة التالف (%)');
reg('Damage Approval', 'موافقة التالف');
reg('Continue', 'متابعة');
reg('Sorted contents by product and condition.', 'المحتويات المفروزة حسب المنتج والحالة.');
reg('Received shipments waiting for sorting, ordered by priority. Only the highest priority shipment can be started.', 'الشحنات المستلمة بانتظار الفرز، مرتبة حسب الأولوية. يمكن بدء الشحنة ذات الأولوية الأعلى فقط.');
reg('Start Sorting', 'بدء الفرز');
reg('Waiting for higher priority', 'بانتظار الأولوية الأعلى');
reg('No shipments waiting for sorting.', 'لا توجد شحنات بانتظار الفرز.');
reg('Sort Shipment', 'فرز شحنة');
reg('Pick the sorting zone, enter the materials with their condition, then move the shipment to storage.', 'اختر منطقة الفرز، أدخل المواد مع حالتها، ثم انقل الشحنة إلى التخزين.');
reg('No shipment selected', 'لم يتم اختيار شحنة');
reg('Shipment moved to storage!', 'تم نقل الشحنة إلى التخزين!');
reg('Usable quantities were added to the warehouse stock.', 'تمت إضافة الكميات الصالحة إلى مخزون المستودع.');
reg('Sorting Zone', 'منطقة الفرز');
reg('Storage Zone', 'منطقة التخزين');
reg('Select a sorting zone…', 'اختر منطقة فرز…');
reg('Select a storage zone…', 'اختر منطقة تخزين…');
reg('The shipment moves from the receiving zone to this sorting zone. After that it can no longer be released.', 'تنتقل الشحنة من منطقة الاستقبال إلى منطقة الفرز هذه. بعد ذلك لا يمكن إلغاء حجزها.');
reg('Move to Sorting Zone', 'نقل إلى منطقة الفرز');
reg('Please select a sorting zone.', 'يرجى اختيار منطقة الفرز.');
reg('Please select a storage zone.', 'يرجى اختيار منطقة التخزين.');
reg('Materials', 'المواد');
reg('Select a product…', 'اختر منتجاً…');
reg('Please select a product.', 'يرجى اختيار المنتج.');
reg('Enter a valid quantity.', 'أدخل كمية صحيحة.');
reg('Condition', 'الحالة');
reg('Closed Warehouses', 'المستودعات المغلقة');
reg('Open Warehouses', 'المستودعات المفتوحة');
reg('Sites that have stopped taking new work. They keep their stock and history, and can be re-opened.',
    'مواقع توقفت عن استقبال عمل جديد. تحتفظ بمخزونها وسجلّها، ويمكن إعادة فتحها.');
reg('Re-open Warehouse', 'إعادة فتح المستودع');
reg('Re-open this warehouse? It will start receiving new shipments and orders again.',
    'إعادة فتح هذا المستودع؟ سيعود لاستقبال الشحنات والطلبات من جديد.');
reg('Warehouse re-opened.', 'تمت إعادة فتح المستودع.');
reg('No closed warehouses.', 'لا توجد مستودعات مغلقة.');
reg('No warehouse matches this search.', 'لا يوجد مستودع يطابق هذا البحث.');
reg('Search by warehouse name…', 'ابحث باسم المستودع…');
reg('Add Line', 'إضافة بند');
reg('Undo Last Line', 'تراجع عن آخر بند');
// ── Damage by shipment (admin) ──
reg('Damage by Shipment', 'التلف حسب الشحنة');
reg('Material written off during sorting, per delivery — with what was lost, who reported it, and what the manager decided.',
    'المواد التي تم إتلافها أثناء الفرز، لكل شحنة — مع ما فُقد ومن أبلغ عنه وما قرره المدير.');
reg('Search by shipment, warehouse, material…', 'ابحث برقم الشحنة أو المستودع أو المادة…');
reg('Loading damage records…', 'جارٍ تحميل سجلات التلف…');
reg('No damage recorded for these filters.', 'لا توجد سجلات تلف ضمن هذه الفلاتر.');
reg('Decision', 'القرار');
reg('Damaged At', 'تاريخ التلف');
reg('Recorded By', 'سجّله');
reg('Awaiting manager', 'بانتظار المدير');
reg('Written off', 'تم الإتلاف');
reg('Refused — stored instead', 'مرفوض — تم تخزينها');
reg('No request', 'لا يوجد طلب');
reg('From', 'من');
reg('To', 'إلى');
// ── The per-unit summary the sorter confirms against ──
reg('Before you confirm', 'قبل التأكيد');
reg('Unit', 'الوحدة');
reg('Lines', 'عدد البنود');
reg('To storage', 'إلى التخزين');
reg('Total entered', 'إجمالي المُدخل');
reg('No unit', 'بلا وحدة');
reg('The damaged quantity stays in the sorting zone until the warehouse manager decides.',
    'الكمية التالفة تبقى في منطقة الفرز حتى يقرر مدير المستودع.');
// ── Damage: ANY quantity waits for the manager, however small ──
reg('Any damaged quantity needs manager approval before storage, however small.',
    'أي كمية تالفة تحتاج موافقة المدير قبل التخزين مهما كانت قليلة.');
reg('Nothing marked damaged — you can move it to storage directly.',
    'لا يوجد ما هو موسوم بالتلف — يمكنك نقلها إلى التخزين مباشرة.');
reg('Excellent', 'ممتازة');
reg('Good', 'جيدة');
reg('Damaged', 'تالفة');
reg('Filter', 'تصفية');
// ── Stock by condition + per-condition order deduction ──
reg('In Stock', 'في المخزون');
reg('Some materials do not have enough stock in the requested condition. The order cannot be completed until stock of the exact condition is available.',
    'بعض المواد لا يتوفر منها مخزون كافٍ بالحالة المطلوبة. لا يمكن إتمام الطلبية حتى يتوفر مخزون بنفس الحالة تماماً.');
reg('Deduction is per condition: each line only consumes stock matching its own condition.',
    'الخصم يتم بحسب الحالة: كل بند يستهلك فقط المخزون المطابق لحالته.');
reg('Insufficient stock for one or more materials in the requested condition.',
    'لا تتوفر كمية كافية بالمخزون لمادة واحدة أو أكثر بالحالة المطلوبة.');
reg('Total damaged of the shipment', 'إجمالي التالف من الشحنة');
reg('Damage Reason', 'سبب التالف');
reg('Request Manager Approval', 'طلب موافقة المدير');
reg('Approval request sent. Waiting for the warehouse manager…', 'تم إرسال طلب الموافقة. بانتظار مدير المستودع…');
reg('Approval request sent to the warehouse manager.', 'تم إرسال طلب الموافقة إلى مدير المستودع.');
reg('Accept & Move to Storage', 'قبول ونقل إلى التخزين');
reg('Add at least one product line first.', 'أضف بنداً واحداً على الأقل أولاً.');
reg('Rejection reason', 'سبب الرفض');
reg('Report a Problem', 'الإبلاغ عن مشكلة');
reg('Current state:', 'الحالة الحالية:');
reg('Describe the problem in detail.', 'صف المشكلة بالتفصيل.');
reg('Send Report', 'إرسال التقرير');
reg('Report sent to the warehouse manager.', 'تم إرسال التقرير إلى مدير المستودع.');
reg('My Reports', 'تقاريري');

/* Manager: damaged sorting requests + zones */
reg('Damaged Sorting Requests', 'طلبات الفرز المتضررة');
reg('Sorting operations with more than 40% damaged materials. Approve to let the employee move the shipment to storage, or reject with a reason.', 'عمليات فرز فيها أكثر من 40% مواد تالفة. وافق ليتمكن الموظف من نقل الشحنة للتخزين، أو ارفض مع ذكر السبب.');
reg('Search shipment or employee…', 'ابحث بالشحنة أو الموظف…');
reg('Employee', 'الموظف');
reg('Reason', 'السبب');
reg('Pending Approval', 'بانتظار الموافقة');
reg('Move to Storage', 'نقل إلى التخزين');
reg('Confirm Rejection', 'تأكيد الرفض');
reg('Rejection reason…', 'سبب الرفض…');
reg('No damaged sorting requests.', 'لا توجد طلبات فرز متضررة.');
reg('Request approved. The employee was notified.', 'تمت الموافقة على الطلب وتم إشعار الموظف.');
reg('Request rejected. The employee was notified.', 'تم رفض الطلب وتم إشعار الموظف.');
reg('Shipment moved to storage.', 'تم نقل الشحنة إلى التخزين.');
reg('Zones of your warehouse, filterable by type.', 'مناطق مستودعك مع فلترة حسب النوع.');
reg('No zones found.', 'لا توجد مناطق.');

/* Profile */
reg('Profile Updated', 'تم تحديث الملف الشخصي');
reg('Your profile has been updated successfully.', 'تم تحديث ملفك الشخصي بنجاح.');
reg('Failed to save profile. Please try again.', 'فشل حفظ الملف الشخصي. يرجى المحاولة مرة أخرى.');
reg('Your account details, role, and system access information.', 'تفاصيل حسابك، دورك، وصلاحيات الوصول إلى النظام.');
reg('Your account details, role and warehouse assignment.', 'تفاصيل حسابك ودورك وتعيين المستودع.');
reg('Warehouse', 'المستودع');
reg('Role', 'الدور');
reg('National ID', 'الرقم الوطني');
reg('Log Out', 'تسجيل الخروج');
reg('Update failed. Please try again.', 'فشل التحديث. حاول مرة أخرى.');
reg('Address', 'العنوان');
reg('City', 'المدينة');
reg('Country', 'الدولة');

// Expose globally so backend menu script can use tr() without module import
window.dwTrBackend = tr;
reg('Approval Thresholds (%)', 'نسب الموافقات (%)');
reg('Weight warning from', 'تحذير فرق الوزن من');
reg('Transfer to manager above', 'التحويل للمدير فوق');
reg('Damage approval above', 'موافقة التلف فوق');
reg('Invalid percentages: warning must be lower than the transfer limit (both between 0 and 100).',
    'نسب غير صالحة: نسبة التحذير يجب أن تكون أقل من حد التحويل (وكلاهما بين 0 و100).');

/* Settings Page */
reg('Dark mode active', 'الوضع الداكن مفعّل');
reg('Light mode active', 'الوضع الفاتح مفعّل');
reg('Please fill in all fields', 'يرجى ملء جميع الحقول');
reg('New passwords do not match', 'كلمتا المرور الجديدتان غير متطابقتين');
reg('Password must be at least 6 characters', 'يجب أن تكون كلمة المرور 6 أحرف على الأقل');
reg('Failed to change password', 'فشل تغيير كلمة المرور');
reg('Current password is incorrect', 'كلمة المرور الحالية غير صحيحة');
reg('Change Password', 'تغيير كلمة المرور');
reg('Current Password', 'كلمة المرور الحالية');
reg('Enter current password', 'أدخل كلمة المرور الحالية');
reg('New Password', 'كلمة المرور الجديدة');
reg('Enter new password', 'أدخل كلمة المرور الجديدة');
reg('Confirm New Password', 'تأكيد كلمة المرور الجديدة');
reg('Confirm new password', 'أكد كلمة المرور الجديدة');
reg('Saving…', 'جاري الحفظ…');
reg('Password Changed Successfully!', 'تم تغيير كلمة المرور بنجاح!');
reg('Your password has been updated. You can now login with your new password.', 'تم تحديث كلمة المرور. يمكنك الآن تسجيل الدخول بكلمة المرور الجديدة.');
reg('A password reset link will be sent to your email address.', 'سيتم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني.');
reg('Please provide both current and new password', 'يرجى إدخال كلمة المرور الحالية والجديدة');
reg('Processing shipment...', 'جاري معالجة الشحنة...');
reg('Please wait while we verify the shipment data.', 'يرجى الانتظار بينما نتحقق من بيانات الشحنة.');
reg('Shipment Accepted!', 'تم قبول الشحنة!');
reg('Shipment Transferred!', 'تم تحويل الشحنة!');
reg('Processing Details', 'تفاصيل المعالجة');
reg('Enter actual weight…', 'أدخل الوزن الفعلي…');
reg('Optional notes…', 'ملاحظات اختيارية…');
reg('Enter transfer reason…', 'أدخل سبب التحويل…');
reg('Open camera and scan the shipment label directly.', 'افتح الكاميرا وامسح ملصق الشحنة مباشرة.');
reg('Choose a photo with a QR code from your gallery.', 'اختر صورة تحتوي على رمز QR من معرض الصور.');
reg('Assigned Employees', 'الموظفون المعينون');
reg('No employees assigned', 'لا يوجد موظفون معينون');
reg('Employee Count', 'عدد الموظفين');
reg('employees', 'موظفون');

// ─── Shift Assignment (Manager) ───
reg('Assign Shift to Employee', 'إسناد وردية لموظف');
reg('Select an employee to assign or change their work shift. Only shifts linked to your warehouse are available.', 'اختر موظفاً لإسناد أو تغيير وردية العمل. فقط الورديات المرتبطة بمستودعك متاحة.');
reg('Total Employees', 'إجمالي الموظفين');
reg('With Shift', 'مع وردية');
reg('Without Shift', 'بدون وردية');
reg('Has Shift', 'لديه وردية');
reg('No Shift', 'بدون وردية');
reg('Assigned', 'مسند');
reg('Unassigned', 'غير مسند');
reg('Assign', 'إسناد');
reg('Assign or change the work shift for this employee.', 'إسناد أو تغيير وردية العمل لهذا الموظف.');
reg('Current Shift', 'الوردية الحالية');
reg('Select Shift', 'اختر الوردية');
reg('No Shift (Unassign)', 'بدون وردية (إلغاء الإسناد)');
reg('Only shifts linked to your warehouse by the administrator are shown.', 'فقط الورديات المرتبطة بمستودعك من قبل المدير العام معروضة.');
reg('No warehouse shifts available', 'لا توجد ورديات مستودع متاحة');
reg('Ask the administrator to link shifts to your warehouse before assigning them.', 'اطلب من المدير العام ربط الورديات بمستودعك قبل إسنادها.');
reg('Assign Shift', 'إسناد وردية');
reg('Shift assigned successfully!', 'تم إسناد الوردية بنجاح!');
reg('Invalid shift selection.', 'اختيار وردية غير صالح.');
reg('Assignment failed. Please try again.', 'فشل الإسناد. يرجى المحاولة مرة أخرى.');
reg('Not assigned', 'غير مخصص');

// ─── Shift Assignment Notifications ───
reg('Shift Assigned', 'تم إسناد وردية');
reg('Shift Unassigned', 'تم إلغاء إسناد وردية');
reg('Unassign current shift', 'إلغاء إسناد الوردية الحالية');

// ─── Unassigned Employee Management ───
reg('Unassigned', 'غير مسند');
reg('Unassigned Employees', 'الموظفون غير المعيّنين');
reg('No unassigned employees found.', 'لم يتم العثور على موظفين غير معيّنين.');
reg('All employees have been assigned a warehouse and role.', 'تم تعيين مستودع وrole لجميع الموظفين.');
reg('Assign warehouse and role to this employee', 'تعيين مستودع وrole لهذا الموظف');
reg('Step 1: Assign Warehouse', 'الخطوة 1: تعيين المستودع');
reg('Step 2: Assign Role Type', 'الخطوة 2: تعيين نوع الدور');
reg('Select Warehouse (without manager)', 'اختر المستودع (بدون مدير)');
reg('-- Select Warehouse --', '-- اختر المستودع --');
reg('All warehouses have managers. Create a new warehouse or remove an existing manager first.', 'جميع المستودعات لها مديرون. أنشئ مستودعاً جديداً أو أزل مديراً موجوداً أولاً.');
reg('Assign Warehouse', 'تعيين المستودع');
reg('Warehouse assigned successfully!', 'تم تعيين المستودع بنجاح!');
reg('Notification sent to warehouse manager.', 'تم إرسال الإشعار لمدير المستودع.');
reg('Awaiting Role', 'بانتظار الدور');
reg('Awaiting Assignment', 'بانتظار التعيين');
reg('Not assigned', 'غير معيّن');
reg('Role Type', 'نوع الدور');
reg('Warehouse Manager', 'مدير المستودع');
reg('Becomes manager of the warehouse immediately', 'يصبح مدير المستودع فوراً');
reg('Employee', 'موظف');
reg('Assigned to warehouse. Manager will assign the specific role.', 'معيّن للمستودع. المدير سيعيّن الدور المحدد.');
reg('Assign Role Type', 'تعيين نوع الدور');
reg('Role assigned successfully!', 'تم تعيين الدور بنجاح!');
reg('Please select a warehouse.', 'يرجى اختيار مستودع.');
reg('Please select a role type.', 'يرجى اختيار نوع الدور.');
reg('Please assign a warehouse first.', 'يرجى تعيين المستودع أولاً.');
reg('Assignment failed.', 'فشل الإسناد.');
reg('This warehouse already has a manager.', 'هذا المستودع لديه مدير بالفعل.');
reg('Invalid role type.', 'نوع دور غير صالح.');
reg('Never assigned', 'لم يتم التعيين من قبل');
reg('This employee is awaiting a role assignment. Click Edit to assign a role.', 'هذا الموظف ينتظر تعيين دور. انقر على Edit لتعيين الدور.');
reg('Change History', 'سجل التغييرات');
reg('Loading history…', 'جاري تحميل السجل…');
reg('No history records yet.', 'لا توجد سجلات بعد.');
reg('Role Change', 'تغيير الدور');
reg('Warehouse Change', 'تغيير المستودع');
reg('Direct Addition', 'إضافة مباشرة');
reg('Assignment Start', 'بداية التعيين');
reg('Assignment End', 'نهاية التعيين');
reg('Archived', 'مؤرشف');
reg('Restored', 'مستعاد');
reg('Role:', 'الدور:');
reg('Warehouse:', 'المستودع:');
reg('Started:', 'بدأ:');
reg('Ended:', 'انتهى:');
reg('By:', 'بواسطة:');
reg('Back to Unassigned', 'العودة لقائمة غير المعيّنين');
reg('New Employee Assignment', 'تعيين موظف جديد');
reg('Loading unassigned employees…', 'جاري تحميل الموظفين غير المعيّنين…');
reg('No unassigned employees found.', 'لم يتم العثور على موظفين غير معيّنين.');
reg('Assign', 'تعيين');
reg('Done', 'تم');
reg('Job Applicant', 'متقدم للوظيفة');
reg('This employee has been assigned to your warehouse. Assign a role and shift.', 'تم تعيين هذا الموظف في مستودعك. قم بتعيين الدور والوردية.');
reg('Restore', 'استعادة');
reg('Reject', 'رفض');
reg('Account reactivated.', 'تمت استعادة الحساب.');
reg('Request declined.', 'تم رفض الطلب.');
reg('Action failed.', 'فشلت العملية.');

// ── Reception intake rework (scan → read-only info → accept/release) ──
reg('Shipments reserved for you and shipments you have received.', 'الشحنات المحجوزة لك والشحنات التي استلمتها.');
reg('Received Status', 'تم الاستقبال');
reg('Truck Info', 'معلومات الشاحنة');
reg('Dispatch Date', 'تاريخ الإرسال');
reg('Expected Materials', 'المواد المتوقعة');
reg('Material', 'المادة');
reg('Expected Quantity', 'الكمية المتوقعة');
reg('Unit', 'الوحدة');
reg('pcs', 'قطعة');
reg('No expected materials declared for this shipment.', 'لم يتم تحديد مواد متوقعة لهذه الشحنة.');
reg('Entered', 'المُدخل');
reg('Pieces', 'قطع');
reg('short', 'نقص');
reg('Missing materials', 'مواد ناقصة');
reg('Not declared for this shipment', 'غير مصرّح بها لهذه الشحنة');
reg('Details', 'التفاصيل');
reg('Storage', 'التخزين');
reg('One zone for the whole shipment', 'منطقة واحدة للشحنة كاملة');
reg('A zone per material', 'منطقة لكل مادة');
reg('All sorted materials will be placed in this zone.', 'ستُوضع كل المواد المفروزة في هذه المنطقة.');
reg('Finish Storage', 'إنهاء التخزين');
reg('Assign a storage zone to every material.', 'عيّن منطقة تخزين لكل مادة.');
reg('Nothing to store.', 'لا شيء للتخزين.');
reg('The damaged quantity is sent to the warehouse manager for review. You can store the sound materials now — no need to wait.', 'الكمية التالفة تُرسَل إلى مدير المستودع للمراجعة. يمكنك تخزين المواد السليمة الآن — دون انتظار.');
reg('Describe what was damaged and why.', 'صِف ما تلف ولماذا.');
reg('Describe the damage before moving to storage — it will be sent to the manager, and you can store the sound materials now.', 'صِف التلف قبل الانتقال للتخزين — سيُرسَل للمدير، ويمكنك تخزين المواد السليمة الآن.');
reg('Damaged quantity is sent to the manager for review — you can still store the sound materials now.', 'الكمية التالفة تُرسَل للمدير للمراجعة — ويمكنك تخزين المواد السليمة الآن.');
reg('Export Excel', 'تصدير Excel');
reg('Download PDF', 'تنزيل PDF');
reg('Stored Date', 'تاريخ التخزين');
reg('Stored By', 'خُزِّنت بواسطة');
reg('Good Qty', 'الكمية السليمة');
reg('Damaged Qty', 'الكمية التالفة');
reg('Damaged %', 'نسبة التلف %');
reg('Hide', 'إخفاء');
reg('Approve & Store', 'موافقة وتخزين');
reg('Send Back', 'إرجاع للموظف');
reg('Sent back to the employee to correct the quantities.', 'تم الإرجاع إلى الموظف لتصحيح الكميات.');
reg('Approved. The shipment was moved to storage.', 'تمت الموافقة. تم نقل الشحنة إلى التخزين.');
reg('Not in this shipment', 'ليست ضمن الشحنة');
reg('Missing', 'ناقص');
reg('Description for the manager', 'وصف لمدير المستودع');
reg('Describe why this shipment needs manager review…', 'اشرح سبب حاجة هذه الشحنة لمراجعة المدير…');
reg('The quantities you entered are more than what was declared for this shipment. Please review the quantities.', 'الكميات التي أدخلتها أكبر من المصرّح به لهذه الشحنة. يرجى مراجعة الكميات.');
reg('There is a difference between the entered quantities and what was declared for this shipment. Please describe the reason.', 'يوجد فرق بين الكميات المُدخلة والمصرّح به لهذه الشحنة. يرجى وصف السبب.');
reg('There is a difference between the entered quantities and the declared materials. Please describe the reason.', 'يوجد فرق بين الكميات المُدخلة والمواد المصرّح بها. يرجى وصف السبب.');
reg('Visual check only — confirm what arrived roughly matches this list, no exact measurement needed here.', 'فحص بصري فقط — تأكد أن ما وصل يتوافق تقريباً مع هذه القائمة، دون الحاجة لقياس دقيق هنا.');
reg('No receiving zone is configured for your warehouse. Contact the warehouse manager.', 'لا توجد منطقة استقبال معرفة لمستودعك. تواصل مع مدير المستودع.');
reg('Confirm Receipt', 'تم الاستلام');
reg('Shipment Received!', 'تم استقبال الشحنة!');
reg('Release', 'إفلات');
reg('Truck ID', 'معرّف الشاحنة');
reg('Truck Serial Number', 'الرقم التسلسلي للشاحنة');

// ── Admin Settings: Apps launcher + Add Administrator ──
reg('Apps', 'التطبيقات');
reg('All Apps', 'كل التطبيقات');
reg('Switch to another installed app (Website, etc.)', 'التبديل إلى تطبيق آخر مثبت (الموقع الإلكتروني وغيره).');
reg('Administration', 'الإدارة');
reg('Add Administrator', 'إضافة أدمن');
reg('Creates a new user with full administrator access. A password-setup email is sent to them.', 'ينشئ مستخدماً جديداً بصلاحيات أدمن كاملة. سيتم إرسال بريد إلكتروني لتعيين كلمة المرور.');
reg('Email required', 'البريد الإلكتروني مطلوب');
reg('An account with this email already exists.', 'يوجد حساب بهذا البريد الإلكتروني مسبقاً.');
reg('You are not allowed to do this.', 'لا تملك صلاحية القيام بهذا.');
reg('Administrator account created. A password-setup email was sent.', 'تم إنشاء حساب الأدمن. تم إرسال بريد لتعيين كلمة المرور.');
reg('Enter email address', 'أدخل البريد الإلكتروني');
reg('Enter full name', 'أدخل الاسم الكامل');

// ─── Output dashboard: order/invoice processing ───
reg('$', '$');
reg('All orders have been reserved by other employees.', 'تم حجز جميع الطلبات من قبل موظفين آخرين.');
reg('Amount', 'المبلغ');
reg('Available', 'متوفر');
reg('Complete & Generate Invoice', 'إكمال وإنشاء الفاتورة');
reg('Complete Order', 'إكمال الطلب');
reg('Completed orders with generated invoices.', 'الطلبات المكتملة مع الفواتير الصادرة.');
reg('Completing…', 'جارٍ الإكمال…');
reg('Download Invoice PDF', 'تحميل الفاتورة PDF');
reg('Insufficient', 'غير كافٍ');
reg('Invoice Detail', 'تفاصيل الفاتورة');
reg('Invoice details and material breakdown.', 'تفاصيل الفاتورة وتفصيل المواد.');
reg('items', 'عناصر');
reg('Material Breakdown', 'تفصيل المواد');
reg('Material List', 'قائمة المواد');
reg('No invoices found.', 'لا توجد فواتير.');
reg('No pending orders available.', 'لا توجد طلبات معلقة متاحة.');
reg('Order Detail', 'تفاصيل الطلب');
reg('Order details and material list.', 'تفاصيل الطلب وقائمة المواد.');
reg('Order Type', 'نوع الطلب');
reg('Profile updated.', 'تم تحديث الملف الشخصي.');
reg('Required', 'مطلوب');
reg('Reserve & Process', 'حجز ومعالجة');
reg('Reserving…', 'جارٍ الحجز…');
reg('Review order details and reserve it.', 'راجع تفاصيل الطلب واحجزه.');
reg('Search by order, customer...', 'ابحث برقم الطلب أو العميل...');
reg('Search by order, invoice, customer...', 'ابحث برقم الطلب أو الفاتورة أو العميل...');
reg('Select an unreserved order to process.', 'اختر طلباً غير محجوز لمعالجته.');
reg('Start Processing', 'بدء المعالجة');
reg('Stock Requirements', 'متطلبات المخزون');
reg('Storage Zones', 'مناطق التخزين');
reg('System alerts and updates for you', 'تنبيهات وتحديثات النظام الخاصة بك');
reg('Verify stock availability and complete the order.', 'تحقق من توفر المخزون وأكمل الطلب.');
reg('View and manage your assigned orders.', 'عرض وإدارة الطلبات المخصصة لك.');
reg('Weight', 'الوزن');
reg('You are not currently assigned to a work shift.', 'أنت غير مخصص حالياً لوردية عمل.');

// ─── Driver shift-change requests + driver detail (manager) + truck problems ───
reg('Shift Change Requests', 'طلبات تغيير الوردية');
reg('Truck Problems', 'مشاكل الشاحنات');
reg('Requests submitted by your drivers in the app, newest first. Process, then approve with a truck or reject.',
    'الطلبات المقدَّمة من سائقيك في التطبيق، الأحدث أولاً. ابدأ المعالجة ثم اقبل بتحديد شاحنة أو ارفض.');
reg('Loading requests…', 'جارٍ تحميل الطلبات…');
reg('No shift-change requests.', 'لا توجد طلبات تغيير وردية.');
reg('Processing', 'قيد المعالجة');
reg('Rejection:', 'سبب الرفض:');
reg('From:', 'من:');
reg('To:', 'إلى:');
reg('Change Shift', 'تغيير الوردية');
reg('Choose a truck for the new shift', 'اختر شاحنة للوردية الجديدة');
reg('Approve and Assign', 'الموافقة والإسناد');
reg('Reject this request?', 'رفض هذا الطلب؟');
reg('Why is this request rejected?', 'ما سبب رفض هذا الطلب؟');
reg('Reason:', 'السبب:');
reg('Move to shift', 'النقل إلى وردية');
reg('Choose a free truck', 'اختر شاحنة متاحة');
reg('Confirm Shift Change', 'تأكيد تغيير الوردية');
reg('Block Driver', 'حظر السائق');
reg('Unblock Driver', 'فك حظر السائق');
reg('Blocked', 'محظور');
reg('Block this driver?', 'حظر هذا السائق؟');
reg('He will be signed out of the app immediately and cannot sign in again until unblocked.',
    'سيتم تسجيل خروجه من التطبيق فوراً ولا يمكنه الدخول ثانيةً حتى يُرفع الحظر.');
reg('Optional reason…', 'سبب اختياري…');
reg('Driver blocked — he was signed out of the app.', 'تم حظر السائق — وسُجّل خروجه من التطبيق.');
reg('Driver unblocked — he can sign in again.', 'تم فك الحظر — يمكنه الدخول ثانيةً.');
reg('Driver moved to the new shift and truck.', 'تم نقل السائق إلى الوردية والشاحنة الجديدة.');
reg('Could not load available trucks.', 'تعذّر تحميل الشاحنات المتاحة.');
reg('Truck taken out of service.', 'تم إخراج الشاحنة من الخدمة.');
reg('Truck put in service.', 'تم إدخال الشاحنة للخدمة.');
reg('Disable this truck', 'تعطيل هذه الشاحنة');
reg('Why is this truck being taken out of service?', 'ما سبب إخراج هذه الشاحنة من الخدمة؟');
reg('Reports submitted by your drivers, newest first — read only.',
    'التقارير المقدَّمة من سائقيك، الأحدث أولاً — للقراءة فقط.');
reg('Loading problems…', 'جارٍ تحميل المشاكل…');
reg('No truck problems reported.', 'لا توجد مشاكل شاحنات مُبلَّغ عنها.');
reg('Change Warehouse', 'تغيير المستودع');
reg('Move to warehouse', 'النقل إلى مستودع');
reg('Choose a warehouse…', 'اختر مستودعاً…');
reg('Confirm Move', 'تأكيد النقل');
reg('If his truck belongs to the old warehouse, the truck assignment is removed.',
    'إن كانت شاحنته تابعة للمستودع القديم، يُلغى إسناد الشاحنة.');
reg('Driver warehouse changed.', 'تم تغيير مستودع السائق.');

// ─── Driver attendance (truck pickup / dropoff — read-only) ───
reg('Driver Attendance', 'حضور السائقين');
reg('When your drivers picked up and handed back their trucks — read-only.',
    'متى استلم سائقوك سياراتهم وسلّموها — للقراءة فقط.');
reg('When drivers picked up and handed back their trucks — read-only.',
    'متى استلم السائقون سياراتهم وسلّموها — للقراءة فقط.');
reg('Picked Up', 'وقت الاستلام');
reg('Handed Over', 'وقت التسليم');
reg('Late (min)', 'التأخير (دقيقة)');
reg('Holding', 'ماسك السيارة');
reg('Missed Pickup', 'لم يستلم');
reg('No driver attendance records yet.', 'لا توجد سجلات حضور سائقين بعد.');
reg('Note', 'ملاحظة');
reg('Problem reports submitted by your drivers in the app — read-only.',
    'تقارير المشاكل المقدَّمة من سائقيك في التطبيق — للقراءة فقط.');

// ─── Remaining translation gaps (audit pass) ───
reg('-- Choose a warehouse --', '-- اختر مستودعاً --');
reg('Active Shipments', 'الشحنات النشطة');
reg('Actual', 'الفعلي');
reg('All Status', 'كل الحالات');
reg('Approve', 'موافقة');
reg('Assign a sorting zone, log materials, then move to storage.', 'حدد منطقة فرز، سجّل المواد، ثم انقل إلى التخزين.');
reg('Assigning…', 'جارٍ التعيين…');
reg('Complete Step 1 first to assign a warehouse.', 'أكمل الخطوة 1 أولاً لتعيين مستودع.');
reg('Employee Information', 'معلومات الموظف');
reg('Expected', 'المتوقع');
reg('Full control of the warehouse', 'تحكم كامل بالمستودع');
reg('General: any of the three employee roles is assigned later. A specific role locks every hire from this job to that role only.', 'عام: يتم تعيين أحد الأدوار الثلاثة لاحقاً. الدور المحدد يقيّد كل توظيف من هذه الوظيفة بهذا الدور فقط.');
reg('Manager will assign the specific role', 'سيقوم المدير بتعيين الدور المحدد');
reg('No accepted applicants.', 'لا يوجد متقدمون مقبولون.');
reg('No applications found.', 'لا توجد طلبات توظيف.');
reg('No attendance records.', 'لا توجد سجلات حضور.');
reg('No damaged requests.', 'لا توجد طلبات تلف.');
reg('No deleted applications.', 'لا توجد طلبات محذوفة.');
reg('No hiring stages.', 'لا توجد مراحل توظيف.');
reg('No manager', 'بدون مدير');
reg('No product categories found.', 'لا توجد فئات منتجات.');
reg('No rejected applicants.', 'لا يوجد متقدمون مرفوضون.');
reg('No stock records.', 'لا توجد سجلات مخزون.');
reg('No talent pool records found.', 'لا توجد سجلات في مجمع المواهب.');
reg('No transferred shipments.', 'لا توجد شحنات محولة.');
reg('No warehouses available. Create a new warehouse first.', 'لا توجد مستودعات متاحة. أنشئ مستودعاً جديداً أولاً.');
reg('No website users found.', 'لا يوجد مستخدمو موقع.');
reg('Pending Shipments', 'الشحنات المعلقة');
reg('Personal Details', 'البيانات الشخصية');
reg('Previous Role', 'الدور السابق');
reg('Reception WMS', 'نظام الاستقبال');
reg('Select Warehouse', 'اختر المستودع');
reg('Shipment details and contents.', 'تفاصيل الشحنة ومحتوياتها.');
reg('Used as login and for password reset.', 'يُستخدم لتسجيل الدخول واستعادة كلمة المرور.');
reg('Your account information.', 'معلومات حسابك.');
reg('Your assigned work shift and schedule.', 'ورديتك المخصصة وجدولها.');
reg('Your current shift details and schedule.', 'تفاصيل ورديتك الحالية وجدولها.');

// ─── Reception: wrong-warehouse scan error ───
reg('You cannot receive this shipment because it does not belong to your warehouse.',
    'لا يمكنك استقبال هذه الشحنة لأنها لا تتبع لمستودعك.');

// ─── Reception/Sorting: pending-shipments KPI ───
reg('Reserved to you', 'محجوزة لك');

// ─── Manager/Admin: stock-by-storage-zone filter ───
reg('Storage Zone', 'منطقة التخزين');
reg('All Storage Zones', 'كل مناطق التخزين');
reg('All Conditions', 'كل الحالات');

// ─── Sorting reconciliation rewrite: uom.uom, thresholds, damage reports ───
reg('Pending Sorting Approval', 'بانتظار موافقة الفرز');
reg('Sorting Reconciliation Settings', 'إعدادات مطابقة الفرز');
reg('Auto-accepted shortage per material (%)', 'نسبة النقص المقبولة تلقائياً لكل مادة (%)');
reg('Maximum shortage before manager approval (%)', 'أقصى نسبة نقص قبل موافقة المدير (%)');
reg('Please select a unit of measure.', 'الرجاء اختيار وحدة قياس.');
reg('Select a unit…', 'اختر وحدة…');
reg('Declared Totals', 'الإجماليات المصرح بها');
reg('units', 'وحدات');

reg('Report Damaged Material', 'تبليغ عن مادة تالفة');
reg('Report material already in storage that turned out to be damaged. The warehouse manager must approve before it is deducted from stock.',
    'بلّغ عن مادة موجودة بالفعل بالمخزون تبيّن أنها تالفة. يجب موافقة مدير المستودع قبل خصمها من المخزون.');
reg('Damaged Quantity', 'الكمية التالفة');
reg('Photo (optional)', 'صورة (اختياري)');
reg('Submit Report', 'إرسال التبليغ');
reg('Please select a material.', 'الرجاء اختيار مادة.');
reg('Enter a valid quantity.', 'أدخل كمية صحيحة.');
reg('Please describe the reason.', 'الرجاء وصف السبب.');
reg('Damage report sent to the warehouse manager for approval.', 'تم إرسال تبليغ التلف لمدير المستودع للموافقة.');
reg('Damage Reports', 'تبليغات التلف');
reg('Reference', 'المرجع');
reg('Reported By', 'المُبلِّغ');
reg('No pending damage reports.', 'لا توجد تبليغات تلف بانتظار المراجعة.');
reg('Approved. Stock was updated.', 'تمت الموافقة. تم تحديث المخزون.');
reg('Rejected.', 'تم الرفض.');

reg('Some materials are short of what was declared. Please choose a reason before finishing.',
    'بعض المواد أقل من الكمية المصرح بها. الرجاء اختيار سبب قبل الإنهاء.');
reg('Some materials are short of what was declared. Choose a reason before finishing.',
    'بعض المواد أقل من الكمية المصرح بها. اختر سبباً قبل الإنهاء.');
reg('Shortage Reason', 'سبب النقص');
reg('Select a reason…', 'اختر سبباً…');
reg('Humidity / Evaporation', 'رطوبة / تبخر');
reg('Materials excluded from sorting', 'مواد مستبعدة من الفرز');
reg('Error in the original declared quantity', 'خطأ بالكمية الأصلية المصرح بها');
reg('Describe the reason', 'صف السبب');
reg("These materials need the warehouse manager's approval. Finishing now will send this shipment for review.",
    'هذه المواد تحتاج موافقة مدير المستودع. سيتم إرسال الشحنة للمراجعة عند الإنهاء الآن.');
reg("This shipment needs the warehouse manager's approval and was sent for review.",
    'هذه الشحنة تحتاج موافقة مدير المستودع وتم إرسالها للمراجعة.');
reg('Transfer to Manager', 'تحويل للمدير');
reg('The quantities you entered exceed what was declared for this shipment. Please review the quantities.',
    'الكميات التي أدخلتها تتجاوز ما تم التصريح به لهذه الشحنة. الرجاء مراجعة الكميات.');
reg('Exceeds what was declared — not allowed', 'تتجاوز المصرح به — غير مسموح');
reg('Shortage', 'النقص');

reg('Auto-blocked', 'محظور تلقائياً');
reg('Manual transfer', 'تحويل يدوي');
reg('Approved. The sorter can now finish this shipment.', 'تمت الموافقة. يمكن لموظف الفرز الآن إنهاء هذه الشحنة.');
reg('Shipments transferred by sorting employees, or automatically blocked by the reconciliation rules.',
    'شحنات محوّلة من موظفي الفرز، أو محظورة تلقائياً بقواعد المطابقة.');
reg('Shortfall', 'نسبة النقص');

// ─── Shipments/Orders list rework: dates instead of processor names, state filters ───
reg('Received Date', 'تاريخ الاستلام');
reg('Sorted Date', 'تاريخ الفرز');
reg('All Statuses', 'كل الحالات');
reg('Expected Quantity', 'الكمية المتوقعة');
reg('Invalid shipment barcode.', 'باركود الشحنة غير صالح.');
reg('Recycling Management System', 'نظام إعادة تدوير');

// ─── Sort process rework: storage zone AFTER materials, dynamic Finish/Transfer button ───
reg('Choose Storage Zone', 'اختر منطقة التخزين');
reg('Confirm & Store', 'تأكيد وتخزين');
reg('Enter a lower weight and matching quantity.', 'أدخل وزناً أقل وكمية مطابقة.');
reg("These materials need the warehouse manager's approval before this shipment can be stored.",
    'هذه المواد تحتاج موافقة مدير المستودع قبل تخزين هذه الشحنة.');
reg('Choose the storage zone where the sorted materials will be placed.',
    'اختر منطقة التخزين التي ستوضع فيها المواد المفروزة.');

// ─── Order workflow rework: priority queue + multi-zone deduction + output-zone finish ───
reg('You must process order', 'يجب معالجة الطلبية');
reg('first — it has a higher priority.', 'أولاً — فهي أعلى أولوية.');
reg('Choose Storage Zones', 'اختر مناطق التخزين');
reg('Pick the zone(s) to deduct each material from. Combine more than one zone if needed.',
    'اختر منطقة (أو أكثر) لخصم كل مادة منها. يمكنك دمج أكثر من منطقة عند الحاجة.');
reg('No storage zone currently holds this material/condition.', 'لا توجد منطقة تخزين تحتوي حالياً على هذه المادة/الحالة.');
reg('Quantity insufficient, check your stock', 'الكمية غير كافية، تحقق من مخزونك');
reg('select more than one storage zone if needed to reach the required quantity.',
    'اختر أكثر من منطقة تخزين إذا لزم الأمر لتحقيق الكمية المطلوبة.');
reg('Stock deducted at', 'تم خصم المخزون في');
reg('Choose Output Zone & Finish', 'اختر منطقة الإخراج وأنهِ الطلبية');
reg('Choose Output Zone', 'اختر منطقة الإخراج');
reg('Select the zone the goods were moved to, then finish the order.',
    'اختر المنطقة التي نُقلت إليها البضائع، ثم أنهِ الطلبية.');
reg('No output zone configured for this warehouse.', 'لا توجد منطقة إخراج مُعرّفة لهذا المستودع.');
reg('Finish', 'إنهاء');
reg('Finishing…', 'جارٍ الإنهاء…');
reg('Order finished successfully!', 'تم إنهاء الطلبية بنجاح!');
reg('Back to My Orders', 'العودة إلى طلباتي');

// ─── Manager: employee performance rating ───
reg('Rating', 'التقييم');
reg('Performance Rating', 'تقييم الأداء');
reg('Not rated yet', 'لم يُقيَّم بعد');
reg('Rate', 'قيّم');
reg("Click a star to rate this employee's performance/efficiency. Click the current rating again to clear it.",
    'اضغط على نجمة لتقييم أداء/كفاءة هذا الموظف. اضغط على التقييم الحالي مجدداً لإلغائه.');
reg('Rating saved.', 'تم حفظ التقييم.');
reg('Failed to save rating.', 'فشل حفظ التقييم.');

// ─── Trucks (fleet) — admin dashboard ───
reg('Trucks', 'الشاحنات');
reg('Manage the collection fleet — add trucks, assign them to a warehouse or leave them unassigned. Every change is mirrored to the Dawrha backend automatically.',
    'إدارة أسطول الجمع — أضف الشاحنات، أسندها إلى مستودع أو اتركها غير مسندة. كل تغيير ينعكس تلقائياً على نظام دورها.');
reg('Add Truck', 'إضافة شاحنة');
reg('Edit Truck', 'تعديل شاحنة');
reg('Truck Name', 'اسم الشاحنة');
reg('Plate Number', 'رقم اللوحة');
reg('Model', 'الموديل');
reg('Year', 'سنة الصنع');
reg('Max Payload (kg)', 'الحمولة القصوى (كغ)');
reg('In Service', 'في الخدمة');
reg('Loading trucks…', 'جارٍ تحميل الشاحنات…');
reg('No trucks found.', 'لا توجد شاحنات.');
reg('Search by name, plate, model…', 'ابحث بالاسم أو اللوحة أو الموديل…');
reg('— Unassigned —', '— غير مسندة —');
reg('Enter the truck details. Assign it to a warehouse now or leave it unassigned — you can change this at any time.',
    'أدخل بيانات الشاحنة. أسندها إلى مستودع الآن أو اتركها غير مسندة — يمكنك تغيير ذلك في أي وقت.');
reg('e.g. Damascus Truck 1', 'مثال: شاحنة دمشق 1');
reg('Save Truck', 'حفظ الشاحنة');
reg('Truck created successfully!', 'تم إنشاء الشاحنة بنجاح!');
reg('Truck updated successfully!', 'تم تحديث الشاحنة بنجاح!');
reg('Truck name is required.', 'اسم الشاحنة مطلوب.');
reg('Plate number is required.', 'رقم اللوحة مطلوب.');
reg('Year must be between 1980 and next year.', 'سنة الصنع يجب أن تكون بين 1980 والسنة القادمة.');
reg('Max payload must be a positive number.', 'الحمولة القصوى يجب أن تكون رقماً موجباً.');
reg('Save failed. Please check the fields.', 'فشل الحفظ. يرجى التحقق من الحقول.');
reg('Could not update the truck status.', 'تعذر تحديث حالة الشاحنة.');

// ─── Shift type (driver / warehouse) ───
reg('Shift For', 'الوردية مخصصة لـ');
reg('Warehouse Staff', 'موظفي المستودع');
reg('Drivers', 'السائقين');
reg('Driver shifts are offered to drivers in the app and can never be assigned to warehouse employees.',
    'ورديات السائقين تُعرض للسائقين في التطبيق ولا يمكن أبداً إسنادها لموظفي المستودع.');

// ─── Trucks — state toggle + manager screen ───
reg('Take out of service', 'إخراج من الخدمة');
reg('Put in service', 'إعادة للخدمة');
reg('Truck put in service.', 'أُعيدت الشاحنة للخدمة.');
reg('Truck taken out of service.', 'أُخرجت الشاحنة من الخدمة.');
reg('Trucks assigned to your warehouse. You can put a truck in or out of service — truck data is managed by the administrator.',
    'الشاحنات المسندة لمستودعك. يمكنك إخراج الشاحنة من الخدمة أو إعادتها — بيانات الشاحنة يديرها الأدمن.');
reg('All Trucks', 'كل الشاحنات');

// ─── Driver Requests (admin dashboard) ───
reg('Driver Requests', 'طلبات السائقين');
// ─── Manage warehouse (zones / manager / info) ───
reg('Manage Warehouse', 'إدارة المستودع');
reg('Edit Warehouse Info', 'تعديل بيانات المستودع');
reg('Change Manager', 'تغيير المدير');
reg('Add Zone', 'إضافة منطقة');
reg('Zones', 'المناطق');
reg('Zone Name', 'اسم المنطقة');
reg('No zones yet.', 'لا توجد مناطق بعد.');
reg('A zone can only be deleted while it holds no stock records.',
    'لا يمكن حذف المنطقة إلا إذا لم يكن فيها أي سجل مخزون.');
reg('Delete this zone?', 'حذف هذه المنطقة؟');
reg('Zone added successfully.', 'تمت إضافة المنطقة بنجاح.');
reg('Zone deleted successfully.', 'تم حذف المنطقة بنجاح.');
reg('Zone name is required.', 'اسم المنطقة مطلوب.');
reg('e.g. Storage Hall 2', 'مثال: صالة تخزين 2');
reg('Receiving', 'استقبال');
reg('Sorting', 'فرز');
reg('Storage', 'تخزين');
reg('Output', 'إخراج');
reg('Only managers who are not running another warehouse are listed. The current manager keeps the manager role but loses access to this warehouse.',
    'تُعرض فقط الكوادر الإدارية غير المسنَدة لمستودع آخر. المدير الحالي يحتفظ بدوره كمدير مستودع لكنه يفقد صلاحية الوصول لهذا المستودع.');
reg('— Select Manager —', '— اختر المدير —');
reg('No unassigned managers available.', 'لا يوجد مدراء غير مسنَدين.');
reg('Choose the new manager.', 'اختر المدير الجديد.');
reg('Manager changed successfully.', 'تم تغيير المدير بنجاح.');
reg('Warehouse updated successfully.', 'تم تحديث المستودع بنجاح.');
reg('Name and code cannot be empty.', 'الاسم والرمز لا يمكن أن يكونا فارغين.');

// ─── Driver request review (table + detail cards) ───
reg('Driver Name', 'اسم السائق');
reg('Account Information', 'معلومات الحساب');
reg('Documents', 'الملفات');
reg('Location Note', 'وصف الموقع');
reg('Coordinates', 'الإحداثيات');
reg('Full application: account details, registered location and uploaded documents.',
    'الطلب كاملاً: معلومات الحساب، الموقع المسجَّل، والملفات المرفوعة.');
reg('Re-open request', 'إعادة فتح الطلب');
reg('Re-open this rejected request for review?', 'إعادة فتح هذا الطلب المرفوض للمراجعة؟');
reg('Request re-opened — it is under review again.', 'أُعيد فتح الطلب — أصبح قيد المراجعة من جديد.');
reg('Applications submitted by drivers in the app. Accept (assigning a warehouse), reject with a reason, or reject a single document so the driver re-uploads it.',
    'الطلبات المقدمة من السائقين عبر التطبيق. اقبل الطلب (مع إسناده لمستودع)، أو ارفضه مع ذكر السبب، أو ارفض مستنداً واحداً ليعيد السائق رفعه.');
reg('Loading driver requests…', 'جارٍ تحميل طلبات السائقين…');
reg('No driver requests.', 'لا توجد طلبات سائقين.');
reg('Needs Changes', 'بحاجة لتعديل');
reg('Reason:', 'السبب:');
reg('Document', 'مستند');
reg('No documents attached.', 'لا توجد مستندات مرفقة.');
reg('Accept', 'قبول');
reg('Reject', 'رفض');
reg('Reject image', 'رفض الصورة');
// ── Judging a document is one act; asking the driver for it is another ──
reg('Accept image', 'قبول الصورة');
reg('Stop waiting for the driver', 'أوقف انتظار السائق');
reg('Stopped waiting — the request is back under review.', 'تم إيقاف الانتظار — عاد الطلب إلى المراجعة.');
reg('Stop waiting for this driver? The documents keep their status — you can then reject the request, but accepting it is still blocked by any rejected document.',
    'إيقاف انتظار هذا السائق؟ تبقى الوثائق على حالتها — يمكنك عندها رفض الطلب، لكن قبوله يبقى محجوباً بأي وثيقة مرفوضة.');
reg('This driver was asked for a document and has not answered. No decision can be taken until he does — or until you stop waiting.',
    'طُلبت من هذا السائق وثيقة ولم يجب. لا يمكن اتخاذ قرار حتى يجيب — أو حتى توقف الانتظار.');

reg('Ask driver to re-upload', 'اطلب من السائق إعادة الرفع');
reg('Asked for', 'مطلوبة');
reg('Document accepted.', 'تم قبول الوثيقة.');
reg('Document rejected. The driver has not been told — ask for it when you are ready.',
    'تم رفض الوثيقة. لم يُبلَّغ السائق — اطلبها منه عندما تكون جاهزاً.');
reg('The driver was asked to re-upload this document.',
    'تم الطلب من السائق إعادة رفع هذه الوثيقة.');
reg('The driver is NOT told. This records your judgement so you can finish reading the rest — ask him for it when you are ready.',
    'لا يتم إبلاغ السائق. هذا يسجّل حكمك لتتمكن من إكمال قراءة البقية — اطلبها منه عندما تكون جاهزاً.');
reg('The request moves to Needs Changes and the driver is told to replace this exact document. He comes back into the queue once he has replaced everything you asked for.',
    'ينتقل الطلب إلى «يحتاج تعديلاً» ويُبلَّغ السائق باستبدال هذه الوثيقة بالذات. ويعود إلى قائمة المراجعة بعد أن يستبدل كل ما طلبته منه.');
reg('What is wrong with it — this is the whole message he receives…',
    'ما الخطأ فيها — هذه هي كامل الرسالة التي ستصله…');
reg('A document is rejected. Accept the document, or ask the driver to re-upload it, before accepting the request.',
    'هناك وثيقة مرفوضة. اقبل الوثيقة أو اطلب من السائق إعادة رفعها قبل قبول الطلب.');
reg('Accept driver', 'قبول السائق');
reg('Assign', 'إسناد');
reg('to a warehouse:', 'إلى مستودع:');
reg('Accept and notify driver', 'قبول وإشعار السائق');
reg('Reject request', 'رفض الطلب');
reg('Why is this request rejected?', 'ما سبب رفض هذا الطلب؟');
reg('Reject and notify driver', 'رفض وإشعار السائق');
reg('Reject document image', 'رفض صورة المستند');
reg('Optional note for the driver (e.g. photo is blurry)…', 'ملاحظة اختيارية للسائق (مثلاً: الصورة غير واضحة)…');
reg('Choose the warehouse this driver will serve.', 'اختر المستودع الذي سيخدمه هذا السائق.');
reg('A rejection reason is required.', 'سبب الرفض مطلوب.');
reg('Driver accepted — the backend was notified.', 'تم قبول السائق — وتم إبلاغ النظام.');
reg('Request rejected — the driver was notified.', 'تم رفض الطلب — وتم إشعار السائق.');
reg('Action failed. Please try again.', 'فشل الإجراء. حاول مرة أخرى.');
reg('Drivers', 'السائقين');
reg('Accepted drivers and the warehouse each one serves.', 'السائقون المقبولون والمستودع الذي يخدمه كل منهم.');
reg('Loading drivers…', 'جارٍ تحميل السائقين…');
reg('Accepted At', 'تاريخ القبول');
reg('No accepted drivers yet.', 'لا يوجد سائقون مقبولون بعد.');

// ─── Drivers screen filters + warehouse fleet + assign-driver-to-truck ───
reg('Accepted drivers — search by name, filter by shift or truck link.',
    'السائقون المقبولون — ابحث بالاسم وصفِّ حسب الوردية أو الارتباط بشاحنة.');
reg('Drivers accepted into your warehouse — search by name, filter by shift or truck link.',
    'السائقون المقبولون في مستودعك — ابحث بالاسم وصفِّ حسب الوردية أو الارتباط بشاحنة.');
reg('Search by driver name…', 'ابحث باسم السائق…');
reg('Assigned Shift', 'الوردية');
reg('Truck', 'الشاحنة');
reg('No Shift Assigned', 'غير مسند لوردية');
reg('All Drivers', 'كل السائقين');
reg('Linked to a Truck', 'مربوط بشاحنة');
reg('Not Linked to a Truck', 'غير مربوط بشاحنة');
reg('No Shift', 'بلا وردية');
reg('No Truck', 'بلا شاحنة');
reg('No drivers match these filters.', 'لا يوجد سائقون يطابقون هذه الفلاتر.');
reg('Truck Management', 'إدارة الشاحنات');
reg('Assign Driver to Truck', 'إسناد سائق لشاحنة');
reg('Pick the shift first — then choose one of its free trucks and one of its unassigned drivers.',
    'اختر الوردية أولاً — ثم اختر شاحنة متاحة فيها وسائقاً من سائقيها غير المسندين.');
reg('Choose a driver shift…', 'اختر وردية سائقين…');
reg("The driver's shift comes with his info — choose it to see matching trucks and drivers.",
    'وردية السائق تأتي مع معلوماته — اخترها لعرض الشاحنات والسائقين المطابقين.');
reg('Loading available trucks and drivers…', 'جارٍ تحميل الشاحنات والسائقين المتاحين…');
reg('Available Trucks', 'الشاحنات المتاحة');
reg('All trucks are reserved for this shift.', 'كل السيارات محجوزة في هذه الوردية.');
reg('Selected', 'مختارة');
reg('Choose the driver', 'اختر السائق');
reg('No unassigned drivers in this shift.', 'لا يوجد سائقون غير مسندين في هذه الوردية.');
reg('Choose a driver…', 'اختر سائقاً…');
reg('Assign Driver', 'إسناد السائق');
reg('Driver assigned to the truck successfully!', 'تم إسناد السائق للشاحنة بنجاح!');
reg('Could not load assignment options.', 'تعذر تحميل خيارات الإسناد.');
reg('Assignment failed. Please try again.', 'فشل الإسناد. حاول مرة أخرى.');
reg('Loading fleet…', 'جارٍ تحميل الأسطول…');
reg('No trucks assigned to this warehouse.', 'لا توجد شاحنات مسندة لهذا المستودع.');
reg('No accepted drivers for this warehouse.', 'لا يوجد سائقون مقبولون لهذا المستودع.');

// ─── Warehouse lifecycle (closing) ───
reg('Warehouse Details', 'بيانات المستودع');
reg('Close Warehouse', 'إغلاق المستودع');
reg('Closing', 'قيد الإغلاق');
reg('Start Closing', 'بدء الإغلاق');
reg('Stop Permanently', 'إيقاف نهائي');
reg('Cancel Closing', 'إلغاء الإغلاق');
reg('Edit details, zones, manager and closing.', 'تعديل البيانات والمناطق والمدير والإغلاق.');
reg('Everything here applies to this warehouse only — no warehouse picker needed.',
    'كل ما هنا يخص هذا المستودع فقط — بلا اختيار مستودع.');
reg('Starting the closing stops new intake. The team is released, free trucks are unassigned, and the warehouse disappears from every selection list. Existing stock is still shipped out.',
    'بدء الإغلاق يوقف استقبال أي عمل جديد. يُفكّ الفريق، وتُحرَّر الشاحنات غير المستلمة، ويختفي المستودع من كل قوائم الاختيار. المخزون الموجود يستمر إخراجه.');
reg('Closing in progress: no new intake. Stop it permanently only after all remaining stock has been shipped out.',
    'الإغلاق جارٍ: لا استقبال جديد. الإيقاف النهائي بعد إخراج كامل المخزون المتبقي فقط.');
reg('This warehouse is permanently stopped and kept for history only.',
    'هذا المستودع موقوف نهائياً ويُحفظ للتاريخ فقط.');
reg('Start closing this warehouse? New intake stops and the team is released.',
    'بدء إغلاق هذا المستودع؟ سيتوقف استقبال العمل الجديد ويُفكّ الفريق.');
reg('Stop this warehouse permanently? This cannot be undone.',
    'إيقاف هذا المستودع نهائياً؟ لا يمكن التراجع.');
reg('Closing started — the warehouse no longer accepts new work.',
    'بدأ الإغلاق — المستودع لم يعد يستقبل عملاً جديداً.');
reg('Warehouse stopped permanently.', 'تم إيقاف المستودع نهائياً.');
reg('Closing cancelled — the warehouse is active again.', 'أُلغي الإغلاق — المستودع نشط من جديد.');
reg('A zone can only be deleted while it holds no stock records. Shipments and orders keep their zone history for auditing.',
    'لا تُحذف المنطقة إلا إذا لم يكن فيها أي سجل مخزون. الشحنات والطلبات تحتفظ بسجل المنطقة للمراقبة.');
reg('Reopen Warehouse', 'إعادة فتح المستودع');
reg('Reopen this warehouse? Its old team and trucks will NOT come back automatically.',
    'إعادة فتح هذا المستودع؟ فريقه وشاحناته السابقة لن تعود تلقائياً.');
reg('Warehouse reopened. No employee or truck was re-assigned automatically — assign resources manually.',
    'تمت إعادة فتح المستودع. لم يُعَد تعيين أي موظف أو شاحنة تلقائياً — يرجى إسناد الموارد يدوياً من الشاشات المخصصة.');
reg('Closing cancelled — no employee or truck was re-assigned automatically.',
    'أُلغي الإغلاق — لم يُعَد تعيين أي موظف أو شاحنة تلقائياً.');

// ── Material price sheet (prices come from the backend: per buyer tier, and
//    per material condition when the material has any) ──────────────────
reg('View Prices', 'عرض الأسعار');
reg('Offer ends', 'ينتهي العرض');
// The figure is substituted into the sentence rather than concatenated onto
// it: Arabic puts the number and the word in the other order, and a glued-on
// "%" cannot be moved by a translator.
reg('{pct}% off', 'خصم {pct}%');
reg('Prices', 'الأسعار');
reg('Loading prices…', 'جارٍ تحميل الأسعار…');
reg('Could not load prices.', 'تعذّر تحميل الأسعار.');
reg('Factories', 'المعامل');
reg('Free Facilities', 'الجهات الحرة');
reg('No price received from the backend for this tier yet.',
    'لم يصل أي سعر من الباك إند لهذه الفئة بعد.');
reg('Plain price (no conditions)', 'السعر المباشر (لا توجد حالات للمادة)');


// ─── Fleet, delivery drivers, grades and the strings that were
//     reaching the screen untranslated ───
reg('View Trucks', 'عرض الشاحنات');
reg('Truck Job', 'عمل الشاحنة');
reg('Truck Type', 'نوع الشاحنة');
reg('Collection', 'جمع');
reg('Delivery', 'توصيل');
reg('Collection Truck', 'شاحنة جمع');
reg('Delivery Truck', 'شاحنة توصيل');
reg('Picks material up from citizens. Driven by a collector on a shift.', 'تجمع المواد من المواطنين. يقودها سائق جمع ضمن وردية.');
reg('Carries sold goods to buyers. Driven by a delivery driver.', 'تنقل البضاعة المباعة إلى المشترين. يقودها سائق توصيل.');
reg('The whole fleet — collection trucks and delivery trucks together, filtered by job. Every change is mirrored to the Dawrha backend automatically.', 'الأسطول كاملاً — شاحنات الجمع وشاحنات التوصيل معاً، مع فلترة حسب العمل. كل تغيير يُزامَن تلقائياً مع نظام دورها.');
reg('The job of a truck cannot be changed after it is created — every driver assignment made since assumes it.', 'لا يمكن تغيير عمل الشاحنة بعد إنشائها — كل إسناد سائق تمّ منذ ذلك الحين مبنيّ عليه.');
reg('Take truck out of service', 'إخراج الشاحنة من الخدمة');
reg('why is it being disabled?', 'ما سبب الإخراج من الخدمة؟');
reg('Disable reason (required)…', 'سبب الإخراج من الخدمة (إلزامي)…');
reg('View the trucks of', 'عرض شاحنات');
reg('View the drivers of', 'عرض سائقي');
reg('Delivery Drivers', 'سائقو التوصيل');
reg('Add Delivery Driver', 'إضافة سائق توصيل');
reg('Edit Delivery Driver', 'تعديل سائق توصيل');
reg('Save Driver', 'حفظ السائق');
reg('Driver full name', 'الاسم الكامل للسائق');
reg('Date of Birth', 'تاريخ الميلاد');
reg('Used as the login when access is granted', 'يُستخدم اسمَ دخول عند منح الصلاحية');
reg('Personal details, national ID and BOTH sides of the driving licence. A delivery truck can be assigned now or later.', 'المعلومات الشخصية والرقم الوطني و**وجهَا** رخصة القيادة. يمكن إسناد شاحنة توصيل الآن أو لاحقاً.');
reg('Drivers who carry sold goods from a warehouse to the buyer. They drive DELIVERY trucks only — collection rounds are worked by collectors from the mobile app.', 'سائقون ينقلون البضاعة المباعة من المستودع إلى المشتري. يقودون شاحنات التوصيل فقط — أما جولات الجمع فيعمل عليها سائقو الجمع من التطبيق.');
reg('Drivers who carry sold goods from your warehouse to the buyer. They are recruited by the administrator; you assign them a delivery truck.', 'سائقون ينقلون البضاعة المباعة من مستودعك إلى المشتري. يوظّفهم الأدمن، وأنت تُسند لهم شاحنة توصيل.');
reg('No delivery drivers found.', 'لا يوجد سائقو توصيل.');
reg('Search by name, phone, national ID…', 'ابحث بالاسم أو الهاتف أو الرقم الوطني…');
reg('Licence Number', 'رقم الرخصة');
reg('Licence Expiry', 'تاريخ انتهاء الرخصة');
reg('Licence — Front', 'الرخصة — الوجه الأمامي');
reg('Licence — Back', 'الرخصة — الوجه الخلفي');
reg('Leave empty to keep the stored image.', 'اتركه فارغاً للإبقاء على الصورة المحفوظة.');
reg('Both sides of the driving licence are required.', 'وجها رخصة القيادة إلزاميان.');
reg('Driver name is required.', 'اسم السائق مطلوب.');
reg('Phone is required.', 'رقم الهاتف مطلوب.');
reg('National ID is required.', 'الرقم الوطني مطلوب.');
reg('Warehouse is required — deliveries start at one.', 'المستودع مطلوب — التوصيل يبدأ من مستودع.');
reg('Delivery driver created successfully!', 'تمت إضافة سائق التوصيل بنجاح!');
reg('Delivery driver updated successfully!', 'تم تحديث سائق التوصيل بنجاح!');
reg('Create Login', 'إنشاء حساب دخول');
reg('Login created for the driver.', 'تم إنشاء حساب دخول للسائق.');
reg('Print PDF', 'طباعة PDF');
reg('Assign a truck', 'إسناد شاحنة');
reg('Assign a delivery truck to', 'إسناد شاحنة توصيل إلى');
reg('Assigned to a truck', 'مرتبط بشاحنة');
reg('No truck yet', 'بلا شاحنة بعد');
reg('Remove truck', 'إزالة الشاحنة');
reg('Choose a delivery truck', 'اختر شاحنة توصيل');
reg('Choose a delivery truck…', 'اختر شاحنة توصيل…');
reg('Select a delivery truck…', 'اختر شاحنة توصيل…');
reg('Please select a delivery truck.', 'يرجى اختيار شاحنة توصيل.');
reg('No free delivery truck matches.', 'لا توجد شاحنة توصيل متاحة مطابقة.');
reg('No free delivery truck in that warehouse right now.', 'لا توجد شاحنة توصيل متاحة في ذلك المستودع حالياً.');
reg('No free delivery truck in your warehouse right now.', 'لا توجد شاحنة توصيل متاحة في مستودعك حالياً.');
reg('No free delivery truck in this warehouse right now — you can assign one later.', 'لا توجد شاحنة توصيل متاحة في هذا المستودع حالياً — يمكنك الإسناد لاحقاً.');
reg('Choose the warehouse first — a driver loads from one site, so only its trucks are offered.', 'اختر المستودع أولاً — السائق يحمّل من موقع واحد، فتُعرض شاحنات ذلك المستودع فقط.');
reg('Driver assigned to the truck.', 'تم إسناد السائق إلى الشاحنة.');
reg('Truck assignment removed.', 'تمت إزالة إسناد الشاحنة.');
reg('Driver moved to the new warehouse.', 'تم نقل السائق إلى المستودع الجديد.');
reg('Clear', 'مسح');
reg('Block', 'حظر');
reg('Unblock', 'رفع الحظر');
reg('Block this driver', 'حظر هذا السائق');
reg('Block reason (required)…', 'سبب الحظر (إلزامي)…');
reg('Give a reason for the block — it is what the driver is told.', 'اكتب سبب الحظر — فهو ما سيُبلَّغ به السائق.');
reg('their truck is taken back and their login is disabled.', 'تُسحب شاحنته ويُعطَّل حساب دخوله.');
reg('Driver blocked.', 'تم حظر السائق.');
reg('Driver unblocked.', 'تم رفع الحظر عن السائق.');
reg('My Truck', 'سيارتي');
reg('My Trips', 'رحلاتي');
reg('Click the map to set the warehouse location', 'انقر على الخريطة لتحديد موقع المستودع');
// ── Delivery-driver dashboard: redesigned home, trips tabs, warehouse ──
reg('To deliver', 'للتوصيل');
reg('Delivered', 'تم التوصيل');
reg('Trips this month', 'رحلات هذا الشهر');
reg('Delivered this month', 'سُلّمت هذا الشهر');
reg('The trips still to run, and the ones you have already delivered.', 'الرحلات التي عليك تنفيذها، والرحلات التي سلّمتها.');
reg('You have no delivery trips to run right now.', 'لا توجد لديك رحلات توصيل لتنفيذها الآن.');
reg('You have not delivered any trips yet.', 'لم تُسلّم أي رحلات بعد.');
reg('Delivered at', 'سُلّمت في');
reg('Stations', 'المحطات');
reg('Warehouses & quantities', 'المستودعات والكميات');
reg('Collected', 'جُمِعت');
// My Warehouse screen
reg('The warehouse you deliver from. Set by your warehouse manager.', 'المستودع الذي توصّل منه. يحدّده مدير مستودعك.');
reg('No warehouse yet', 'لا يوجد مستودع بعد');
reg('You have not been assigned to a warehouse yet. You will see it here as soon as your manager sets it.', 'لم يتم تعيينك لمستودع بعد. سيظهر هنا فور أن يحدّده مديرك.');
reg('Open in Maps', 'افتح في الخرائط');
// Settings + system info
reg('Customize your dashboard appearance and preferences.', 'خصّص مظهر لوحتك وتفضيلاتك.');
reg('Privacy & Security', 'الخصوصية والأمان');
reg('Delivery Driver', 'سائق توصيل');
// ── Delivery-trip dashboard (driver's next-stop screen) ──
reg('My Delivery Trips', 'رحلات التوصيل الخاصة بي');
reg('Drive to the next station shown, confirm the pickup, and the following one opens.', 'اذهب إلى المحطة التالية المعروضة، أكّد الاستلام، ثم تُفتح التي تليها.');
reg('You have no delivery trips right now.', 'لا توجد لديك رحلات توصيل حالياً.');
reg('Buyer', 'المشتري');
reg('Progress', 'التقدّم');
reg('stations collected', 'محطات مُستلمة');
reg('Next station', 'المحطة التالية');
reg('Goods', 'البضاعة');
reg('Open in Google Maps', 'افتح في خرائط غوغل');
reg('Confirm Pickup', 'تأكيد الاستلام');
reg('Confirming…', 'جارٍ التأكيد…');
reg('Deliver to the buyer', 'التسليم إلى المشتري');
reg('Confirm Delivery', 'تأكيد التسليم');
// ── Admin split-order reassignment ──
reg('Reassign This Part (Split Order)', 'إعادة توزيع هذا الجزء (طلبية مقسّمة)');
reg('Part', 'الجزء');
reg('Move this part to another warehouse that holds the quantity. A split may be re-routed, never grown — its current and sibling warehouses are excluded.', 'انقل هذا الجزء إلى مستودع آخر يملك الكمية. يمكن إعادة توجيه التقسيم لا تكبيره — المستودع الحالي ومستودعات الأشقّاء مستثناة.');
reg('— choose —', '— اختر —');
reg('Reassign', 'إعادة التوزيع');
reg('Reassigning…', 'جارٍ إعادة التوزيع…');
reg('No other eligible warehouse is available for this part.', 'لا يوجد مستودع آخر مؤهّل لهذا الجزء.');
reg('Choose a warehouse to move this part to.', 'اختر مستودعاً لنقل هذا الجزء إليه.');
reg('Order part reassigned.', 'تمت إعادة توزيع جزء الطلبية.');
reg('My Driving Licence', 'رخصة القيادة');
reg('You deliver sold goods from your warehouse to the buyer.', 'أنت تنقل البضاعة المباعة من مستودعك إلى المشتري.');
reg('The vehicle assigned to you. Assignments are made by your warehouse manager.', 'المركبة المسندة إليك. الإسناد يتم من مدير مستودعك.');
reg('The warehouse manager will assign you one.', 'سيقوم مدير المستودع بإسناد واحدة لك.');
reg('Your warehouse manager has not assigned you a delivery truck yet. You will see it here as soon as they do.', 'لم يُسند إليك مدير المستودع شاحنة توصيل بعد. ستظهر هنا فور إسنادها.');
reg('This account is not linked to a delivery driver record.', 'هذا الحساب غير مرتبط بسجل سائق توصيل.');
reg('Security', 'الأمان');
reg('Theme', 'المظهر');
reg('Switch to Dark', 'التبديل إلى الداكن');
reg('Switch to Light', 'التبديل إلى الفاتح');
reg('No sessions found.', 'لا توجد جلسات.');
reg('Profile updated successfully.', 'تم تحديث الملف الشخصي بنجاح.');
reg('Current password is required', 'كلمة المرور الحالية مطلوبة');
reg('Passwords do not match', 'كلمتا المرور غير متطابقتين');
reg('Grade', 'الحالة');
reg('No grade', 'بلا حالة');
reg('Damaged?', 'تالفة؟');
reg('Damaged Grade', 'الحالة التالفة');
reg('Damaged — written off', 'تالفة — تُشطب');
reg('Usable — goes to storage', 'صالحة — تذهب للتخزين');
reg('Select the grade…', 'اختر الحالة…');
reg('Select a material…', 'اختر مادة…');
reg('This material has no grades — quantity only.', 'هذه المادة بلا حالات — أدخل الكمية فقط.');
reg('This material has no grades — enter the damaged quantity.', 'هذه المادة بلا حالات — أدخل الكمية التالفة.');
reg('Please select the grade for this material.', 'يرجى اختيار حالة هذه المادة.');
reg('Please select the grade that was damaged.', 'يرجى اختيار الحالة التي تلفت.');
reg('Free in this grade', 'المتاح في هذه الحالة');
reg('Free now', 'المتاح الآن');
reg('Only what is free in this grade can be reported — the rest is promised to open orders.', 'لا يمكن الإبلاغ إلا عن المتاح في هذه الحالة — الباقي محجوز لطلبيات قائمة.');
reg('Report material already in storage that was damaged and must be written off. The warehouse manager must approve before any stock is deducted.', 'أبلغ عن مواد مخزَّنة تلفت ويجب شطبها. لا يُخصم أي مخزون قبل موافقة مدير المستودع.');
reg('Stock Reports', 'تقارير المخزون');
reg('No pending stock reports.', 'لا توجد تقارير مخزون قيد الانتظار.');
reg('Material reported after being stored. Approving a write-off removes the quantity from the warehouse; approving a downgrade only moves it to a lower grade — the total does not change.', 'مواد أُبلغ عنها بعد تخزينها. الموافقة على الشطب تُخرج الكمية من المستودع.');
reg('Items', 'العناصر');
reg('Scope', 'النطاق');
reg('Global', 'عام');
reg('Global (all warehouses)', 'عام (كل المستودعات)');
reg('Specific warehouses', 'مستودعات محددة');
reg('Appears for every warehouse.', 'يظهر لكل المستودعات.');
reg('Pick one or more warehouses below.', 'اختر مستودعاً أو أكثر أدناه.');
reg('Convert to global', 'التحويل إلى عام');
reg('Makes the shift appear for every warehouse. This cannot be undone.', 'يجعل الوردية تظهر لكل المستودعات. لا يمكن التراجع عن هذا.');
reg('Selecting every warehouse makes the shift global.', 'اختيار كل المستودعات يجعل الوردية عامة.');
reg('A global shift cannot be converted to a specific one.', 'لا يمكن تحويل وردية عامة إلى وردية خاصة.');
reg('Choose at least one warehouse, or make the shift global.', 'اختر مستودعاً واحداً على الأقل، أو اجعل الوردية عامة.');
reg('warehouse(s)', 'مستودع/مستودعات');
reg('Invalid shift. Please select a valid shift for your warehouse.', 'وردية غير صالحة. يرجى اختيار وردية صحيحة لمستودعك.');
reg('Your shift has been updated', 'تم تحديث ورديتك');
reg('Requests submitted by your drivers in the app, newest first. Start processing, then approve with a free truck of the requested shift — or reject with a reason.', 'طلبات أرسلها سائقوك من التطبيق، الأحدث أولاً. ابدأ المعالجة ثم وافق بشاحنة متاحة في الوردية المطلوبة — أو ارفض مع ذكر السبب.');
reg('Request approved — the driver was notified.', 'تمت الموافقة على الطلب — وأُشعِر السائق.');
reg('Request moved to processing.', 'تم نقل الطلب إلى قيد المعالجة.');
reg('Request declined. Notification and email sent.', 'تم رفض الطلب. وأُرسِل الإشعار والبريد.');
reg('Role Updated', 'تم تحديث الدور');
reg('Your role has been changed to', 'تم تغيير دورك إلى');
reg('Invalid role.', 'دور غير صالح.');
reg('This position is specialized — only the role designated for the job can be assigned.', 'هذه الوظيفة متخصصة — لا يمكن إسناد غير الدور المخصص لها.');
reg('Employee information has been updated successfully.', 'تم تحديث معلومات الموظف بنجاح.');
reg('Employee not found.', 'الموظف غير موجود.');
reg('Employee archived.', 'تمت أرشفة الموظف.');
reg('Employee restored. Notification and email sent.', 'تمت استعادة الموظف. وأُرسِل الإشعار والبريد.');
reg('Archive this employee? Their role and warehouse will be unassigned.', 'أرشفة هذا الموظف؟ سيُلغى دوره وإسناده للمستودع.');
reg('Failed to archive employee:', 'تعذّرت أرشفة الموظف:');
reg('Failed to reject employee:', 'تعذّر رفض الموظف:');
reg('This employee was not found or is already assigned.', 'هذا الموظف غير موجود أو مُسنَد بالفعل.');
reg('Warehouse not found.', 'المستودع غير موجود.');
reg('You do not have permission to perform this action.', 'لا تملك صلاحية القيام بهذا الإجراء.');
reg('Failed to save. Please try again.', 'تعذّر الحفظ. يرجى المحاولة مرة أخرى.');
reg('Update failed:', 'فشل التحديث:');
reg('Update failed.', 'فشل التحديث.');
reg('Stage History:', 'سجل المراحل:');
reg('Invite sent at:', 'أُرسلت الدعوة في:');
reg('✓ Fully accepted at the final stage — the pipeline is closed. Approve/Reject/Advance are no longer available.', '✓ مقبول نهائياً في المرحلة الأخيرة — أُغلق المسار. لم تعد خيارات القبول/الرفض/التقديم متاحة.');
reg('Suggest a Material', 'اقتراح مادة');
reg('Material Name', 'اسم المادة');
reg('Material name is required.', 'اسم المادة مطلوب.');
reg('Unit of Measure', 'وحدة القياس');
reg('Why this material?', 'لماذا هذه المادة؟');
reg('Where does it come from, who buys it, why is it worth adding?', 'من أين تأتي، ومن يشتريها، ولماذا تستحق الإضافة؟');
reg('Materials are created in the backend together with their prices. Describe the material here and the backend administrator will review it.', 'المواد تُنشأ في الباك ايند مع أسعارها. صِف المادة هنا وسيراجعها أدمن الباك ايند.');
reg('Send for Review', 'إرسال للمراجعة');
reg('Sending…', 'جارٍ الإرسال…');
reg('Saved!', 'تم الحفظ!');
reg('Suggestion sent for review.', 'أُرسل الاقتراح للمراجعة.');
reg('Could not save the suggestion. Please check the fields.', 'تعذّر حفظ الاقتراح. يرجى التحقق من الحقول.');
reg('Could not reach the backend. The suggestion was saved — try sending it again.', 'تعذّر الوصول إلى الباك ايند. حُفظ الاقتراح — أعد المحاولة.');
reg('Invalid percentages: the first threshold must be lower than the second (both between 0 and 100).', 'نسب غير صالحة: يجب أن يكون الحد الأول أقل من الثاني (كلاهما بين 0 و100).');
reg('Cannot access camera. Please allow camera permission.', 'تعذّر الوصول إلى الكاميرا. يرجى السماح بإذن الكاميرا.');
reg('Cannot read the file as an image.', 'تعذّرت قراءة الملف كصورة.');
reg('Invalid image data.', 'بيانات صورة غير صالحة.');
reg('Image library not installed on the server.', 'مكتبة الصور غير مثبّتة على الخادم.');
reg('QR library not loaded yet. Please try again.', 'لم تُحمَّل مكتبة الباركود بعد. يرجى المحاولة مرة أخرى.');
reg('QR/Barcode library not installed on the server.', 'مكتبة QR/الباركود غير مثبّتة على الخادم.');
reg('No QR code or barcode found in the image.', 'لم يُعثر على رمز QR أو باركود في الصورة.');
reg('Scan failed.', 'فشل المسح.');
reg('Network error. Please check your connection.', 'خطأ في الشبكة. يرجى التحقق من اتصالك.');
reg('Shipment not found. It may not exist or be reserved by a colleague.', 'الشحنة غير موجودة. قد تكون غير موجودة أو محجوزة من زميل.');
reg('This shipment is currently reserved by %s.', 'هذه الشحنة محجوزة حالياً من %s.');
reg('Toggle dark mode', 'تبديل الوضع الداكن');

// ─── The driver's own page: truck-holding history and its release reasons ───
reg('Collection Drivers', 'سائقو الجمع');
reg('Driver Information', 'معلومات السائق');
reg('Everything recorded about this driver, and every action that can be taken on them.', 'كل ما هو مسجَّل عن هذا السائق، وكل إجراء يمكن اتخاذه بشأنه.');
reg('This driver is no longer available.', 'هذا السائق لم يعد متاحاً.');
reg('This driver has not held a truck yet.', 'لم يستلم هذا السائق أي شاحنة بعد.');
reg('Trucks Held', 'الشاحنات المستلَمة');
reg('Held From', 'مستلَمة من');
reg('Held Until', 'مستلَمة حتى');
reg('Days Held', 'أيام الاستلام');
reg('Currently Held', 'مستلَمة حالياً');
reg('Released Because', 'سبب التسليم');
reg('Unassigned by an administrator or manager', 'أُلغي الإسناد من الأدمن أو المدير');
reg('Truck moved to another warehouse', 'نُقلت الشاحنة إلى مستودع آخر');
reg('Given to another driver', 'أُسندت إلى سائق آخر');
reg('Driver blocked', 'حُظر السائق');
reg('Driver record removed or deactivated', 'حُذف سجل السائق أو عُطِّل');

reg('Could not generate the PDF file.', 'تعذّر إنشاء ملف PDF.');
reg('Assign Manager', 'إسناد مدير');
reg('This warehouse has no manager yet. Only managers who are not running another warehouse are listed.', 'لا يوجد مدير لهذا المستودع بعد. تُعرض فقط الإدارات غير المسؤولة عن مستودع آخر.');
reg('Show', 'عرض');

// ─── Adding an employee from the admin screen ───
reg('Receives incoming shipments and checks them in.', 'يستقبل الشحنات الواردة ويسجّل دخولها.');
reg('Grades processed material and moves it to storage.', 'يصنّف المواد المعالَجة وينقلها إلى التخزين.');
reg('Prepares orders, deducts stock and invoices them.', 'يجهّز الطلبيات ويخصم المخزون ويصدر الفواتير.');
reg('Runs one warehouse. A site has one manager, and a manager has one site.', 'يدير مستودعاً واحداً. للموقع مدير واحد، وللمدير موقع واحد.');
reg('Employee full name', 'الاسم الكامل للموظف');
reg('name@example.com', 'name@example.com');
reg('09XXXXXXXX', '09XXXXXXXX');
reg('Used as the login and for the set-password link.', 'يُستخدم اسمَ دخول ولإرسال رابط تعيين كلمة المرور.');
reg('Unique across everyone in the system — staff, drivers and applicants alike.', 'فريد على مستوى كل من في النظام — الموظفون والسائقون والمتقدّمون سواء.');
reg('The employee sets their own password from a link sent to this email — nobody, including you, ever sees it.', 'يعيّن الموظف كلمة مروره بنفسه عبر رابط يُرسل إلى هذا البريد — ولا يراها أحد، ولا أنت.');
reg('Only warehouses without a manager are listed — a site has one manager, and a manager runs one site.', 'تُعرض فقط المستودعات بلا مدير — للموقع مدير واحد، والمدير يدير موقعاً واحداً.');
reg('Every active warehouse already has a manager. Change one from its own screen instead.', 'كل مستودع نشط له مدير بالفعل. غيّر المدير من شاشة المستودع نفسه.');
reg('Choose the warehouse this employee works in.', 'اختر المستودع الذي يعمل فيه هذا الموظف.');
reg('Employee added. A set-password link was emailed to them.', 'تمت إضافة الموظف. وأُرسل إليه رابط تعيين كلمة المرور.');
reg('This warehouse already has a manager:', 'هذا المستودع له مدير بالفعل:');
reg('This warehouse is closing or closed and takes no new staff.', 'هذا المستودع قيد الإغلاق أو مغلق ولا يستقبل موظفين جدداً.');
reg('This national ID or email is already registered.', 'هذا الرقم الوطني أو البريد مسجَّل بالفعل.');
reg('This material has no price yet — it will be priced later.', 'لا يوجد سعر لهذه المادة بعد — سيتم تسعيرها لاحقاً.');

// ─── Sorting: what is left to enter, and what was lost ───
reg('Lost', 'الضائع');
reg('Remaining for this material:', 'المتبقّي لهذه المادة:');
reg('Only %s left to enter for this material.', 'المتبقّي لهذه المادة %s فقط.');

// ── Shared message dialog + branded loading screen (2026-08-04) ──────────
// Added with the in-page dialog that replaced `alert()`. The browser's own box
// could not be translated at all, so these strings had no Arabic to give.
reg('Something went wrong', 'حدث خطأ ما');
reg('Already accepted elsewhere', 'مقبول مسبقاً في طلب آخر');
reg('This applicant already has an accepted application for:',
    'لهذا المتقدّم طلب مقبول مسبقاً في:');
// Caption of a truck-problem photo opened in the in-page viewer.
reg('Truck problem', 'مشكلة شاحنة');

// ── Titles for the in-page confirm dialog ─────────────────────────────────
// `window.confirm()` had no title to translate — the browser supplied its own
// chrome. Naming the act is the point of replacing it, so each one is a string
// that reaches the screen and therefore needs an Arabic entry.
reg('Sign out', 'تسجيل الخروج');
reg('Re-open warehouse', 'إعادة فتح المستودع');
reg('Close warehouse', 'إغلاق المستودع');
reg('Stop warehouse permanently', 'إيقاف المستودع نهائياً');
reg('Delete zone', 'حذف المنطقة');
reg('Delete stage', 'حذف المرحلة');
reg('Delete shift', 'حذف الوردية');
reg('Re-open request', 'إعادة فتح الطلب');
reg('Stop waiting', 'التوقف عن الانتظار');
reg('Archive employee', 'أرشفة الموظف');
reg('Delete account permanently', 'حذف الحساب نهائياً');
// Used by the shared dialog helper when a caller gives no title of its own.
reg('Something went wrong', 'حدث خطأ');
reg('Done', 'تم');
reg('OK', 'حسناً');
