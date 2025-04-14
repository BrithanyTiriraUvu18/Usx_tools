import base64
from datetime import datetime, timedelta

import xlrd

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.TransientModel):
    _name = "import.account.move.wizard"
    _description = "Import account move wizard"

    move_type = fields.Selection(
        [("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        string="Move type",
        required=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain=[("type", "in", ("sale", "purchase"))],
    )
    xlsx_file = fields.Binary("File", required=True)
    search_product = fields.Selection(
        [("name", "Name"), ("default_code", "Internal Reference")],
        string="Search product by",
        required=True,
        default="name",
    )
    invoice_state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")],
        string="Invoice state",
        required=True,
        default="draft",
    )

    def _get_journal_domain(self):
        if self.move_type == "out_invoice":
            return [("type", "=", "sale")]
        elif self.move_type == "in_invoice":
            return [("type", "=", "purchase")]
        else:
            return [("type", "in", ("sale", "purchase"))]

    @api.onchange("move_type")
    def _onchange_move_type(self):
        if self.move_type:
            return {"domain": {"journal_id": self._get_journal_domain()}}

    def parse_date(self, value, date_format="%m/%d/%y"):
        if isinstance(value, float):  # Caso de fechas en formato de Excel
            base_date = datetime(1899, 12, 30)
            return (base_date + timedelta(days=int(value))).date()
        elif isinstance(value, str):  # Caso de fechas en formato texto
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                raise ValueError(f"Formato de fecha no válido: {value}")
        else:
            raise TypeError(f"Tipo de dato no soportado: {type(value)}")

    def action_import(self):
        if self.xlsx_file:
            # Decode the binary data and read the XLSX file using xlrd
            try:
                data = base64.b64decode(self.xlsx_file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(
                    0
                )  # Assuming data is in the first sheet
            except xlrd.biffh.XLRDError:
                raise UserError(_("Unsupported format or currupt file"))

            invoices = []
            error_message = ""

            # Process the XLSX data and create the invoice
            # Skip header row, start from 2nd row
            invoice = {}
            invoice_lines = []
            for row_index in range(1, sheet.nrows):
                row = row_index + 1

                name = sheet.cell_value(row_index, 0)
                support_document = sheet.cell_value(row_index, 1)
                partner_name = sheet.cell_value(row_index, 2)
                date_string = sheet.cell_value(row_index, 3)
                end_date_string = sheet.cell_value(row_index, 4)
                payment_method = sheet.cell_value(row_index, 5)
                tax_support = sheet.cell_value(row_index, 6)
                doc_type = sheet.cell_value(row_index, 7)
                sales_partner = sheet.cell_value(row_index, 8)
                product = sheet.cell_value(row_index, 9)
                label = sheet.cell_value(row_index, 10)
                account = sheet.cell_value(row_index, 11)
                quantity = sheet.cell_value(row_index, 12)
                price = sheet.cell_value(row_index, 13)

                if name:
                    name_id = self.env["account.move"].search([("name", "=", name)])
                    if name_id:
                        error_message += "Invoice '%s' already exists, on row %s \n" % (
                            name,
                            row,
                        )

                if partner_name:
                    partner_id = self.env["res.partner"].search(
                        [("name", "=", partner_name)]
                    )

                    if not partner_id:
                        error_message += "Partner '%s' not found, on row %s \n" % (
                            partner_name,
                            row,
                        )
                    try:
                        date = self.parse_date(date_string, date_format="%m/%d/%y")
                    except ValueError:
                        error_message += (
                            "Date string '%s' does not match the expected format, on row %s \n"
                            % (date_string, row)
                        )

                    try:
                        end_date = self.parse_date(
                            end_date_string, date_format="%m/%d/%y"
                        )

                    except ValueError:
                        error_message += (
                            "Date string '%s' does not match the expected format, on row %s \n"
                            % (end_date_string, row)
                        )

                    payment_method_id = self.env["account.sri.charts"].search(
                        [
                            ("name", "=", payment_method),
                        ]
                    )
                    if not payment_method_id:
                        error_message += (
                            "Payment method '%s' not found, on row %s \n"
                            % (
                                payment_method,
                                row,
                            )
                        )

                    tax_support_id = self.env["account.ats.support"].search(
                        [
                            ("type_support", "=", tax_support),
                        ]
                    )
                    if not tax_support_id:
                        error_message += "Tax support '%s' not found, on row %s \n" % (
                            tax_support,
                            row,
                        )

                    doc_type_id = self.env["account.voucher.type"].search(
                        [
                            ("name", "=", doc_type),
                        ]
                    )
                    if not doc_type_id:
                        error_message += (
                            "Document type '%s' not found, on row %s \n"
                            % (
                                doc_type,
                                row,
                            )
                        )

                    if self.move_type == "out_invoice":
                        sales_partner_id = self.env["res.partner"].search(
                            [("name", "=", sales_partner)]
                        )
                        if not sales_partner_id:
                            error_message += "Vendor '%s' not found, on row %s \n" % (
                                sales_partner,
                                row,
                            )

                if self.search_product == "name":
                    product_id = self.env["product.product"].search(
                        [("name", "=", product)]
                    )
                else:
                    product_id = self.env["product.product"].search(
                        [("default_code", "=", product)]
                    )

                if not product_id:
                    error_message += "Product '%s' not found, on row %s \n" % (
                        product,
                        row,
                    )

                if account:
                    account_id = self.env["account.account"].search(
                        [
                            ("code", "=", account),
                            ("company_id", "=", self.env.company.id),
                        ]
                    )
                    if not account_id:
                        error_message += "Account '%s' not found, on row %s \n" % (
                            account,
                            row,
                        )

                if error_message:
                    raise ValidationError(error_message)

                if partner_name and invoice_lines and row > 2:
                    invoice["invoice_line_ids"] = invoice_lines
                    invoices.append(invoice)
                    invoice = {}
                    invoice_lines = []

                if partner_name:
                    invoice = {
                        "name": name,
                        "move_type": self.move_type,
                        "journal_id": self.journal_id.id,
                        "partner_id": partner_id.id,
                        "invoice_date": date,
                        "invoice_date_due": end_date,
                        "epayment_id": payment_method_id.id,
                        "tax_support_id": tax_support_id.id,
                        "voucher_type_ats": doc_type_id.id,
                        "is_imported": True,
                    }

                    if self.move_type == "in_invoice":
                        invoice["support_document"] = support_document

                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product_id.id,
                            "quantity": float(quantity),
                            "price_unit": float(price),
                        },
                    )
                )

                if label:
                    invoice_lines[len(invoice_lines) - 1][2]["name"] = str(label)

                if account:
                    invoice_lines[len(invoice_lines) - 1][2][
                        "account_id"
                    ] = account_id.id

            if invoice and invoice_lines:
                invoice["invoice_line_ids"] = invoice_lines
                invoices.append(invoice)
                invoice = {}
                invoice_lines = []

            res = self.env["account.move"].create(invoices)

            if self.invoice_state == "posted":
                for record in res:
                    record.post()

            return self.env.user.notify_success("Importado con exito")

    def action_test(self):
        if self.xlsx_file:
            # Decode the binary data and read the XLSX file using xlrd
            try:
                data = base64.b64decode(self.xlsx_file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(
                    0
                )  # Assuming data is in the first sheet
            except xlrd.biffh.XLRDError as e:
                raise UserError(_("Unsupported format or currupt file"))

            error_message = ""

            # Process the XLSX data and create the invoice
            # Skip header row, start from 2nd row
            for row_index in range(1, sheet.nrows):
                row = row_index + 1

                name = sheet.cell_value(row_index, 0)
                partner_name = sheet.cell_value(row_index, 2)
                date_string = sheet.cell_value(row_index, 3)
                end_date_string = sheet.cell_value(row_index, 4)
                payment_method = sheet.cell_value(row_index, 5)
                tax_support = sheet.cell_value(row_index, 6)
                doc_type = sheet.cell_value(row_index, 7)
                sales_partner = sheet.cell_value(row_index, 8)
                product = sheet.cell_value(row_index, 9)
                account = sheet.cell_value(row_index, 11)
                quantity = sheet.cell_value(row_index, 12)
                price = sheet.cell_value(row_index, 13)

                if name:
                    name_id = self.env["account.move"].search([("name", "=", name)])
                    if name_id:
                        error_message += "Invoice '%s' already exists, on row %s \n" % (
                            name,
                            row,
                        )

                if partner_name:
                    partner_id = self.env["res.partner"].search(
                        [("name", "=", partner_name)]
                    )

                    if not partner_id:
                        error_message += "Partner '%s' not found, on row %s \n" % (
                            partner_name,
                            row,
                        )
                    try:
                        date = self.parse_date(date_string, date_format="%m/%d/%y")
                    except ValueError:
                        error_message += (
                            "Date string '%s' does not match the expected format, on row %s \n"
                            % (date_string, row)
                        )

                    try:
                        end_date = self.parse_date(
                            end_date_string, date_format="%m/%d/%y"
                        )
                    except ValueError:
                        error_message += (
                            "Date string '%s' does not match the expected format, on row %s \n"
                            % (end_date_string, row)
                        )

                    payment_method_id = self.env["account.sri.charts"].search(
                        [
                            ("name", "=", payment_method),
                        ]
                    )
                    if not payment_method_id:
                        error_message += (
                            "Payment method '%s' not found, on row %s \n"
                            % (
                                payment_method,
                                row,
                            )
                        )

                    tax_support_id = self.env["account.ats.support"].search(
                        [
                            ("type_support", "=", tax_support),
                        ]
                    )
                    if not tax_support_id:
                        error_message += "Tax support '%s' not found, on row %s \n" % (
                            tax_support,
                            row,
                        )

                    doc_type_id = self.env["account.voucher.type"].search(
                        [
                            ("name", "=", doc_type),
                        ]
                    )
                    if not doc_type_id:
                        error_message += (
                            "Document type '%s' not found, on row %s \n"
                            % (
                                doc_type,
                                row,
                            )
                        )

                    if self.move_type == "out_invoice":
                        sales_partner_id = self.env["res.partner"].search(
                            [("name", "=", sales_partner)]
                        )
                        if not sales_partner_id:
                            error_message += "Vendor '%s' not found, on row %s \n" % (
                                sales_partner,
                                row,
                            )

                if self.search_product == "name":
                    product_id = self.env["product.product"].search(
                        [("name", "=", product)]
                    )
                else:
                    product_id = self.env["product.product"].search(
                        [("default_code", "=", product)]
                    )

                if not product_id:
                    error_message += "Product '%s' not found, on row %s \n" % (
                        product,
                        row,
                    )

                if account:
                    account_id = self.env["account.account"].search(
                        [
                            ("code", "=", account),
                            ("company_id", "=", self.env.company.id),
                        ]
                    )
                    if not account_id:
                        error_message += "Account '%s' not found, on row %s \n" % (
                            account,
                            row,
                        )

                try:
                    float(quantity)
                except ValueError:
                    error_message += (
                        "Quantity '%s' must be an integer, on row %s \n"
                        % (
                            quantity,
                            row,
                        )
                    )

                try:
                    float(price)
                except ValueError:
                    error_message += "Price '%s' must be an integer, on row %s \n" % (
                        price,
                        row,
                    )

            if error_message:
                raise ValidationError(error_message)
            else:
                return self.env.user.notify_success("Todo parece correcto")
