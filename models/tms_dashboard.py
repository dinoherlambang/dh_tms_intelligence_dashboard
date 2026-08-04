# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class DhTmsDashboard(models.TransientModel):
    _name = 'dh.tms.dashboard'
    _description = 'TMS Fleet & Tire Intelligence Dashboard'

    def action_print_executive_report(self):
        self.ensure_one()
        return self.env.ref('dh_tms_intelligence_dashboard.action_report_tms_dashboard_executive').report_action(self)

    @api.model
    def get_intelligence_dashboard_data(self, unit_id=None, truck_type_id=None):
        """
        Returns real-time intelligence metrics for the TMS Fleet & Tire Dashboard
        with dynamic hub/vehicle type filtering, predictive lifespan forecaster,
        automated rotation recommendations, drilldown targets, and interactive brand comparison.
        """
        Vehicle = self.env['dh.vehicle']
        Lot = self.env['stock.production.lot']
        TruckType = self.env['dh.truck.type']

        # 1. Available Filter Dropdown Options
        operating_units = []
        if 'operating.unit' in self.env:
            ou_records = self.env['operating.unit'].search([])
            operating_units = [{'id': ou.id, 'name': ou.name} for ou in ou_records]

        tt_records = TruckType.search([])
        truck_types = [{'id': tt.id, 'name': tt.name} for tt in tt_records]

        # 2. Filter Vehicles based on Location (Operating Unit) / Truck Type selection
        vehicle_domain = []
        if unit_id:
            vehicle_domain.append(('location_id', '=', int(unit_id)))
        if truck_type_id:
            vehicle_domain.append(('truck_type_id', '=', int(truck_type_id)))

        vehicles = Vehicle.search(vehicle_domain)
        total_vehicles = len(vehicles)
        active_vehicles = len(vehicles.filtered(lambda v: v.active if hasattr(v, 'active') else True))

        # 3. Vehicle Quick-Grid & Telemetry Analytics
        vehicle_grid = []
        total_mounted_tires = 0
        total_expected_tires = 0
        critical_tires_count = 0
        warning_tires_count = 0
        normal_tires_count = 0

        rotation_recommendations = []
        replacement_forecast = []

        for v in vehicles:
            try:
                chassis_data = v.get_chassis_detail_report_data()
            except Exception:
                chassis_data = {'tires_by_position': {}}

            tires_dict = chassis_data.get('tires_by_position', {})
            mounted_count = len(tires_dict)
            expected_count = v.expected_tire_count or (v.truck_type_id.jumlah_ban if v.truck_type_id else 0)
            
            v_critical = 0
            v_warning = 0
            v_normal = 0

            rtd_by_pos = {}

            for code, t_info in tires_dict.items():
                alert = t_info.get('alert_state', 'normal')
                gr1 = float(t_info.get('gr1') or 0.0)
                gr2 = float(t_info.get('gr2') or 0.0)
                gr3 = float(t_info.get('gr3') or 0.0)
                gr4 = float(t_info.get('gr4') or 0.0)
                
                grooves = [g for g in [gr1, gr2, gr3, gr4] if g > 0]
                min_rtd = min(grooves) if grooves else 0.0
                rtd_by_pos[str(code)] = min_rtd

                if alert == 'critical':
                    v_critical += 1
                    critical_tires_count += 1
                    replacement_forecast.append({
                        'vehicle_id': v.id,
                        'vehicle_name': v.name,
                        'pos_code': code,
                        'serial_number': t_info.get('serial_number', '-'),
                        'rtd': min_rtd,
                        'est_days': 'Immediate (< 7 Days)',
                        'urgency': 'critical'
                    })
                elif alert == 'warning':
                    v_warning += 1
                    warning_tires_count += 1
                    replacement_forecast.append({
                        'vehicle_id': v.id,
                        'vehicle_name': v.name,
                        'pos_code': code,
                        'serial_number': t_info.get('serial_number', '-'),
                        'rtd': min_rtd,
                        'est_days': '15 - 30 Days',
                        'urgency': 'warning'
                    })
                else:
                    v_normal += 1
                    normal_tires_count += 1

            # Check Steer Pair Variance (P1 vs P2)
            p1_rtd = rtd_by_pos.get('1') or rtd_by_pos.get('P1') or 0.0
            p2_rtd = rtd_by_pos.get('2') or rtd_by_pos.get('P2') or 0.0
            if p1_rtd > 0 and p2_rtd > 0 and abs(p1_rtd - p2_rtd) >= 1.5:
                rotation_recommendations.append({
                    'vehicle_id': v.id,
                    'vehicle_name': v.name,
                    'reason': _('Steer axle RTD variance >= 1.5 mm (P1: %.1f mm vs P2: %.1f mm)') % (p1_rtd, p2_rtd),
                    'action': _('Swap Steer Tires P1 <-> P2 to equalize tread wear'),
                })

            total_mounted_tires += mounted_count
            total_expected_tires += expected_count

            # Overall vehicle health status
            if v_critical > 0:
                health_state = 'critical'
            elif v_warning > 0:
                health_state = 'warning'
            elif mounted_count == 0:
                health_state = 'unmounted'
            else:
                health_state = 'normal'

            vehicle_grid.append({
                'id': v.id,
                'name': v.name,
                'nopol': v.name,
                'nomor_lambung': v.nomor_lambung or '-',
                'truck_type': v.truck_type_id.name if v.truck_type_id else '-',
                'axle_count': v.axle_count,
                'mounted_count': mounted_count,
                'expected_count': expected_count,
                'health_state': health_state,
                'critical_count': v_critical,
                'warning_count': v_warning,
            })

        # 4. Priority Alert Queue
        alert_queue = []
        for v_item in vehicle_grid:
            if v_item['critical_count'] > 0:
                alert_queue.append({
                    'severity': 'critical',
                    'vehicle_id': v_item['id'],
                    'vehicle_name': v_item['name'],
                    'title': _('Critical Tire Replacement Needed'),
                    'message': _('Vehicle %s has %d tire(s) with RTD <= 3.0 mm. Order replacement stock.') % (v_item['name'], v_item['critical_count']),
                })
            elif v_item['warning_count'] > 0:
                alert_queue.append({
                    'severity': 'warning',
                    'vehicle_id': v_item['id'],
                    'vehicle_name': v_item['name'],
                    'title': _('Tire Wear Warning'),
                    'message': _('Vehicle %s has %d tire(s) nearing limit (RTD 3.1 - 6.0 mm).') % (v_item['name'], v_item['warning_count']),
                })

        # 5. Advanced Dynamic Brand Performance Benchmarking & Category Comparison
        tire_lots = Lot.search([('is_tire', '=', True)])
        brand_data = {}
        total_fleet_cost = 0.0
        total_fleet_km = 0.0

        for lot in tire_lots:
            b_name = '-'
            brand_obj_id = False
            if hasattr(lot, 'product_id') and lot.product_id:
                if hasattr(lot.product_id, 'product_brand_id') and lot.product_id.product_brand_id:
                    b_name = lot.product_id.product_brand_id.name
                    brand_obj_id = lot.product_id.product_brand_id.id
                elif hasattr(lot.product_id, 'brand_id') and lot.product_id.brand_id:
                    b_name = lot.product_id.brand_id.name
                    brand_obj_id = lot.product_id.brand_id.id
                elif lot.product_id.name:
                    b_name = lot.product_id.name

            cost = getattr(lot.product_id, 'standard_price', 0.0) or 0.0
            km = getattr(lot, 'total_mileage', 0.0) or getattr(lot, 'total_km', 0.0) or 0.0

            total_fleet_cost += cost
            total_fleet_km += km

            t_type = getattr(lot, 'tire_type', 'original') or 'original'

            if b_name not in brand_data:
                brand_data[b_name] = {
                    'count': 0,
                    'original_count': 0,
                    'retread_count': 0,
                    'total_cost': 0.0,
                    'total_km': 0.0,
                    'brand_id': brand_obj_id,
                }
            
            brand_data[b_name]['count'] += 1
            if t_type == 'retread':
                brand_data[b_name]['retread_count'] += 1
            else:
                brand_data[b_name]['original_count'] += 1

            brand_data[b_name]['total_cost'] += cost
            brand_data[b_name]['total_km'] += km

        brand_performance = []
        max_brand_km = 1.0
        min_cpkm_val = 999999.0
        best_brand_leader = False

        for b_name, b_info in brand_data.items():
            avg_km = round(b_info['total_km'] / b_info['count'], 1) if b_info['count'] > 0 else 0.0
            cpkm_val = round(b_info['total_cost'] / b_info['total_km'], 2) if b_info['total_km'] > 0 else 0.0
            
            if avg_km > max_brand_km:
                max_brand_km = avg_km
            if cpkm_val > 0 and cpkm_val < min_cpkm_val:
                min_cpkm_val = cpkm_val
                best_brand_leader = b_name

            brand_performance.append({
                'brand': b_name,
                'brand_id': b_info['brand_id'],
                'count': b_info['count'],
                'original_count': b_info['original_count'],
                'retread_count': b_info['retread_count'],
                'avg_km': avg_km,
                'cpkm_val': cpkm_val,
                'cost_per_km': f"Rp {cpkm_val} / km" if cpkm_val > 0 else "-",
            })

        for b in brand_performance:
            b['bar_pct'] = round((b['avg_km'] / max_brand_km * 100), 1) if max_brand_km > 0 else 0.0
            if b['cpkm_val'] > 0 and b['brand'] == best_brand_leader:
                b['badge_text'] = '🏆 BEST CPKM LEADER'
                b['badge_class'] = 'badge-success'
            elif b['cpkm_val'] > 0:
                b['badge_text'] = 'OPTIMAL'
                b['badge_class'] = 'badge-info'
            else:
                b['badge_text'] = 'NO USAGE LOG'
                b['badge_class'] = 'badge-secondary'

        brand_performance.sort(key=lambda x: x['avg_km'], reverse=True)

        if total_fleet_km > 0 and total_fleet_cost > 0:
            avg_fleet_cpkm = f"Rp {round(total_fleet_cost / total_fleet_km, 2)} / km"
        else:
            avg_fleet_cpkm = "-"

        # 6. Donut Geometry Calculations
        total_tires_tracked = total_mounted_tires if total_mounted_tires > 0 else 0
        normal_pct = round(normal_tires_count / total_tires_tracked * 100, 1) if total_tires_tracked > 0 else 0.0
        warning_pct = round(warning_tires_count / total_tires_tracked * 100, 1) if total_tires_tracked > 0 else 0.0
        critical_pct = round(critical_tires_count / total_tires_tracked * 100, 1) if total_tires_tracked > 0 else 0.0

        circ = 251.32
        normal_dash = round((normal_pct / 100.0) * circ, 2)
        warning_dash = round((warning_pct / 100.0) * circ, 2)
        critical_dash = round((critical_pct / 100.0) * circ, 2)

        return {
            'filters': {
                'operating_units': operating_units,
                'truck_types': truck_types,
                'selected_unit_id': unit_id,
                'selected_truck_type_id': truck_type_id,
            },
            'kpis': {
                'total_vehicles': total_vehicles,
                'active_vehicles': active_vehicles,
                'operational_pct': round((active_vehicles / total_vehicles * 100), 1) if total_vehicles > 0 else 100.0,
                'total_mounted_tires': total_mounted_tires,
                'total_expected_tires': total_expected_tires,
                'critical_tires': critical_tires_count,
                'warning_tires': warning_tires_count,
                'normal_tires': normal_tires_count,
                'avg_cpkm': avg_fleet_cpkm,
            },
            'wear_distribution': {
                'normal_pct': normal_pct,
                'warning_pct': warning_pct,
                'critical_pct': critical_pct,
                'normal_dash': normal_dash,
                'warning_dash': warning_dash,
                'critical_dash': critical_dash,
                'circumference': circ,
            },
            'vehicle_grid': vehicle_grid,
            'alert_queue': alert_queue[:10],
            'brand_performance': brand_performance,
            'best_brand_leader': best_brand_leader or '-',
            'rotation_recommendations': rotation_recommendations[:5],
            'replacement_forecast': replacement_forecast[:5],
        }
