from odoo import fields, models


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    is_edocument = fields.Boolean(string="Documento Electrónico", copy=False)
