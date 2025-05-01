from odoo import api, fields, models


class AccountVoucherType(models.Model):
    _name = "account.voucher.type"
    _description = "Voucher Type"

    @api.depends("name", "code")
    def name_get(self):
        res = []
        for record in self:
            name = "%s - %s" % (record.code, record.name)
            res.append((record.id, name))
        return res

    name = fields.Char()
    code = fields.Char(size=4, required=True)
    xml_code = fields.Char("Código XML", size=4, required=True)
    active = fields.Boolean(string="Activo?")
    description = fields.Char()
    ats_support_ids = fields.Many2many(
        "account.ats.support",
        "support_voucher_rel",
        "voucher_type_id",
        "support_id",
        string="Soporte ATS",
    )
