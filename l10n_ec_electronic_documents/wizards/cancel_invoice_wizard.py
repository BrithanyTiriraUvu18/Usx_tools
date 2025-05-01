from odoo import fields, models


class CancelInvoiceWizard(models.TransientModel):
    _name = "cancel.invoice.wizard"
    _description = "Cancel invoice wizard"

    reason = fields.Char("Motivo de la Anulación")

    def cancel_document(self):
        account_move = self.env["account.move"].search(
            [("id", "=", self._context["account_move"])]
        )
        account_move.cancel_invoice(self.reason)
