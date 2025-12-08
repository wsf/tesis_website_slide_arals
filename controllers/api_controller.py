# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class APIController(http.Controller):

    @http.route('/api/slides/recommendations', type='json', auth='user', methods=['POST'])
    def get_recommendations(self, channel_id=None, limit=5):
        """Obtiene recomendaciones personalizadas para el usuario"""
        try:
            user = request.env.user
            limit = int(limit or 5)
            channel_id = int(channel_id) if channel_id else False

            adaptive_service = request.env['slide.adaptive.learning.service']
            result = adaptive_service.generate_recommendations(user.id, channel_id, limit=limit)

            return {
                'status': 'success',
                'data': result.get('recommendations', [])
            }
        except Exception as e:
            _logger.exception("Error al obtener recomendaciones")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/arals/api/user-data', type='json', auth='user', methods=['POST'])
    def get_user_data(self, channel_id=None, limit=5):
        """Devuelve progreso, perfil y recomendaciones para el dashboard ARALS."""
        try:
            user = request.env.user
            limit = int(limit or 5)
            channel_id = int(channel_id) if channel_id else False

            profile_engine = request.env['slide.user.profile.engine']
            payload = profile_engine.get_dashboard_payload(user.id, channel_id, limit=limit)
            payload['status'] = 'success'
            return payload
        except Exception as e:
            _logger.exception("Error al obtener datos de usuario ARALS")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/arals/api/generate-recommendations', type='json', auth='user', methods=['POST'])
    def generate_recommendations(self, channel_id=None, limit=5):
        """Genera recomendaciones bajo demanda y actualiza la ruta activa."""
        try:
            user = request.env.user
            limit = int(limit or 5)
            channel_id = int(channel_id) if channel_id else False

            if not channel_id:
                ruta = request.env['slide.ruta.aprendizaje'].search([
                    ('user_id', '=', user.id),
                    ('activa', '=', True)
                ], limit=1)
                channel_id = ruta.channel_id.id if ruta else False

            adaptive_service = request.env['slide.adaptive.learning.service']
            result = adaptive_service.generate_recommendations(user.id, channel_id, limit=limit)

            return {
                'status': 'success',
                'recommendations': result.get('recommendations', []),
                'route_id': result.get('route_id'),
            }
        except Exception as e:
            _logger.exception("Error al generar recomendaciones")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/arals/api/track-recommendation', type='json', auth='user', methods=['POST'])
    def track_recommendation(self, recommendation_id=None, action=None):
        """Registra interacciones del usuario con recomendaciones."""
        try:
            user = request.env.user
            _logger.info(
                "ARALS tracking - user=%s recommendation=%s action=%s",
                user.id,
                recommendation_id,
                action,
            )
            return {'status': 'success'}
        except Exception as e:
            _logger.exception("Error al registrar interacción de recomendación")
            return {
                'status': 'error',
                'message': str(e)
            }
