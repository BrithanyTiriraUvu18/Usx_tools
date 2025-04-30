import logging

from stdnum import ec

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .utils import get_data_partner

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    trade_name = fields.Char("Trade name", index=True)
    identifier = fields.Char(
        "ID / STR",
        required=True,
        help="Identification or Single Taxpayer Registry",
        default="0000000000",
    )
    type_identifier = fields.Selection(
        [("cedula", "ID"), ("ruc", "STR"), ("pasaporte", "PASSPORT")],
        "ID Type",
        required=True,
        default="pasaporte",
    )
    is_end_consumer = fields.Boolean(default=False)
    is_company = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals):
        self = self.with_context(no_vat_validation=True)
        return super(ResPartner, self).create(vals)

    def write(self, vals):
        self = self.with_context(no_vat_validation=True)
        return super(ResPartner, self).write(vals)

    @api.depends("trade_name")
    def _compute_display_name(self):
        res = super()._compute_display_name()
        return res

    @api.constrains("identifier", "type_identifier")
    def _check_identifier(self):
        for record in self:
            res = record.validate_identifier(record.identifier, record.type_identifier)
            if not res:
                raise ValidationError(_("Error in the identifier."))
            record.vat = record.identifier
            return True

    # Method for data autocompletion (search by ID or Ruc)
    @api.onchange("identifier", "type_identifier")
    def _get_data(self):
        self.vat = self.identifier
        fill_data = bool(self.env["ir.config_parameter"].sudo().get_param("fill_data"))
        _logger.debug("fill_data: %s", fill_data)
        if fill_data:
            if self.identifier:
                if self.type_identifier == "ruc":
                    docType = "r"
                elif self.type_identifier == "cedula":
                    docType = "c"
                else:
                    docType = "p"

                if docType != "p" and self.identifier != "0000000000":
                    result = get_data_partner(self.vat, docType)
                    if isinstance(result, dict):
                        if "document" in result:
                            document = result.get("document")
                            establishments = None
                        else:
                            return

                        if "establishments" in document:
                            establishments = document["establishments"]
                        street = ""
                        street2 = ""
                        city = ""
                        state_id = ""

                        if document:
                            name = document.get("socialReason")
                        else:
                            if not self.name:
                                name = ""
                            else:
                                name = self.name
                        if establishments:
                            adr = establishments[0].get("address").split(" / ")
                            if len(adr) == 4:
                                street = (
                                    adr[3].title() if isinstance(adr[3], str) else ""
                                )
                                street2 = (
                                    adr[2].title() if isinstance(adr[2], str) else ""
                                )
                                city = (
                                    adr[1].capitalize()
                                    if isinstance(adr[1], str)
                                    else ""
                                )
                                prov = adr[0].title() if isinstance(adr[0], str) else ""

                            if len(adr) == 5:
                                street = (
                                    adr[4].title() if isinstance(adr[4], str) else ""
                                )
                                city_part = (
                                    adr[2].capitalize()
                                    if isinstance(adr[2], str)
                                    else ""
                                )
                                additional_part = (
                                    adr[3].title() if isinstance(adr[3], str) else ""
                                )
                                street2 = (
                                    f"{city_part} {additional_part}".strip()
                                )  # .strip() elimina espacios extras
                                # street2 = (
                                #     adr[3].title() if isinstance(adr[3], str) else ""
                                # )
                                city = (
                                    adr[1].capitalize()
                                    if isinstance(adr[1], str)
                                    else ""
                                )
                                prov = adr[0].title() if isinstance(adr[0], str) else ""

                            if len(adr) == 1:
                                street = (
                                    adr[0].title() if isinstance(adr[0], str) else ""
                                )
                        else:
                            street = document.get("address")
                            city = document.get("city")
                            prov = document.get("province").capitalize()

                        states = self.env["res.country.state"]
                        state = states.search(
                            [("name", "=", prov)],
                        )
                        state_id = state.ids[0] if state else False
                        self._change_data(name.title(), street, street2, city, state_id)
        else:
            _logger.debug("no autocomplete")

    def _change_data(self, name, street, street2, city, state):
        self.name = name
        self.street = street
        self.street2 = street2
        self.city = city
        self.state_id = state

    def validate_identifier(self, identifier, type_identifier):
        if type_identifier == "cedula":
            return ec.ci.is_valid(identifier)
        elif type_identifier == "ruc":
            if identifier == "9999999999999":
                self.is_end_consumer = True
                return True
            if len(identifier) != 13:
                return False
        return True

    # Function to validate identification number
    @api.constrains("vat")
    def _check_vat_unique(self):
        for record in self:
            if record.parent_id or not record.vat:
                continue

            if record.same_vat_partner_id:
                if record.type_identifier == "pasaporte" and record.vat == "0000000000":
                    continue
                else:
                    raise ValidationError(
                        _("There is already a contact with the same ID or VAT.")
                    )
