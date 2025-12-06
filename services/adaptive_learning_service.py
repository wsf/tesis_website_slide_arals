from odoo import models, fields


class AdaptiveLearningService(models.AbstractModel):
	_name = 'slide.adaptive.learning.service'
	_description = 'Servicio Adaptativo ARALS'

	def get_or_create_active_route(self, user_id, channel_id, nivel_dificultad='basico'):
		"""Ensure the user has an active learning path for the channel."""
		Ruta = self.env['slide.ruta.aprendizaje']
		route = Ruta.search([
			('user_id', '=', user_id),
			('channel_id', '=', channel_id),
			('activa', '=', True),
		], limit=1)

		if route:
			return route

		return Ruta.create({
			'user_id': user_id,
			'channel_id': channel_id,
			'nivel_dificultad': nivel_dificultad,
			'fecha_creacion': fields.Datetime.now(),
			'fecha_actualizacion': fields.Datetime.now(),
		})

	def generate_recommendations(self, user_id, channel_id, limit=5):
		"""Generate recommendations and keep the learning path up to date."""
		if not channel_id:
			return {'recommendations': [], 'route_id': False}

		recommendation_engine = self.env['slide.recommendation.engine']

		route = self.get_or_create_active_route(user_id, channel_id)
		recommendations = recommendation_engine.get_recommendations(user_id, channel_id, limit=limit)

		if recommendations:
			slide_ids = [rec['id'] for rec in recommendations]
			route.write({'slide_ids': [(6, 0, slide_ids)]})

		return {
			'recommendations': recommendations,
			'route_id': route.id,
		}
