# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class Course(models.Model):
    _name = 'academy.course'
    _description = 'Curso Información'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción', required=True)
    level = fields.Selection([('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja')],string='Dificultad', required= True)

    active = fields.Boolean(string='Activo', default=True)
    base_price = fields.Float(string='Precio Base', required=True, default=0.0)
    additional_fee = fields.Float(string='Costo Adicional', required=True, default=10.0)
    total_price = fields.Float(
        string='Precio Total',
        compute='_compute_total_price',
        store=True,
    )
    #AGrego de session
    session_ids = fields.One2many('academy.session', 'course_id', string='Sesiones')
    def init(self):
        records = self.search([])
        records._compute_total_price()
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._compute_total_price()
            
        return records
    @api.depends('base_price', 'additional_fee')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.base_price + record.additional_fee

    @api.constrains('base_price')
    def _check_base_price(self):
        for record in self:
            if record.base_price < 0.0:
                raise ValidationError('El precio base no puede tener un valor negativo')

    @api.constrains('additional_fee')
    def _check_additional_fee(self):
        for record in self:
            if record.additional_fee < 10.00:
                raise ValidationError('El costo adicional debe ser mayor o igual a 10.00')

