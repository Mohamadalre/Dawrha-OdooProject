/* ── Dawrha — Profile Completion (client-side) ─────────────────────────
   * Mirrors the server validation rules so the user gets instant, bilingual
     feedback before the form is even submitted.
   * Reads the active language from the shared website_i18n.js engine
     (window.dwGetLang / window.dwTr) so messages match the rest of the site.
   * Handles the "already applied" duplicate modal (confirm → resubmit with
     confirm_update=1; cancel → close).
   ==================================================================== */
(function () {
    'use strict';

    // Local bilingual messages (kept in sync with website.py::_pc_msg).
    var MSG = {
        en: {
            required:  'Please fill all required fields',
            bad_email: 'Invalid email',
            bad_phone: 'Phone must contain only numbers',
            bad_cv:    'Only PDF or Word files allowed',
            bad_nid:   'National ID must contain only digits (5 to 20 characters).',
        },
        ar: {
            required:  'الرجاء ملء جميع الحقول المطلوبة',
            bad_email: 'البريد الإلكتروني غير صحيح',
            bad_phone: 'رقم الهاتف يجب أن يحتوي على أرقام فقط',
            bad_cv:    'اسمح فقط ملفات PDF أو Word',
            bad_nid:   'يجب أن يحتوي الرقم الوطني على أرقام فقط (5 إلى 20 رقماً).',
        },
    };

    function lang() {
        try { return window.dwGetLang ? window.dwGetLang() : 'en'; }
        catch (e) { return 'en'; }
    }
    function msg(key) {
        var l = lang();
        return (MSG[l] && MSG[l][key]) || (MSG.en[key] || key);
    }

    var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    var CV_RE = /\.(pdf|doc|docx)$/i;

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else { fn(); }
    }

    ready(function () {
        var form = document.getElementById('dw-profile-form');
        if (!form) return;

        // Keep the hidden dw_lang field in sync so the server picks the same
        // language when it renders errors after a POST.
        var langInput = form.querySelector('.dw_lang_input');
        if (langInput) langInput.value = lang();
        window.addEventListener('dw-lang-change', function () {
            if (langInput) langInput.value = lang();
        });

        // ── Inline error banner ──────────────────────────────────────
        var banner = document.createElement('div');
        banner.className = 'dw-alert dw-alert-error dw-profile-alert';
        banner.style.display = 'none';
        form.parentNode.insertBefore(banner, form);

        function showErrors(list) {
            if (!list.length) { banner.style.display = 'none'; return; }
            banner.innerHTML = '<ul style="margin:0;padding-inline-start:20px;">' +
                list.map(function (e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
            banner.style.display = 'block';
            banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        function markField(el, bad) {
            if (!el) return;
            el.classList.toggle('dw-field-invalid', !!bad);
        }

        function validate() {
            var errors = [];
            var seen = {};
            function push(k) { if (!seen[k]) { seen[k] = 1; errors.push(msg(k)); } }

            // Required fields
            var reqs = form.querySelectorAll('[data-req="1"]');
            for (var i = 0; i < reqs.length; i++) {
                var el = reqs[i];
                var empty = el.type === 'file'
                    ? !(el.files && el.files.length)
                    : !String(el.value || '').trim();
                markField(el, empty);
                if (empty) push('required');
            }

            // Email
            var email = form.querySelector('[data-check="email"]');
            if (email && email.value.trim() && !EMAIL_RE.test(email.value.trim())) {
                markField(email, true); push('bad_email');
            }

            // Phone (digits only, allow leading + and spaces)
            var phone = form.querySelector('[data-check="phone"]');
            if (phone && phone.value.trim()) {
                var digits = phone.value.replace(/[+\s]/g, '');
                if (!/^\d+$/.test(digits)) { markField(phone, true); push('bad_phone'); }
            }

            // National ID (5–20 digits)
            var nid = form.querySelector('[data-check="nid"]');
            if (nid && nid.value.trim()) {
                var v = nid.value.trim();
                if (!/^\d{5,20}$/.test(v)) { markField(nid, true); push('bad_nid'); }
            }

            // CV + extra docs file types
            var fileInputs = form.querySelectorAll('[data-check="cv"]');
            for (var k = 0; k < fileInputs.length; k++) {
                var fi = fileInputs[k];
                if (fi.files && fi.files.length) {
                    for (var j = 0; j < fi.files.length; j++) {
                        if (!CV_RE.test(fi.files[j].name)) {
                            markField(fi, true); push('bad_cv'); break;
                        }
                    }
                }
            }

            showErrors(errors);
            return errors.length === 0;
        }

        form.addEventListener('submit', function (e) {
            if (!validate()) { e.preventDefault(); }
        });

        // Clear a field's error state as the user fixes it.
        form.addEventListener('input', function (e) {
            if (e.target.classList) e.target.classList.remove('dw-field-invalid');
        });

        // ── Duplicate application modal ──────────────────────────────
        var modal   = document.getElementById('dw-dup-modal');
        var confirm = document.getElementById('dw-dup-confirm');
        var cancel  = document.getElementById('dw-dup-cancel');
        var hidden  = document.getElementById('dw-confirm-update');

        if (confirm && hidden) {
            confirm.addEventListener('click', function () {
                // Re-submit the same form, this time confirming the update.
                hidden.value = '1';
                if (modal) modal.classList.remove('dw-modal-open');
                form.submit();
            });
        }
        if (cancel && modal) {
            cancel.addEventListener('click', function () {
                modal.classList.remove('dw-modal-open');
            });
        }
    });
})();
