from odoo import api, fields, models


class AccountInvoiceTax(models.Model):
    _inherit = "account.tax"

    type = fields.Char(string="Tipo")
    code = fields.Char(string="Código")
    l10n_ec_code_applied = fields.Char(
        string="Código Aplicado",
        help="Tax declaration code of the resulting "
        "amount after the calculation of the tax",
    )
    code_edocument = fields.Char(
        string="Código Facturación Electrónica",
        help="Code in Electronic Invoicing",
    )

    # Code in Electronic Invoicing

    @api.onchange("tax_group_id")
    def onchange_code(self):
        for record in self:
            record.type = record.tax_group_id.l10n_ec_type


# class AccountTaxTemplate(models.Model):
#     _inherit = "account.tax.template"

#     def _get_tax_vals(self, company, tax_template_to_tax):
#         vals = super(AccountTaxTemplate, self)._get_tax_vals(
#             company, tax_template_to_tax
#         )
#         vals.update(
#             {
#                 "code": self.code,
#                 "l10n_ec_code_applied": self.l10n_ec_code_applied,
#                 "code_edocument": self.code_edocument,
#             }
#         )
#         return vals

#     l10n_ec_code_applied = fields.Char(
#         string="Code applied",
#         help="Tax declaration code of the resulting amount "
#         "after the calculation of the tax",
#     )
#     code = fields.Char(
#         string="Code base",
#         help="Tax declaration code of the base amount prior "
#         "to the calculation of the tax",
#     )
#     code_edocument = fields.Char(
#         string="Code in Electronic Invoicing",
#         help="Code in Electronic Invoicing",
#     )
