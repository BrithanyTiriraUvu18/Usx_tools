from odoo import models, fields, api

class ImportContactWizard(models.TransientModel):
    _name = 'import.contact.wizard'
    _description = 'Import Contact Wizard'

    contact_type = fields.Selection([
        ('cliente', 'Cliente'),
        ('proveedor', 'Proveedor')
    ], string="Tipo de Contacto", required=False)

