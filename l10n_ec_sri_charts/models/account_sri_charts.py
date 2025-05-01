from odoo import api, fields, models


class AccountSriCharts(models.Model):
    _name = "account.sri.charts"
    _description = "SRI Tables"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    value = fields.Char()
    type = fields.Selection(
        required=True,
        selection=[
            ("document_type", "Document Type"),
            ("identification_type", "Identification Type"),
            ("vat_withholding", "Vat Withholding"),
            ("tax_withholding", "Tax Withholding"),
            ("tax_code", "Tax Code"),
            ("vat_rate", "Vat Rate"),
            ("payment_method", "Payment Method"),
        ],
    )
    active = fields.Boolean(default=True)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            val = str(self.name)
            self.name = val.upper()
