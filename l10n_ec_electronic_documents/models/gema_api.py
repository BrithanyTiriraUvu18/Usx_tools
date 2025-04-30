import json
import logging
import re
import traceback
from datetime import datetime

from odoo import _, models
from odoo.exceptions import UserError

from .Gema import GemaApi

_logger = logging.getLogger(__name__)


class CustomAccountMove(models.Model):
    _name = "account.move"
    _description = "New account move model with electronic documents"
    _inherit = ["account.move", "account.edocument"]

    STATUS_AUTHORIZED = "AUTORIZADO"
    STATUS_RETURNED = "DEVUELTA"
    MSG_KEY_REGISTERED = "CLAVE ACCESO REGISTRADA"
    MSG_ERROR_TOKEN = "Error Token inautorizado"
    MSG_SENT_SRI = "Enviado al SRI"
    MSG_ERROR_DATA_BUILD = "Error in data build"
    status_dict = {
        "DEVUELTA": "returned",
        "AUTORIZADO": "authorized",
        "NO AUTORIZADO": "returned",
    }
    _doc_type = {
        "out_invoice": "Factura",
        "out_refund": "Nota de crédito",
        "liq_purchase": "Liquidación",
    }

    def check_errors(self, gema_response):
        status_code = gema_response.get("statusCode", False)
        if status_code == 200:
            return
        if status_code == 400:
            data = gema_response.get("data")
            error_msg = gema_response.get("message")
            status = data.get("status")
            self.state_send_document = self.status_dict[status]
            error = (
                error_msg
                + " "
                + (
                    json.dumps(data.get("details"), ensure_ascii=False)
                    if data.get("details")
                    else ""
                )
            )
            self.info_message = error_msg.capitalize()
            self.auth_document = error
            self.state_document = "request_rejected"
            self.unauthorized_bool = False
            raise Exception(error)
        if status_code == 503:
            raise Exception(
                "Servicio del SRI no disponible, vuelva a intentarlo más tarde"
            )
        else:
            raise Exception(
                "Servicio del SRI retornó una respuesta desconocida."
                "Vuelva a intentarlo más tarde"
            )

    def _get_attachments(self):
        if self.ride:
            document = self._doc_type.get(self.doc_type, "Documento")
            if not self.pdf_ride_attachment:
                self.pdf_ride_attachment = self.env["ir.attachment"].create(
                    {
                        "name": document + " - " + self.name + ".pdf",
                        "datas": self.ride,
                        "res_model": "account.move",
                        "res_id": self.id,
                        "type": "binary",
                    }
                )
            if not self.xml_ride_attachment:
                self.xml_ride_attachment = self.env["ir.attachment"].create(
                    {
                        "name": self.xml_name,
                        "datas": self.xml_ride,
                        "res_model": "account.move",
                        "res_id": self.id,
                        "type": "binary",
                    }
                )
            attachments = [self.pdf_ride_attachment.id, self.xml_ride_attachment.id]
            return self.env["ir.attachment"].browse(attachments)

    def process_document(self):
        if not self.company_id.conect_gema:
            self.info_message = "API Gema está desactivada."
            self.auth_document = "API Gema está desactivada."
            raise UserError(self.info_message)

        for record in self:
            record.auth_document = ""
            record.info_message = ""
            payload = self.render_data(record)
            self._check_invoice(2)
            if payload:
                try:
                    if self.company_id.conect_gema:
                        self.attempts += 1
                        user = self.company_id.gema_user
                        password = self.company_id.gema_password
                        token = GemaApi().get_token(user, password)
                        if not token:
                            raise Exception(self.MSG_ERROR_TOKEN)
                        else:
                            document_sri = GemaApi().send_sri(self, token, payload)
                        self.check_errors(document_sri)
                        data = document_sri.get("data")
                        key_access = data.get("accessKey")
                        authDate = data.get("authDate")
                        status = data.get("status")
                        message = document_sri.get("message")
                        xml = data.get("xml")
                        self.access_key_label = key_access
                        if status == self.STATUS_AUTHORIZED:
                            self._check_invoice(3)
                            self.state_document = "edocument_correct"
                            date_authorized = datetime.strptime(
                                authDate, "%Y-%m-%dT%H:%M:%S%z"
                            )
                            formatted_date = date_authorized.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            self.date_authorized = formatted_date
                            self.state_send_document = "authorized"
                            self.unauthorized_bool = False
                            ride = GemaApi().get_ride(self, xml, token)
                            self.xml_ride = xml
                            self.xml_name = key_access + ".xml"
                            self.ride = ride
                            self.ride_name = key_access + ".pdf"
                            self._get_attachments()
                            self.auth_document = ""
                            return self.env.user.notify_success(
                                message=(self.MSG_SENT_SRI)
                            )

                        elif status == self.STATUS_RETURNED:
                            if message == self.MSG_KEY_REGISTERED:
                                self.state_document = "edocument_correct"
                                xml = GemaApi().get_xml_base64(self, key_access, token)
                                ride = GemaApi().get_ride(self, xml, token)
                                self.xml_ride = xml
                                self.xml_name = key_access + ".xml"
                                self.ride = ride
                                self.ride_name = key_access + ".pdf"
                                self._get_attachments()
                                self.state_send_document = "authorized"
                                self.unauthorized_bool = False
                                self._check_invoice(4)
                                return self.env.user.notify_success(
                                    message=(self.MSG_SENT_SRI)
                                )
                            else:
                                self.state_document = "request_rejected"
                                self.state_send_document = "returned"
                                self.unauthorized_bool = True
                                self.info_message = message
                                self.auth_document = message
                                raise Exception("No se pudo Enviar al SRI")

                except Exception as e:
                    record.info_message = str(e)
                    record.auth_document = str(e)
                    raise e
            else:
                self.info_message += self.MSG_ERROR_DATA_BUILD
                raise Exception(self.info_message)

    def send_electronic_document(self):
        try:
            return self.process_document()
        except Exception as e:
            _logger.error(str(e))
            traceback.print_exc()
            return self.env.user.notify_danger(
                f"Error al autorizar el documento: {self.name}"
            )

    def render_data(self, invoice):
        try:
            # Nota de Debito
            if invoice.journal_id.name == "Nota de Débito":
                debit_tax_info = self._get_debit_tax_info(invoice)
                debit_info = self._get_debit_info(invoice)
                motivos = self._get_motivos(invoice)
                additional_info = self._get_additional_info(invoice)

                data = {
                    "id": "comprobante",
                    "version": "1.0.0",
                    "infoTributaria": debit_tax_info,
                }
                data.update({"infoNotaDebito": debit_info})

                data.update(
                    {
                        "motivos": motivos,
                        "infoAdicional": {"campoAdicional": additional_info},
                    }
                )
            # Factura
            elif invoice.move_type == "out_invoice":
                tax_info = self._get_tax_info_factura(invoice)
                invoice_info = self._get_info(invoice)
                details = self._get_details(invoice)
                additional_info = self._get_additional_info(invoice)

                data = {
                    "id": "comprobante",
                    "version": "2.1.0",
                    "infoTributaria": tax_info,
                }
                data.update({"infoFactura": invoice_info})
                data["infoFactura"].update(self._compute_discount({"detalle": details}))
                data.update(
                    {
                        "detalles": {"detalle": details},
                        "infoAdicional": {"campoAdicional": additional_info},
                    }
                )
            # Nota de Credito
            elif invoice.move_type == "out_refund":
                credit = self._get_credit_info(invoice)
                credit_info = self._get_info_note_credit(invoice)
                details = self._get_details(invoice)
                additional_info = self._get_additional_info(invoice)

                data = {
                    "id": "comprobante",
                    "version": "1.1.0",
                    "infoTributaria": credit,
                }
                data.update({"infoNotaCredito": credit_info})
                data.update(
                    {
                        "detalles": {"detalle": details},
                        "infoAdicional": {"campoAdicional": additional_info},
                    }
                )
            # Liquidacion
            elif invoice.doc_type == "liq_purchase":
                liquid = self._get_info_liquid(invoice)
                lquid_info = self._get_liquid_info(invoice)
                details = self._get_details(invoice)
                additional_info = self._get_additional_info(invoice)

                data = {
                    "id": "comprobante",
                    "version": "1.0.0",
                    "infoTributaria": liquid,
                }
                data.update({"infoLiquidacionCompra": lquid_info})
                if invoice.sustento == 41:
                    refund = self._get_refund_info(invoice)
                    data.update(
                        {
                            "detalles": {"detalle": details},
                            "reembolsos": refund,
                            "infoAdicional": {"campoAdicional": additional_info},
                        }
                    )
                    if data["reembolsos"] is None:
                        del data["reembolsos"]
                else:
                    data.update(
                        {
                            "detalles": {"detalle": details},
                            "infoAdicional": {"campoAdicional": additional_info},
                        }
                    )
            return data
        except Exception as e:
            invoice.info_message = str(e)
            invoice.auth_document = str(e)
            raise e

    # Factura
    def _get_tax_info_factura(self, document):
        """"""
        types_docs = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "document_type")])
        )
        type_doc = types_docs.filtered(lambda t: t.value == self.move_type).code
        company = document.company_id
        sequential = self.get_sequential()
        tax_info = {
            "ambiente": self.env.user.company_id.env_service,
            "tipoEmision": "1",
            "razonSocial": company.name,
            "nombreComercial": (
                self.fix_chars(company.partner_id.trade_name.strip())
                if company.partner_id.trade_name
                else company.name
            ),
            "ruc": company.partner_id.identifier,
            "codDoc": type_doc,
            "estab": self._get_num_estab_ruc(),
            "ptoEmi": self._get_emission_series(),
            "secuencial": sequential,
            "dirMatriz": company.street,
        }
        return tax_info

    def _get_invoice_taxes(self, invoice):
        total_with_taxes = []
        for tax in invoice.invoice_line_ids.mapped("tax_ids"):
            base_imponible = 0.0
            valor_impuesto = 0.0

            # Verificar si el impuesto es fijo
            if tax.amount_type == "fixed":
                for line in invoice.invoice_line_ids:
                    if tax in line.tax_ids:
                        # Agregar el valor fijo para cada línea que tenga este impuesto
                        base_imponible += line.price_subtotal
                        valor_impuesto += (
                            line.quantity * tax.amount
                        )  # Valor fijo directamente
            else:  # Si no es fijo, asumir que es porcentual
                for line in invoice.invoice_line_ids:
                    if tax in line.tax_ids:
                        # Base imponible de la línea
                        base_imponible += line.price_subtotal
                        # Valor del impuesto para esa línea
                        valor_impuesto += line.price_subtotal * (tax.amount / 100)

            total_taxes = {
                "codigo": tax.tax_group_id.tax_code.code,
                "codigoPorcentaje": tax.code_edocument,
                "baseImponible": "{:.2f}".format(base_imponible),
                "valor": "{:.2f}".format(valor_impuesto),
            }
            total_with_taxes.append(total_taxes)
        if not total_with_taxes:
            raise UserError(_("No se ha asignado correctamente los impuestos"))
        return total_with_taxes

    def _get_info(self, invoice):
        """"""
        payment_form = invoice.epayment_id.code
        company = invoice.company_id
        partner = invoice.partner_id
        date_invoice = invoice.invoice_date.strftime("%d/%m/%Y")
        ids_type = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "identification_type")])
        )
        id_type = ids_type.filtered(
            lambda line: line.value == partner.type_identifier
        ).code
        pay = payment_form
        direccionComprador = (
            partner.street
            + (" / " + partner.city if partner.city else "")
            + (
                " / " + partner.state_id.display_name
                if partner.state_id.display_name
                else ""
            )
        )
        branch_address = company.street
        if "journal_id" in self.env["stock.warehouse"]._fields:
            warehouse = self.env["stock.warehouse"].search(
                [("journal_id", "=", invoice.journal_id.id)]
            )
            if warehouse:
                branch_address = warehouse.partner_id.street
                if not branch_address:
                    raise UserError(_("No está configurada la dirección en el almacén"))
        if invoice.move_type == "out_invoice":
            shipping = self.partner_shipping_id
            if (
                "delivery_address" in self.env["account.move"]._fields
                and invoice.delivery_address
            ):
                direccionComprador += " entrega: " + invoice.delivery_address
            elif shipping.street:
                direccionComprador += " entrega: " + shipping.street
            invoice_info = {
                "fechaEmision": date_invoice,
                "dirEstablecimiento": branch_address,
                "contribuyenteEspecial": (
                    company.company_registry if company.company_registry else None
                ),
                "obligadoContabilidad": company.required_accounting,
                "tipoIdentificacionComprador": id_type,
                "razonSocialComprador": partner.name,
                "identificacionComprador": partner.identifier,
                "direccionComprador": direccionComprador,
                "totalSinImpuestos": "%.2f" % invoice.amount_untaxed,
                "totalDescuento": "0.00",
            }

        if invoice_info["contribuyenteEspecial"] is None:
            del invoice_info["contribuyenteEspecial"]
        total_with_taxes = self._get_invoice_taxes(invoice)
        invoice_info.update({"totalConImpuestos": {"totalImpuesto": total_with_taxes}})
        invoice_info.update(
            {
                "propina": "0.00",
                "importeTotal": "{:.2f}".format(invoice.amount_total),
                "moneda": "DOLAR",
            }
        )

        payments = []

        pay = payment_form
        payment = {
            "formaPago": pay,
            "total": round(invoice.amount_total, 2),
            "plazo": sum([x.nb_days for x in invoice.invoice_payment_term_id.line_ids]),
            "unidadTiempo": "dias",
        }
        if company.ride_disable_payment_timeout_param:
            payment["plazo"] = 30 if payment["plazo"] > 0 else payment["plazo"]
        payments.append(payment)

        if invoice.move_type != "out_refund":
            invoice_info.update({"pagos": {"pago": payments}})

        return invoice_info

    def _get_details(self, invoice):
        """"""

        def fix_chars(code):
            special = [["%", " "], ["º", " "], ["Ñ", "N"], ["ñ", "n"], ["\n", " "]]
            for f, r in special:
                code = code.replace(f, r)
            return code

        details = []
        for line in invoice.invoice_line_ids:
            main_code = (
                line.product_id
                and line.product_id.default_code
                and fix_chars(line.product_id.default_code)
                or "001"
            )
            description = (
                line.product_id
                and line.product_id.name
                and fix_chars(line.product_id.name)
                or fix_chars(line.name.strip())
            )
            discount = 0
            if line.discount_fixed != 0:
                discount = line.discount_fixed * line.quantity

            if line.discount != 0:
                discount = (line.price_unit * line.discount / 100) * line.quantity

            # Nota de Credito
            if invoice.move_type == "out_refund":
                detail = {
                    "codigoInterno": main_code,
                    "descripcion": description,
                    "cantidad": "%.2f" % (line.quantity),
                    "precioUnitario": "%.4f" % (line.price_unit),
                    "descuento": "%.2f" % discount,
                    "precioTotalSinImpuesto": "%.2f" % (line.price_subtotal),
                }
            # Factura
            else:
                detail = {
                    "codigoPrincipal": main_code,
                    "codigoAuxiliar": main_code,
                    "descripcion": description,
                    "cantidad": "%.2f" % (line.quantity),
                    "precioUnitario": "%.4f" % (line.price_unit),
                    "descuento": "%.2f" % discount,
                    "precioTotalSinImpuesto": "%.2f" % (line.price_subtotal),
                }

            taxes = []

            if line.tax_ids:
                for tax_line in line.tax_ids:
                    if tax_line.amount_type == "fixed":
                        # Si el impuesto es fijo
                        tax = {
                            "codigo": tax_line.tax_group_id.tax_code.code,
                            "codigoPorcentaje": tax_line.code_edocument,
                            "tarifa": "{:.2f}".format(tax_line.amount),
                            "baseImponible": "{:.2f}".format(line.price_subtotal),
                            "valor": "{:.2f}".format(
                                line.quantity * tax_line.amount
                            ),  # Valor fijo
                        }
                    else:
                        # Si el impuesto no es fijo (asumimos que es porcentual)
                        tax = {
                            "codigo": tax_line.tax_group_id.tax_code.code,
                            "codigoPorcentaje": tax_line.code_edocument,
                            "tarifa": "{:.0f}".format(tax_line.amount),
                            "baseImponible": "{:.2f}".format(line.price_subtotal),
                            "valor": "{:.2f}".format(
                                line.price_subtotal * (tax_line.amount / 100)
                            ),
                        }
                    taxes.append(tax)
            else:
                # Sin impuestos aplicables
                amount = 0.0
                tax = {
                    "codigo": "2",
                    "codigoPorcentaje": "0",
                    "tarifa": "{:.0f}".format(amount),
                    "baseImponible": "{:.2f}".format(line.price_subtotal),
                    "valor": "{:.2f}".format(line.price_subtotal * (amount / 100)),
                }
                taxes.append(tax)
            detail.update({"impuestos": {"impuesto": taxes}})
            details.append(detail)
        return details

    def _calculate_tax(self, tax_line, line, amount):
        tax = {
            "codigo": tax_line.tax_group_id.tax_code.code,
            "codigoPorcentaje": tax_line.code_edocument,
            "tarifa": "{:.0f}".format(amount),
            "baseImponible": "{:.2f}".format(line),
            "valor": "{:.2f}".format(line * (amount / 100)),
        }
        return tax

    def _get_additional_info(self, invoice):
        info_lines = []
        info_lines.append({"nombre": "Emitido por", "valor": "FenixERP"})
        for info_line in invoice.lines_info_additional:
            info = {"nombre": info_line.name, "valor": info_line.description}
            info_lines.append(info)

        return info_lines

    def _compute_discount(self, details):
        total = sum([float(det["descuento"]) for det in details["detalle"]])
        total_rounded = round(total, 2)

        return {"totalDescuento": total_rounded}

    # Nota de Credito
    def _get_credit_info(self, document):
        """"""
        types_docs = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "document_type")])
        )
        type_doc = types_docs.filtered(lambda t: t.value == self.move_type).code
        company = document.company_id
        sequential = self.get_sequential()
        credit_info = {
            "ambiente": self.env.user.company_id.env_service,
            "tipoEmision": "1",
            "razonSocial": company.name,
            "nombreComercial": (
                self.fix_chars(company.partner_id.trade_name.strip())
                if company.partner_id.trade_name
                else company.name
            ),
            "ruc": company.partner_id.identifier,
            "codDoc": type_doc,
            "estab": self._get_num_estab_ruc(),
            "ptoEmi": self._get_emission_series(),
            "secuencial": sequential,
            "dirMatriz": company.street,
            # "agenteRetencion": "0",
        }
        return credit_info

    def _get_info_note_credit(self, invoice):
        company = invoice.company_id
        partner = invoice.partner_id
        date_invoice = invoice.invoice_date.strftime("%d/%m/%Y")
        ids_type = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "identification_type")])
        )

        if partner.is_end_consumer:
            id_type = ids_type.filtered(
                lambda line: line.value == "final_consumer_sale"
            ).code
        else:
            id_type = ids_type.filtered(
                lambda line: line.value == partner.type_identifier
            ).code
        branch_address = company.street
        if "journal_id" in self.env["stock.warehouse"]._fields:
            warehouse = self.env["stock.warehouse"].search(
                [("journal_id", "=", invoice.journal_id.id)]
            )
            if warehouse:
                branch_address = warehouse.partner_id.street
                if not branch_address:
                    raise UserError(_("No está configurada la dirección en el almacén"))
        invoice_info = {
            "fechaEmision": date_invoice,
            "dirEstablecimiento": branch_address,
            "tipoIdentificacionComprador": id_type,
            "razonSocialComprador": partner.name,
            "identificacionComprador": partner.identifier,
            "contribuyenteEspecial": (
                company.company_registry if company.company_registry else None
            ),
            "obligadoContabilidad": company.required_accounting,
            # # "formaPago": pay,
            # "valorRetIva": amount_vat,
            # "valorRetRenta": amount_ir,
        }
        if invoice_info["contribuyenteEspecial"] is None:
            del invoice_info["contribuyenteEspecial"]

        inv = invoice.reversed_entry_id
        date_doc_sustento = invoice.reversed_entry_id.date.strftime("%d/%m/%Y")
        if inv:
            inv_number = "{}-{}-{}".format(
                inv._get_num_estab_ruc(),
                inv._get_emission_series(),
                inv.get_sequential(),
            )
            types_documents = (
                self.env["account.sri.charts"]
                .sudo()
                .search([("type", "=", "document_type")])
            )
            document_type = types_documents.filtered(
                lambda line: line.value == inv.move_type
            ).code
            credit_note = {
                "codDocModificado": document_type,
                "numDocModificado": inv_number,
                "fechaEmisionDocSustento": date_doc_sustento,
                "totalSinImpuestos": "%.2f" % invoice.amount_untaxed,
                "valorModificacion": "{:.2f}".format(invoice.amount_total),
                "moneda": "DOLAR",
            }
            invoice_info.update(credit_note)

        total_with_taxes = []

        # Acumulamos las bases imponibles y los valores de impuestos
        tax_totals = {}

        # Recorremos las líneas de la factura
        for line in invoice.invoice_line_ids:
            # Recorremos los impuestos asociados a cada línea
            for tax in line.tax_ids:
                # Si el impuesto aún no está en el diccionario, lo inicializamos
                if tax.id not in tax_totals:
                    tax_totals[tax.id] = {
                        "codigo": tax.tax_group_id.tax_code.code,
                        "codigoPorcentaje": tax.code_edocument,
                        "baseImponible": 0.0,
                        "valor": 0.0,
                    }
                # Acumulamos la base imponible y el valor del impuesto
                tax_totals[tax.id]["baseImponible"] += line.price_subtotal
                tax_value = (
                    line.quantity * tax.amount
                    if tax.amount_type == "fixed"
                    else line.price_subtotal * (tax.amount / 100)
                )
                tax_totals[tax.id]["valor"] += tax_value

        # Convertimos los valores acumulados y los agregamos a total_with_taxes
        for tax_data in tax_totals.values():
            total_taxes = {
                "codigo": tax_data["codigo"],
                "codigoPorcentaje": tax_data["codigoPorcentaje"],
                "baseImponible": "{:.2f}".format(tax_data["baseImponible"]),
                "valor": "{:.2f}".format(tax_data["valor"]),
            }
            # Agregamos cada impuesto calculado a la lista final
            total_with_taxes.append(total_taxes)
        if not total_with_taxes:
            raise UserError(_("No se ha asignado correctamente los impuestos"))
        invoice_info.update({"totalConImpuestos": {"totalImpuesto": total_with_taxes}})
        invoice_info.update(
            {
                "motivo": invoice.reason,
            }
        )
        return invoice_info

    # Liquidacion
    def _get_liquid_info(self, document):
        payment_form = document.epayment_id.code
        company = document.company_id
        partner = document.partner_id
        date_invoice = document.invoice_date.strftime("%d/%m/%Y")
        ids_type = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "identification_type")])
        )

        if partner.is_end_consumer:
            id_type = ids_type.filtered(
                lambda line: line.value == "final_consumer_sale"
            ).code
        else:
            id_type = ids_type.filtered(
                lambda line: line.value == partner.type_identifier
            ).code

        pay = payment_form
        branch_address = company.street
        if "journal_id" in self.env["stock.warehouse"]._fields:
            warehouse = self.env["stock.warehouse"].search(
                [("journal_id", "=", document.journal_id.id)]
            )
            if warehouse:
                branch_address = warehouse.partner_id.street
                if not branch_address:
                    raise UserError(_("No está configurada la dirección en el almacén"))
        invoice_info = {
            "fechaEmision": date_invoice,
            "dirEstablecimiento": branch_address,
            "contribuyenteEspecial": (
                company.company_registry if company.company_registry else None
            ),
            "obligadoContabilidad": company.required_accounting,
            "tipoIdentificacionProveedor": id_type,
            "razonSocialProveedor": partner.name,
            "identificacionProveedor": partner.identifier,
            "direccionProveedor": partner.street,
            "totalSinImpuestos": "%.2f" % document.amount_untaxed,
            "totalDescuento": "0.00",
            # # "formaPago": pay,
            # "valorRetIva": amount_vat,
            # "valorRetRenta": amount_ir,
        }
        if invoice_info["contribuyenteEspecial"] is None:
            del invoice_info["contribuyenteEspecial"]

        total_with_taxes = []
        for line in document.invoice_line_ids:
            for tax in line.tax_ids:
                total_taxes = {
                    "codigo": tax.tax_group_id.tax_code.code,
                    "codigoPorcentaje": tax.code_edocument,
                    "baseImponible": "{:.2f}".format(line.amount_currency),
                    "valor": "{:.2f}".format(line.amount_currency * (tax.amount / 100)),
                }
                total_with_taxes.append(total_taxes)
        if not total_with_taxes:
            raise UserError(_("No se ha asignado correctamente los impuestos"))
        invoice_info.update({"totalConImpuestos": {"totalImpuesto": total_with_taxes}})

        if document.doc_type == "liq_purchase":
            invoice_info.update(
                {
                    "importeTotal": "{:.2f}".format(document.amount_total),
                    "moneda": "DOLAR",
                }
            )

        payments = []

        pay = payment_form
        payment = {
            "formaPago": pay,
            "total": round(document.amount_total, 2),
            "plazo": sum([x.days for x in document.invoice_payment_term_id.line_ids]),
            "unidadTiempo": "dias",
        }
        if company.ride_disable_payment_timeout_param:
            payment["plazo"] = 30 if payment["plazo"] > 0 else payment["plazo"]
        payments.append(payment)

        invoice_info.update({"pagos": {"pago": payments}})

        return invoice_info

    def _get_info_liquid(self, document):
        """"""
        company = document.company_id
        sequential = self.get_sequential()
        tax_info = {
            "ambiente": self.env.user.company_id.env_service,
            "tipoEmision": "1",
            "razonSocial": company.name,
            "nombreComercial": (
                self.fix_chars(company.partner_id.trade_name.strip())
                if company.partner_id.trade_name
                else company.name
            ),
            "ruc": company.partner_id.identifier,
            "codDoc": "03",
            "estab": self._get_num_estab_ruc(),
            "ptoEmi": self._get_emission_series(),
            "secuencial": sequential,
            "dirMatriz": company.street,
        }
        return tax_info

    def _get_refund_info(self, document):
        liquid_ids = document.liquid_ids

        ids_type = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "identification_type")])
        )

        id_type = ids_type.filtered(
            lambda line: line.value == "final_consumer_sale"
        ).code

        invoice_info = {"reembolsoDetalle": []}  # Inicializar como una lista

        for liquid_info in liquid_ids:
            sequential = self.get_sequential()
            date_invoice = liquid_info.fecha_emision.strftime("%d/%m/%Y")
            estabDoc = re.match(r"(\d{3})", liquid_info.nmro)
            primer_valor = estabDoc.group(1)
            country_chart = self.env["account.sri.charts"].search(
                [("type", "=", "country_sri"), ("code", "=", liquid_info.pais.code)],
                limit=1,
            )
            refund_info = {
                "tipoIdentificacionProveedorReembolso": id_type,
                "identificacionProveedorReembolso": liquid_info.ruc,
                "codPaisPagoProveedorReembolso": (
                    country_chart.value if country_chart else ""
                ),
                "tipoProveedorReembolso": "01",
                "codDocReembolso": "41",
                "estabDocReembolso": primer_valor,
                "ptoEmiDocReembolso": self._get_emission_series(),
                "secuencialDocReembolso": sequential,
                "fechaEmisionDocReembolso": date_invoice,
                "numeroautorizacionDocReemb": liquid_info.nro_autorizacion,
            }

            if liquid_info.valor_iva == 12:
                code = 2
            elif liquid_info.valor_iva == 0:
                code = 0
            elif liquid_info.valor_iva == 14:
                code = 3
            elif liquid_info.valor_iva == 15:
                code = 4

            tax_refund = {
                "codigo": 2,
                "codigoPorcentaje": code,
                "tarifa": liquid_info.valor_iva,
                "baseImponibleReembolso": liquid_info.valor,
                "impuestoReembolso": liquid_info.valor * liquid_info.valor_iva / 100,
            }
            refund_info["detalleImpuestos"] = {"detalleImpuesto": tax_refund}
            invoice_info["reembolsoDetalle"].append(refund_info)
        if len(invoice_info["reembolsoDetalle"]) < 1:
            return None
        return {"reembolsoDetalle": invoice_info["reembolsoDetalle"]}

    # Nota de Debito
    def _get_debit_tax_info(self, document):
        """"""
        company = document.company_id
        sequential = self.get_sequential()
        tax_info = {
            "ambiente": self.env.user.company_id.env_service,
            "tipoEmision": "1",
            "razonSocial": company.name,
            "nombreComercial": (
                self.fix_chars(company.partner_id.trade_name.strip())
                if company.partner_id.trade_name
                else company.name
            ),
            "ruc": company.partner_id.identifier,
            "codDoc": "05",
            "estab": self._get_num_estab_ruc(),
            "ptoEmi": self._get_emission_series(),
            "secuencial": sequential,
            "dirMatriz": company.street,
            # "agenteRetencion": "1",
        }
        return tax_info

    def _get_debit_info(self, invoice):
        """"""
        payment_form = invoice.epayment_id.code
        company = invoice.company_id
        partner = invoice.partner_id
        date_invoice = invoice.invoice_date.strftime("%d/%m/%Y")
        ids_type = (
            self.env["account.sri.charts"]
            .sudo()
            .search([("type", "=", "identification_type")])
        )

        if partner.is_end_consumer:
            id_type = ids_type.filtered(
                lambda line: line.value == "final_consumer_sale"
            ).code
        else:
            id_type = ids_type.filtered(
                lambda line: line.value == partner.type_identifier
            ).code

        pay = payment_form
        branch_address = company.street
        if "journal_id" in self.env["stock.warehouse"]._fields:
            warehouse = self.env["stock.warehouse"].search(
                [("journal_id", "=", invoice.journal_id.id)]
            )
            if warehouse:
                branch_address = warehouse.partner_id.street
                if not branch_address:
                    raise UserError(_("No está configurada la dirección en el almacén"))
        invoice_info = {
            "fechaEmision": date_invoice,
            "dirEstablecimiento": branch_address,
            "tipoIdentificacionComprador": id_type,
            "razonSocialComprador": partner.name,
            "identificacionComprador": partner.identifier,
            "obligadoContabilidad": company.required_accounting,
            "rise": "rise0",
        }

        credit_note = {
            "codDocModificado": "05",
            "numDocModificado": invoice.name,
            "fechaEmisionDocSustento": date_invoice,
            "totalSinImpuestos": "%.2f" % invoice.amount_untaxed,
        }
        invoice_info.update(credit_note)

        total_with_taxes = []
        for tax in invoice.invoice_line_ids.tax_ids:
            total_taxes = {
                "codigo": tax.tax_group_id.tax_code.code,
                "codigoPorcentaje": tax.code_edocument,
                "tarifa": "{:.0f}".format(tax.amount),
                "baseImponible": "{:.2f}".format(invoice.amount_untaxed),
                "valor": "{:.2f}".format(invoice.amount_tax),
                "valorDevolucionIva": "{:.2f}".format(invoice.amount_tax),
            }
            total_with_taxes.append(total_taxes)

        invoice_info.update({"impuestos": {"impuesto": total_with_taxes}})

        invoice_info.update(
            {
                "valorTotal": "{:.2f}".format(invoice.amount_total),
            }
        )
        payments = []

        pay = payment_form
        payment = {
            "formaPago": pay,
            "total": round(invoice.amount_total, 2),
            "plazo": sum([x.days for x in invoice.invoice_payment_term_id.line_ids]),
            "unidadTiempo": "dias",
        }
        if company.ride_disable_payment_timeout_param:
            payment["plazo"] = 30 if payment["plazo"] > 0 else payment["plazo"]
        payments.append(payment)

        if invoice.move_type != "out_refund":
            invoice_info.update({"pagos": {"pago": payments}})

        return invoice_info

    def _get_motivos(self, invoice):
        total_with_taxes = []
        for line in invoice.invoice_line_ids:
            total_taxes = {
                "razon": line.name,
                "valor": line.price_subtotal,
            }
            total_with_taxes.append(total_taxes)

        invoice_info = {"motivo": total_with_taxes}

        return invoice_info
