odoo.define('dh_tms_intellegence_dashboard.Dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var TmsIntelligenceDashboard = AbstractAction.extend({
        template: 'dh_tms_intellegence_dashboard.MainDashboard',
        events: {
            'click .js_refresh_dashboard': '_onRefreshDashboard',
            'click .js_open_chassis_diagram': '_onOpenChassisDiagram',
            'change .js_filter_unit': '_onChangeFilter',
            'change .js_filter_truck_type': '_onChangeFilter',
            'click .js_filter_wear_state': '_onFilterWearState',
            'click .js_clear_wear_filter': '_onClearWearFilter',
            'click .js_export_pdf_report': '_onExportPdfReport',

            // Interactive Drilldown Handlers
            'click .js_drilldown_fleet': '_onDrilldownFleet',
            'click .js_drilldown_mounted_tires': '_onDrilldownMountedTires',
            'click .js_drilldown_wear_alerts': '_onDrilldownWearAlerts',
            'click .js_drilldown_cpkm': '_onDrilldownCPKM',
            'click .js_drilldown_brand': '_onDrilldownBrand',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.kpis = {};
            this.wear_distribution = {};
            this.vehicle_grid = [];
            this.filtered_vehicle_grid = [];
            this.alert_queue = [];
            this.brand_performance = [];
            this.rotation_recommendations = [];
            this.replacement_forecast = [];
            this.filters = {};
            this.selected_unit_id = false;
            this.selected_truck_type_id = false;
            this.active_filter_state = false;
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
                self.wear_distribution = data.wear_distribution || {};
                self.vehicle_grid = data.vehicle_grid || [];
                self.alert_queue = data.alert_queue || [];
                self.brand_performance = data.brand_performance || [];
                self.rotation_recommendations = data.rotation_recommendations || [];
                self.replacement_forecast = data.replacement_forecast || [];

                self._applyLocalWearFilter();
            }).catch(function (error) {
                console.error('[DH_TMS_DASHBOARD] Error fetching dashboard data:', error);
            });
        },

        _applyLocalWearFilter: function () {
            var self = this;
            if (!self.active_filter_state) {
                self.filtered_vehicle_grid = self.vehicle_grid;
            } else {
                self.filtered_vehicle_grid = self.vehicle_grid.filter(function (v) {
                    return v.health_state === self.active_filter_state;
                });
            }
        },

        _onChangeFilter: function (ev) {
            this.selected_unit_id = this.$('.js_filter_unit').val() || false;
            this.selected_truck_type_id = this.$('.js_filter_truck_type').val() || false;
            var self = this;
            this._fetchDashboardData().then(function () {
                self.renderElement();
            });
        },

        _onFilterWearState: function (ev) {
            ev.preventDefault();
            var state = $(ev.currentTarget).data('state');
            this.active_filter_state = state;
            this._applyLocalWearFilter();
            this.renderElement();
        },

        _onClearWearFilter: function (ev) {
            if (ev) ev.preventDefault();
            this.active_filter_state = false;
            this._applyLocalWearFilter();
            this.renderElement();
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
                self.do_action({
                    type: 'ir.actions.report',
                    report_name: 'dh_tms_intellegence_dashboard.report_tms_dashboard_executive',
                    report_type: 'qweb-pdf',
                    res_model: 'dh.tms.dashboard',
                    res_id: recId,
                });
            });
        },

        // --- Interactive Drilldown Handlers ---

        // KPI 1: Active Fleet Units Drilldown -> Vehicle List View
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

        // KPI 2: Active Mounted Tires Drilldown -> Serial Numbers List View
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

        // KPI 3: Wear & PSI Alerts Drilldown -> Tire Serial Numbers List View
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

        // KPI 4: Fleet CPKM Drilldown -> Tire Usage View
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

        // Brand Table Row Drilldown -> Serial Numbers by Brand
        _onDrilldownBrand: function (ev) {
            ev.preventDefault();
            var brandId = $(ev.currentTarget).data('brand-id');
            var brandName = $(ev.currentTarget).data('brand-name');
            var domain = [['is_tire', '=', true]];
            
            if (brandId) {
                domain.push('|', ['product_id.product_brand_id', '=', brandId], ['product_id.brand_id', '=', brandId]);
            } else if (brandName) {
                domain.push(['product_id.name', 'ilike', brandName]);
            }

            this.do_action({
                name: 'Tire Inventory - Brand: ' + (brandName || 'All'),
                type: 'ir.actions.act_window',
                res_model: 'stock.production.lot',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        }
    });

    core.action_registry.add('dh_tms_intellegence_dashboard_main', TmsIntelligenceDashboard);

    return TmsIntelligenceDashboard;
});
