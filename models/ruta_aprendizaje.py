# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RutaAprendizaje(models.Model):
    _name = 'slide.ruta.aprendizaje'
    _description = 'Ruta de Aprendizaje Personalizada'
    _order = 'fecha_creacion desc'

    name = fields.Char(
        'Nombre de la Ruta',
        compute='_compute_name',
        store=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        index=True,
        ondelete='cascade'
    )
    channel_id = fields.Many2one(
        'slide.channel',
        string='Curso',
        required=True,
        ondelete='cascade'
    )
    slide_ids = fields.Many2many(
        'slide.slide',
        'ruta_aprendizaje_slide_rel',
        'ruta_id',
        'slide_id',
        string='Diapositivas Recomendadas'
    )
    nivel_dificultad = fields.Selection([
        ('basico', 'Básico'),
        ('intermedio', 'Intermedio'),
        ('avanzado', 'Avanzado')
    ], string='Nivel de Dificultad', default='basico')

    fecha_creacion = fields.Datetime(
        'Fecha de Creación',
        default=fields.Datetime.now,
        required=True
    )
    fecha_actualizacion = fields.Datetime(
        'Última Actualización',
        default=fields.Datetime.now
    )
    activa = fields.Boolean(
        'Ruta Activa',
        default=True
    )
    descripcion = fields.Text('Descripción')

    total_slides = fields.Integer(
        'Total de Diapositivas',
        compute='_compute_total_slides',
        store=True
    )
    progreso_ruta = fields.Float(
        'Progreso de la Ruta (%)',
        compute='_compute_progreso_ruta',
        store=True
    )

    @api.depends('user_id', 'channel_id')
    def _compute_name(self):
        for record in self:
            record.name = f"Ruta de {record.user_id.name} - {record.channel_id.name}"

    @api.depends('slide_ids')
    def _compute_total_slides(self):
        for record in self:
            record.total_slides = len(record.slide_ids)

    @api.depends('slide_ids', 'user_id')
    def _compute_progreso_ruta(self):
        for record in self:
            if not record.slide_ids:
                record.progreso_ruta = 0.0
                continue

            historial = self.env['slide.historial.progreso'].search([
                ('user_id', '=', record.user_id.id),
                ('slide_id', 'in', record.slide_ids.ids),
                ('completado', '=', True)
            ])

            completadas = len(historial)
            total = len(record.slide_ids)
            record.progreso_ruta = (completadas / total * 100) if total > 0 else 0.0

    @api.model
    def create(self, vals):
        vals['fecha_actualizacion'] = fields.Datetime.now()
        return super(RutaAprendizaje, self).create(vals)

    def write(self, vals):
        vals['fecha_actualizacion'] = fields.Datetime.now()
        return super(RutaAprendizaje, self).write(vals)

    def actualizar_recomendaciones(self):
        """Actualiza las recomendaciones de la ruta basándose en el progreso actual"""
        self.ensure_one()
        recommendation_engine = self.env['slide.recommendation.engine']
        nuevas_slides = recommendation_engine.get_recommendations(
            self.user_id.id,
            self.channel_id.id
        )

        if nuevas_slides:
            slide_ids = [s['id'] for s in nuevas_slides]
            self.write({'slide_ids': [(6, 0, slide_ids)]})

        return True

    def action_view_progreso(self):
        """Abre una vista con el progreso detallado de esta ruta"""
        self.ensure_one()
        
        domain = [
            ('user_id', '=', self.user_id.id),
            ('slide_id', 'in', self.slide_ids.ids)
        ]
        
        return {
            'name': f'Progreso de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'slide.historial.progreso',
            'view_mode': 'list,form,pivot,graph',
            'domain': domain,
            'context': {
                'default_user_id': self.user_id.id,
                'search_default_group_by_slide': 1,
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    No hay registros de progreso para esta ruta
                </p>
                <p>
                    El progreso se registra automáticamente cuando el usuario
                    completa las diapositivas de la ruta.
                </p>
            """
        }

    def action_view_slides(self):
        """Abre una vista con las diapositivas de esta ruta"""
        self.ensure_one()
        
        return {
            'name': f'Diapositivas de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'slide.slide',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.slide_ids.ids)],
            'context': {
                'default_channel_id': self.channel_id.id,
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    No hay diapositivas en esta ruta
                </p>
                <p>
                    Use el botón "Actualizar Recomendaciones" para generar
                    diapositivas recomendadas para esta ruta.
                </p>
            """
        }
