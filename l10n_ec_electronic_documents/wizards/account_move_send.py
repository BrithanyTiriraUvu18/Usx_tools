from odoo import api, models


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send"

    def _get_placeholder_mail_attachments_data(self, move):
        if move.ride:
            return []
        return super()._get_placeholder_mail_attachments_data(move)

    @api.model
    def _get_invoice_extra_attachments(self, move):
        if move.ride:
            return move._get_attachments()
        return super()._get_invoice_extra_attachments(move)
