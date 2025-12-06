# -*- coding: utf-8 -*-
from odoo import models


def _ordered_difficulties(target_level):
    """Return a prioritized list of difficulty levels starting from the target."""
    levels = ['basico', 'intermedio', 'avanzado']
    if target_level not in levels:
        return levels
    start = levels.index(target_level)
    return levels[start:] + levels[:start]

class RecommendationEngine(models.AbstractModel):
    _name = 'slide.recommendation.engine'
    _description = 'Motor de Recomendaciones para eLearning'

    def get_recommendations(self, user_id, channel_id, limit=5):
        if not channel_id:
            return []

        Slide = self.env['slide.slide']
        Historial = self.env['slide.historial.progreso']
        Ruta = self.env['slide.ruta.aprendizaje']

        # Obtener ruta activa del usuario para ese canal
        ruta = Ruta.search([
            ('user_id', '=', user_id),
            ('channel_id', '=', channel_id),
            ('activa', '=', True)
        ], limit=1)

        nivel_dificultad = ruta.nivel_dificultad if ruta else 'basico'

        # Obtener slides del canal priorizando el nivel configurado en la ruta
        difficulties = _ordered_difficulties(nivel_dificultad)
        all_slides = Slide.browse()
        for level in difficulties:
            candidates = Slide.search([
                ('channel_id', '=', channel_id),
                ('nivel_dificultad', '=', level),
            ])
            all_slides |= candidates
            if len(all_slides) >= limit:
                break

        # Obtener las que ya completó el usuario
        historial_completado = Historial.search([
            ('user_id', '=', user_id),
            ('channel_id', '=', channel_id),
            ('completado', '=', True),
        ])
        completadas_ids = historial_completado.mapped('slide_id').ids

        # Filtrar las no completadas
        slides_recomendadas = all_slides.filtered(lambda s: s.id not in completadas_ids)

        # Orden por secuencia y limitar
        recomendadas = slides_recomendadas.sorted(key=lambda s: s.sequence)[:limit]

        completadas_count = len(completadas_ids)
        total_ruta = ruta.total_slides if ruta else 0

        def _compute_confidence(slide):
            if not total_ruta:
                return 60
            ratio = completadas_count / total_ruta if total_ruta else 0
            return min(95, int(60 + ratio * 40))

        result = []
        for slide in recomendadas:
            description = slide.description or getattr(slide, 'website_description', '') or ''
            estimated_time = getattr(slide, 'completion_time', 0) or getattr(slide, 'duration', 0)

            result.append({
                'id': slide.id,
                'name': slide.name,
                'title': slide.name,
                'description': description,
                'difficulty': slide.nivel_dificultad or 'basico',
                'estimated_time': int(estimated_time),
                'url': f'/slides/slide/{slide.id}',
                'channel_id': slide.channel_id.id,
                'confidence': _compute_confidence(slide),
            })

        return result
