from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = ["account.move"]

    voucher_type_ats = fields.Many2one(
        comodel_name="account.voucher.type",
        string="Tipo Documento",
        ondelete="cascade",
        default=lambda self: self.env["account.voucher.type"].search([], limit=1).id,
    )

    amended_invoice_id = fields.Many2one(
        "account.move",
        string="Factura Rectificativa",
        copy=False,
    )
    tax_support_id = fields.Many2one(
        comodel_name="account.ats.support", string="Tax Support"
    )

    def default_get(self, fields=None):
        if not fields:
            fields = []
        res = super(AccountMove, self).default_get(fields)
        for record in self:
            if record.move_type == "out_refund":
                inv = record.reversed_entry_id
                if inv:
                    record.amended_invoice_id = inv.id
                else:
                    origin_name = record.invoice_origin
                    if origin_name:
                        origin = self.env["sale.order"].search(
                            [("name", "=", origin_name)]
                        )
                        moves = origin.mapped("invoice_ids")
                        invoices = moves.filtered(
                            lambda l: l.move_type == "out_invoice"
                        )
                        if len(invoices) == 1:
                            record.amended_invoice_id = invoices.id

        return res

    @api.onchange("partner_id")
    def _onchange_partner(self):
        for rec in self:
            if rec.partner_id:
                rec.tax_support_id = rec.partner_id.ats_support_id

    @api.onchange("tax_support_id", "partner_id")
    def _onchange_tax_support(self):
        self.ensure_one()
        if self.move_type in ["out_invoice", "out_refund"]:
            return

        vouchers = self.tax_support_id.mapped("document_type_ids").mapped("id")
        if vouchers:
            return {"domain": {"voucher_type_ats": [("id", "in", vouchers)]}}
        else:
            return {"domain": {"voucher_type_ats": [("id", "in", [])]}}

    def action_post(self):
        for record in self:
            if record.move_type == "out_refund" and not record.reversed_entry_id:
                record.reversed_entry_id = record.amended_invoice_id.id
        res = super().action_post()
        return res
