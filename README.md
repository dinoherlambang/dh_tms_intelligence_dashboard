# 🚚 TMS Fleet & Tire Intelligence Dashboard (`dh_tms_intelligence_dashboard`)

[![Odoo Version](https://img.shields.io/badge/Odoo-13.0-1e62d0.svg)](https://www.odoo.com/)
[![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)
[![Category](https://img.shields.io/badge/Category-Transportation--Management-green.svg)]()

A standalone, real-time **Executive & Operational Command Center** for commercial fleet managers and logistics operators. Built specifically to extend Odoo 13 Transportation Management Systems (TMS) with live vehicle telemetry, tire tread wear heatmaps, Cost-per-Kilometer (CPKM) benchmarking, predictive maintenance queues, and 1-click interactive chassis inspection visualizers.

---

## 🌟 Key Features

- 📊 **Executive KPI Metrics**: Live indicators tracking Active Fleet Units (% Operational Readiness), Active Mounted Tires (Position Ratio), Critical Wear / PSI Risk Alerts, and Average Fleet CPKM.
- 🟢 **Fleet Tire Wear Heatmap**: Dynamic progress bar breakdown categorizing fleet tires by health states:
  - 🟢 **Normal**: Remaining Tread Depth (RTD) $> 6.0\text{ mm}$
  - 🟡 **Warning**: RTD between $3.1\text{ mm}$ and $6.0\text{ mm}$ (Rotation / Upcoming replacement)
  - 🔴 **Critical**: RTD $\le 3.0\text{ mm}$ (Immediate replacement required)
- 📍 **Vehicle Telemetry Quick-Grid**: Interactive vehicle cards displaying plate numbers (`Nopol`), internal unit IDs (`No. Lambung`), chassis axle configurations, and real-time mounted tire ratios.
- 🎯 **1-Click Chassis Visualizer Navigation**: Click any vehicle card on the dashboard to immediately open its interactive **Chassis Diagram Visualizer**!
- 📈 **Tire Brand & Pattern Performance Benchmarks**: Automated Cost-per-Kilometer ($\text{CPKM} = \frac{\text{Purchase Price}}{\text{Total Mileage}}$) benchmarking calculated dynamically across tire brands.
- 🔔 **Actionable Maintenance Alert Queue**: Prioritized alert feed highlighting critical wear limits and rotation recommendations.

---

## 📁 Repository & Module Structure

```text
dh_tms_intelligence_dashboard/
├── README.md                                  # Module Documentation for GitHub
├── __init__.py                                # Python package initializer
├── __manifest__.py                            # Odoo 13 module manifest
├── models/
│   ├── __init__.py                            # Models package initializer
│   └── tms_dashboard.py                       # Backend intelligence RPC data engine
├── security/
│   └── ir.model.access.csv                    # Security access rights definition
├── views/
│   ├── assets.xml                             # Web backend JS & CSS asset registration
│   └── tms_dashboard_views.xml                # Client action & top-level menu definitions
└── static/
    └── src/
        ├── css/
        │   └── tms_intelligence_dashboard.css # Glassmorphism modern dashboard styling
        ├── js/
        │   └── tms_intelligence_dashboard.js  # AbstractAction web client action
        └── xml/
            └── tms_intelligence_dashboard_templates.xml # QWeb UI templates
```

---

## ⚙️ Installation & Usage Guide

### Prerequisites
- **Odoo 13.0** (Community or Enterprise Edition)
- Core TMS Module: `dh_tms`

### Installation Steps
1. Clone or place the repository folder into your Odoo custom addons directory:
   ```bash
   cd /path/to/odoo/custom/addons
   git clone https://github.com/dinoherlambang/dh_tms_intelligence_dashboard.git
   ```
2. Restart your Odoo server instance:
   ```bash
   service odoo restart
   ```
3. Log in to Odoo as an Administrator.
4. Enable **Developer Mode** (`Settings → Activate the developer mode`).
5. Go to **Apps → Update Apps List**.
6. Search for `TMS Fleet & Tire Intelligence Dashboard` (`dh_tms_intelligence_dashboard`).
7. Click **Install**.

---

## 💻 Navigation
Once installed, navigate to:
**`TMS → Intelligence Dashboard`**

---

## 👨‍💻 Author & License

- **Author**: Dino Herlambang
- **License**: GNU Lesser General Public License v3.0 (LGPL-3)
- **Repository**: [github.com/dinoherlambang/dh_tms_intelligence_dashboard](https://github.com/dinoherlambang/dh_tms_intelligence_dashboard)
