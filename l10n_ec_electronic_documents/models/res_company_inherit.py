from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    env_service = fields.Selection(
        [("1", "Test"), ("2", "Production")],
        string="Enviroment",
        required=True,
        default="1",
    )

    required_accounting = fields.Selection(
        [("SI", "YES"), ("NO", "NO")],
        string="Mandatory Accounting",
        required=True,
        default="SI",
    )

    attempts_per_day = fields.Integer(
        string="#Shipping attempts per day:", required=True, default=3
    )

    ride_name_param = fields.Char(
        string="Ride Name:",
        required=False,
    )

    ride_footer_param = fields.Char(
        string="Ride Footer:",
        required=False,
    )

    ride_main_color_param = fields.Char(
        string="Ride Main Color:",
        required=False,
    )

    ride_disable_payment_timeout_param = fields.Boolean(
        string="Ride Disable Payment Timeouts",
        default=False,
    )

    gema_user = fields.Char(
        string="Gema User:",
        required=True,
    )

    gema_password = fields.Char(
        string="Gema Password:",
        required=True,
    )

    conect_gema = fields.Boolean(
        string="Conectar con Gema",
        default=False,
    )
