import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class IdentificationNumberSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fill_data = fields.Boolean(
        string="Automatically fill in data?",
    )

    def set_values(self):
        res = super(IdentificationNumberSettings, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param("fill_data", self.fill_data)
        return res

    def get_values(self):
        res = super(IdentificationNumberSettings, self).get_values()
        fill_data = self.env["ir.config_parameter"].get_param("fill_data")
        res.update(
            {
                "fill_data": fill_data,
            }
        )
        return res
