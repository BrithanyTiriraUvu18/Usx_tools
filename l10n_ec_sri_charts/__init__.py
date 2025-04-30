from . import models
from odoo import _, api, SUPERUSER_ID
from odoo.exceptions import UserError


def pre_init_hook(cr):
    pass
    # env = api.Environment(cr, SUPERUSER_ID, {})
    # exclude = "l10n_ec"
    # modules = env["ir.module.module"].search_count(
    #     [
    #         ("name", "=", exclude),
    #         ("state", "in", ["installed", "to install", "to upgrade"]),
    #     ]
    # )
    # if modules > 0:

    #     raise UserError(
    #         _(
    #             'The module l10n_ec_sri_charts replaces "%s". Please uninstall first.',
    #             exclude,
    #         )
    #     )
