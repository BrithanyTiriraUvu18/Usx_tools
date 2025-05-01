from odoo import fields, models


class Ride(models.TransientModel):
    _name = "ride.wizard"
    _description = "Download file RIDE"

    ride_name = fields.Char("File name", readonly=True)
    ride = fields.Binary(
        "File data",
        readonly=True,
        help="File(jpg, csv, xls, exe, any binary or text format)",
    )
