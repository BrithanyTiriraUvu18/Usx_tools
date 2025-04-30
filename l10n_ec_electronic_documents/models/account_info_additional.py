from odoo import fields, models


class AccountInfoAdditional(models.Model):
    _name = "account.info.additional"
    _description = "Account Additional Info"

    name = fields.Char()

    description = fields.Char()

    move_invoice_id = fields.Many2one(
        "account.move",
        string="Move",
        index=True,
        auto_join=True,
        ondelete="cascade",
    )


class CustomAccountMove(models.Model):
    _inherit = "account.move"

    # @api.model
    # def create(self, vals):
    #     document_type_id = vals.get("voucher_type_ats")
    #     if document_type_id == 1:  # Factura
    #         if vals.get("access_key_label"):  # Solo validamos evoucher para facturas
    #             domain = [
    #                 ("access_key_label", "=", vals.get("access_key_label")),
    #             ]
    #             existing_records = self.search(domain)
    #             if existing_records:
    #                 raise ValidationError(
    #                     _("Ya existe una factura con la misma Clave de Acceso.")
    #                 )
    #     elif document_type_id == 2:  # Nota de Venta
    #         if vals.get("support_document"):
    #             domain = [
    #                 ("support_document", "=", vals.get("support_document")),
    #             ]
    #             existing_records = self.search(domain)
    #             if existing_records:
    #                 raise ValidationError(
    #                     _(
    #                         "Ya existe una nota de venta con el mismo Documento de Apoyo."
    #                     )
    #                 )

    #     return super(CustomAccountMove, self).create(vals)

    # def write(self, vals):
    #     document_type_id = vals.get("voucher_type_ats")
    #     if document_type_id == 1:  # Factura
    #         if vals.get("access_key_label"):  # Solo validamos evoucher para facturas
    #             domain = [
    #                 ("access_key_label", "=", vals.get("access_key_label")),
    #                 ("id", "!=", self.id),
    #             ]
    #             existing_records = self.search(domain)
    #             if existing_records:
    #                 raise ValidationError(
    #                     _("Ya existe una factura con la misma Clave de Acceso.")
    #                 )
    #     elif document_type_id == 2:  # Nota de Venta
    #         if vals.get("support_document"):
    #             domain = [
    #                 ("support_document", "=", vals.get("support_document")),
    #                 ("id", "!=", self.id),
    #             ]
    #             existing_records = self.search(domain)
    #             if existing_records:
    #                 raise ValidationError(
    #                     _(
    #                         "Ya existe una nota de venta con el mismo Documento de Apoyo."
    #                     )
    #                 )

    #     return super(CustomAccountMove, self).write(vals)
