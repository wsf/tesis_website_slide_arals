# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HistorialProgreso(models.Model):
    _name = 'slide.historial.progreso'
    _description = 'Historial de Progreso del Estudiante'
    _order = 'fecha_acceso desc'

    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        index=True,
        ondelete='cascade'
    )
    slide_id = fields.Many2one(
        'slide.slide',
        string='Diapositiva',
        ondelete='cascade'
    )
    channel_id = fields.Many2one(
        'slide.channel',
        string='Canal/Curso',
        ondelete='cascade',
        index=True
    )
    tiempo_dedicado = fields.Float(
        'Tiempo Dedicado (minutos)',
        default=0.0
    )
    intentos_quiz = fields.Integer(
        'Intentos en Quiz',
        default=0
    )
    puntuacion = fields.Float(
        'Puntuación',
        default=0.0
    )
    fecha_acceso = fields.Datetime(
        'Fecha de Acceso',
        default=fields.Datetime.now,
        required=True
    )
    completado = fields.Boolean(
        'Completado',
        default=False
    )
    notas = fields.Text('Notas del Estudiante')

    progreso_porcentaje = fields.Float(
        'Progreso (%)',
        compute='_compute_progreso_porcentaje',
        store=True
    )

    @api.depends('completado', 'puntuacion')
    def _compute_progreso_porcentaje(self):
        for record in self:
            if record.completado:
                record.progreso_porcentaje = 100.0
            else:
                record.progreso_porcentaje = min(record.puntuacion, 100.0)

    @api.constrains('puntuacion')
    def _check_puntuacion(self):
        for record in self:
            if record.puntuacion < 0 or record.puntuacion > 100:
                raise ValidationError('La puntuación debe estar entre 0 y 100')

    @api.constrains('tiempo_dedicado')
    def _check_tiempo_dedicado(self):
        for record in self:
            if record.tiempo_dedicado < 0:
                raise ValidationError('El tiempo dedicado no puede ser negativo')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.user_id.name} - {record.slide_id.name if record.slide_id else record.channel_id.name}"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        result = super(HistorialProgreso, self).create(vals)
        self._update_rutas_progreso(result)
        return result

    def write(self, vals):
        result = super(HistorialProgreso, self).write(vals)
        if 'completado' in vals or 'puntuacion' in vals:
            self._update_rutas_progreso(self)
        return result

    def _update_rutas_progreso(self, records):
        """Actualiza el progreso de las rutas afectadas"""
        for record in records:
            if record.user_id and record.slide_id:
                rutas = self.env['slide.ruta.aprendizaje'].search([
                    ('user_id', '=', record.user_id.id),
                    ('slide_ids', 'in', record.slide_id.id)
                ])
                # Forzar recalculo del campo computado
                rutas._compute_progreso_ruta()
