# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from datetime import date

class DhTmsDashboard(models.TransientModel):
    _name = 'dh.tms.dashboard'
    _description = 'TMS Fleet & Tire Intelligence Dashboard'

    def action_print_executive_report(self):
        self.ensure_one()
        if not self.env.user.has_group('dh_tms_intelligence_dashboard.group_tms_dashboard_manager'):
            raise AccessError(_("Access Restricted: Only TMS Dashboard Managers can print the Executive Report."))
        return self.env.ref('dh_tms_intelligence_dashboard.action_report_tms_dashboard_executive').report_action(self)

    @api.model
    def get_intelligence_dashboard_data(self, unit_id=None, truck_type_id=None):
        """
        Returns real-time intelligence metrics for the TMS Fleet & Tire Dashboard
        with dynamic hub/vehicle type filtering, predictive lifespan forecaster,
        automated rotation recommendations, drilldown targets, interactive brand comparison,
        Tire Pressure (PSI) Matrix, Trailer Exchange Monitor, and CPK Billing / Min-KM Deficit Telemetry.
        """
        if not self.env.user.has_group('dh_tms_intelligence_dashboard.group_tms_dashboard_manager'):
            raise AccessError(_("Access Restricted: Only TMS Dashboard Managers can view the Intelligence Dashboard."))

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

        # Tire Pressure (PSI) Analytics Counters
        normal_psi_count = 0
        low_psi_count = 0
        critical_psi_count = 0

        rotation_recommendations = []
        replacement_forecast = []
        alert_queue = []

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

                # Tire Pressure Telemetry Evaluation
                psi_val = float(t_info.get('press_monitoring') or t_info.get('press') or 0.0)
                if psi_val >= 100.0:
                    normal_psi_count += 1
                elif psi_val >= 85.0:
                    low_psi_count += 1
                    alert_queue.append({
                        'severity': 'warning',
                        'vehicle_id': v.id,
                        'vehicle_name': v.name,
                        'title': _('Low Tire Pressure (PSI) Warning'),
                        'message': _('Vehicle %s tire pos %s (Serial %s) pressure is low (%.1f PSI). Inflate to standard.') % (
                            v.name, code, t_info.get('serial_number', '-'), psi_val
                        ),
                    })
                elif psi_val > 0.0:
                    critical_psi_count += 1
                    alert_queue.append({
                        'severity': 'critical',
                        'vehicle_id': v.id,
                        'vehicle_name': v.name,
                        'title': _('Critical Tire Under-Inflation'),
                        'message': _('Vehicle %s tire pos %s (Serial %s) has critical pressure loss (%.1f PSI). Inspect for punctures.') % (
                            v.name, code, t_info.get('serial_number', '-'), psi_val
                        ),
                    })

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

        # 4. Priority Alert Queue for Wear Thresholds
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

        # 5. Trailer Coupling & Exchange Telemetry
        total_heads = len(vehicles.filtered(lambda v: v.is_head))
        total_trailers = len(vehicles.filtered(lambda v: v.is_trailer))
        connected_trailers = len(vehicles.filtered(lambda v: v.is_trailer and v.head_id))
        uncoupled_trailers = total_trailers - connected_trailers

        recent_trailer_exchanges = []
        if 'dh.trailer.exchange' in self.env:
            ex_domain = []
            if unit_id:
                ex_domain.append(('location_id', '=', int(unit_id)))
            ex_records = self.env['dh.trailer.exchange'].search(
                ex_domain, order='date desc, id desc', limit=5
            )
            for ex in ex_records:
                recent_trailer_exchanges.append({
                    'id': ex.id,
                    'name': ex.name,
                    'date': fields.Datetime.to_string(ex.date) if ex.date else '',
                    'head_name': ex.head_vehicle_id.name if ex.head_vehicle_id else '-',
                    'previous_trailer': ex.previous_trailer_id.name if ex.previous_trailer_id else '-',
                    'new_trailer': ex.new_trailer_id.name if ex.new_trailer_id else '-',
                    'odometer': ex.odometer or 0.0,
                    'location': ex.location_id.name if ex.location_id else '-',
                    'state': ex.state or 'draft',
                })

        # 6. CPK Billing Revenue Projections & Min-KM Floor Deficit Telemetry
        date_to = fields.Date.today()
        try:
            if date_to.day >= 25:
                date_from = date_to.replace(day=24)
            else:
                prev_month = date_to.month - 1 if date_to.month > 1 else 12
                prev_year = date_to.year if date_to.month > 1 else date_to.year - 1
                date_from = date(prev_year, prev_month, 24)
        except Exception:
            date_from = date_to

        cpk_billing_hubs = 0
        total_projected_billing = 0.0
        total_min_km_adjustment = 0.0
        min_km_deficit_vehicles = []

        hub_chart_data = []
        utilization_status = {
            'target_met': 0,
            'near_target': 0,
            'under_utilized': 0,
        }

        if 'operating.unit' in self.env:
            ou_domain = [('is_cpk_billing', '=', True)]
            if unit_id:
                ou_domain.append(('id', '=', int(unit_id)))
            cpk_ous = self.env['operating.unit'].search(ou_domain)
            cpk_billing_hubs = len(cpk_ous)

            for ou in cpk_ous:
                enable_min_km = getattr(ou, 'enable_min_km_guarantee', True)
                min_threshold = getattr(ou, 'min_km_threshold', 2500.0) if enable_min_km else 0.0
                
                cpk_rate = 120.0
                if 'dh.tms.pricing' in self.env:
                    pricing = self.env['dh.tms.pricing'].search([('operating_unit_id', '=', ou.id)], limit=1)
                    if not pricing:
                        pricing = self.env['dh.tms.pricing'].search([], limit=1)
                    if pricing and pricing.cpk_rate > 0:
                        cpk_rate = pricing.cpk_rate

                ou_vehicles = vehicles.filtered(lambda v: v.location_id.id == ou.id) if unit_id else Vehicle.search([('location_id', '=', ou.id)])
                
                ou_base_rev = 0.0
                ou_deficit_rev = 0.0

                for v in ou_vehicles:
                    tires_count = v.tire_count or v.expected_tire_count or (16 if v.is_trailer else 10)
                    
                    usages = self.env['dh.tire.usage'].search([
                        ('vehicle_id', '=', v.id),
                        ('install_date', '<=', date_to),
                        '|', ('removal_date', '=', False), ('removal_date', '>=', date_from)
                    ])

                    km_aktual = 0.0
                    monitorings = self.env['dh.tire.monitoring'].search([
                        ('vehicle_id', '=', v.id),
                        ('monitor_date', '>=', date_from),
                        ('monitor_date', '<=', date_to)
                    ], order='monitor_date desc')

                    if monitorings:
                        latest_m = monitorings[0]
                        earliest_m = monitorings[-1]
                        km_aktual = max(0.0, (latest_m.monitor_odometer or 0.0) - (earliest_m.install_odometer or 0.0))
                    elif usages:
                        valid_kms = [u.km_used for u in usages if u.km_used > 0]
                        km_aktual = max(valid_kms) if valid_kms else 0.0

                    base_val = km_aktual * tires_count * cpk_rate
                    ou_base_rev += base_val
                    billed_km = max(km_aktual, min_threshold) if min_threshold > 0 else km_aktual
                    v_billing = billed_km * tires_count * cpk_rate
                    total_projected_billing += v_billing

                    if km_aktual >= 2500.0:
                        utilization_status['target_met'] += 1
                    elif km_aktual >= 2000.0:
                        utilization_status['near_target'] += 1
                    else:
                        utilization_status['under_utilized'] += 1

                    if min_threshold > 0 and km_aktual < min_threshold:
                        deficit_km = min_threshold - km_aktual
                        adjustment_val = deficit_km * tires_count * cpk_rate
                        ou_deficit_rev += adjustment_val
                        total_min_km_adjustment += adjustment_val

                        min_km_deficit_vehicles.append({
                            'vehicle_id': v.id,
                            'name': v.name,
                            'nomor_lambung': v.nomor_lambung or v.name,
                            'hub_name': ou.name,
                            'km_aktual': round(km_aktual, 1),
                            'min_threshold': min_threshold,
                            'deficit_km': round(deficit_km, 1),
                            'tire_count': tires_count,
                            'cpk_rate': cpk_rate,
                            'adjustment_val': round(adjustment_val, 2),
                            'adjustment_str': f"Rp {round(adjustment_val, 0):,.0f}",
                        })

                hub_chart_data.append({
                    'name': ou.name,
                    'base_revenue': round(ou_base_rev, 2),
                    'deficit_revenue': round(ou_deficit_rev, 2),
                    'total_revenue': round(ou_base_rev + ou_deficit_rev, 2),
                })

        # 7. Tire Monitoring Report Telemetry Query
        monitoring_domain = []
        if unit_id:
            monitoring_domain.append(('vehicle_id.location_id', '=', int(unit_id)))
        if truck_type_id:
            monitoring_domain.append(('vehicle_id.truck_type_id', '=', int(truck_type_id)))

        monitoring_recs = self.env['dh.tire.monitoring'].search(monitoring_domain, order='monitor_date desc, id desc', limit=150)

        monitoring_list = []
        brands_set = set()
        sizes_set = set()

        for m in monitoring_recs:
            brand_val = m.tire_brand or (m.lot_id.product_id.product_brand_id.name if m.lot_id and m.lot_id.product_id and hasattr(m.lot_id.product_id, 'product_brand_id') and m.lot_id.product_id.product_brand_id else 'Unbranded')
            size_val = m.tire_size or (m.lot_id.product_id.name if m.lot_id and m.lot_id.product_id else 'Standard')

            if brand_val:
                brands_set.add(brand_val)
            if size_val:
                sizes_set.add(size_val)

            monitoring_list.append({
                'id': m.id,
                'name': m.name or 'Monitoring',
                'monitor_date': fields.Date.to_string(m.monitor_date) if m.monitor_date else '',
                'serial_no': m.lot_id.name if m.lot_id else '-',
                'tire_brand': brand_val,
                'tire_type': m.tire_type or 'original',
                'tire_size': size_val,
                'vehicle_name': m.vehicle_id.nomor_lambung or m.vehicle_id.name if m.vehicle_id else '-',
                'position_name': m.position_id.name if m.position_id else '-',
                'km_traveled': m.km_traveled or 0.0,
                'rtd_monitoring': m.rtd_monitoring or 0.0,
                'install_rtd': m.install_rtd or 0.0,
                'rtd_used': m.rtd_used or 0.0,
                'wear_percentage': m.wear_percentage or 0.0,
                'psi_monitoring': m.psi_monitoring or 0.0,
                'km_per_mm': m.km_per_mm or 0.0,
                'price_per_mm': getattr(m, 'price_per_mm', 0.0) or 0.0,
                'current_asset_value': getattr(m, 'current_asset_value', 0.0) or 0.0,
                'est_cpk': m.est_cpk or 0.0,
                'notes': m.monitor_notes or '',
            })

        vehicles_dict = {}
        for m in monitoring_recs:
            if m.vehicle_id:
                v_name = m.vehicle_id.nomor_lambung or m.vehicle_id.name
                if v_name and v_name not in vehicles_dict:
                    vehicles_dict[v_name] = {
                        'id': m.vehicle_id.id,
                        'name': v_name,
                    }

        for v in vehicles:
            v_name = v.nomor_lambung or v.name
            if v_name and v_name not in vehicles_dict:
                vehicles_dict[v_name] = {
                    'id': v.id,
                    'name': v_name,
                }

        monitoring_vehicles = sorted(list(vehicles_dict.values()), key=lambda x: x['name'])

        years_set = set()
        for m in monitoring_recs:
            if m.monitor_date:
                years_set.add(str(m.monitor_date.year))

        if not years_set:
            years_set.add(str(fields.Date.today().year))

        monitoring_years = sorted(list(years_set), reverse=True)

        monitoring_brands = sorted([{'name': b} for b in brands_set], key=lambda x: x['name'])
        monitoring_sizes = sorted([{'name': s} for s in sizes_set], key=lambda x: x['name'])

        total_fleet_km = sum(m['km_traveled'] for m in monitoring_list)
        total_fleet_rtd = sum(m['rtd_used'] for m in monitoring_list)

        if total_fleet_km > 0 and total_fleet_rtd > 0:
            avg_fleet_cpkm = f"{round(total_fleet_km / total_fleet_rtd, 1):,.1f} km/mm"
        else:
            avg_fleet_cpkm = "-"

        # Compute tire movement counts (Installed, Rotated, Removed)
        installed_tires = 0
        rotated_tires = 0
        removed_tires = 0

        if 'dh.tire.usage' in self.env:
            usage_domain = []
            if unit_id:
                usage_domain.append(('vehicle_id.location_id', '=', int(unit_id)))
            usage_recs = self.env['dh.tire.usage'].search(usage_domain)
            installed_tires = len(usage_recs.filtered(lambda u: u.usage_type == 'mount' or u.install_date))
            rotated_tires = len(usage_recs.filtered(lambda u: getattr(u, 'is_rotation', False) or getattr(u, 'action_type', '') == 'rotation'))
            removed_tires = len(usage_recs.filtered(lambda u: u.removal_date or u.usage_type in ('scrap', 'retread') or u.removal_reason))

        if installed_tires == 0 and rotated_tires == 0 and removed_tires == 0 and 'dh.tire' in self.env:
            tire_domain = []
            tires = self.env['dh.tire'].search(tire_domain)
            installed_tires = len(tires.filtered(lambda t: t.state == 'mounted'))
            rotated_tires = sum(t.rotation_count for t in tires)
            removed_tires = len(tires.filtered(lambda t: t.state in ('unmounted', 'retread', 'scrapped')))

        # 7.5 Compute Tire Rotation Analytics & Wear Variance Distribution
        high_priority_rotations = 0
        medium_priority_rotations = 0
        balanced_wear_vehicles = 0
        total_est_benefit_km = 0
        hub_rotation_map = {}

        if 'dh.tire.usage' in self.env:
            for v in vehicles:
                current_usages = self.env['dh.tire.usage'].search([
                    ('vehicle_id', '=', v.id),
                    ('removal_date', '=', False)
                ])
                wear_values = [u.wear_percentage for u in current_usages if u.wear_percentage is not False]
                if len(wear_values) >= 2:
                    max_w = max(wear_values)
                    min_w = min(wear_values)
                    wear_var = max_w - min_w
                    if wear_var >= 25.0:
                        high_priority_rotations += 1
                        total_est_benefit_km += int(wear_var * 100)
                    elif wear_var >= 15.0:
                        medium_priority_rotations += 1
                        total_est_benefit_km += int(wear_var * 100)
                    else:
                        balanced_wear_vehicles += 1
                elif len(wear_values) == 1:
                    balanced_wear_vehicles += 1

            if 'operating.unit' in self.env:
                ou_records = self.env['operating.unit'].search([('id', '=', int(unit_id))] if unit_id else [])
                for ou in ou_records:
                    hub_rotation_map[ou.name] = {'rotations': 0, 'benefit_km': 0}

                all_rotation_usages = self.env['dh.tire.usage'].search([
                    '|', ('is_rotation', '=', True), ('action_type', '=', 'rotation')
                ])
                if unit_id:
                    all_rotation_usages = all_rotation_usages.filtered(lambda u: u.vehicle_id and u.vehicle_id.location_id.id == int(unit_id))

                for u in all_rotation_usages:
                    h_name = u.vehicle_id.location_id.name if u.vehicle_id and u.vehicle_id.location_id else 'Depot Stock'
                    if h_name not in hub_rotation_map:
                        hub_rotation_map[h_name] = {'rotations': 0, 'benefit_km': 0}
                    hub_rotation_map[h_name]['rotations'] += 1

                for v in vehicles:
                    h_name = v.location_id.name if v.location_id else 'Depot Stock'
                    current_usages = self.env['dh.tire.usage'].search([
                        ('vehicle_id', '=', v.id),
                        ('removal_date', '=', False)
                    ])
                    wear_values = [u.wear_percentage for u in current_usages if u.wear_percentage is not False]
                    if len(wear_values) >= 2:
                        wear_var = max(wear_values) - min(wear_values)
                        if wear_var >= 15.0:
                            if h_name not in hub_rotation_map:
                                hub_rotation_map[h_name] = {'rotations': 0, 'benefit_km': 0}
                            hub_rotation_map[h_name]['benefit_km'] += int(wear_var * 100)

        hub_rotation_chart_data = []
        for name, d in sorted(hub_rotation_map.items()):
            if d['rotations'] > 0 or d['benefit_km'] > 0:
                hub_rotation_chart_data.append({
                    'name': name,
                    'rotations': d['rotations'],
                    'benefit_km': d['benefit_km'],
                })

        total_vehicles_analyzed = len(vehicles)
        total_needing_rotation = high_priority_rotations + medium_priority_rotations

        # 8. Tire Asset Valuation & Financial Depreciation Query
        asset_gross_total = 0.0
        asset_depr_total = 0.0
        asset_net_total = 0.0

        hub_asset_data = []
        status_asset_data = {
            'mounted': 0.0,
            'stock': 0.0,
            'scrapped': 0.0
        }

        if 'dh.tire' in self.env:
            tire_domain = []
            if unit_id:
                tire_domain = [
                    '|',
                    ('usage_ids.vehicle_id.location_id', '=', int(unit_id)),
                    ('location_id', '=', int(unit_id))
                ]

            all_tires = self.env['dh.tire'].sudo().search(tire_domain)
            
            for t in all_tires:
                gross = getattr(t, 'asset_gross_value', 0.0) or getattr(t.serial_number, 'asset_gross_value', 0.0) or (getattr(t, 'tire_price', 0.0) or 0.0)
                depr = getattr(t, 'accumulated_depreciation', 0.0) or getattr(t.serial_number, 'accumulated_depreciation', 0.0)
                net = getattr(t, 'asset_net_value', 0.0) or getattr(t.serial_number, 'asset_net_value', 0.0)
                if net == 0.0 and gross > 0:
                    net = max(0.0, gross - depr)

                asset_gross_total += gross
                asset_depr_total += depr
                asset_net_total += net

                state_val = t.state or 'mounted'
                if state_val == 'mounted':
                    status_asset_data['mounted'] += net
                elif state_val in ('new', 'unmounted', 'retread'):
                    status_asset_data['stock'] += net
                else:
                    status_asset_data['scrapped'] += net

            # Group per operating unit
            ou_map = {}
            if 'operating.unit' in self.env:
                ous = self.env['operating.unit'].search([('id', '=', int(unit_id))] if unit_id else [])
                for ou in ous:
                    ou_map[ou.name] = {'gross': 0.0, 'depr': 0.0, 'net': 0.0}

                for t in all_tires:
                    cur_u = t.usage_ids.filtered(lambda u: not u.removal_date)
                    veh = cur_u[0].vehicle_id if cur_u else False
                    ou_name = veh.location_id.name if veh and veh.location_id else (t.location_id.name if hasattr(t, 'location_id') and t.location_id else 'Depot Stock')

                    if ou_name not in ou_map:
                        ou_map[ou_name] = {'gross': 0.0, 'depr': 0.0, 'net': 0.0}

                    gross = getattr(t, 'asset_gross_value', 0.0) or getattr(t.serial_number, 'asset_gross_value', 0.0) or (getattr(t, 'tire_price', 0.0) or 0.0)
                    depr = getattr(t, 'accumulated_depreciation', 0.0) or getattr(t.serial_number, 'accumulated_depreciation', 0.0)
                    net = getattr(t, 'asset_net_value', 0.0) or getattr(t.serial_number, 'asset_net_value', 0.0)
                    if net == 0.0 and gross > 0:
                        net = max(0.0, gross - depr)

                    ou_map[ou_name]['gross'] += gross
                    ou_map[ou_name]['depr'] += depr
                    ou_map[ou_name]['net'] += net

                for name, d in sorted(ou_map.items()):
                    if d['gross'] > 0 or d['net'] > 0:
                        hub_asset_data.append({
                            'name': name,
                            'gross': round(d['gross'], 2),
                            'depr': round(d['depr'], 2),
                            'net': round(d['net'], 2),
                        })

        asset_retention_pct = round((asset_net_total / asset_gross_total * 100), 1) if asset_gross_total > 0 else 0.0

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
                'installed_tires': installed_tires,
                'rotated_tires': rotated_tires,
                'removed_tires': removed_tires,
                'total_inspections': len(monitoring_list),
            },
            'rotation_analytics': {
                'high_priority_count': high_priority_rotations,
                'medium_priority_count': medium_priority_rotations,
                'balanced_count': balanced_wear_vehicles,
                'total_analyzed': total_vehicles_analyzed,
                'total_needing_rotation': total_needing_rotation,
                'total_est_benefit_km': total_est_benefit_km,
                'hub_rotation_chart_data': hub_rotation_chart_data,
            },
            'psi_distribution': {
                'normal_count': normal_psi_count,
                'low_count': low_psi_count,
                'critical_count': critical_psi_count,
                'total_tracked': total_mounted_tires,
                'normal_pct': round(normal_psi_count / total_mounted_tires * 100, 1) if total_mounted_tires > 0 else 0.0,
                'low_pct': round(low_psi_count / total_mounted_tires * 100, 1) if total_mounted_tires > 0 else 0.0,
                'critical_pct': round(critical_psi_count / total_mounted_tires * 100, 1) if total_mounted_tires > 0 else 0.0,
            },
            'trailer_coupling_summary': {
                'total_heads': total_heads,
                'total_trailers': total_trailers,
                'connected_trailers': connected_trailers,
                'uncoupled_trailers': uncoupled_trailers,
                'coupling_pct': round(connected_trailers / total_trailers * 100, 1) if total_trailers > 0 else 0.0,
            },
            'cpk_billing_summary': {
                'cpk_hubs': cpk_billing_hubs,
                'projected_billing_total': round(total_projected_billing, 2),
                'projected_billing_str': f"Rp {round(total_projected_billing, 0):,.0f}" if total_projected_billing > 0 else "Rp 0",
                'total_min_km_adjustment': round(total_min_km_adjustment, 2),
                'adjustment_str': f"Rp {round(total_min_km_adjustment, 0):,.0f}" if total_min_km_adjustment > 0 else "Rp 0",
                'deficit_vehicle_count': len(min_km_deficit_vehicles),
                'periode_str': f"{date_from.strftime('%d %b')} - {date_to.strftime('%d %b %Y')}",
                'hub_chart_data': hub_chart_data,
                'utilization_status': utilization_status,
            },
            'asset_valuation_summary': {
                'total_gross': round(asset_gross_total, 2),
                'total_gross_str': f"Rp {round(asset_gross_total, 0):,.0f}" if asset_gross_total > 0 else "Rp 0",
                'total_depr': round(asset_depr_total, 2),
                'total_depr_str': f"Rp {round(asset_depr_total, 0):,.0f}" if asset_depr_total > 0 else "Rp 0",
                'total_net': round(asset_net_total, 2),
                'total_net_str': f"Rp {round(asset_net_total, 0):,.0f}" if asset_net_total > 0 else "Rp 0",
                'retention_pct': asset_retention_pct,
                'as_of_date': fields.Date.today().strftime('%d %b %Y'),
                'hub_asset_data': hub_asset_data,
                'status_asset_data': {
                    'mounted': round(status_asset_data['mounted'], 2),
                    'stock': round(status_asset_data['stock'], 2),
                    'scrapped': round(status_asset_data['scrapped'], 2),
                },
            },
            'min_km_deficit_vehicles': min_km_deficit_vehicles,
            'recent_trailer_exchanges': recent_trailer_exchanges,
            'alert_queue': alert_queue[:10],
            'rotation_recommendations': rotation_recommendations[:5],
            'replacement_forecast': replacement_forecast[:5],
            'monitoring_report': {
                'records': monitoring_list,
                'vehicles': monitoring_vehicles,
                'brands': monitoring_brands,
                'sizes': monitoring_sizes,
                'years': monitoring_years,
                'total_count': len(monitoring_list),
            }
        }

