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
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.kpis = {};
            this.wear_distribution = {};
            this.vehicle_grid = [];
            this.alert_queue = [];
            this.brand_performance = [];
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
            }).then(function (data) {
                self.kpis = data.kpis || {};
                self.wear_distribution = data.wear_distribution || {};
                self.vehicle_grid = data.vehicle_grid || [];
                self.alert_queue = data.alert_queue || [];
                self.brand_performance = data.brand_performance || [];
            }).catch(function (error) {
                console.error('[DH_TMS_DASHBOARD] Error fetching dashboard data:', error);
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

            this._rpc({
                model: 'dh.vehicle',
                method: 'action_view_chassis_diagram',
                args: [[vehicleId]],
            }).then(function (action) {
                if (action) {
                    self.do_action(action);
                }
            });
        }
    });

    core.action_registry.add('dh_tms_intellegence_dashboard_main', TmsIntelligenceDashboard);

    return TmsIntelligenceDashboard;
});
