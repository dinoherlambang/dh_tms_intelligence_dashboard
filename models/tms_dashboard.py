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

                    billed_km = max(km_aktual, min_threshold) if min_threshold > 0 else km_aktual
                    v_billing = billed_km * tires_count * cpk_rate
                    total_projected_billing += v_billing

                    if min_threshold > 0 and km_aktual < min_threshold:
                        deficit_km = min_threshold - km_aktual
                        adjustment_val = deficit_km * tires_count * cpk_rate
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

        # 7. Advanced Dynamic Brand & Pattern Multi-Dimensional Performance Analytics
        tire_lots = Lot.search([('is_tire', '=', True)])
        brand_data = {}

        # Search dh.tire records for pattern mapping
        tire_records = self.env['dh.tire'].search([('serial_number', 'in', tire_lots.ids)])
        tire_pattern_map = {t.serial_number.id: t.pattern or 'Standard' for t in tire_records if t.serial_number}

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

            km = getattr(lot, 'total_mileage', 0.0) or getattr(lot, 'total_km', 0.0) or 0.0
            initial_rtd = getattr(lot, 'rtd_initial', 0.0) or 15.0
            current_rtd = getattr(lot, 'current_rtd', 0.0) or initial_rtd
            rtd_used = max(0.0, initial_rtd - current_rtd)

            t_type = getattr(lot, 'tire_type', 'original') or 'original'
            pattern_name = tire_pattern_map.get(lot.id, 'Standard Pattern')

            # Position / Axle category
            pos_name = lot.current_position_id.name if lot.current_position_id else ''
            pos_code = lot.current_position_id.code if lot.current_position_id else ''

            is_steer = pos_code in ('1', '2', 'P1', 'P2') or 'steer' in pos_name.lower() or 'depan' in pos_name.lower()
            is_trailer = 'trailer' in pos_name.lower() or (lot.current_vehicle_id and lot.current_vehicle_id.is_trailer)

            if b_name not in brand_data:
                brand_data[b_name] = {
                    'count': 0,
                    'original_count': 0,
                    'retread_count': 0,
                    'total_km': 0.0,
                    'total_rtd_used': 0.0,
                    'steer_km': 0.0,
                    'steer_rtd': 0.0,
                    'drive_km': 0.0,
                    'drive_rtd': 0.0,
                    'trailer_km': 0.0,
                    'trailer_rtd': 0.0,
                    'premature_scrap': 0,
                    'brand_id': brand_obj_id,
                    'patterns': {},
                }

            brand_data[b_name]['count'] += 1
            if t_type == 'retread' or (hasattr(lot, 'retread_count') and lot.retread_count > 0):
                brand_data[b_name]['retread_count'] += 1
            else:
                brand_data[b_name]['original_count'] += 1

            brand_data[b_name]['total_km'] += km
            brand_data[b_name]['total_rtd_used'] += rtd_used

            if is_steer:
                brand_data[b_name]['steer_km'] += km
                brand_data[b_name]['steer_rtd'] += rtd_used
            elif is_trailer:
                brand_data[b_name]['trailer_km'] += km
                brand_data[b_name]['trailer_rtd'] += rtd_used
            else:
                brand_data[b_name]['drive_km'] += km
                brand_data[b_name]['drive_rtd'] += rtd_used

            if getattr(lot, 'tire_state', '') == 'scrapped' and current_rtd > 5.0:
                brand_data[b_name]['premature_scrap'] += 1

            # Pattern level stats
            if pattern_name not in brand_data[b_name]['patterns']:
                brand_data[b_name]['patterns'][pattern_name] = {
                    'count': 0,
                    'km': 0.0,
                    'rtd_used': 0.0,
                }
            brand_data[b_name]['patterns'][pattern_name]['count'] += 1
            brand_data[b_name]['patterns'][pattern_name]['km'] += km
            brand_data[b_name]['patterns'][pattern_name]['rtd_used'] += rtd_used

        brand_performance = []
        max_brand_wear_rate = 1.0
        best_brand_leader = False

        for b_name, b_info in brand_data.items():
            count = b_info['count']
            tot_km = b_info['total_km']
            tot_rtd_used = b_info['total_rtd_used']
            avg_km = round(tot_km / count, 1) if count > 0 else 0.0
            km_per_mm = round(tot_km / tot_rtd_used, 1) if tot_rtd_used > 0 else 0.0

            if km_per_mm > max_brand_wear_rate:
                max_brand_wear_rate = km_per_mm
                best_brand_leader = b_name

            steer_rate = round(b_info['steer_km'] / b_info['steer_rtd'], 1) if b_info['steer_rtd'] > 0 else 0.0
            drive_rate = round(b_info['drive_km'] / b_info['drive_rtd'], 1) if b_info['drive_rtd'] > 0 else 0.0
            trailer_rate = round(b_info['trailer_km'] / b_info['trailer_rtd'], 1) if b_info['trailer_rtd'] > 0 else 0.0

            total_rate_sum = max(1.0, steer_rate + drive_rate + trailer_rate)
            steer_spark_pct = round((steer_rate / total_rate_sum) * 100, 1)
            drive_spark_pct = round((drive_rate / total_rate_sum) * 100, 1)
            trailer_spark_pct = round((trailer_rate / total_rate_sum) * 100, 1)

            rates = [('Steer Axles', steer_rate), ('Drive Axles', drive_rate), ('Trailer Axles', trailer_rate)]
            valid_rates = [r for r in rates if r[1] > 0]
            best_axle = max(valid_rates, key=lambda x: x[1])[0] if valid_rates else 'All-Position'

            retread_pct = round((b_info['retread_count'] / count) * 100, 1) if count > 0 else 0.0
            failure_pct = round((b_info['premature_scrap'] / count) * 100, 1) if count > 0 else 0.0
            healthy_scrap_pct = max(0.0, round(100.0 - failure_pct, 1))

            target_km_pct = min(100.0, round((avg_km / 100000.0) * 100, 1))

            patterns_list = []
            for p_name, p_data in b_info['patterns'].items():
                p_rtd = p_data['rtd_used']
                p_km_mm = round(p_data['km'] / p_rtd, 1) if p_rtd > 0 else 0.0
                patterns_list.append({
                    'pattern': p_name,
                    'count': p_data['count'],
                    'avg_km': round(p_data['km'] / p_data['count'], 1) if p_data['count'] > 0 else 0.0,
                    'km_per_mm': p_km_mm,
                    'pattern_bar_pct': min(100.0, round((p_km_mm / 10000.0) * 100, 1)) if p_km_mm > 0 else 5.0,
                })
            patterns_list.sort(key=lambda x: x['km_per_mm'], reverse=True)

            brand_performance.append({
                'brand': b_name,
                'brand_id': b_info['brand_id'],
                'count': count,
                'original_count': b_info['original_count'],
                'retread_count': b_info['retread_count'],
                'avg_km': avg_km,
                'km_per_mm': km_per_mm,
                'steer_km_per_mm': steer_rate,
                'drive_km_per_mm': drive_rate,
                'trailer_km_per_mm': trailer_rate,
                'steer_spark_pct': steer_spark_pct,
                'drive_spark_pct': drive_spark_pct,
                'trailer_spark_pct': trailer_spark_pct,
                'best_axle': best_axle,
                'retread_pct': retread_pct,
                'failure_pct': failure_pct,
                'healthy_scrap_pct': healthy_scrap_pct,
                'target_km_pct': target_km_pct,
                'patterns': patterns_list,
            })

        for b in brand_performance:
            b['bar_pct'] = round((b['km_per_mm'] / max_brand_wear_rate * 100), 1) if max_brand_wear_rate > 0 else 0.0
            if b['brand'] == best_brand_leader and b['km_per_mm'] > 0:
                b['badge_text'] = '🏆 TOP WEAR INDEX'
                b['badge_class'] = 'badge-success'
            elif b['km_per_mm'] > 5000.0:
                b['badge_text'] = 'HIGH DURABILITY'
                b['badge_class'] = 'badge-info'
            else:
                b['badge_text'] = 'STANDARD WEAR'
                b['badge_class'] = 'badge-secondary'

        brand_performance.sort(key=lambda x: x['km_per_mm'], reverse=True)

        total_fleet_km = sum(b_info['total_km'] for b_info in brand_data.values())
        total_fleet_rtd = sum(b_info['total_rtd_used'] for b_info in brand_data.values())

        if total_fleet_km > 0 and total_fleet_rtd > 0:
            avg_fleet_cpkm = f"{round(total_fleet_km / total_fleet_rtd, 1):,.1f} km/mm"
        else:
            avg_fleet_cpkm = "-"

        # 8. Donut Geometry Calculations
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
            },
            'min_km_deficit_vehicles': min_km_deficit_vehicles,
            'recent_trailer_exchanges': recent_trailer_exchanges,
            'vehicle_grid': vehicle_grid,
            'alert_queue': alert_queue[:10],
            'brand_performance': brand_performance,
            'best_brand_leader': best_brand_leader or '-',
            'rotation_recommendations': rotation_recommendations[:5],
            'replacement_forecast': replacement_forecast[:5],
        }
