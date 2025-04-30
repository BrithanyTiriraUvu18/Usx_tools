import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DocElectronic(models.AbstractModel):
    _name = "account.edocument"
    _description = "Document Electronic"

    auth_document = fields.Char(string="Mensaje", copy=False, readonly=True)
    info_message = fields.Char(string="Mensaje Informativo", copy=False)
    state_document = fields.Selection(
        selection=[
            ("edocument_not_generated", "Elec. Document not generated"),
            ("edocument_correct", "Elec. Document correct"),
            ("request_cancel", "Cancellation in process"),
            ("edocument_cancelled", "Elec. Document cancelled"),
            ("request_rejected", "Cancellation rejected"),
        ],
        string="Estado Factura",
        default="edocument_not_generated",
        readonly=True,
        copy=False,
    )

    attempts = fields.Integer(copy=False, default=0)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    ei_is_valid = fields.Boolean(
        string="Valid", copy=False, readonly=True, default=False
    )

    check_progress = fields.Float(string="Progreso", default=0.0)

    unauthorized_bool = fields.Boolean(
        string="no autorizado", copy=False, default=False
    )
    access_key_label = fields.Char(string="Clave Acceso", copy=False)
    ride_name = fields.Char(string="Archivo Facturas")
    ride = fields.Binary(string="RIDE", copy=False, attachment=True)
    pdf_ride_attachment = fields.Many2one(
        "ir.attachment", string="Ride PDF", copy=False
    )
    xml_ride_attachment = fields.Many2one(
        "ir.attachment", string="Ride XML", copy=False
    )

    date_authorized = fields.Datetime(string="Fecha Autorización", copy=False)
    xml_name = fields.Char(string="Archivo Factura XML")
    xml_ride = fields.Binary(string="RIDE XML", copy=False, attachment=True)

    state_send_document = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("created", "Created"),
            ("sent", "Sent"),
            ("authorized", "Authorized ✔"),
            ("returned", "Returned"),
            ("in_process", "In process"),
        ],
        default="draft",
        readonly=True,
        copy=False,
    )

    total_len = 4
    doc_type = fields.Char(string="Tipo Documento")

    @api.constrains("access_key_label")
    def _check_access_key_label(self):
        if self._name != "account.move":
            return
        for record in self:
            if not record.access_key_label:
                return
            if record.invoice_filter_type_domain == "purchase":
                if record.is_receipt:
                    continue
                if record.voucher_type_ats.code == "2":
                    pattern = r"^\d{10}$"
                    error_message = _("The authorization number must contain 10 digits")
                else:
                    pattern = r"^\d{49}$"
                    error_message = _("The access key must contain 49 digits")
                if not re.match(pattern, record.access_key_label):
                    raise ValidationError(error_message)

    def _check_invoice(self, num):
        for rec in self:
            if self.total_len != 0:
                rec.check_progress = (num * 100) / self.total_len

    def _get_num_estab_ruc(self):
        if self.sequence_prefix:
            if self.move_type == "referral_guide":
                values = self._get_digit(
                    self.journal_id.bi_referral_guide_sequence_id.prefix
                )
            else:
                values = self._get_digit(self.sequence_prefix)
            estab = values[:3]
            return estab
        else:
            raise Exception("No existe una secuencia establecida")

    def _get_emission_series(self):
        if self.move_type == "referral_guide":
            values = self._get_digit(
                self.journal_id.bi_referral_guide_sequence_id.prefix
            )
        else:
            values = self._get_digit(self.sequence_prefix)
        emission = values[3:]
        return emission

    def _get_digit(self, value):
        numbers = ""
        if value:
            for s in value:
                if s.isdigit():
                    numbers += s
        return numbers

    def get_sequential(self):
        sequencial = ""
        numbers = ""
        for s in self.name:
            if s.isdigit():
                numbers += s
        if len(numbers) <= 9:
            aux = len(numbers)
            while aux < 9:
                sequencial += "0"
                aux += 1
        else:

            aux = 0
            num = numbers[::-1]
            numbers = ""
            while aux < 9:
                numbers += num[aux]
                aux += 1
            numbers = numbers[::-1]
        sequencial += numbers
        return sequencial

    def action_send_email(self):
        mail_template = (
            self.env["mail.template"]
            .sudo()
            .search([("name", "=", "Withholding: Send by email")], limit=1)
        )
        mail_template.send_mail(self.id, force_send=False, notif_layout=True)

    def download_file(self):
        my_file = self.env["ride.wizard"].create(
            {
                "ride_name": self.ride_name,
                "ride": self.ride,
            }
        )

        return {
            "name": _("Download File"),
            "res_id": my_file.id,
            "res_model": "ride.wizard",
            "target": "new",
            "type": "ir.actions.act_window",
            "view_id": self.env.ref(
                "l10n_ec_electronic_documents.save_ride_wizard_view_done"
            ).id,
            "view_mode": "form",
            "view_type": "form",
        }

    def get_access_key(self, order):
        issue_date = order.invoice_date.strftime("%d/%m/%Y").replace("/", "")
        enviroment = self.env.user.company_id.env_service
        type_of_issue = "1"
        company = order.company_id
        ruc = company.partner_id.identifier
        types_docs = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "document_type")])
        )
        type_doc = types_docs.filtered(lambda t: t.value == self.move_type).code
        establishment = self._get_num_estab_ruc()
        point_of_issue = self._get_emission_series()
        sequence = self.get_sequential()
        pre_key = (
            issue_date
            + type_doc
            + ruc
            + enviroment
            + establishment
            + point_of_issue
            + sequence
            + "00000001"
            + type_of_issue
        )

        def check_digit(key):
            new_key = list(map(int, key))
            mult = 7
            check_digit = 0

            for i in range(len(new_key)):
                new_key[i] *= mult
                mult -= 1
                if mult == 1:
                    mult = 7

            for value in new_key:
                check_digit += value

            check_digit %= 11
            check_digit = 11 - check_digit

            if check_digit == 11:
                check_digit = 0
            elif check_digit == 10:
                check_digit = 1

            return check_digit

        return pre_key + str(check_digit(pre_key))
