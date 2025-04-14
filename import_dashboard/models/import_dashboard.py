from odoo import fields, models


class ImportDashboard(models.Model):
    _name = "import.dashboard"
    _description = "Import Dashboard"

    name = fields.Char("Import Dashboard")

    state = fields.Selection([
        ("account.move", "Invoice / Bill"),
        ('res.partner', 'Contactos'),
    ], string="Modelo a importar")
