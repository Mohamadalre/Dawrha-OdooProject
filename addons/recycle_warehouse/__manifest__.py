# -*- coding: utf-8 -*-
{
    'name': 'Recycle Warehouse Management',
    'version': '19.0.1.46.0',
    'category': 'Inventory',
    'summary': 'Warehouses, shipments, sorting, stock, orders API and recruitment portal',
    'description': """
Recycle Warehouse Management
============================
- Multi-warehouse management with zones (Receiving / Sorting / Storage / Output)
- Shipment workflow: Pending -> Accepted -> Sorting -> Sorted (2% weight tolerance)
- Per-warehouse stock, isolated per manager/employee
- Orders REST API for Next.js + PDF invoice
- Website recruitment: jobs list, apply with national ID / phone / files
- Roles: Admin, Warehouse Manager, Input / Sorting / Output Employee
""",
    'author': 'Mohammad',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'hr_recruitment',
        'website',
        'portal',
        'auth_signup',
        'uom',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/email_templates.xml',
        'data/suggestion_cron.xml',
        'views/uom_views.xml',
        'views/catalog_reference_views.xml',
        'views/delivery_tariff_views.xml',
        'views/product_suggestion_views.xml',
        'views/product_views.xml',
        'views/warehouse_views.xml',
        'views/shipment_views.xml',
        'views/stock_views.xml',
        'views/damage_entry_views.xml',
        'views/shift_views.xml',
        'views/truck_views.xml',
        # The report is defined BEFORE the view that puts a print button on it:
        # an action referenced by xmlid must already exist when the view loads.
        'reports/driver_truck_report.xml',
        'views/delivery_driver_views.xml',
        'views/attendance_views.xml',
        'views/order_views.xml',
        'views/delivery_trip_views.xml',
        'views/recruitment_views.xml',
        'views/menus.xml',
        'views/res_config_settings_views.xml',
        'reports/order_invoice_report.xml',
        'reports/shipment_stock_reports.xml',
        'reports/shipment_detail_report.xml',
        'reports/employee_report.xml',
        'reports/driver_report.xml',
        'views/carousel_templates.xml',
        'views/email_layouts.xml',
        'views/website_templates.xml',
        'views/website_profile_templates.xml',
        'views/auth_templates.xml',
        # Loads LAST: it inherits web.webclient_bootstrap, which must already exist.
        'views/splash_templates.xml',
    ],
        'assets': {
            'web.assets_backend': [
                # First in the bundle: its only job is to take the splash down,
                # and nothing else should be able to fail ahead of it.
                'recycle_warehouse/static/src/js/recycle_splash.js',
                'recycle_warehouse/static/src/js/recycle_storage_guard.js',
                'recycle_warehouse/static/src/js/tailwind_loader.js',
                'recycle_warehouse/static/src/css/tailwind_theme.css',
                'recycle_warehouse/static/src/css/recycle_home.css',
                'recycle_warehouse/static/src/css/recycle_employee_theme.css',
                'recycle_warehouse/static/src/css/sorting_storage.css',
                'recycle_warehouse/static/src/css/dashboard_navbar_fix.css',
                'recycle_warehouse/static/src/js/dashboard_page_state.js',
                'recycle_warehouse/static/src/js/dashboard_shared.js',
                'recycle_warehouse/static/src/xml/recycle_home_action.xml',
                'recycle_warehouse/static/src/xml/dashboard_sorting.xml',
                'recycle_warehouse/static/src/xml/dashboard_delivery_driver.xml',
                'recycle_warehouse/static/src/xml/dashboard_output.xml',
                'recycle_warehouse/static/src/xml/dashboard_manager.xml',
                'recycle_warehouse/static/src/xml/dashboard_admin.xml',
                'recycle_warehouse/static/src/xml/dashboard_shared_components.xml',
                'recycle_warehouse/static/src/js/recycle_i18n_shared.js',
                'recycle_warehouse/static/src/js/recycle_backend_i18n.js',
                'recycle_warehouse/static/src/js/recycle_home_action.js',
                'recycle_warehouse/static/src/js/recycle_sorting_dashboard.js',
                'recycle_warehouse/static/src/js/recycle_delivery_driver_dashboard.js',
                'recycle_warehouse/static/src/js/recycle_output_dashboard.js',
                'recycle_warehouse/static/src/js/recycle_manager_dashboard.js',
                'recycle_warehouse/static/src/js/recycle_admin_dashboard.js',
                'recycle_warehouse/static/src/js/recycle_applications_board.js',
                'recycle_warehouse/static/src/js/recycle_employees_board.js',
                'recycle_warehouse/static/src/js/recycle_shift_manager.js',
                'recycle_warehouse/static/src/js/recycle_manager_attendance.js',
                'recycle_warehouse/static/src/js/recycle_chatbot.js',
            ],
        # NOTE: the bundle is 'web.assets_frontend' in Odoo 16+ — the old
        # 'website.assets_frontend' name is silently ignored, which left the
        # translation engine unloaded on /web/login & /web/reset_password.
        'web.assets_frontend': [
            'recycle_warehouse/static/src/js/recycle_storage_guard.js',
            'recycle_warehouse/static/src/js/website_i18n.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
