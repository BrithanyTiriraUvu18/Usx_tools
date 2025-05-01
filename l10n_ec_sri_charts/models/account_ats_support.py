from odoo import api, fields, models


class AccountAtsSupport(models.Model):
    _name = "account.ats.support"
    _description = "Support of the Voucher"

    @api.depends("code", "type_support")
    def name_get(self):
        res = []
        for record in self:
            name = "%s - %s" % (record.code, record.type_support)
            res.append((record.id, name))
        return res

    code = fields.Char(size=2, required=True)
    type_support = fields.Char("Tipo de ayuda", size=128, required=True)
    document_type_ids = fields.Many2many(
        "account.voucher.type",
        "support_voucher_rel",
        "support_id",
        "voucher_type_id",
        string="Tipos Documentos",
        help="",
    )
