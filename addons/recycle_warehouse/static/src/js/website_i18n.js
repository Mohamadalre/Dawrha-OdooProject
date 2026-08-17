/* ── Dawrha Website Translation Engine ─────────────────────────────────
   Shares the localStorage key 'recycle_wms_lang' with the admin dashboard
   so language choice persists across the whole application.
   ==================================================================== */
(function () {
    'use strict';

    // Load-once guard: the file is included both directly (<script src>)
    // and via the web.assets_frontend bundle — run a single instance.
    if (window.__dwI18nLoaded) { return; }
    window.__dwI18nLoaded = true;

    var LANG_KEY = 'recycle_wms_lang';

    var T = {
        en: {},
        ar: {},
    };

    // ──────────── PUBLIC API ────────────

    function getLang() {
        var v = localStorage.getItem(LANG_KEY);
        return v === 'ar' ? 'ar' : 'en';
    }

    function setLang(lang) {
        lang = lang === 'ar' ? 'ar' : 'en';
        localStorage.setItem(LANG_KEY, lang);
        apply();
        try {
            window.dispatchEvent(new CustomEvent('dw-lang-change', { detail: { lang: lang } }));
        } catch (_) {}
    }

    function tr(key) {
        var lang = getLang();
        return (T[lang] && T[lang][key]) || key;
    }

    function apply() {
        try {
            var lang = getLang();
            var isAr = lang === 'ar';
            var root = document.documentElement;

            root.setAttribute('dir', isAr ? 'rtl' : 'ltr');
            root.setAttribute('lang', isAr ? 'ar' : 'en');

            // Translate every element with data-i18n
            var els = document.querySelectorAll('[data-i18n]');
            for (var i = 0; i < els.length; i++) {
                var el = els[i];
                var key = el.getAttribute('data-i18n');
                if (el.children.length === 0) {
                    el.textContent = tr(key);
                } else {
                    var walker = document.createTreeWalker(el, 4, null, false);
                    var node, first = true;
                    while (node = walker.nextNode()) {
                        if (first) { node.textContent = tr(key); first = false; }
                        else { node.textContent = ''; }
                    }
                }
            }

            // Second pass: translate any visible text inside known areas
            // that matches known keys (handles text without data-i18n attr)
            var formAreas = document.querySelectorAll('.dw-nav, .dw-links, .dw-nav-drawer, .dw-modal, .dw-card, .dw-grid, .dw-detail-card, .dw-breadcrumb, .dw-applications-table, .dw-manager-jobs');
            for (var a = 0; a < formAreas.length; a++) {
                var walker = document.createTreeWalker(formAreas[a], 4, null, false);
                var node;
                while (node = walker.nextNode()) {
                    var tx = (node.textContent || '').trim();
                    if (tx.length < 2) continue;
                    var txl = tr(tx);
                    if (txl !== tx) node.textContent = txl;
                }
            }

            // Translate input placeholders
            var plHolders = document.querySelectorAll('input[placeholder]');
            for (var ph = 0; ph < plHolders.length; ph++) {
                var inp = plHolders[ph];
                var pk = inp.getAttribute('placeholder');
                var pt = tr(pk);
                if (pt !== pk) inp.setAttribute('placeholder', pt);
            }

            // Keep every hidden language field in sync with the chosen language,
            // so server-side form handlers render their messages (e.g. the
            // National-ID errors on the complete-profile page) in that language.
            var langInputs = document.querySelectorAll('.dw_lang_input');
            for (var li = 0; li < langInputs.length; li++) {
                langInputs[li].value = lang;
            }

            // Translate compound elements that have data-i18n on a parent
            // with mixed text + child elements (hero, about, contact titles).
            // Replaces text across all descendant nodes so text inside child
            // elements (e.g. <span class="grad">) is also translated.
            var specials = document.querySelectorAll('.dw-i18n-wrap');
            for (var k = 0; k < specials.length; k++) {
                var sp = specials[k];
                var spKey = sp.getAttribute('data-i18n');
                if (!spKey) continue;
                var spText = tr(spKey);
                var walker = document.createTreeWalker(sp, 4, null, false);
                var node;
                var first = true;
                while (node = walker.nextNode()) {
                    if (first) {
                        node.textContent = spText;
                        first = false;
                    } else {
                        node.textContent = '';
                    }
                }
            }

            // Update language toggle buttons on the website
            var btns = document.querySelectorAll('.dw-lang-btn');
            for (var j = 0; j < btns.length; j++) {
                var btn = btns[j];
                if (btn.getAttribute('data-lang') === lang) {
                    btn.classList.add('dw-lang-active');
                } else {
                    btn.classList.remove('dw-lang-active');
                }
            }

            // Theme button tooltip
            var themeBtn = document.getElementById('dw-theme-btn');
            if (themeBtn) themeBtn.title = tr('Toggle dark mode');

            // Tooltips: translate any title attribute that matches a key
            var titled = document.querySelectorAll('[title]');
            for (var tt = 0; tt < titled.length; tt++) {
                var tv = titled[tt].getAttribute('title');
                var tvt = tr(tv);
                if (tvt !== tv) titled[tt].setAttribute('title', tvt);
            }

            // Browser-tab title, segment-wise ("Login | Dawrha")
            var parts = document.title.split('|');
            var tChanged = false;
            for (var pp = 0; pp < parts.length; pp++) {
                var seg = parts[pp].trim();
                var tseg = tr(seg);
                if (tseg !== seg) { parts[pp] = tseg; tChanged = true; }
                else { parts[pp] = seg; }
            }
            if (tChanged) document.title = parts.join(' | ');
        } catch (e) {
            if (console && console.warn) console.warn('dwTr apply error:', e);
        }
    }

    // ──────────── REGISTER TRANSLATIONS ────────────

    function _(en, ar) {
        T.en[en] = en;
        T.ar[en] = ar;
    }

    // ── Navbar ──
    _('Home', 'الرئيسية');
    _('About', 'حول');
    _('Jobs', 'الوظائف');
    _('My Applications', 'طلباتي');
    _('My Jobs', 'وظائفي');
    _('Contact', 'اتصل بنا');
    _('Account', 'الحساب');
    _('Logout', 'تسجيل الخروج');
    _('Sign in', 'تسجيل الدخول');
    _('Register', 'التسجيل');
    _('Toggle dark mode', 'تبديل الوضع الليلي');
    _('♻ Dawrha', '♻ دورها');
    _('🏠 Home', '🏠 الرئيسية');
    _('ℹ️ About', 'ℹ️ حول');
    _('💼 Jobs', '💼 الوظائف');
    _('📋 My Applications', '📋 طلباتي');
    _('💼 My Jobs', '💼 وظائفي');
    _('📞 Contact', '📞 اتصل بنا');
    _('👤 Account', '👤 الحساب');
    _('🚪 Logout', '🚪 تسجيل الخروج');
    _('🔑 Sign in', '🔑 تسجيل الدخول');
    _('✍️ Register', '✍️ التسجيل');

    // ── Footer ──
    _('About', 'حول');
    _('Jobs', 'الوظائف');
    _('Contact', 'اتصل بنا');
    _('© 2026 Dawrha — Smart Recycling Platform', '© 2026 دورها — منصة إعادة التدوير الذكية');

    // ── Home page ──
    _('🌱 Sustainability-Driven Platform', '🌱 منصة مستدامة');
    _('Dawrha — Build a Smarter Future Through Recycling', 'دورها — بناء مستقبل أكثر ذكاءً من خلال إعادة التدوير');
    _('Dawrha is a modern platform that connects individuals, warehouses, and recycling operations to efficiently manage waste collection, sorting, and sustainable resource recovery.', 'دورها هي منصة حديثة تربط الأفراد والمستودعات وعمليات إعادة التدوير لإدارة جمع النفايات وفرزها واستعادة الموارد المستدامة بكفاءة.');
    _('💼 View Open Positions', '💼 عرض الوظائف الشاغرة');
    _('Learn More', 'معرفة المزيد');
    _('Dawrha recycling warehouse', 'مستودع إعادة تدوير دورها');
    _('Warehouses', 'المستودعات');
    _('Employees', 'الموظفون');
    _('Orders', 'الطلبات');
    _('Tons Recycled', 'أطنان مُعاد تدويرها');
    _('Monthly Growth', 'النمو الشهري');
    _('How the Platform Works', 'كيف تعمل المنصة');
    _('Four simple steps from collection to value creation.', 'أربع خطوات بسيطة من التجميع إلى خلق القيمة.');
    _('1. Collect Recyclable Materials', '١. جمع المواد القابلة للتدوير');
    _('Gather and register incoming recyclable materials at the receiving warehouse zone.', 'جمع وتسجيل المواد القابلة للتدوير الواردة في منطقة الاستقبال بالمستودع.');
    _('2. Sort & Manage Operations', '٢. الفرز وإدارة العمليات');
    _('Sort materials by type and condition across dedicated warehouse zones with smart tracking.', 'فرز المواد حسب النوع والحالة عبر مناطق المستودعات المخصصة بتتبع ذكي.');
    _('3. Assign Workers & Track Performance', '٣. تعيين العمال وتتبع الأداء');
    _('Coordinate employees, manage shifts, and monitor attendance and performance in real time.', 'تنسيق الموظفين وإدارة الورديات ومراقبة الحضور والأداء في الوقت الفعلي.');
    _('4. Recycle & Generate Value', '٤. إعادة التدوير وتوليد القيمة');
    _('Process sorted materials into valuable resources, generate orders, and deliver to customers.', 'معالجة المواد المفروزة إلى موارد قيّمة وإنشاء الطلبات وتسليمها للعملاء.');
    _('Why Dawrha?', 'لماذا دورها؟');
    _("We're building the infrastructure for a cleaner, smarter planet.", 'نبني البنية التحتية لكوكب أنظف وأكثر ذكاءً.');
    _('Reduce Environmental Pollution', 'تقليل التلوث البيئي');
    _('Every ton recycled through Dawrha reduces landfill waste and carbon emissions.', 'كل طن يُعاد تدويره عبر دورها يقلل من نفايات المكبات وانبعاثات الكربون.');
    _('Smart Warehouse Management', 'إدارة المستودعات الذكية');
    _('Digitize your entire warehouse workflow — from receiving to stock to orders — in one system.', 'رقمنة سير عمل المستودع بالكامل — من الاستقبال إلى المخزون إلى الطلبات — في نظام واحد.');
    _('Real-Time Material Tracking', 'تتبع المواد في الوقت الفعلي');
    _("Know exactly what's in your warehouse at any moment with live inventory and shipment tracking.", 'اعرف بالضبط ما في مستودعك في أي لحظة عبر تتبع حي للمخزون والشحنات.');
    _('Efficient Workforce Coordination', 'تنسيق فعال للقوى العاملة');
    _('Manage all your employees, shifts, and attendance seamlessly across multiple warehouses.', 'إدارة جميع موظفيك ووردياتهم وحضورهم بسلاسة عبر مستودعات متعددة.');
    _('Ready to Join Us?', 'مستعد للانضمام إلينا؟');
    _('Explore our open positions and start your journey with Dawrha.', 'استكشف وظائفنا الشاغرة وابدأ رحلتك مع دورها.');
    _('💼 Browse Open Positions', '💼 تصفح الوظائف الشاغرة');

    // ── About page ──
    _('🎯 Our Story & Mission', '🎯 قصتنا ورسالتنا');
    _('About Dawrha', 'حول دورها');
    _('Dawrha is a sustainability-driven platform designed to revolutionize the recycling industry by digitizing waste collection, warehouse management, and workforce coordination.', 'دورها هي منصة مدفوعة بالاستدامة مصممة لإحداث ثورة في صناعة إعادة التدوير من خلال رقمنة جمع النفايات وإدارة المستودعات وتنسيق القوى العاملة.');
    _('🌍 Our Vision', '🌍 رؤيتنا');
    _('A Cleaner, Smarter World', 'عالم أنظف وأكثر ذكاءً');
    _('To create a cleaner and more sustainable world by optimizing recycling processes through smart technology. We envision a future where waste is not a problem — it\'s a resource.', 'لخلق عالم أنظف وأكثر استدامة من خلال تحسين عمليات إعادة التدوير بالتكنولوجيا الذكية. نتصور مستقبلاً حيث النفايات ليست مشكلة — بل هي مورد.');
    _('🎯 Our Mission', '🎯 مهمتنا');
    _('Connecting the Recycling Ecosystem', 'ربط منظومة إعادة التدوير');
    _('To connect recycling warehouses, employees, and operations in a unified system that improves efficiency, transparency, and environmental impact — making sustainable business the norm.', 'لربط مستودعات إعادة التدوير والموظفين والعمليات في نظام موحد يحسن الكفاءة والشفافية والأثر البيئي — لجعل الأعمال المستدامة هي القاعدة.');
    _('What We Do', 'ماذا نفعل');
    _('Everything you need to run a modern, efficient recycling operation.', 'كل ما تحتاجه لإدارة عملية إعادة تدوير حديثة وفعالة.');
    _('Manage Recycling Warehouses', 'إدارة مستودعات إعادة التدوير');
    _('Track Recyclable Materials', 'تتبع المواد القابلة للتدوير');
    _('Improve Recycling Efficiency', 'تحسين كفاءة إعادة التدوير');
    _('Coordinate Warehouse Workforce', 'تنسيق قوى العمل في المستودعات');
    _('Real-Time Operations Tracking', 'تتبع العمليات في الوقت الفعلي');
    _('Drive Environmental Sustainability', 'دفع الاستدامة البيئية');
    _('📞 Get in Touch', '📞 تواصل معنا');

    // ── Jobs list ──
    _('Open Positions', 'الوظائف الشاغرة');
    _('Join our eco-friendly operations team and make a real impact.', 'انضم إلى فريق عملياتنا الصديق للبيئة واصنع تأثيراً حقيقياً.');
    _('There are no open positions at the moment. Please check back soon.', 'لا توجد وظائف شاغرة حالياً. يرجى التحقق لاحقاً.');
    _('🏭 Warehouse Management', '🏭 إدارة المستودعات');
    _('♻️ Recycling Operations', '♻️ عمليات إعادة التدوير');
    _('📥 Input Employee', '📥 موظف استقبال');
    _('♻️ Sorting Employee', '♻️ موظف فرز وتخزين');
    _('📤 Output Employee', '📤 موظف إخراج');
    _('View & Apply →', 'عرض والتقديم →');
    _('open role(s)', 'وظيفة (وظائف) شاغرة');
    _('Dawrha Facilities', 'مرافق دورها');

    // ── Job detail ──
    _('Home', 'الرئيسية');
    _('Jobs', 'الوظائف');
    _('♻️ Recycling Operations', '♻️ عمليات إعادة التدوير');
    _('Join our eco-friendly operations team and make a real impact in the sustainability sector.', 'انضم إلى فريق عملياتنا الصديق للبيئة واصنع تأثيراً حقيقياً في قطاع الاستدامة.');
    _('🔒 Administrators manage job postings and cannot apply to them.', '🔒 المدراء يديرون إعلانات الوظائف ولا يمكنهم التقديم عليها.');
    _('Apply Now →', 'تقدم الآن →');
    _('← Back to Jobs', '← العودة إلى الوظائف');

    // ── Apply form ──
    _('Apply', 'تقديم');
    _('Email', 'البريد الإلكتروني');
    _('Phone Number *', 'رقم الهاتف *');
    _('National ID *', 'الرقم الوطني *');
    _('Files (CV, certificates...) *', 'الملفات (السيرة الذاتية، الشهادات...) *');
    _('Description', 'الوصف');
    _('Profile Link (LinkedIn / GitHub)', 'رابط الملف الشخصي (LinkedIn / GitHub)');
    _('Submit Application →', 'إرسال الطلب →');
    _('Cancel', 'إلغاء');
    _('Already Registered', 'مسجل مسبقاً');
    _('OK, Got it', 'حسناً، فهمت');
    _('e.g. 0991234567', 'مثال: ٠٩٩١٢٣٤٥٦٧');
    _('Digits only (5–20)', 'أرقام فقط (٥–٢٠)');
    _('You can select multiple files. CV is required.', 'يمكنك اختيار عدة ملفات. السيرة الذاتية مطلوبة.');
    _('Tell us briefly about yourself...', 'أخبرنا بإيجاز عن نفسك...');
    _('Optional — must start with https://', 'اختياري — يجب أن يبدأ بـ https://');
    _('Applications are only accepted from email addresses ending with', 'يتم قبول الطلبات فقط من عناوين البريد الإلكتروني التي تنتهي بـ');
    _('Your account email', 'بريدك الإلكتروني');
    _('is not allowed.', 'غير مسموح.');
    _('This national ID is already registered by another applicant.', 'هذا الرقم الوطني مسجل بالفعل لمقدم طلب آخر.');

    // ── Account page ──
    _('My Account', 'حسابي');
    _('✅ Your password has been updated successfully.', '✅ تم تحديث كلمة المرور بنجاح.');
    _('🔒 The dashboard is available only to accepted employees.', '🔒 لوحة التحكم متاحة فقط للموظفين المقبولين.');
    _('Name', 'الاسم');
    _('Email', 'البريد الإلكتروني');
    _('Role', 'الدور');
    _('Warehouse', 'المستودع');
    _('Applications', 'الطلبات');
    _('📋 My Applications', '📋 طلباتي');
    _('💼 My Jobs', '💼 وظائفي');
    _('🖥️ Dashboard', '🖥️ لوحة التحكم');
    _('🔑 Set Password', '🔑 تعيين كلمة المرور');
    _('🚪 Logout', '🚪 تسجيل الخروج');
    _('🔐 Set Password', '🔐 تعيين كلمة المرور');
    _('Enter your current password, then choose a new one.', 'أدخل كلمة المرور الحالية، ثم اختر كلمة مرور جديدة.');
    _('Current Password', 'كلمة المرور الحالية');
    _('New Password', 'كلمة المرور الجديدة');
    _('Confirm New Password', 'تأكيد كلمة المرور الجديدة');
    _('Your current password', 'كلمة مرورك الحالية');
    _('Minimum 6 characters', '٦ أحرف على الأقل');
    _('Repeat the new password', 'أعد إدخال كلمة المرور الجديدة');
    _('Update Password', 'تحديث كلمة المرور');
    _('Cancel', 'إلغاء');
    _('✏️ Edit Profile', '✏️ تعديل الملف الشخصي');
    _('Not set', 'غير محدد');
    _('Member', 'عضو');
    _('Address', 'العنوان');
    _('City', 'المدينة');
    _('Profile Image', 'صورة الملف الشخصي');
    _('Save Changes', 'حفظ التغييرات');
    _('Street address', 'عنوان الشارع');

    // ── Complete-profile (before applying) page ──
    _('Complete Profile', 'إكمال الملف الشخصي');
    _('Please fill in your information before applying.', 'يرجى ملء معلوماتك قبل التقديم.');
    _('National ID *', 'الرقم الوطني *');
    _('Save &amp; Continue →', 'حفظ ومتابعة →');
    _('Save & Continue →', 'حفظ ومتابعة →');
    _('Optional. Upload a profile picture.', 'اختياري. حمّل صورة شخصية.');

    // ── Profile Completion page ──
    _('Complete Your Profile', 'إكمال ملفك الشخصي');
    _('Fill in your information to complete your profile and apply.', 'املأ معلوماتك لإكمال ملفك الشخصي والتقديم.');
    _('Contact Information', 'معلومات الاتصال');
    _('First Name', 'الاسم الأول');
    _('Last Name', 'اسم العائلة');
    _('Phone', 'رقم الهاتف');
    _('Country', 'الدولة');
    _('Employment Information', 'معلومات التوظيف');
    _('Job Position', 'الوظيفة المطلوبة');
    _('Select a position', 'اختر وظيفة');
    _('Company Name', 'اسم الشركة');
    _('Company Type', 'نوع الشركة');
    _('Select type', 'اختر النوع');
    _('Factory', 'مصنع');
    _('Organization', 'مؤسسة');
    _('Years of Experience', 'سنوات الخبرة');
    _('CV / Resume', 'السيرة الذاتية');
    _('Only PDF or Word files allowed', 'اسمح فقط ملفات PDF أو Word');
    _('Documents', 'المستندات');
    _('ID Expiry Date', 'تاريخ انتهاء الهوية');
    _('Additional Documents', 'مستندات إضافية');
    _('Optional. PDF or Word. You may select multiple files.', 'اختياري. PDF أو Word. يمكنك اختيار عدة ملفات.');
    _('Digits only (5–20)', 'أرقام فقط (٥–٢٠)');
    _('Save Profile', 'حفظ الملف الشخصي');
    _('Data saved successfully', 'تم حفظ البيانات بنجاح');
    _('Your application has been updated successfully', 'تم تحديث طلبك بنجاح');
    _('Please fill all required fields', 'الرجاء ملء جميع الحقول المطلوبة');
    _('Invalid email', 'البريد الإلكتروني غير صحيح');
    _('Phone must contain only numbers', 'رقم الهاتف يجب أن يحتوي على أرقام فقط');
    _('National ID must contain only digits (5 to 20 characters).', 'يجب أن يحتوي الرقم الوطني على أرقام فقط (٥ إلى ٢٠ رقماً).');
    _('This National ID is already in use by another person.', 'هذا الرقم الوطني مستخدم بالفعل من قبل شخص آخر.');
    _('Application already exists', 'طلب موجود مسبقاً');
    _('You have already applied for this position. Do you want to update your application?', 'أنت قد قدمت على هذه الوظيفة من قبل. هل تريد تحديث طلبك؟');
    _('Yes, update', 'نعم، حدّث');

    // ── Contact page ──
    _('Contact us', 'اتصل بنا');
    _('Get in touch with', 'تواصل مع');
    _('Questions about our eco-friendly warehouses, sorting facilities, or open positions? We\'d love to hear from you.', 'أسئلة حول مستودعاتنا الصديقة للبيئة أو مرافق الفرز أو الوظائف الشاغرة؟ يسعدنا سماع رأيك.');
    _('📧 Send Email', '📧 إرسال بريد إلكتروني');

    // ── Account page (profile) ──
    _('National ID', 'الرقم الوطني');
    _('(verified)', '(مؤكد)');
    _('Save', 'حفظ');
    _('✅ National ID saved successfully!', '✅ تم حفظ الرقم الوطني بنجاح!');
    _('← Go to My Account', '← العودة إلى حسابي');

    // ── My Applications page ──
    _('My Applications', 'طلباتي');
    _('✅ Your application has been submitted successfully!', '✅ تم تقديم طلبك بنجاح!');
    _('You have not applied for any job yet.', 'لم تتقدم لأي وظيفة بعد.');
    _('Browse open positions →', 'تصفح الوظائف الشاغرة →');
    _('Job', 'الوظيفة');
    _('National ID', 'الرقم الوطني');
    _('Current Stage', 'المرحلة الحالية');
    _('Stage Status', 'حالة المرحلة');
    _('Pending', 'قيد الانتظار');
    _('Approved', 'مقبول');
    _('Rejected', 'مرفوض');

    // ── Admin My Jobs page ──
    _('My Jobs', 'وظائفي');
    _('Job postings you created, with their publish status and number of applicants.', 'إعلانات الوظائف التي أنشأتها، مع حالة النشر وعدد المتقدمين.');
    _("You haven't created any job postings yet.", 'لم تنشئ أي إعلانات وظائف بعد.');
    _('Type', 'النوع');
    _('Status', 'الحالة');
    _('Applicants', 'المتقدمون');
    _('🏭 Manager', '🏭 مدير');
    _('♻️ Employee', '♻️ موظف');
    _('Published', 'منشور');
    _('Unpublished', 'غير منشور');

    // ── Account page (sidebar layout) ──
    _('Overview', 'نظرة عامة');
    _('Dashboard', 'لوحة التحكم');
    _('Edit Profile', 'تعديل الملف الشخصي');
    _('Set Password', 'تعيين كلمة المرور');
    _('Welcome back,', 'مرحباً بعودتك،');
    _('Track your applications, manage your personal information, and keep your account secure — all from one place.',
      'تابع طلباتك، وأدر معلوماتك الشخصية، وحافظ على أمان حسابك — كل ذلك من مكان واحد.');
    _('Member Since', 'عضو منذ');
    _('Account Details', 'بيانات الحساب');
    _('Recent Activity', 'آخر النشاطات');
    _('No activity yet.', 'لا يوجد نشاط بعد.');
    _('Administration', 'الإدارة العامة');

    // ── Jobs toolbar ──
    _('All', 'الكل');
    _('Search positions…', 'ابحث عن وظيفة…');
    _('No positions match your search.', 'لا توجد وظائف مطابقة لبحثك.');

    // ── Tooltips + browser-tab titles ──
    _('Dark / Light', 'داكن / فاتح');
    _('Login', 'تسجيل الدخول');
    _('Reset password', 'إعادة تعيين كلمة السر');
    _('My Website', 'دورها');
    _('Dawrha', 'دورها');
    _('My Account', 'حسابي');

    // ── Odoo auth server messages ──
    _('Wrong login/password', 'بيانات الدخول أو كلمة المرور غير صحيحة');
    _('Wrong login/password.', 'بيانات الدخول أو كلمة المرور غير صحيحة.');
    _('Repeat your password', 'أعد كتابة كلمة المرور');
    _('Enter a strong password', 'أدخل كلمة مرور قوية');
    _('https://linkedin.com/in/your-profile', 'https://linkedin.com/in/your-profile');
    _('Confirm', 'تأكيد');
    _('Password reset instructions sent to your email', 'تم إرسال تعليمات إعادة تعيين كلمة المرور إلى بريدك الإلكتروني');
    _('An email has been sent with credentials to reset your password', 'تم إرسال بريد إلكتروني يحتوي على رابط إعادة تعيين كلمة المرور');
    _('Your Email', 'بريدك الإلكتروني');
    _('Confirm Password', 'تأكيد كلمة المرور');

    // ── Register page ──
    _('Create Account', 'إنشاء حساب');
    _('✍️ Join Dawrha', '✍️ انضم إلى دورها');
    _('Create your account', 'أنشئ حسابك');
    _('Already have an account?', 'لديك حساب بالفعل؟');
    _('Sign in →', 'تسجيل الدخول →');
    _('⏰ Verification code expired. Please register again.', '⏰ انتهت صلاحية رمز التحقق. يرجى التسجيل مرة أخرى.');
    _('🔒 Too many wrong attempts. Please register again.', '🔒 عدد محاولات خاطئة كثيرة. يرجى التسجيل مرة أخرى.');
    _('Full Name', 'الاسم الكامل');
    _('Email Address', 'البريد الإلكتروني');
    _('Password', 'كلمة المرور');
    _('Confirm Password', 'تأكيد كلمة المرور');
    _('Send Verification Code →', 'إرسال رمز التحقق →');
    _('By registering you agree to our', 'بالتسجيل فإنك توافق على');
    _('Terms of Service', 'شروط الخدمة');
    _('e.g. Ahmad Khalil', 'مثال: أحمد خليل');
    _('e.g. ahmad@gmail.com', 'مثال: ahmad@gmail.com');

    // ── Verify Email page ──
    _('Verify Email', 'تأكيد البريد الإلكتروني');
    _('Check your email', 'تحقق من بريدك الإلكتروني');
    _('We sent a 6-digit code to', 'لقد أرسلنا رمزاً من ٦ أرقام إلى');
    _('✅ A new verification code has been sent!', '✅ تم إرسال رمز تحقق جديد!');
    _('Enter the 6-digit verification code', 'أدخل رمز التحقق المكون من ٦ أرقام');
    _('✅ Verify & Create Account', '✅ تحقق وإنشاء الحساب');
    _("Didn't receive the code?", 'لم يصلك الرمز؟');
    _('🔄 Resend Code', '🔄 إعادة إرسال الرمز');
    _('← Change Email', '← تغيير البريد الإلكتروني');
    _('Code expires in', 'ينتهي الرمز خلال');
    _('Expired', 'منتهي');

    // ── Error / validation messages (used in controller) ──
    _('Please enter a valid phone number.', 'الرجاء إدخال رقم هاتف صحيح.');
    _('National ID must contain only digits (5 to 20 characters).', 'يجب أن يحتوي الرقم الوطني على أرقام فقط (٥ إلى ٢٠ حرفاً).');
    _('Please upload at least one file (CV is required).', 'الرجاء رفع ملف واحد على الأقل (السيرة الذاتية مطلوبة).');
    _('Profile link must start with http:// or https://', 'يجب أن يبدأ رابط الملف الشخصي بـ http:// أو https://');
    _('Please fill in all password fields.', 'الرجاء ملء جميع حقول كلمة المرور.');
    _('New password must be at least 6 characters.', 'يجب أن تتكون كلمة المرور الجديدة من ٦ أحرف على الأقل.');
    _('New password and confirmation do not match.', 'كلمة المرور الجديدة وتأكيدها غير متطابقين.');
    _('New password must be different from the current one.', 'يجب أن تختلف كلمة المرور الجديدة عن الحالية.');
    _('Your current password is incorrect.', 'كلمة المرور الحالية غير صحيحة.');
    _('An account with this email already exists. Please sign in instead.', 'يوجد حساب بهذا البريد الإلكتروني بالفعل. الرجاء تسجيل الدخول بدلاً من ذلك.');
    _('Please enter your full name (at least 2 characters).', 'الرجاء إدخال اسمك الكامل (حرفان على الأقل).');
    _('Please enter a valid email address.', 'الرجاء إدخال عنوان بريد إلكتروني صحيح.');
    _('Password must be at least 6 characters.', 'يجب أن تتكون كلمة المرور من ٦ أحرف على الأقل.');
    _('Passwords do not match.', 'كلمتا المرور غير متطابقتين.');
    _('Could not send the verification email. Please check the address and try again.', 'تعذر إرسال بريد التحقق. الرجاء التحقق من العنوان والمحاولة مرة أخرى.');
    _('Incorrect code —', 'رمز غير صحيح —');
    _('attempt(s) left.', 'محاولة (محاولات) متبقية.');
    _('Too many wrong attempts.', 'عدد كبير جداً من المحاولات الخاطئة.');

    // ── Miscellaneous dashboard role labels ──
    _('Warehouse Manager', 'مدير المستودع');
    _('Input Employee', 'موظف استقبال');
    _('Sorting Employee', 'موظف فرز وتخزين');
    _('Output Employee', 'موظف إخراج');
    _('Applicant', 'مقدم طلب');

    // ── Breadcrumb / nav ──
    _('Sign in →', 'تسجيل الدخول →');
    _('Create one →', 'أنشئ واحداً →');

    // ── Odoo auth page strings used in auth_templates.xml ──
    _("Don't have an account?", 'ليس لديك حساب؟');
    _('← Back to sign in', '← العودة إلى تسجيل الدخول');
    _('Create an account', 'إنشاء حساب');
    _('✅ Your password was changed. Please sign in with your new password.', '✅ تم تغيير كلمة المرور. الرجاء تسجيل الدخول بكلمة المرور الجديدة.');
    _('Account created successfully!', 'تم إنشاء الحساب بنجاح!');
    _('Your account has been created. Please sign in with your email and password.', 'تم إنشاء حسابك. الرجاء تسجيل الدخول باستخدام بريدك الإلكتروني وكلمة المرور.');
    _("I don't remember my password", 'لا أتذكر كلمة المرور');
    _('Log in', 'تسجيل الدخول');
    _('Welcome back', 'مرحباً بعودتك');
    _('Sign in to your account', 'سجل الدخول إلى حسابك');
    _('Forgot password?', 'نسيت كلمة المرور؟');
    _('Enter your email', 'أدخل بريدك الإلكتروني');
    _('Enter your password', 'أدخل كلمة المرور');
    _('Reset your password', 'إعادة تعيين كلمة المرور');
    _('Enter your email to receive a reset link', 'أدخل بريدك الإلكتروني لاستلام رابط إعادة التعيين');
    _('Create your account', 'أنشئ حسابك');
    _('Sign up', 'التسجيل');
    _('Reset Password', 'إعادة تعيين كلمة المرور');
    _('Use a Passkey', 'استخدام مفتاح المرور');
    _('- or -', '— أو —');
    _('Skip to Content', 'تخطي إلى المحتوى');
    _("I don't have an account", 'ليس لدي حساب');
    _('or', 'أو');
    _('Back to Login', 'العودة إلى تسجيل الدخول');
    _('Choose a user', 'اختر مستخدماً');
    _('Use another user', 'استخدام مستخدم آخر');
    _('Remove user from switcher', 'إزالة المستخدم من المبدّل');

    // ──────────── GLOBAL API ────────────

    window.dwSetLang = setLang;
    window.dwGetLang = getLang;
    window.dwTr = tr;
    window.dwApplyTranslations = apply;

    // ──────────── INIT ────────────

    // Runs on EVERY page — including /web/login and /web/reset_password.
    // Their texts carry data-i18n attributes (added via inherited views in
    // auth_templates.xml), so apply() translates them safely without
    // touching Odoo's form logic.

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', apply);
    } else {
        apply();
    }

    // Re-apply when language changes from admin dashboard
    window.addEventListener('storage', function (e) {
        if (e.key === LANG_KEY) apply();
    });
    window.addEventListener('dw-lang-change', apply);

    // MutationObserver: catch dynamically rendered Owl components
    // (user_switch, passkey, etc.) by watching for new auth-form nodes
    function scanAuthText() {
        var areas = document.querySelectorAll(
            '.dw-nav, .dw-links, .dw-nav-drawer, .dw-modal, ' +
            '.o_database_list, form.oe_login_form, form.oe_signup_form, ' +
            'form.oe_reset_password_form');
        for (var a = 0; a < areas.length; a++) {
            var walker = document.createTreeWalker(areas[a], 4, null, false);
            var node;
            while (node = walker.nextNode()) {
                var tx = (node.textContent || '').trim();
                if (tx.length < 2) continue;
                var txl = tr(tx);
                if (txl !== tx) node.textContent = txl;
            }
        }
    }
    // Run once after Owl has had time to render
    setTimeout(scanAuthText, 500);
    // Watch for any new DOM nodes inside the form area
    var observer = new MutationObserver(function(mutations) {
        for (var m = 0; m < mutations.length; m++) {
            if (mutations[m].addedNodes.length) {
                scanAuthText();
                break;
            }
        }
    });
    var target = document.querySelector('.o_database_list') || document.body;
    observer.observe(target, { childList: true, subtree: true });
})();
/* ── UI-inspection deterrents (spec §19) ────────────────────────────────
   Best-effort friction only — real protection lives on the backend/API.
   Blocks: context menu (quick "Inspect"), common DevTools shortcuts
   (F12 / Ctrl+Shift+I,J,C / Ctrl+U), and direct image dragging. */
(function () {
    'use strict';
    if (window.__dwDeterrentsLoaded) { return; }
    window.__dwDeterrentsLoaded = true;
    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
    });
    document.addEventListener('keydown', function (e) {
        var k = (e.key || '').toUpperCase();
        if (k === 'F12' ||
            (e.ctrlKey && e.shiftKey && (k === 'I' || k === 'J' || k === 'C')) ||
            (e.ctrlKey && !e.shiftKey && k === 'U')) {
            e.preventDefault();
            e.stopPropagation();
        }
    });
    function dwProtectImages() {
        var imgs = document.querySelectorAll('img:not([draggable="false"])');
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].setAttribute('draggable', 'false');
        }
    }
    if (document.readyState !== 'loading') { dwProtectImages(); }
    else { document.addEventListener('DOMContentLoaded', dwProtectImages); }
    setTimeout(dwProtectImages, 1200);
})();
