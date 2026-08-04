# -*- coding: utf-8 -*-
{
    'name': 'TMS Fleet & Tire Intelligence Dashboard',
    'version': '13.0.1.0.0',
    'category': 'Transportation/Management',
    'summary': 'Standalone Executive & Operational Command Center for TMS Fleet & Tire Intelligence',
    'description': """
TMS Fleet & Tire Intelligence Dashboard
========================================
1. Dynamic Hub & Vehicle Type Filter Bar
2. Predictive Tire Lifespan Forecaster
3. Automated Tire Rotation Opportunities Widget
4. Interactive Wear Heatmap Filter
5. 1-Click Executive QWeb PDF Summary Export
    """,
    'author': 'Dino Herlambang',
    'website': 'https://github.com/dinoherlambang/dh_tms',
    'depends': [
        'base',
        'web',
        'dh_tms',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/tms_dashboard_views.xml',
        'reports/tms_dashboard_report_template.xml',
    ],
    'qweb': [
        'static/src/xml/tms_intelligence_dashboard_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dh_tms_intelligence_dashboard/static/src/css/tms_intelligence_dashboard.css',
            'dh_tms_intelligence_dashboard/static/src/scss/tms_intelligence_dashboard.scss',
            'dh_tms_intelligence_dashboard/static/src/js/tms_intelligence_dashboard.js',
        ],
        'web.assets_qweb': [
            'dh_tms_intelligence_dashboard/static/src/xml/tms_intelligence_dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
