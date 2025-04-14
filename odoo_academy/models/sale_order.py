# -*- coding: utf-8 -*-
from odoo import models, fields  # ← ¡Esto era lo que faltaba!

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    session_id = fields.Many2one(
        comodel_name='academy.session',
        string='Sesión Relacionada',
        ondelete='set null'
    )

    instructor_id = fields.Many2one(
        string='Sesión Instructor',
        related='session_id.instructor_id',
        store=True,
        readonly=True
    )

    student_ids = fields.Many2many(
        'res.partner',
        compute='_compute_student_ids',
        string='Estudiantes',
        store=False,
        readonly=True
    )

    def _compute_student_ids(self):
        for order in self:
            order.student_ids = order.session_id.student_ids
