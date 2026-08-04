# -*- coding: utf-8 -*-
{
    'name': 'TMS Fleet & Tire Intelligence Dashboard',
    'version': '13.0.1.0.0',
    'category': 'Transportation/Management',
    'summary': 'Standalone Executive & Operational Command Center for TMS Fleet & Tire Intelligence',
    'description': """
TMS Fleet & Tire Intelligence Dashboard
========================================
- Executive KPI Cards (Active Fleet, Mounted Tires, Wear Risk Alerts, CPKM Efficiency)
- Real-Time Wear Heatmap Distribution
- Vehicle Telemetry Quick-Grid with 1-Click Chassis Visualizer Navigation
- Brand & Pattern Performance Benchmarking
- Actionable Maintenance Alert Queue
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
    ],
    'qweb': [
        'static/src/xml/tms_intelligence_dashboard_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
