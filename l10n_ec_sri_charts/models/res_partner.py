from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_default_tax_support(self):
        tax_support_id = self.env["ir.config_parameter"].sudo().get_param("tax_support")
        return self.env["account.ats.support"].browse(int(tax_support_id))

    ats_support_id = fields.Many2one(
        "account.ats.support",
        string="Apoyo Fiscal",
        required=True,
        default=lambda self: self._get_default_tax_support(),
    )
    is_electronic = fields.Boolean(string="Documentos Electrónicos?", default=True)

    auth_num = fields.Char("Número Autorización", size=128)
    serie_est = fields.Char(
        "Establishment Series",
        size=3,
    )
    serie_issue = fields.Char(
        "Issue Series",
        size=3,
    )

    num_start = fields.Integer("Range from", help="Checkbook start number")
    num_end = fields.Integer("Range to", help="Checkbook end number")

    expiration_date = fields.Date(help="Stub Expiration Date")
