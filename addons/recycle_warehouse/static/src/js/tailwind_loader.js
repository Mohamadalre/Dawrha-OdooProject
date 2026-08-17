/** @odoo-module **/
/**
 * Tailwind CSS CDN Loader for Odoo 19 Backend
 * Loads Tailwind as a <script> tag (it's JS, not CSS).
 */
import { registry } from "@web/core/registry";

function loadTailwindCDN() {
    if (window.tailwind || document.getElementById('tw-cdn')) return;

    const script = document.createElement('script');
    script.id = 'tw-cdn';
    script.src = 'https://cdn.tailwindcss.com';
    script.onload = () => {
        if (window.tailwind) {
            window.tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            brand: {
                                50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0',
                                300: '#6ee7b7', 400: '#34d399', 500: '#10b981',
                                600: '#059669', 700: '#047857', 800: '#065f46',
                                900: '#064e3b', 950: '#022c22',
                            },
                        },
                        boxShadow: {
                            'card': '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
                            'card-hover': '0 10px 15px -3px rgba(0,0,0,0.08)',
                        },
                        fontFamily: {
                            sans: ['Inter', 'Cairo', 'system-ui', 'sans-serif'],
                        },
                        animation: {
                            'scale-in': 'scale-in 0.3s ease-out',
                            'slide-up': 'slide-up 0.3s ease-out',
                            'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
                        },
                        keyframes: {
                            'scale-in': { '0%': { transform: 'scale(0.9)', opacity: '0' }, '100%': { transform: 'scale(1)', opacity: '1' } },
                            'slide-up': { '0%': { transform: 'translateY(10px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
                            'pulse-soft': { '0%, 100%': { opacity: '1' }, '50%': { opacity: '0.6' } },
                        },
                    },
                },
            };
        }
    };
    document.head.appendChild(script);
}

// Load immediately
loadTailwindCDN();

// Load html5-qrcode library for live QR scanning
function loadHtml5QrCode() {
    if (window.Html5Qrcode) return;
    const script = document.createElement('script');
    script.id = 'html5-qrcode-cdn';
    script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
    script.onload = () => console.log('[RecycleWMS] html5-qrcode loaded');
    document.head.appendChild(script);
}
loadHtml5QrCode();
