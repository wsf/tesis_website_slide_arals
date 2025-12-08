from collections import Counter
from datetime import timedelta

from odoo import fields, models
from odoo.tools import format_date, format_datetime


class UserProfileEngine(models.AbstractModel):
	_name = 'slide.user.profile.engine'
	_description = 'Motor de Perfil del Usuario ARALS'

	def get_progress_overview(self, user_id, channel_id=None):
		"""Aggregate progress metrics for the given user/channel."""
		Historial = self.env['slide.historial.progreso']
		Ruta = self.env['slide.ruta.aprendizaje']

		domain = [('user_id', '=', user_id)]
		if channel_id:
			domain.append(('channel_id', '=', channel_id))

		records = Historial.search(domain)
		if not records:
			return {
				'completed': 0,
				'in_progress': 0,
				'recommended': 0,
				'percentage': 0,
				'total_time': 0,
				'last_activity': False,
			}

		completed_slides = records.filtered(lambda r: r.completado).mapped('slide_id')
		in_progress_slides = records.filtered(lambda r: not r.completado and r.slide_id).mapped('slide_id')

		rutas = Ruta.search([
			('user_id', '=', user_id),
			('activa', '=', True),
		] + ([('channel_id', '=', channel_id)] if channel_id else []))

		recommended_count = sum(
			len(ruta.slide_ids.filtered(lambda slide: slide.id not in completed_slides.ids))
			for ruta in rutas
		)

		total_considered = len(set(completed_slides.ids + in_progress_slides.ids)) or 1
		percentage = int((len(completed_slides) / total_considered) * 100)

		return {
			'completed': len(completed_slides),
			'in_progress': len(in_progress_slides),
			'recommended': recommended_count,
			'percentage': percentage,
			'total_time': int(sum(records.mapped('tiempo_dedicado'))),
			'last_activity': fields.Datetime.to_string(records[0].fecha_acceso),
		}

	def get_learning_profile(self, user_id):
		"""Derive a lightweight learning profile based on slide history."""
		Historial = self.env['slide.historial.progreso']
		records = Historial.search([
			('user_id', '=', user_id),
			('slide_id', '!=', False),
		])

		if not records:
			return {
				'visual': 34,
				'auditory': 33,
				'kinesthetic': 33,
				'best_time': 'Mañana',
				'pace': 'Moderado',
				'level': 'Básico',
			}

		mapping = {
			'video': 'visual',
			'presentation': 'visual',
			'document': 'visual',
			'quiz': 'kinesthetic',
			'survey': 'kinesthetic',
			'webpage': 'visual',
			'audio': 'auditory',
		}

		counter = Counter()
		for rec in records:
			category = rec.slide_id.slide_category
			counter[mapping.get(category, 'kinesthetic')] += 1

		total = sum(counter.values()) or 1
		visual = int((counter['visual'] / total) * 100)
		auditory = int((counter['auditory'] / total) * 100)
		kinesthetic = max(0, 100 - visual - auditory)

		avg_score = sum(records.mapped('puntuacion')) / len(records)
		level = 'Avanzado' if avg_score >= 80 else 'Intermedio' if avg_score >= 50 else 'Básico'

		streak = self._compute_activity_streak(records)
		best_time = self._guess_best_time(records)

		return {
			'visual': visual,
			'auditory': auditory,
			'kinesthetic': kinesthetic,
			'best_time': best_time,
			'pace': 'Intensivo' if streak >= 5 else 'Moderado',
			'level': level,
		}

	def get_learning_path_snapshot(self, user_id, channel_id=None):
		"""Provide minimal data for the active learning path."""
		Ruta = self.env['slide.ruta.aprendizaje']
		Historial = self.env['slide.historial.progreso']

		domain = [('user_id', '=', user_id), ('activa', '=', True)]
		if channel_id:
			domain.append(('channel_id', '=', channel_id))

		ruta = Ruta.search(domain, limit=1)
		if not ruta:
			return {}

		historial = Historial.search([
			('user_id', '=', user_id),
			('slide_id', 'in', ruta.slide_ids.ids),
		])

		slide_progress = {rec.slide_id.id: rec for rec in historial if rec.slide_id}

		slides_data = []
		for slide in ruta.slide_ids.sorted(key=lambda s: s.sequence):
			progreso = slide_progress.get(slide.id)
			description = slide.description or getattr(slide, 'website_description', '') or ''
			slides_data.append({
				'id': slide.id,
				'title': slide.name,
				'description': description,
				'difficulty': slide.nivel_dificultad or 'basico',
				'type': slide.slide_category or 'content',
				'url': f'/slides/slide/{slide.id}',
				'completed': bool(progreso and progreso.completado),
				'in_progress': bool(progreso and not progreso.completado and progreso.puntuacion > 0),
				'score': int(progreso.puntuacion) if progreso else 0,
			})

		return {
			'id': ruta.id,
			'name': ruta.name,
			'progress': ruta.progreso_ruta,
			'slides': slides_data,
		}

	def get_dashboard_analytics(self, user_id, channel_id=None, periods=6):
		"""Compute trend, distribution and stats required by the dashboard."""
		Historial = self.env['slide.historial.progreso']
		domain = [('user_id', '=', user_id)]
		if channel_id:
			domain.append(('channel_id', '=', channel_id))

		records = Historial.search(domain, order='fecha_acceso asc')

		def _empty_response():
			return {
				'progress_trend': [],
				'study_time': [],
				'difficulty_distribution': {
					'basico': 0,
					'intermedio': 0,
					'avanzado': 0,
				},
				'stats': {
					'achievements': 0,
					'streak': 0,
					'total_minutes': 0,
					'total_hours': 0,
					'avg_score': 0,
				},
				'recent_activity': [],
			}

		if not records:
			return _empty_response()

		periods = max(1, periods)
		today = fields.Date.context_today(self)
		start_date = today - timedelta(days=7 * (periods - 1))
		weekly_buckets = []
		for idx in range(periods):
			week_start = start_date + timedelta(days=7 * idx)
			label = format_date(self.env, week_start, date_format='dd MMM')
			weekly_buckets.append({
				'label': label,
				'start': week_start,
				'end': week_start + timedelta(days=6),
				'completed': 0,
				'in_progress': 0,
				'minutes': 0,
			})

		for rec in records:
			if not rec.fecha_acceso:
				continue
			rec_date = fields.Date.to_date(rec.fecha_acceso)
			if rec_date < start_date:
				bucket_idx = 0
			else:
				delta_days = (rec_date - start_date).days
				bucket_idx = min(delta_days // 7, periods - 1)
			bucket = weekly_buckets[bucket_idx]
			if rec.completado:
				bucket['completed'] += 1
			else:
				bucket['in_progress'] += 1
			bucket['minutes'] += rec.tiempo_dedicado or 0.0

		difficulty_counts = {
			'basico': 0,
			'intermedio': 0,
			'avanzado': 0,
		}
		for rec in records:
			slide = rec.slide_id
			if not slide:
				continue
			difficulty = slide.nivel_dificultad or 'basico'
			difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

		total_minutes = int(sum(records.mapped('tiempo_dedicado')))
		avg_score = int(round(sum(records.mapped('puntuacion')) / len(records))) if records else 0
		achievements = len(records.filtered(lambda r: r.completado and r.puntuacion >= 80))
		streak = self._compute_activity_streak(records)
		total_hours = round(total_minutes / 60.0, 1) if total_minutes else 0

		recent_records = Historial.search(domain, order='fecha_acceso desc', limit=10)
		recent_activity = []
		for rec in recent_records:
			entry = {
				'slide_id': rec.slide_id.id if rec.slide_id else False,
				'slide': rec.slide_id.name if rec.slide_id else rec.channel_id.name,
				'channel': rec.channel_id.name,
				'completed': rec.completado,
				'score': int(rec.puntuacion or 0),
				'minutes': int(rec.tiempo_dedicado or 0),
				'date': format_datetime(self.env, rec.fecha_acceso) if rec.fecha_acceso else False,
			}
			if rec.slide_id:
				entry['url'] = f'/slides/slide/{rec.slide_id.id}'
			recent_activity.append(entry)

		return {
			'progress_trend': [
				{
					'label': bucket['label'],
					'completed': bucket['completed'],
					'in_progress': bucket['in_progress'],
				}
				for bucket in weekly_buckets
			],
			'study_time': [
				{
					'label': bucket['label'],
					'minutes': int(bucket['minutes']),
				}
				for bucket in weekly_buckets
			],
			'difficulty_distribution': difficulty_counts,
			'stats': {
				'achievements': achievements,
				'streak': streak,
				'total_minutes': total_minutes,
				'total_hours': total_hours,
				'avg_score': avg_score,
			},
			'recent_activity': recent_activity,
		}

	def get_dashboard_payload(self, user_id, channel_id=None, limit=5):
		"""Bundle all data required by ARALS dashboards and API."""
		Ruta = self.env['slide.ruta.aprendizaje']
		Historial = self.env['slide.historial.progreso']
		recommendation_engine = self.env['slide.recommendation.engine']

		req_channel_id = int(channel_id) if channel_id else False
		active_route = Ruta.search([
			('user_id', '=', user_id),
			('activa', '=', True),
		] + ([('channel_id', '=', req_channel_id)] if req_channel_id else []), limit=1)

		active_channel_id = req_channel_id or False
		if active_route:
			active_channel_id = active_route.channel_id.id
		else:
			last_historial = Historial.search([
				('user_id', '=', user_id),
				('channel_id', '!=', False),
			], order='fecha_acceso desc', limit=1)
			if last_historial:
				active_channel_id = last_historial.channel_id.id

		if active_channel_id and (not active_route or active_route.channel_id.id != active_channel_id):
			active_route = Ruta.search([
				('user_id', '=', user_id),
				('channel_id', '=', active_channel_id),
				('activa', '=', True),
			], limit=1)

		progress = self.get_progress_overview(user_id, active_channel_id) if active_channel_id else self.get_progress_overview(user_id, False)
		global_progress = self.get_progress_overview(user_id, False)
		profile = self.get_learning_profile(user_id)
		learning_path = self.get_learning_path_snapshot(user_id, active_channel_id)
		analytics = self.get_dashboard_analytics(user_id, active_channel_id) if active_channel_id else self.get_dashboard_analytics(user_id, False)

		recommendations = []
		if active_channel_id:
			recommendations = recommendation_engine.get_recommendations(user_id, active_channel_id, limit=limit)

		notifications = []
		if progress.get('percentage', 0) >= 80:
			notifications.append({
				'title': '¡Excelente progreso!',
				'message': 'Estás muy cerca de completar tu ruta actual.',
				'type': 'success',
				'icon': 'fa-smile-o',
			})
		elif not recommendations and active_channel_id:
			notifications.append({
				'title': 'Necesitas nuevas recomendaciones',
				'message': 'Genera nuevas sugerencias para continuar avanzando.',
				'type': 'warning',
				'icon': 'fa-lightbulb-o',
			})

		return {
			'progress': progress,
			'global_progress': global_progress,
			'profile': profile,
			'learning_path': learning_path,
			'recommendations': recommendations,
			'analytics': analytics,
			'notifications': notifications,
			'active_channel_id': active_channel_id,
			'active_route_id': active_route.id if active_route else False,
		}

	def _compute_activity_streak(self, records):
		"""Compute consecutive-day activity streak from historial records."""
		dates = sorted({fields.Date.to_date(rec.fecha_acceso) for rec in records if rec.fecha_acceso})
		if not dates:
			return 0

		streak = 1
		best_streak = 1
		for idx in range(1, len(dates)):
			if (dates[idx] - dates[idx - 1]).days == 1:
				streak += 1
				best_streak = max(best_streak, streak)
			else:
				streak = 1
		return best_streak

	def _guess_best_time(self, records):
		"""Guess preferred study time based on access timestamp distribution."""
		buckets = Counter()
		for rec in records:
			if not rec.fecha_acceso:
				continue
			hour = fields.Datetime.context_timestamp(self, rec.fecha_acceso).hour
			if 6 <= hour < 12:
				buckets['Mañana'] += 1
			elif 12 <= hour < 18:
				buckets['Tarde'] += 1
			else:
				buckets['Noche'] += 1

		if not buckets:
			return 'Mañana'
		return max(buckets, key=buckets.get)
