odoo.define('dh_tms_intelligence_dashboard.Dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var TmsIntelligenceDashboard = AbstractAction.extend({
        template: 'dh_tms_intelligence_dashboard.MainDashboard',
        events: {
            'click .js_refresh_dashboard': '_onRefreshDashboard',
            'click .js_open_chassis_diagram': '_onOpenChassisDiagram',
            'change .js_filter_unit': '_onChangeFilter',
            'change .js_filter_truck_type': '_onChangeFilter',
            'click .js_export_pdf_report': '_onExportPdfReport',

            // Tire Monitoring Report Handlers & Actions
            'click .js_open_monitoring_wizard': '_onOpenMonitoringWizard',
            'click .js_open_monitoring_list': '_onOpenMonitoringList',
            'click .js_create_monitoring_rec': '_onCreateMonitoringRec',
            'click .js_open_monitoring_detail': '_onOpenMonitoringDetail',

            // Multi-Tab Chart Selection & Period Filters
            'click .js_select_chart_tab': '_onSelectChartTab',
            'change .js_filter_monitoring_year': '_onChangeMonitoringYear',
            'change .js_filter_monitoring_period': '_onChangeMonitoringPeriod',
            'click .js_clear_period_filter': '_onClearPeriodFilter',

            // Tire Monitoring 2-Column Search & Checkbox Filters
            'change .js_check_vehicle_filter': '_onCheckVehicleFilter',
            'change .js_check_brand_filter': '_onCheckBrandFilter',
            'change .js_check_size_filter': '_onCheckSizeFilter',
            'keyup .js_search_vehicle_filter': '_onSearchVehicleFilter',
            'keyup .js_search_brand_filter': '_onSearchBrandFilter',
            'keyup .js_search_size_filter': '_onSearchSizeFilter',
            'click .js_clear_vehicle_filter': '_onClearVehicleFilter',
            'click .js_clear_brand_filter': '_onClearBrandFilter',
            'click .js_clear_size_filter': '_onClearSizeFilter',

            // Interactive Drilldown Handlers
            'click .js_drilldown_fleet': '_onDrilldownFleet',
            'click .js_drilldown_mounted_tires': '_onDrilldownMountedTires',
            'click .js_drilldown_wear_alerts': '_onDrilldownWearAlerts',
            'click .js_drilldown_psi_alerts': '_onDrilldownPSIAlerts',
            'click .js_drilldown_cpkm': '_onDrilldownCPKM',
            'click .js_open_trailer_exchange': '_onOpenTrailerExchange',
            'click .js_drilldown_trailer_exchanges': '_onDrilldownTrailerExchanges',
            'click .js_open_billing_wizard': '_onOpenBillingWizard',
            'click .js_open_asset_valuation_wizard': '_onOpenAssetValuationWizard',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.kpis = {};
            this.psi_distribution = {};
            this.trailer_coupling_summary = {};
            this.recent_trailer_exchanges = [];
            this.cpk_billing_summary = {};
            this.asset_valuation_summary = { total_gross_str: 'Rp 0', total_depr_str: 'Rp 0', total_net_str: 'Rp 0', retention_pct: 0, as_of_date: '', hub_asset_data: [], status_asset_data: { mounted: 0, stock: 0, scrapped: 0 } };
            this.min_km_deficit_vehicles = [];
            this.alert_queue = [];
            this.rotation_recommendations = [];
            this.replacement_forecast = [];
            this.filters = {};
            this.selected_unit_id = false;
            this.selected_truck_type_id = false;

            // Tire Monitoring Report Data & Tab / Filter State
            this.monitoring_report = { records: [], vehicles: [], brands: [], sizes: [], years: [] };
            this.filtered_monitoring_records = [];
            this.selected_vehicles = [];
            this.selected_brands = [];
            this.selected_sizes = [];
            this.selected_year = '';
            this.selected_period = '';
            this.active_chart_tab = 'rtd'; // 'rtd' or 'mileage'
        },

        willStart: function () {
            var self = this;
            return Promise.all([
                this._super.apply(this, arguments),
                this._fetchDashboardData()
            ]);
        },

        _fetchDashboardData: function () {
            var self = this;
            return rpc.query({
                model: 'dh.tms.dashboard',
                method: 'get_intelligence_dashboard_data',
                args: [],
                kwargs: {
                    unit_id: self.selected_unit_id,
                    truck_type_id: self.selected_truck_type_id,
                }
            }).then(function (data) {
                self.filters = data.filters || {};
                self.kpis = data.kpis || {};
                self.psi_distribution = data.psi_distribution || {};
                self.trailer_coupling_summary = data.trailer_coupling_summary || {};
                self.recent_trailer_exchanges = data.recent_trailer_exchanges || [];
                self.cpk_billing_summary = data.cpk_billing_summary || {};
                self.asset_valuation_summary = data.asset_valuation_summary || { total_gross_str: 'Rp 0', total_depr_str: 'Rp 0', total_net_str: 'Rp 0', retention_pct: 0, as_of_date: '', hub_asset_data: [], status_asset_data: { mounted: 0, stock: 0, scrapped: 0 } };
                self.min_km_deficit_vehicles = data.min_km_deficit_vehicles || [];
                self.alert_queue = data.alert_queue || [];
                self.rotation_recommendations = data.rotation_recommendations || [];
                self.replacement_forecast = data.replacement_forecast || [];
                self.monitoring_report = data.monitoring_report || { records: [], vehicles: [], brands: [], sizes: [], years: [] };

                self._applyMonitoringFilter();
            }).catch(function (error) {
                console.error('[DH_TMS_DASHBOARD] Error fetching dashboard data:', error);
            });
        },

        _applyMonitoringFilter: function () {
            var self = this;
            var recs = (self.monitoring_report.records || []).slice();

            if (self.selected_year) {
                recs = recs.filter(function (r) {
                    return r.monitor_date && r.monitor_date.substring(0, 4) === self.selected_year;
                });
            }

            if (self.selected_period) {
                recs = recs.filter(function (r) {
                    if (!r.monitor_date) return false;
                    var monthNum = parseInt(r.monitor_date.substring(5, 7));
                    if (self.selected_period === 'Q1') return monthNum >= 1 && monthNum <= 3;
                    if (self.selected_period === 'Q2') return monthNum >= 4 && monthNum <= 6;
                    if (self.selected_period === 'Q3') return monthNum >= 7 && monthNum <= 9;
                    if (self.selected_period === 'Q4') return monthNum >= 10 && monthNum <= 12;
                    return monthNum === parseInt(self.selected_period);
                });
            }

            if (self.selected_vehicles.length > 0) {
                recs = recs.filter(function (r) {
                    return self.selected_vehicles.indexOf(r.vehicle_name) > -1;
                });
            }

            if (self.selected_brands.length > 0) {
                recs = recs.filter(function (r) {
                    return self.selected_brands.indexOf(r.tire_brand) > -1;
                });
            }

            if (self.selected_sizes.length > 0) {
                recs = recs.filter(function (r) {
                    return self.selected_sizes.indexOf(r.tire_size) > -1;
                });
            }

            self.filtered_monitoring_records = recs;
        },

        on_attach_to_dom: function () {
            this._super.apply(this, arguments);
            this._renderLineChart();
            this._renderCPKBillingCharts();
            this._renderAssetValuationCharts();
        },

        renderElement: function () {
            this._super.apply(this, arguments);
            this._renderLineChart();
            this._renderCPKBillingCharts();
            this._renderAssetValuationCharts();
            this._restoreCheckboxStates();
        },

        _restoreCheckboxStates: function () {
            var self = this;
            this.selected_vehicles.forEach(function (v) {
                self.$('.js_check_vehicle_filter[value="' + v + '"]').prop('checked', true);
            });
            this.selected_brands.forEach(function (b) {
                self.$('.js_check_brand_filter[value="' + b + '"]').prop('checked', true);
            });
            this.selected_sizes.forEach(function (s) {
                self.$('.js_check_size_filter[value="' + s + '"]').prop('checked', true);
            });
        },

        _renderLineChart: function () {
            var self = this;
            var canvas = this.$('#js_tire_monitoring_canvas')[0];
            if (!canvas) return;

            var ctx = canvas.getContext('2d');
            var records = (self.filtered_monitoring_records || []).slice();

            records.sort(function (a, b) {
                return (a.monitor_date || '').localeCompare(b.monitor_date || '');
            });

            var tab = self.active_chart_tab || 'rtd';
            var mainLabel = 'Remaining Tread Depth (mm)';
            var datasetColor = '#1e62d0';
            var unitSuffix = ' mm';

            if (tab === 'mileage') {
                mainLabel = 'Distance Traveled (KM)';
                datasetColor = '#28a745';
                unitSuffix = ' km';
            } else if (tab === 'wear_pct') {
                mainLabel = 'Tire Wear Percentage (%)';
                datasetColor = '#fd7e14';
                unitSuffix = '%';
            } else if (tab === 'efficiency') {
                mainLabel = 'Wear Efficiency (KM / mm)';
                datasetColor = '#6f42c1';
                unitSuffix = ' km/mm';
            } else if (tab === 'psi') {
                mainLabel = 'Inflation Pressure (PSI)';
                datasetColor = '#17a2b8';
                unitSuffix = ' PSI';
            } else if (tab === 'cpk') {
                mainLabel = 'Est. Cost per KM (Rp)';
                datasetColor = '#e83e8c';
                unitSuffix = ' Rp';
            }

            if (window.Chart) {
                if (this.chartInstance) {
                    this.chartInstance.destroy();
                }

                var labels = records.map(function (r) { return r.monitor_date || r.serial_no; });
                var mainData = records.map(function (r) {
                    if (tab === 'mileage') return r.km_traveled || 0;
                    if (tab === 'wear_pct') return r.wear_percentage || 0;
                    if (tab === 'efficiency') return r.km_per_mm || 0;
                    if (tab === 'psi') return r.psi_monitoring || 0;
                    if (tab === 'cpk') return r.est_cpk || 0;
                    return r.rtd_monitoring || 0;
                });

                var datasets = [
                    {
                        label: mainLabel,
                        data: mainData.length ? mainData : [0],
                        borderColor: datasetColor,
                        backgroundColor: 'rgba(30, 98, 208, 0.05)',
                        pointBackgroundColor: datasetColor,
                        pointBorderColor: '#ffffff',
                        pointHoverBackgroundColor: '#ffffff',
                        pointHoverBorderColor: datasetColor,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        fill: true,
                        lineTension: 0.3,
                    }
                ];

                if (labels.length) {
                    if (tab === 'rtd') {
                        datasets.push({
                            label: 'Safety Threshold (3.0 mm)',
                            data: labels.map(function () { return 3.0; }),
                            borderColor: '#dc3545',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false,
                        });
                        datasets.push({
                            label: 'Baseline New (18.0 mm)',
                            data: labels.map(function () { return 18.0; }),
                            borderColor: '#28a745',
                            borderDash: [2, 4],
                            pointRadius: 0,
                            fill: false,
                        });
                    } else if (tab === 'wear_pct') {
                        datasets.push({
                            label: 'Warning Level (50%)',
                            data: labels.map(function () { return 50.0; }),
                            borderColor: '#ffc107',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false,
                        });
                        datasets.push({
                            label: 'Critical Replacement (80%)',
                            data: labels.map(function () { return 80.0; }),
                            borderColor: '#dc3545',
                            borderDash: [3, 3],
                            pointRadius: 0,
                            fill: false,
                        });
                    } else if (tab === 'psi') {
                        datasets.push({
                            label: 'Standard Target (110 PSI)',
                            data: labels.map(function () { return 110.0; }),
                            borderColor: '#28a745',
                            borderDash: [4, 4],
                            pointRadius: 0,
                            fill: false,
                        });
                        datasets.push({
                            label: 'Low Pressure Hazard (90 PSI)',
                            data: labels.map(function () { return 90.0; }),
                            borderColor: '#dc3545',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false,
                        });
                    }
                }

                this.chartInstance = new window.Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels.length ? labels : ['No Data'],
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                fontColor: '#2c3e50',
                                fontSize: 11,
                                usePointStyle: true,
                                padding: 12
                            }
                        },
                        scales: {
                            yAxes: [
                                {
                                    ticks: { beginAtZero: true },
                                    scaleLabel: { display: true, labelString: mainLabel }
                                }
                            ]
                        }
                    }
                });
            } else {
                self._drawCanvasFallbackChart(ctx, canvas, records, tab, mainLabel, datasetColor, unitSuffix);
            }
        },

        _drawCanvasFallbackChart: function (ctx, canvas, records, tab, mainLabel, mainColor, unitSuffix) {
            var width = canvas.width = canvas.parentElement.offsetWidth || 500;
            var height = canvas.height = canvas.parentElement.offsetHeight || 320;

            ctx.clearRect(0, 0, width, height);

            var paddingLeft = 60;
            var paddingRight = 30;
            var paddingTop = 45;
            var paddingBottom = 40;

            var plotWidth = width - paddingLeft - paddingRight;
            var plotHeight = height - paddingTop - paddingBottom;

            var maxVal = 20;
            if (tab === 'wear_pct') maxVal = 100;
            else if (tab === 'psi') maxVal = 140;
            else if (records.length) {
                var rawVals = records.map(function (r) {
                    if (tab === 'mileage') return r.km_traveled || 0;
                    if (tab === 'efficiency') return r.km_per_mm || 0;
                    if (tab === 'cpk') return r.est_cpk || 0;
                    return r.rtd_monitoring || 0;
                });
                var maxRaw = Math.max.apply(Math, rawVals);
                maxVal = maxRaw > 0 ? maxRaw * 1.15 : 100;
            }

            // Draw Top Legends
            ctx.font = '11px sans-serif';
            ctx.fillStyle = mainColor;
            ctx.fillRect(width - 240, 12, 12, 12);
            ctx.fillStyle = '#2c3e50';
            ctx.fillText(mainLabel, width - 224, 22);

            // Draw Background Grid
            ctx.strokeStyle = '#e9ecef';
            ctx.lineWidth = 1;

            for (var i = 0; i <= 5; i++) {
                var y = paddingTop + (plotHeight / 5) * i;
                ctx.beginPath();
                ctx.moveTo(paddingLeft, y);
                ctx.lineTo(width - paddingRight, y);
                ctx.stroke();

                var valLabel = Math.round(maxVal - (maxVal / 5) * i);
                ctx.fillStyle = '#6c757d';
                ctx.font = '10px sans-serif';
                ctx.fillText(valLabel.toLocaleString() + unitSuffix, 5, y + 3);
            }

            if (!records || !records.length) {
                ctx.fillStyle = '#6c757d';
                ctx.font = '14px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('No telemetry data for active filters', width / 2, height / 2 + 15);
                return;
            }

            var points = [];
            var stepX = plotWidth / (records.length > 1 ? records.length - 1 : 1);

            for (var idx = 0; idx < records.length; idx++) {
                var rec = records[idx];
                var x = records.length === 1 ? paddingLeft + plotWidth / 2 : paddingLeft + idx * stepX;
                var rawVal = 0;
                if (tab === 'mileage') rawVal = rec.km_traveled || 0;
                else if (tab === 'wear_pct') rawVal = rec.wear_percentage || 0;
                else if (tab === 'efficiency') rawVal = rec.km_per_mm || 0;
                else if (tab === 'psi') rawVal = rec.psi_monitoring || 0;
                else if (tab === 'cpk') rawVal = rec.est_cpk || 0;
                else rawVal = rec.rtd_monitoring || 0;

                var val = Math.min(maxVal, Math.max(0, rawVal));
                var yPoint = paddingTop + plotHeight - (val / maxVal) * plotHeight;
                points.push({ x: x, y: yPoint, val: rawVal, date: rec.monitor_date, serial: rec.serial_no });
            }

            // Draw Line
            ctx.beginPath();
            ctx.strokeStyle = mainColor;
            ctx.lineWidth = 2.5;
            points.forEach(function (pt, index) {
                if (index === 0) {
                    ctx.moveTo(pt.x, pt.y);
                } else {
                    ctx.lineTo(pt.x, pt.y);
                }
            });
            ctx.stroke();

            // Draw Markers
            points.forEach(function (pt) {
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI);
                ctx.fillStyle = '#ffffff';
                ctx.fill();
                ctx.strokeStyle = mainColor;
                ctx.lineWidth = 2.5;
                ctx.stroke();

                ctx.fillStyle = '#2c3e50';
                ctx.font = 'bold 10px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(pt.val.toLocaleString() + unitSuffix, pt.x, pt.y - 8);
            });
        },

        // --- Event Handlers ---

        _onSelectChartTab: function (ev) {
            ev.preventDefault();
            var tab = $(ev.currentTarget).data('tab');
            if (tab && this.active_chart_tab !== tab) {
                this.active_chart_tab = tab;
                this.renderElement();
            }
        },

        _onChangeMonitoringYear: function (ev) {
            this.selected_year = $(ev.currentTarget).val() || '';
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onChangeMonitoringPeriod: function (ev) {
            this.selected_period = $(ev.currentTarget).val() || '';
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onClearPeriodFilter: function (ev) {
            if (ev) ev.preventDefault();
            this.selected_year = '';
            this.selected_period = '';
            this.$('.js_filter_monitoring_year').val('');
            this.$('.js_filter_monitoring_period').val('');
            this._applyMonitoringFilter();
            this.renderElement();
        },

        // --- Event Handlers ---

        _onOpenMonitoringWizard: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Tire Monitoring Report Wizard',
                type: 'ir.actions.act_window',
                res_model: 'tire.monitoring.report.wizard',
                views: [[false, 'form']],
                target: 'new',
            });
        },

        _onOpenMonitoringList: function (ev) {
            ev.preventDefault();
            var domain = [];
            if (this.selected_unit_id) {
                domain.push(['vehicle_id.location_id', '=', parseInt(this.selected_unit_id)]);
            }
            this.do_action({
                name: 'Tire Inspection / Monitoring Log',
                type: 'ir.actions.act_window',
                res_model: 'dh.tire.monitoring',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        },

        _onCreateMonitoringRec: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Create Tire Monitoring Record',
                type: 'ir.actions.act_window',
                res_model: 'dh.tire.monitoring',
                views: [[false, 'form']],
                target: 'current',
            });
        },

        _onOpenMonitoringDetail: function (ev) {
            ev.preventDefault();
            var recId = $(ev.currentTarget).data('id');
            if (!recId) return;
            this.do_action({
                name: 'Tire Monitoring Record',
                type: 'ir.actions.act_window',
                res_model: 'dh.tire.monitoring',
                res_id: parseInt(recId),
                views: [[false, 'form']],
                target: 'current',
            });
        },

        _onCheckVehicleFilter: function (ev) {
            var selected = [];
            this.$('.js_check_vehicle_filter:checked').each(function () {
                selected.push($(this).val());
            });
            this.selected_vehicles = selected;
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onCheckBrandFilter: function (ev) {
            var selected = [];
            this.$('.js_check_brand_filter:checked').each(function () {
                selected.push($(this).val());
            });
            this.selected_brands = selected;
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onCheckSizeFilter: function (ev) {
            var selected = [];
            this.$('.js_check_size_filter:checked').each(function () {
                selected.push($(this).val());
            });
            this.selected_sizes = selected;
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onSearchVehicleFilter: function (ev) {
            var term = $(ev.currentTarget).val().toLowerCase();
            this.$('.vehicle-item-option').each(function () {
                var txt = $(this).text().toLowerCase();
                if (txt.indexOf(term) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        },

        _onSearchBrandFilter: function (ev) {
            var term = $(ev.currentTarget).val().toLowerCase();
            this.$('.brand-item-option').each(function () {
                var txt = $(this).text().toLowerCase();
                if (txt.indexOf(term) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        },

        _onSearchSizeFilter: function (ev) {
            var term = $(ev.currentTarget).val().toLowerCase();
            this.$('.size-item-option').each(function () {
                var txt = $(this).text().toLowerCase();
                if (txt.indexOf(term) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        },

        _onClearVehicleFilter: function (ev) {
            if (ev) ev.preventDefault();
            this.selected_vehicles = [];
            this.$('.js_check_vehicle_filter').prop('checked', false);
            this.$('.js_search_vehicle_filter').val('');
            this.$('.vehicle-item-option').show();
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onClearBrandFilter: function (ev) {
            if (ev) ev.preventDefault();
            this.selected_brands = [];
            this.$('.js_check_brand_filter').prop('checked', false);
            this.$('.js_search_brand_filter').val('');
            this.$('.brand-item-option').show();
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onClearSizeFilter: function (ev) {
            if (ev) ev.preventDefault();
            this.selected_sizes = [];
            this.$('.js_check_size_filter').prop('checked', false);
            this.$('.js_search_size_filter').val('');
            this.$('.size-item-option').show();
            this._applyMonitoringFilter();
            this.renderElement();
        },

        _onChangeFilter: function (ev) {
            this.selected_unit_id = this.$('.js_filter_unit').val() || false;
            this.selected_truck_type_id = this.$('.js_filter_truck_type').val() || false;
            var self = this;
            this._fetchDashboardData().then(function () {
                self.renderElement();
            });
        },

        _onRefreshDashboard: function (ev) {
            ev.preventDefault();
            var self = this;
            this._fetchDashboardData().then(function () {
                self.renderElement();
            });
        },

        _onOpenChassisDiagram: function (ev) {
            ev.preventDefault();
            var vehicleId = $(ev.currentTarget).data('vehicle-id');
            if (!vehicleId) return;

            var self = this;
            this._rpc({
                model: 'dh.vehicle',
                method: 'action_view_chassis_diagram',
                args: [[vehicleId]],
            }).then(function (action) {
                if (action) {
                    self.do_action(action);
                }
            });
        },

        _onExportPdfReport: function (ev) {
            ev.preventDefault();
            var self = this;
            this._rpc({
                model: 'dh.tms.dashboard',
                method: 'create',
                args: [{}],
            }).then(function (recId) {
                self._rpc({
                    model: 'dh.tms.dashboard',
                    method: 'action_print_executive_report',
                    args: [[recId]],
                }).then(function (action) {
                    if (action) {
                        self.do_action(action);
                    }
                });
            });
        },

        _onDrilldownFleet: function (ev) {
            ev.preventDefault();
            var domain = [];
            if (this.selected_unit_id) {
                domain.push(['location_id', '=', parseInt(this.selected_unit_id)]);
            }
            if (this.selected_truck_type_id) {
                domain.push(['truck_type_id', '=', parseInt(this.selected_truck_type_id)]);
            }
            this.do_action({
                name: 'Active Fleet Vehicles',
                type: 'ir.actions.act_window',
                res_model: 'dh.vehicle',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        },

        _onDrilldownMountedTires: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Mounted Tire Inventory',
                type: 'ir.actions.act_window',
                res_model: 'stock.production.lot',
                views: [[false, 'list'], [false, 'form']],
                domain: [['is_tire', '=', true], ['tire_state', '=', 'mounted']],
                target: 'current',
            });
        },

        _onDrilldownWearAlerts: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Tire Wear & PSI Risk Alerts',
                type: 'ir.actions.act_window',
                res_model: 'stock.production.lot',
                views: [[false, 'list'], [false, 'form']],
                domain: [['is_tire', '=', true], ['current_rtd', '<=', 6.0]],
                target: 'current',
            });
        },

        _onDrilldownCPKM: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Tire Usage History & CPKM',
                type: 'ir.actions.act_window',
                res_model: 'dh.tire.usage',
                views: [[false, 'list'], [false, 'form']],
                domain: [],
                target: 'current',
            });
        },

        _onDrilldownPSIAlerts: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Tire Pressure (PSI) Telemetry & Alerts',
                type: 'ir.actions.act_window',
                res_model: 'stock.production.lot',
                views: [[false, 'list'], [false, 'form']],
                domain: [['is_tire', '=', true], ['tire_state', '=', 'mounted'], ['current_psi', '<', 100]],
                target: 'current',
            });
        },

        _onOpenTrailerExchange: function (ev) {
            ev.preventDefault();
            var exchangeId = $(ev.currentTarget).data('exchange-id');
            if (!exchangeId) return;
            this.do_action({
                name: 'Trailer Exchange Detail',
                type: 'ir.actions.act_window',
                res_model: 'dh.trailer.exchange',
                res_id: exchangeId,
                views: [[false, 'form']],
                target: 'current',
            });
        },

        _onDrilldownTrailerExchanges: function (ev) {
            ev.preventDefault();
            var domain = [];
            if (this.selected_unit_id) {
                domain.push(['location_id', '=', parseInt(this.selected_unit_id)]);
            }
            this.do_action({
                name: 'Trailer Exchange History',
                type: 'ir.actions.act_window',
                res_model: 'dh.trailer.exchange',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        },

        _renderCPKBillingCharts: function () {
            var self = this;
            var summary = (self.dashboard_data && self.dashboard_data.cpk_billing_summary) || {};
            var hubData = summary.hub_chart_data || [];
            var utilStatus = summary.utilization_status || { target_met: 0, near_target: 0, under_utilized: 0 };

            // 1. Left Chart: Hub Base Revenue vs Deficit Recovery
            var canvas1 = this.$('#js_cpk_hub_revenue_canvas')[0];
            if (canvas1) {
                var ctx1 = canvas1.getContext('2d');
                var labels1 = hubData.map(function (h) { return h.name; });
                var baseData = hubData.map(function (h) { return h.base_revenue; });
                var deficitData = hubData.map(function (h) { return h.deficit_revenue; });

                if (!labels1.length) {
                    labels1 = ['No Active CPK Hubs'];
                    baseData = [0];
                    deficitData = [0];
                }

                if (window.Chart) {
                    if (self.cpk_hub_chart) self.cpk_hub_chart.destroy();
                    self.cpk_hub_chart = new window.Chart(ctx1, {
                        type: 'bar',
                        data: {
                            labels: labels1,
                            datasets: [
                                {
                                    label: 'Base Distance Revenue (Rp)',
                                    data: baseData,
                                    backgroundColor: '#1e62d0',
                                },
                                {
                                    label: 'Min-KM Deficit Recovery (Rp)',
                                    data: deficitData,
                                    backgroundColor: '#fd7e14',
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'top' },
                            scales: {
                                xAxes: [{ stacked: false }],
                                yAxes: [{ ticks: { beginAtZero: true } }]
                            }
                        }
                    });
                }
            }

            // 2. Right Chart: Vehicle Guarantee Utilization Status
            var canvas2 = this.$('#js_cpk_utilization_canvas')[0];
            if (canvas2) {
                var ctx2 = canvas2.getContext('2d');
                var utilData = [
                    utilStatus.target_met || 0,
                    utilStatus.near_target || 0,
                    utilStatus.under_utilized || 0
                ];

                if (window.Chart) {
                    if (self.cpk_util_chart) self.cpk_util_chart.destroy();
                    self.cpk_util_chart = new window.Chart(ctx2, {
                        type: 'doughnut',
                        data: {
                            labels: ['Target Met (≥ 2.5k KM)', 'Near Target (2k - 2.5k KM)', 'Under-Utilized (< 2k KM)'],
                            datasets: [{
                                data: utilData,
                                backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'bottom' }
                        }
                    });
                }
            }
        },

        _onOpenBillingWizard: function (ev) {
            ev.preventDefault();
            var ctx = {};
            if (this.selected_unit_id) {
                ctx.default_operating_unit_id = parseInt(this.selected_unit_id);
            }
            this.do_action({
                name: 'CPK Billing Recap Wizard',
                type: 'ir.actions.act_window',
                res_model: 'billing.recap.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: ctx,
            });
        },

        _renderAssetValuationCharts: function () {
            var self = this;
            var summary = (self.dashboard_data && self.dashboard_data.asset_valuation_summary) || {};
            var hubData = summary.hub_asset_data || [];
            var statusData = summary.status_asset_data || { mounted: 0, stock: 0, scrapped: 0 };

            // 1. Left Stacked Bar Chart: Asset Valuation per Operating Hub
            var canvas1 = this.$('#js_asset_hub_valuation_canvas')[0];
            if (canvas1) {
                var ctx1 = canvas1.getContext('2d');
                var labels1 = hubData.map(function (h) { return h.name; });
                var netData = hubData.map(function (h) { return h.net; });
                var deprData = hubData.map(function (h) { return h.depr; });

                if (!labels1.length) {
                    labels1 = ['No Active Asset Data'];
                    netData = [0];
                    deprData = [0];
                }

                if (window.Chart) {
                    if (self.asset_hub_chart) self.asset_hub_chart.destroy();
                    self.asset_hub_chart = new window.Chart(ctx1, {
                        type: 'bar',
                        data: {
                            labels: labels1,
                            datasets: [
                                {
                                    label: 'Net Book Value (Rp)',
                                    data: netData,
                                    backgroundColor: '#28a745',
                                },
                                {
                                    label: 'Accumulated Depreciation (Rp)',
                                    data: deprData,
                                    backgroundColor: '#fd7e14',
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'top' },
                            scales: {
                                xAxes: [{ stacked: true }],
                                yAxes: [{ stacked: true, ticks: { beginAtZero: true } }]
                            }
                        }
                    });
                }
            }

            // 2. Right Doughnut Chart: Capital Asset Distribution by Status
            var canvas2 = this.$('#js_asset_status_valuation_canvas')[0];
            if (canvas2) {
                var ctx2 = canvas2.getContext('2d');
                var values2 = [
                    statusData.mounted || 0,
                    statusData.stock || 0,
                    statusData.scrapped || 0
                ];

                if (window.Chart) {
                    if (self.asset_status_chart) self.asset_status_chart.destroy();
                    self.asset_status_chart = new window.Chart(ctx2, {
                        type: 'doughnut',
                        data: {
                            labels: ['Mounted Fleet (Rp)', 'Depot Stock (Rp)', 'Scrapped/Afkir (Rp)'],
                            datasets: [{
                                data: values2,
                                backgroundColor: ['#1e62d0', '#28a745', '#dc3545']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'bottom' }
                        }
                    });
                }
            }
        },

        _onOpenAssetValuationWizard: function (ev) {
            ev.preventDefault();
            var ctx = {};
            if (this.selected_unit_id) {
                ctx.default_operating_unit_ids = [[6, 0, [parseInt(this.selected_unit_id)]]];
                ctx.default_all_operating_units = false;
            }
            this.do_action({
                name: 'Tire Asset Valuation & Depreciation Wizard',
                type: 'ir.actions.act_window',
                res_model: 'tire.asset.valuation.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: ctx,
            });
        }
    });

    core.action_registry.add('dh_tms_intelligence_dashboard_main', TmsIntelligenceDashboard);

    return TmsIntelligenceDashboard;
});

