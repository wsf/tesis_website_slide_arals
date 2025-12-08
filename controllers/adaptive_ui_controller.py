# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import http
from odoo.http import request
from odoo.tools import format_datetime
from odoo.addons.website_slides.controllers.main import WebsiteSlides

class AdaptiveUIController(WebsiteSlides):

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super()._prepare_additional_channel_values(values, **kwargs)

        channel = values.get('channel')
        user = request.env.user
        values.setdefault('arals_learning_path', False)
        values.setdefault('arals_learning_path_slides', request.env['slide.slide'].browse([]))
        values.setdefault('arals_learning_path_slide_ids', [])

        if not channel or user._is_public():
            return values

        profile_engine = request.env['slide.user.profile.engine']
        path_snapshot = profile_engine.get_learning_path_snapshot(user.id, channel.id)

        if path_snapshot and path_snapshot.get('slides'):
            slide_ids = [slide['id'] for slide in path_snapshot['slides']]
            personalized_slides = request.env['slide.slide'].browse(slide_ids)

            values['arals_learning_path'] = path_snapshot
            values['arals_learning_path_slides'] = personalized_slides
            values['arals_learning_path_slide_ids'] = slide_ids

        return self._filter_channel_slides_for_user(values, channel, user)

    def _filter_channel_slides_for_user(self, values, channel, user):
        """Ensure personalized material is only visible to its intended student."""
        category_data = values.get('category_data')
        if not category_data:
            return values

        if channel.can_publish or user.has_group('website_slides.group_website_slides_officer'):
            return values

        Ruta = request.env['slide.ruta.aprendizaje']
        active_routes = Ruta.search([
            ('channel_id', '=', channel.id),
            ('activa', '=', True),
        ])
        if not active_routes:
            return values

        all_route_slide_ids = set(active_routes.mapped('slide_ids').ids)
        current_route_slide_ids = set(
            active_routes.filtered(lambda r: r.user_id == user).mapped('slide_ids').ids
        )

        # Slides reservados para otros estudiantes
        restricted_slide_ids = all_route_slide_ids - current_route_slide_ids

        # Evitar duplicados en la lista general, pero mantener progreso para el dueño
        hidden_for_owner = set(values.get('arals_learning_path_slide_ids', []))
        exclude_from_general = restricted_slide_ids | hidden_for_owner

        if not restricted_slide_ids:
            return values

        Slide = request.env['slide.slide']
        filtered_category_data = []
        visible_slides_total = 0
        visible_slide_ids = set()
        for category in category_data:
            slides = category.get('slides', Slide.browse([]))
            visible_slides = slides.filtered(lambda s: s.id not in exclude_from_general)

            if not visible_slides and not category.get('category'):
                # Keep uncategorized bucket even if empty to preserve layout
                new_entry = dict(category, slides=visible_slides, total_slides=len(visible_slides))
                filtered_category_data.append(new_entry)
                visible_slides_total += len(visible_slides)
                continue

            if visible_slides or category.get('category'):
                new_entry = dict(category)
                new_entry['slides'] = visible_slides
                new_entry['total_slides'] = len(visible_slides)
                filtered_category_data.append(new_entry)
                visible_slides_total += len(visible_slides)
                visible_slide_ids.update(visible_slides.ids)

        values['category_data'] = filtered_category_data
        values['slide_count'] = visible_slides_total

        channel_progress = dict(values.get('channel_progress') or {})
        for slide_id in list(channel_progress.keys()):
            if slide_id in restricted_slide_ids:
                channel_progress.pop(slide_id, None)

        # Ensure progress data exists for all visible slides (including personalized ones)
        personalized_ids = set(values.get('arals_learning_path_slide_ids', []))
        for slide_id in visible_slide_ids.union(personalized_ids):
            channel_progress.setdefault(slide_id, {})

        values['channel_progress'] = defaultdict(dict, channel_progress)

        return values

    @http.route('/slides/adaptive/dashboard', type='http', auth='user', website=True)
    def adaptive_dashboard(self, **kwargs):
        """Dashboard principal del estudiante con información adaptativa"""
        user = request.env.user

        channel_id = kwargs.get('channel_id')
        try:
            channel_id = int(channel_id) if channel_id else False
        except (TypeError, ValueError):
            channel_id = False

        profile_engine = request.env['slide.user.profile.engine']
        dashboard_data = profile_engine.get_dashboard_payload(user.id, channel_id, limit=8)

        historial = request.env['slide.historial.progreso'].search([
            ('user_id', '=', user.id)
        ], order='fecha_acceso desc', limit=10)

        rutas = request.env['slide.ruta.aprendizaje'].search([
            ('user_id', '=', user.id),
            ('activa', '=', True)
        ])

        return request.render('tesis_website_slide_arals.student_dashboard', {
            'user': user,
            'dashboard_data': dashboard_data,
            'historial': historial,
            'rutas': rutas,
            'notifications': dashboard_data.get('notifications', []),
            'recent_activity': dashboard_data.get('analytics', {}).get('recent_activity', []),
        })

    @http.route('/slides/adaptive/teacher/dashboard', type='http', auth='user', website=True)
    def teacher_dashboard(self, **kwargs):
        """Dashboard para profesores con análisis de estudiantes"""
        user = request.env.user

        canales = request.env['slide.channel'].search([
            ('user_id', '=', user.id)
        ])

        if not canales:
            return request.redirect('/slides')

        estudiantes_data = []
        for canal in canales:
            miembros = canal.slide_partner_ids
            for miembro in miembros:
                user_ids = miembro.partner_id.user_ids
                if not user_ids:
                    continue

                historial = request.env['slide.historial.progreso'].search([
                    ('user_id', '=', user_ids[0].id),
                    ('channel_id', '=', canal.id)
                ])

                if historial:
                    estudiantes_data.append({
                        'nombre': miembro.partner_id.name,
                        'canal': canal.name,
                        'progreso': len(historial.filtered(lambda h: h.completado)),
                        'tiempo_total': sum(historial.mapped('tiempo_dedicado')),
                        'promedio': sum(historial.mapped('puntuacion')) / len(historial) if historial else 0
                    })

        analytics = {
            'active_students': len(estudiantes_data),
            'completion_rate': 0,
            'arals_effectiveness': 0,
            'average_time': 0,
        }

        if estudiantes_data:
            total_progress = sum(student['progreso'] for student in estudiantes_data)
            total_score = sum(student['promedio'] for student in estudiantes_data)
            total_time = sum(student['tiempo_total'] for student in estudiantes_data)
            count = len(estudiantes_data)
            analytics['completion_rate'] = round(total_progress / count, 1) if count else 0
            analytics['arals_effectiveness'] = round(total_score / count, 1) if count else 0
            analytics['average_time'] = round(total_time / count, 1) if count else 0

        channel_summary_map = {}
        for entry in estudiantes_data:
            summary = channel_summary_map.setdefault(entry['canal'], {
                'canal': entry['canal'],
                'estudiantes': 0,
                'progreso_acumulado': 0,
                'tiempo_total': 0,
                'puntaje_acumulado': 0,
            })
            summary['estudiantes'] += 1
            summary['progreso_acumulado'] += entry['progreso']
            summary['tiempo_total'] += entry['tiempo_total']
            summary['puntaje_acumulado'] += entry['promedio']

        channel_summary = []
        for summary in channel_summary_map.values():
            estudiantes = summary['estudiantes'] or 1
            channel_summary.append({
                'canal': summary['canal'],
                'estudiantes': summary['estudiantes'],
                'progreso_promedio': round(summary['progreso_acumulado'] / estudiantes, 1),
                'tiempo_promedio': round(summary['tiempo_total'] / estudiantes, 1),
                'puntaje_promedio': round(summary['puntaje_acumulado'] / estudiantes, 1),
            })

        leaderboard = sorted(estudiantes_data, key=lambda a: (a['progreso'], a['promedio']), reverse=True)[:5]

        route_metrics = []
        student_user_ids = set()
        for canal in canales:
            for miembro in canal.slide_partner_ids:
                for user_rec in miembro.partner_id.user_ids:
                    if user_rec._is_public():
                        continue
                    student_user_ids.add(user_rec.id)

        if student_user_ids:
            Ruta = request.env['slide.ruta.aprendizaje']
            Historial = request.env['slide.historial.progreso']
            student_users = request.env['res.users'].browse(list(student_user_ids))

            routes_by_user = defaultdict(lambda: request.env['slide.ruta.aprendizaje'])
            for ruta in Ruta.search([('user_id', 'in', student_users.ids)]):
                routes_by_user[ruta.user_id.id] |= ruta

            historial_by_user = defaultdict(lambda: request.env['slide.historial.progreso'])
            for registro in Historial.search([('user_id', 'in', student_users.ids)]):
                historial_by_user[registro.user_id.id] |= registro

            for student in student_users:
                user_routes = routes_by_user.get(student.id, request.env['slide.ruta.aprendizaje'])
                user_historial = historial_by_user.get(student.id, request.env['slide.historial.progreso'])

                route_count = len(user_routes)
                route_slide_ids = set(user_routes.mapped('slide_ids').ids)
                route_channel_ids = set(user_routes.mapped('channel_id').ids)

                relevant_historial = user_historial.filtered(
                    lambda rec: (
                        rec.slide_id and rec.slide_id.id in route_slide_ids
                    ) or (
                        rec.channel_id and rec.channel_id.id in route_channel_ids
                    )
                )

                usage_count = len(relevant_historial)
                last_usage_dt = max(relevant_historial.mapped('fecha_acceso')) if relevant_historial else False
                last_usage = format_datetime(request.env, last_usage_dt) if last_usage_dt else False

                resource_count = len(route_slide_ids)
                utility_score = 0.0
                acceptance_score = 0.0

                if route_count:
                    total_progress = sum(user_routes.mapped('progreso_ruta'))
                    utility_score = round(total_progress / route_count, 1)

                    routes_with_activity = 0
                    for ruta in user_routes:
                        ruta_slide_ids = set(ruta.slide_ids.ids)
                        has_activity = any(
                            (
                                registro.slide_id and registro.slide_id.id in ruta_slide_ids
                            ) or (
                                registro.channel_id and registro.channel_id.id == ruta.channel_id.id
                            )
                            for registro in relevant_historial
                        )
                        if has_activity:
                            routes_with_activity += 1

                    acceptance_score = round((routes_with_activity / route_count) * 100, 1)

                route_metrics.append({
                    'user_name': student.partner_id.name or student.name,
                    'route_count': route_count,
                    'usage_records': usage_count,
                    'resource_count': resource_count,
                    'utility_score': utility_score,
                    'acceptance_score': acceptance_score,
                    'last_usage': last_usage,
                })

        route_metrics.sort(key=lambda entry: entry['user_name'])

        return request.render('tesis_website_slide_arals.teacher_dashboard', {
            'user': user,
            'canales': canales,
            'estudiantes_data': estudiantes_data,
            'channel_summary': channel_summary,
            'leaderboard': leaderboard,
            'analytics': analytics,
            'route_metrics': route_metrics,
        })

    @http.route('/slides/adaptive/ruta/<int:ruta_id>', type='http', auth='user', website=True)
    def ver_ruta(self, ruta_id, **kwargs):
        """Ver detalles de una ruta de aprendizaje específica"""
        ruta = request.env['slide.ruta.aprendizaje'].browse(ruta_id)

        if not ruta.exists() or ruta.user_id != request.env.user:
            return request.redirect('/slides/adaptive/dashboard')

        return request.render('tesis_website_slide_arals.ruta_detalle', {
            'ruta': ruta,
        })
