from collections import Counter

from odoo import fields, models


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
