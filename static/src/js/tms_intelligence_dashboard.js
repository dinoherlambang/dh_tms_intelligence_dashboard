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
            'click .js_filter_wear_state': '_onFilterWearState',
            'click .js_clear_wear_filter': '_onClearWearFilter',
            'click .js_export_pdf_report': '_onExportPdfReport',

            // Brand Panel Interactive Filters & Duel Handlers
            'change .js_filter_brand_category': '_onFilterBrandCategory',
            'change .js_filter_brand_sort': '_onSortBrandPerformance',
            'change .js_select_brand_duel_a': '_onSelectBrandDuelA',
            'change .js_select_brand_duel_b': '_onSelectBrandDuelB',
            'click .js_toggle_pattern_expand': '_onTogglePatternExpand',

            // Interactive Drilldown Handlers
            'click .js_drilldown_fleet': '_onDrilldownFleet',
            'click .js_drilldown_mounted_tires': '_onDrilldownMountedTires',
            'click .js_drilldown_wear_alerts': '_onDrilldownWearAlerts',
            'click .js_drilldown_psi_alerts': '_onDrilldownPSIAlerts',
            'click .js_drilldown_cpkm': '_onDrilldownCPKM',
            'click .js_drilldown_brand': '_onDrilldownBrand',
            'click .js_open_trailer_exchange': '_onOpenTrailerExchange',
            'click .js_drilldown_trailer_exchanges': '_onDrilldownTrailerExchanges',
            'click .js_open_billing_wizard': '_onOpenBillingWizard',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.kpis = {};
            this.wear_distribution = {};
            this.psi_distribution = {};
            this.trailer_coupling_summary = {};
            this.recent_trailer_exchanges = [];
            this.cpk_billing_summary = {};
            this.min_km_deficit_vehicles = [];
            this.vehicle_grid = [];
            this.filtered_vehicle_grid = [];
            this.alert_queue = [];
            this.brand_performance = [];
            this.filtered_brand_performance = [];
            this.best_brand_leader = '-';
            this.brand_duel_a = false;
            this.brand_duel_b = false;
            this.selected_brand_a_name = '';
            this.selected_brand_b_name = '';
            this.rotation_recommendations = [];
            this.replacement_forecast = [];
            this.filters = {};
            this.selected_unit_id = false;
            this.selected_truck_type_id = false;
            this.active_filter_state = false;
            this.active_brand_category = '';
            this.active_brand_sort = 'wear_rate';
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
                self.psi_distribution = data.psi_distribution || {};
                self.trailer_coupling_summary = data.trailer_coupling_summary || {};
                self.recent_trailer_exchanges = data.recent_trailer_exchanges || [];
                self.cpk_billing_summary = data.cpk_billing_summary || {};
                self.min_km_deficit_vehicles = data.min_km_deficit_vehicles || [];
                self.vehicle_grid = data.vehicle_grid || [];
                self.alert_queue = data.alert_queue || [];
                self.brand_performance = data.brand_performance || [];
                self.best_brand_leader = data.best_brand_leader || '-';
                self.rotation_recommendations = data.rotation_recommendations || [];
                self.replacement_forecast = data.replacement_forecast || [];

                self._applyLocalWearFilter();
                self._applyBrandFilterAndSort();
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

        _applyBrandFilterAndSort: function () {
            var self = this;
            var list = (self.brand_performance || []).slice();

            // 1. Filter by Category
            if (self.active_brand_category === 'original') {
                list = list.filter(function (b) { return b.original_count > 0; });
            } else if (self.active_brand_category === 'retread') {
                list = list.filter(function (b) { return b.retread_count > 0; });
            }

            // 2. Multi-Dimensional Sort (No Price Metrics)
            if (self.active_brand_sort === 'wear_rate') {
                list.sort(function (a, b) {
                    return b.km_per_mm - a.km_per_mm;
                });
            } else if (self.active_brand_sort === 'retread') {
                list.sort(function (a, b) {
                    return b.retread_pct - a.retread_pct;
                });
            } else if (self.active_brand_sort === 'failure') {
                list.sort(function (a, b) {
                    return a.failure_pct - b.failure_pct;
                });
            } else if (self.active_brand_sort === 'count') {
                list.sort(function (a, b) {
                    return b.count - a.count;
                });
            } else {
                // Sort by Mileage (KM)
                list.sort(function (a, b) {
                    return b.avg_km - a.avg_km;
                });
            }

            self.filtered_brand_performance = list;

            // Preserve Brand Duel selection references
            if (self.selected_brand_a_name) {
                self.brand_duel_a = list.find(function (b) { return b.brand === self.selected_brand_a_name; }) || false;
            }
            if (self.selected_brand_b_name) {
                self.brand_duel_b = list.find(function (b) { return b.brand === self.selected_brand_b_name; }) || false;
            }
        },

        _onSelectBrandDuelA: function (ev) {
            ev.preventDefault();
            var bName = $(ev.currentTarget).val();
            this.selected_brand_a_name = bName;
            this.brand_duel_a = (this.brand_performance || []).find(function (b) { return b.brand === bName; }) || false;
            this.renderElement();
        },

        _onSelectBrandDuelB: function (ev) {
            ev.preventDefault();
            var bName = $(ev.currentTarget).val();
            this.selected_brand_b_name = bName;
            this.brand_duel_b = (this.brand_performance || []).find(function (b) { return b.brand === bName; }) || false;
            this.renderElement();
        },

        _onTogglePatternExpand: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var bName = $(ev.currentTarget).data('brand-name');
            if (!bName) return;
            var sanitizeId = bName.replace(/\s+/g, '_');
            var $row = this.$('#pattern_row_' + sanitizeId);
            if ($row.length) {
                $row.toggleClass('d-none');
                var $icon = $(ev.currentTarget).find('i');
                if ($row.hasClass('d-none')) {
                    $icon.removeClass('fa-minus-square-o').addClass('fa-plus-square-o');
                } else {
                    $icon.removeClass('fa-plus-square-o').addClass('fa-minus-square-o');
                }
            }
        },

        _onFilterBrandCategory: function (ev) {
            ev.preventDefault();
            this.active_brand_category = $(ev.currentTarget).val() || '';
            this._applyBrandFilterAndSort();
            this.renderElement();
        },

        _onSortBrandPerformance: function (ev) {
            ev.preventDefault();
            this.active_brand_sort = $(ev.currentTarget).val() || 'wear_rate';
            this._applyBrandFilterAndSort();
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
        }
    });

    core.action_registry.add('dh_tms_intelligence_dashboard_main', TmsIntelligenceDashboard);

    return TmsIntelligenceDashboard;
});
