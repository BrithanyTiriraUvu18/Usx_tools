from odoo import api, fields, models


class ElectronicDocumentSettings(models.TransientModel):
    _inherit = "res.config.settings"

    voucher_out_invoice = fields.Many2one(
        comodel_name="account.voucher.type",
        string="Default Invoice Document Type",
    )
    voucher_out_refund = fields.Many2one(
        comodel_name="account.voucher.type",
        string="Default Refund Document Type",
    )
    epayment_config = fields.Many2one(
        "account.sri.charts",
        string="Default payment method",
        domain="[('type', '=', 'payment_method')]",
    )
    tax_support = fields.Many2one(
        "account.ats.support",
        string="Default tax support",
    )

    def set_values(self):
        res = super(ElectronicDocumentSettings, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "voucher_out_invoice", self.voucher_out_invoice.id
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "voucher_out_refund", self.voucher_out_refund.id
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "epayment_config", self.epayment_config.id
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "tax_support", self.tax_support.id
        )
        return res

    @api.model
    def get_values(self):
        res = super(ElectronicDocumentSettings, self).get_values()
        voucher_out_invoice = self.env["ir.config_parameter"].get_param(
            "voucher_out_invoice"
        )
        voucher_out_refund = self.env["ir.config_parameter"].get_param(
            "voucher_out_refund"
        )
        epayment_config = self.env["ir.config_parameter"].get_param("epayment_config")
        tax_support = self.env["ir.config_parameter"].get_param("tax_support")

        if voucher_out_invoice is not False:
            res["voucher_out_invoice"] = int(voucher_out_invoice)

        if voucher_out_refund is not False:
            res["voucher_out_refund"] = int(voucher_out_refund)

        if epayment_config is not False:
            res["epayment_config"] = int(epayment_config)

        if tax_support is not False:
            res["tax_support"] = int(tax_support)

        return res
