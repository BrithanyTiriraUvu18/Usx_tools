import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

userVeronica = "user"

TYPE_REVERSE_MAP = {
    "entry": "entry",
    "out_invoice": "out_refund",
    "out_refund": "entry",
    "in_invoice": "in_refund",
    "in_refund": "entry",
    "out_receipt": "out_refund",
    "in_receipt": "in_refund",
}


class AccountMove(models.Model):
    _name = "account.move"
    _description = "New account move model with electronic documents"
    _inherit = ["account.move", "account.edocument"]

    @api.model
    def _get_default_journal(self):
        if self._context.get("default_doc_type"):
            if self._context.get("default_doc_type") == "liq_purchase":
                return self.env["account.journal"].search(
                    [("is_purchase_liq", "=", True)], limit=1
                )
        else:
            if self._context.get("default_move_type") == "out_invoice":
                return self.env["account.journal"].search(
                    [("type", "=", "sale")], limit=1
                )
            if self._context.get("default_move_type") == "in_invoice":
                return self.env["account.journal"].search(
                    [("type", "=", "purchase")], limit=1
                )

    epayment_id = fields.Many2one(
        "account.sri.charts",
        string="Método de Pago",
        domain="[('type', '=', 'payment_method')]",
    )

    lines_info_additional = fields.One2many(
        "account.info.additional",
        "move_invoice_id",
        "Info",
    )

    reason = fields.Char()
    reason_for_cancellation = fields.Char(string="Motivo Anulación")
    canceled_document = fields.Boolean(string="Documento Anulado", default=False)

    # Replace default journal with purchase liquidation journal
    def _search_default_journal(self):
        if self._context.get("doc_type"):
            if self._context.get("doc_type") == "liq_purchase":
                self.doc_type = "liq_purchase"
                self.move_type = "in_invoice"
                return self.env["account.journal"].search(
                    [("is_purchase_liq", "=", True)], limit=1
                )
        else:
            return super(AccountMove, self)._search_default_journal()

    # Method to obtain default values
    def default_get(self, fields=None):
        if not fields:
            fields = []

        context = dict(self.env.context)
        # Within the context of an invoice,
        # this default value is for the type of the invoice,
        # not the type of the asset.
        # This has to be cleaned from the context before creating the asset,
        # otherwise it tries to create the asset with the type of the invoice.
        key_to_delete = "default_type"
        if key_to_delete in context:
            del context[key_to_delete]
            self = self.with_context(**context)

        res = super(AccountMove, self).default_get(fields)
        for record in self:
            if (
                record.move_type
                and record.state != "posted"
                and record.move_type
                not in [
                    "entry",
                    "out_receipt",
                    "in_receipt",
                ]
            ):
                param_voucher = False
                param_epayment = "epayment_config"
                if record.move_type == "out_invoice":
                    param_voucher = "voucher_out_invoice"
                elif record.move_type == "out_refund":
                    reason = self._get_reason(self)
                    if reason:
                        record.reason = reason
                    else:
                        if record.reason:
                            record.ref = "Reversal of: "
                            record.ref += (
                                (record.amended_invoice_id.name + ", ")
                                if record.amended_invoice_id
                                else ""
                            )
                            record.ref += record.reason
                    param_voucher = "voucher_out_refund"
                if param_voucher and (
                    not record.voucher_type_ats or record.voucher_type_ats.id == 1
                ):
                    voucher_default = (
                        self.env["ir.config_parameter"].sudo().get_param(param_voucher)
                    )
                    if voucher_default != 0:
                        record.voucher_type_ats = int(voucher_default)
                if not record.epayment_id:
                    epay_default = (
                        self.env["ir.config_parameter"].sudo().get_param(param_epayment)
                    )
                    record.epayment_id = int(epay_default)

            if not record.doc_type:
                record.doc_type = record.move_type
                record.update({"doc_type": record.move_type})

        return res

    @api.depends("journal_id.bi_sequence_id.is_edocument")
    def _compute_on_validate_seq(self):
        for record in self:
            if record.doc_type == "liq_purchase":
                liq_id = record.journal_id.bi_liq_pur_seq_id.is_edocument
                record.valide_seq = liq_id

            elif record.doc_type == "out_refund":
                ref_id = record.journal_id.bi_refund_sequence_id.is_edocument
                record.valide_seq = ref_id
            else:
                record.valide_seq = record.journal_id.bi_sequence_id.is_edocument

    def action_cancel_invoice(self):
        return {
            "name": _("Cancel Invoice"),
            "view_mode": "form",
            "res_model": "cancel.invoice.wizard",
            "type": "ir.actions.act_window",
            "context": {
                "account_move": self.id,
            },
            "target": "new",
        }

    def cancel_invoice(self, reason_for_cancellation):
        self.ensure_one()
        self.write(
            {
                "reason_for_cancellation": reason_for_cancellation,
                "canceled_document": True,
                "state_document": "edocument_cancelled",
            }
        )
        self.button_draft()
        self.button_cancel()

    def check_date(self, invoice_date):
        """
        Validate that the electronic voucher is sent within 24 hours after its issuance.
        """
        LIMIT_TO_SEND = 1
        MESSAGE_TIME_LIMIT = " ".join(
            [
                "Electronic vouchers must be sent ",
                "within 24 hours of their issuance..",
            ]
        )
        dt = datetime(invoice_date.year, invoice_date.month, invoice_date.day)
        days = (datetime.today() - dt).days
        if days > LIMIT_TO_SEND:
            raise UserError(MESSAGE_TIME_LIMIT)

    def _get_reason(self, invoice):
        text = str(invoice.ref)
        reason = ""
        if self.reason:
            return reason

        title = text.split(",")
        if len(title) >= 2:
            reason = title[1]

        return reason

    def action_post(self):
        if self.canceled_document:
            raise UserError(
                _(
                    "The document has already been cancelled at the SRI and"
                    "cannot be sent again."
                )
            )
        action = super().action_post()
        for record in self:
            if record.move_type not in ["entry", "out_receipt", "in_receipt"]:
                record.info_message = ""
                identifier = record.partner_id.is_end_consumer
                if identifier:
                    if (
                        record.amount_total
                        > record.company_id.max_amount_final_consumer
                    ):
                        raise UserError(
                            _("Exceeds the maximum value for end consumers")
                        )
        return action

    # Do not return to draf
    def button_draft(self):
        draft = super(AccountMove, self).button_draft()

        for rec in self:
            if rec.move_type == "entry":
                return draft

        if not self.canceled_document:
            if self.ei_is_valid or self.state_send_document in [
                "sent",
                "authorized",
            ]:
                raise UserError(
                    _(
                        "The Document has already been to the SRI and cannot be returned "
                        "to draft."
                    )
                )

        self.state_send_document = "draft"

        return draft

    # validate that the type of document, whether reimbursement or invoice is authorized,
    # because if it is authorized it should not break the reconciliation.
    def js_validate_unreconcile(self, partial_id):
        self.ensure_one()
        partial = self.env["account.partial.reconcile"].browse(partial_id)
        move_id = partial.credit_move_id.move_id

        if self.move_type == "out_refund" and self.state_send_document == "authorized":
            return True

        if (
            self.move_type == "out_invoice"
            and move_id.state_send_document == "authorized"
        ):
            return True

        return False


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"
    """
           'IVA': '2',
           'ICE': '3',
           'IRBPNR': '5'
       """
    name = fields.Char(required=True, translate=True)


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def refund_moves(self):

        res = super(AccountMoveReversal, self).refund_moves()
        voucher_default = int(
            self.env["ir.config_parameter"].sudo().get_param("voucher_out_refund")
        )

        if not res["res_id"] in self.move_ids.reversal_move_id.ids:
            raise ValidationError(_("Error while creating credit note"))

        reversal = self.env["account.move"].search([("id", "=", res["res_id"])])

        reversal.write(
            {"amount_tax_vat_with": 0, "amount_tax_ir_with": 0, "amount_vat_plus_ir": 0}
        )

        if "evoucher" in self.env.context:
            evoucher = self.env["account.evoucher"].search(
                [("id", "=", self.env.context["evoucher"])]
            )
            reversal.evoucher = evoucher
            reversal.access_key_label = evoucher.name
            evoucher.state = "processed"

        reversal.reason = self.reason
        if voucher_default != 0:
            reversal.voucher_type_ats = voucher_default

        return res
