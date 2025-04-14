from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_imported = fields.Boolean("Imported")
