from odoo import api, fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    _TYPE_EC = [
        ("vat", "IVA Diferente de 0%"),
        ("vat0", "IVA 0%"),
        ("novat", "No objeto de IVA"),
        ("ret_vat_b", "Retención de IVA (Bienes)"),
        ("ret_vat_srv", "Retención de IVA (Servicios)"),
        ("withhold_vat", "VAT Withhold"),
        ("exempt_vat", "VAT Excempt"),
        ("ret_ir", "Ret. Imp. Renta"),
        ("no_ret_ir", "No sujetos a Ret. de Imp. Renta"),
        ("imp_ad", "Imps. Aduanas"),
        ("imp_sbs", "Super de Bancos"),
        ("ice", "ICE"),
        ("irbpnr", "Plastic Bottles (IRBPNR)"),
        ("other", "Other"),
    ]

    l10n_ec_type = fields.Selection(
        _TYPE_EC, string="Tipo Impuesto Ecuatoriano", help="Ecuadorian taxes subtype"
    )

    tax_code = fields.Many2one(
        "account.sri.charts",
        domain="[('type', '=', 'tax_code')]",
    )

    @api.onchange("l10n_ec_type")
    def on_change_l10n_type(self):
        tax_code = (
            self.env["account.sri.charts"].sudo().search([("type", "=", "tax_code")])
        )

        self.tax_code = tax_code.filtered(lambda l: l.value == self.l10n_ec_type).id
