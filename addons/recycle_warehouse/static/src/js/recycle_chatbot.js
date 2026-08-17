/* ══════════════════════════════════════════════════════════════════
   Dawrha — Support Chatbot (backend dashboards)
   Opens when the sidebar brand text (.o_ra_sb_brand_txt) is clicked.
   Self-contained: injects its own styles + DOM, AR/EN via the shared
   'recycle_wms_lang' key, rule-based answers about the WMS workflows.
   ══════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';
    if (window.__dwChatbotLoaded) { return; }
    window.__dwChatbotLoaded = true;

    var LANG_KEY = 'recycle_wms_lang';
    function isAr() { return localStorage.getItem(LANG_KEY) === 'ar'; }

    var TXT = {
        title:   { en: 'Dawrha Assistant', ar: 'مساعد دورها' },
        subtitle:{ en: 'Ask me about the system', ar: 'اسألني عن النظام' },
        hello:   { en: 'Hi 👋 I am the Dawrha assistant. How can I help you today?',
                   ar: 'أهلاً 👋 أنا مساعد دورها. كيف أقدر أساعدك اليوم؟' },
        ph:      { en: 'Type your message…', ar: 'اكتب رسالتك…' },
        fallback:{ en: 'I did not fully get that. Try one of the quick topics below, or contact the administrator.',
                   ar: 'لم أفهم سؤالك تماماً. جرّب أحد المواضيع السريعة بالأسفل، أو تواصل مع الإدارة.' },
        topics: [
            { q: { en: '📦 Shipments', ar: '📦 الشحنات' },
              a: { en: 'Shipments flow: Pending → Reception (weigh & accept) → Sorting (classify by condition) → Stored in the storage zone. Use the Shipments menu to track every step.',
                   ar: 'مسار الشحنة: قيد الانتظار ← الاستقبال (وزن وقبول) ← الفرز (تصنيف حسب الحالة) ← التخزين في منطقة التخزين. تابع كل خطوة من قائمة الشحنات.' } },
            { q: { en: '🚚 Orders', ar: '🚚 الطلبات' },
              a: { en: 'Orders flow: Pending → reserved by an output employee → stock allocated & deducted → Completed with a PDF invoice (price by customer tier).',
                   ar: 'مسار الطلبية: قيد الانتظار ← حجز من موظف الإخراج ← تخصيص وخصم المخزون ← مكتملة مع فاتورة PDF (السعر حسب جهة العميل).' } },
            { q: { en: '⏰ Shifts & Attendance', ar: '⏰ الورديات والحضور' },
              a: { en: 'Shifts are defined per warehouse (or unassigned). An employee gets a shift from their employee form. Attendance is tracked by check-in/check-out.',
                   ar: 'الورديات تُعرَّف لكل مستودع (أو غير مسندة). تُسند الوردية للموظف من نموذج بياناته، ويُتابع الحضور بتسجيل الدخول والخروج.' } },
            { q: { en: '👤 Contact admin', ar: '👤 التواصل مع الإدارة' },
              a: { en: 'For account or permission issues, contact the system administrator from the Account page, or email the administration.',
                   ar: 'لمشاكل الحساب أو الصلاحيات، تواصل مع مدير النظام من صفحة الحساب أو راسل الإدارة عبر البريد.' } },
        ],
    };

    var KEYWORDS = [
        { re: /(ship|شحن)/i, topic: 0 },
        { re: /(order|طلب|فاتور|invoice)/i, topic: 1 },
        { re: /(shift|ورد|حضور|attend)/i, topic: 2 },
        { re: /(admin|إدار|ادار|تواصل|contact|help|مساعد)/i, topic: 3 },
    ];

    var CSS = [
        '.dw-cb-fab-open{cursor:pointer;}',
        '.dw-cb{position:fixed;bottom:20px;inset-inline-end:20px;z-index:2000;width:360px;max-width:calc(100vw - 24px);',
        ' height:520px;max-height:calc(100vh - 40px);display:none;flex-direction:column;border-radius:20px;overflow:hidden;',
        ' background:#0f1a2e;border:1px solid rgba(148,163,184,.2);box-shadow:0 30px 80px rgba(0,0,0,.5);',
        ' font-family:Cairo,Inter,system-ui,sans-serif;}',
        '.dw-cb.open{display:flex;animation:dwCbIn .3s cubic-bezier(.4,0,.2,1);}',
        '@keyframes dwCbIn{from{opacity:0;transform:translateY(16px) scale(.97)}to{opacity:1;transform:none}}',
        '.dw-cb-head{padding:16px 18px;background:linear-gradient(135deg,#064e3b,#047857);color:#fff;display:flex;align-items:center;gap:12px;}',
        '.dw-cb-ava{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-size:20px;}',
        '.dw-cb-head b{display:block;font-size:15px;}',
        '.dw-cb-head small{opacity:.8;font-size:12px;}',
        '.dw-cb-x{margin-inline-start:auto;background:none;border:none;color:#fff;font-size:20px;cursor:pointer;opacity:.8;}',
        '.dw-cb-x:hover{opacity:1;}',
        '.dw-cb-body{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;',
        ' background:radial-gradient(60% 40% at 80% 0%,rgba(31,184,118,.12),transparent),#0b1220;}',
        '.dw-cb-msg{max-width:85%;padding:10px 14px;border-radius:14px;font-size:13.5px;line-height:1.6;white-space:pre-line;}',
        '.dw-cb-bot{background:#16213a;color:#e2e8f0;border:1px solid rgba(148,163,184,.14);border-start-start-radius:4px;align-self:flex-start;}',
        '.dw-cb-user{background:linear-gradient(135deg,#047857,#1fb876);color:#fff;border-end-end-radius:4px;align-self:flex-end;}',
        '.dw-cb-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px;background:#0b1220;}',
        '.dw-cb-chip{border:1px solid rgba(31,184,118,.4);background:rgba(31,184,118,.1);color:#34d399;border-radius:100px;',
        ' padding:6px 12px;font-size:12px;cursor:pointer;transition:all .15s;font-family:inherit;}',
        '.dw-cb-chip:hover{background:#1fb876;color:#fff;}',
        '.dw-cb-foot{display:flex;gap:8px;padding:12px;background:#0f1a2e;border-top:1px solid rgba(148,163,184,.14);}',
        '.dw-cb-in{flex:1;padding:11px 14px;border-radius:12px;border:1px solid rgba(148,163,184,.2);background:#0b1220;',
        ' color:#f1f5f9;font-size:13.5px;outline:none;font-family:inherit;}',
        '.dw-cb-in:focus{border-color:#1fb876;}',
        '.dw-cb-send{width:42px;height:42px;border-radius:12px;border:none;cursor:pointer;font-size:16px;color:#fff;',
        ' background:linear-gradient(135deg,#047857,#1fb876);transition:transform .15s;}',
        '.dw-cb-send:hover{transform:scale(1.07);}',
        '@media (max-width:480px){.dw-cb{bottom:10px;inset-inline-end:10px;height:70vh;}}',
        /* Mobile-only floating trigger: the sidebar brand text lives inside
           the collapsible drawer, so on small screens it is not always a
           reliable/reachable open point — this persistent button guarantees
           one regardless of sidebar/drawer state. Desktop keeps the
           brand-text trigger only (no visual change there). */
        '.dw-cb-fab{display:none;}',
        '@media (max-width:767px){',
        ' .dw-cb-fab{display:flex;position:fixed;bottom:18px;inset-inline-end:18px;z-index:1999;',
        ' width:52px;height:52px;border-radius:50%;align-items:center;justify-content:center;',
        ' background:linear-gradient(135deg,#047857,#1fb876);color:#fff;font-size:24px;border:none;',
        ' box-shadow:0 10px 28px rgba(16,185,129,.45);cursor:pointer;}',
        ' .dw-cb-fab.hidden{display:none;}',
        '}',
    ].join('\n');

    var panel, body, chips, fab, styleInjected = false;

    // Inject the widget's stylesheet ONCE, at load — not lazily on first open.
    // The floating trigger (.dw-cb-fab) is created at page load by buildFab(),
    // but its rules (display:none on desktop; a fixed bottom-right circle on
    // mobile) live in CSS. When that CSS was only injected inside build() —
    // which runs on first OPEN — the button sat in the DOM UNSTYLED until then,
    // collapsing to a full-width block at the TOP of the page: the "cloud + white
    // strip above the navbar". Injecting here means the trigger is styled the
    // moment it exists, so it is either hidden or at the BOTTOM, never a top bar.
    function ensureStyle() {
        if (styleInjected) { return; }
        styleInjected = true;
        var style = document.createElement('style');
        style.textContent = CSS;
        document.head.appendChild(style);
    }

    function t(o) { return isAr() ? o.ar : o.en; }

    function addMsg(text, who) {
        var m = document.createElement('div');
        m.className = 'dw-cb-msg ' + (who === 'user' ? 'dw-cb-user' : 'dw-cb-bot');
        m.textContent = text;
        body.appendChild(m);
        body.scrollTop = body.scrollHeight;
    }

    function answer(text) {
        var q = (text || '').trim();
        if (!q) { return; }
        addMsg(q, 'user');
        var topic = null;
        for (var i = 0; i < KEYWORDS.length; i++) {
            if (KEYWORDS[i].re.test(q)) { topic = KEYWORDS[i].topic; break; }
        }
        setTimeout(function () {
            addMsg(topic === null ? t(TXT.fallback) : t(TXT.topics[topic].a), 'bot');
        }, 350);
    }

    function build() {
        if (panel) { return; }
        ensureStyle();

        panel = document.createElement('div');
        panel.className = 'dw-cb';
        panel.innerHTML =
            '<div class="dw-cb-head">' +
            '  <div class="dw-cb-ava">♻</div>' +
            '  <div><b></b><small></small></div>' +
            '  <button type="button" class="dw-cb-x" aria-label="Close">✕</button>' +
            '</div>' +
            '<div class="dw-cb-body"></div>' +
            '<div class="dw-cb-chips"></div>' +
            '<div class="dw-cb-foot">' +
            '  <input type="text" class="dw-cb-in"/>' +
            '  <button type="button" class="dw-cb-send">➤</button>' +
            '</div>';
        document.body.appendChild(panel);
        body = panel.querySelector('.dw-cb-body');
        chips = panel.querySelector('.dw-cb-chips');
        panel.querySelector('.dw-cb-x').addEventListener('click', toggle);
        var input = panel.querySelector('.dw-cb-in');
        var send = function () { answer(input.value); input.value = ''; };
        panel.querySelector('.dw-cb-send').addEventListener('click', send);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { send(); }
        });
    }

    function refreshLang() {
        panel.querySelector('.dw-cb-head b').textContent = t(TXT.title);
        panel.querySelector('.dw-cb-head small').textContent = t(TXT.subtitle);
        panel.querySelector('.dw-cb-in').setAttribute('placeholder', t(TXT.ph));
        panel.dir = isAr() ? 'rtl' : 'ltr';
        chips.innerHTML = '';
        TXT.topics.forEach(function (tp) {
            var c = document.createElement('button');
            c.type = 'button';
            c.className = 'dw-cb-chip';
            c.textContent = t(tp.q);
            c.addEventListener('click', function () { answer(t(tp.q)); });
            chips.appendChild(c);
        });
    }

    function toggle() {
        build();
        var opening = !panel.classList.contains('open');
        panel.classList.toggle('open', opening);
        if (fab) { fab.classList.toggle('hidden', opening); }
        if (opening) {
            refreshLang();
            if (!body.childElementCount) { addMsg(t(TXT.hello), 'bot'); }
        }
    }

    // Mobile-only floating trigger — see .dw-cb-fab in CSS above. Created
    // once at load time (not lazily like the panel) so it is always
    // reachable, independent of the sidebar drawer's open/closed state.
    function buildFab() {
        ensureStyle();
        fab = document.createElement('button');
        fab.type = 'button';
        fab.className = 'dw-cb-fab';
        fab.setAttribute('aria-label', 'Dawrha Assistant');
        fab.textContent = '💬';
        fab.addEventListener('click', toggle);
        document.body.appendChild(fab);
    }

    // Open from the dashboards' sidebar brand text (event delegation:
    // the Owl dashboards render after this script loads).
    document.addEventListener('click', function (e) {
        var brand = e.target.closest && e.target.closest('.o_ra_sb_brand_txt');
        if (brand) { toggle(); }
    });
    // Make the brand text feel clickable.
    var styleHint = document.createElement('style');
    styleHint.textContent = '.o_ra_sb_brand_txt{cursor:pointer;} .o_ra_sb_brand_txt:hover{opacity:.85;}';
    document.head.appendChild(styleHint);

    if (document.body) { buildFab(); }
    else { document.addEventListener('DOMContentLoaded', buildFab); }
})();
