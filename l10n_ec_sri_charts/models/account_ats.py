import base64
import os
from io import StringIO
from itertools import groupby
from operator import itemgetter

from jinja2 import Environment, FileSystemLoader
from lxml import etree
from lxml.etree import DocumentInvalid

from odoo import fields, models

tpIdProv = {"ruc": "01", "cedula": "02", "pasaporte": "03"}

tpIdCliente = {"ruc": "04", "cedula": "05", "pasaporte": "06"}


class Ats(dict):
    """
    representacion del ATS
    >>> ats.campo = 'valor'
    >>> ats['campo']
    'valor'
    """

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError as err:
            raise AttributeError(item) from err

    def __setattr__(self, item, value):
        if item in self.__dict__:
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)


class AccountAts(models.Model):
    _name = "account.ats"
    _description = "Anexo Transaccional Simplificado"

    period = fields.Date(required=True, help="Periodo")

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("export", "Exported"),
            ("export_error", "Error"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        default="draft",
    )
    num_estab_ruc = fields.Char(
        "Nº Establecimientos", size=3, required=True, default="001"
    )
    fcname = fields.Char("Nombre Archivo", size=50, readonly=True)
    fcname_errores = fields.Char("Errores Archivos", size=50, readonly=True)

    xml_ats = fields.Binary(string="Archivo A.T.S")
    error_data = fields.Binary("Archivo Error")

    all_documents = fields.Many2many(
        comodel_name="account.move", string="Facturas Venta"
    )

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    document_lines = fields.One2many(
        "documents.line", "ats_id", "Documentos", copy=False
    )

    def get_all_documents(self):
        self.write({"document_lines": False})

        ats = Ats()
        ruc = self.company_id.partner_id.identifier
        ats.TipoIDInformante = "R"
        ats.IdInformante = ruc
        ats.razonSocial = self.company_id.name.upper()
        ats.Anio = self.period.strftime("%Y")
        ats.Mes = self.period.strftime("%m")
        ats.numEstabRuc = self.num_estab_ruc.zfill(3)
        documents_period = self._get_documents()
        sales = self._get_sales(documents_period)
        ats.totalVentas = "%.2f" % sales
        ats.codigoOperativo = "IVA"
        ats.compras = self.read_purchases(documents_period)
        ats.ventas = self.read_sales(documents_period)
        ats.codEstab = self.num_estab_ruc
        ats.ventasEstab = "%.2f" % sales
        ats.ivaComp = "0.00"

        documents_line_ids = []

        for document in documents_period:
            check_document = self._verify_document(document)

            documents_line_ids.append(
                self.env["documents.line"]
                .create(
                    {
                        "identifier": document.partner_id.identifier,
                        "document_id": document.id,
                        "document_type": document.move_type,
                        "date": document.invoice_date,
                        "amount_total": document.amount_total,
                        "validation_ats": check_document,
                    }
                )
                .id
            )
        self.write({"document_lines": [(6, 0, documents_line_ids)]})

    def _verify_document(self, document):
        msg = ""
        aux = True
        if document.withholding_id:
            if not document.withholding_id.key_access_auth:
                msg += "• Verifique el número de autorización de Retencion.\n"
                aux = False

            if not document.withholding_id.access_key_label:
                msg += "• Retención no autorizada.\n"
                aux = False
            if not document.withholding_id.support_id.code:
                msg += "• Ingreso sujeto a impuestos no definido de Retencion.\n"
                aux = False
            if not document.withholding_id.voucher_type_id.code:
                msg += "• Tipo de documento no definido de Retencion.\n"
                aux = False
        if document.doc_type != "in_invoice":
            if not document.access_key_label:
                msg += "• Documento no autorizado.\n"
                aux = False
            if not document.voucher_type_ats.code:
                msg += "• Tipo de documento no definido.\n"
                aux = False

        valid = True * aux

        if valid:
            msg = "✔ ok"
        return msg

    def export_ats(self):
        self.write({"error_data": False, "fcname_errores": False})

        ats = Ats()
        ruc = self.company_id.partner_id.identifier
        ats.TipoIDInformante = "R"
        ats.IdInformante = ruc
        ats.razonSocial = self.company_id.name.replace(".", "").upper()

        year = self.period.strftime("%Y")
        month = self.period.strftime("%m")

        ats.Anio = year
        ats.Mes = month
        ats.numEstabRuc = self.num_estab_ruc.zfill(3)
        documents_period = self._get_documents()
        sales = self._get_sales(documents_period)
        ats.totalVentas = "%.2f" % sales
        ats.codigoOperativo = "IVA"
        ats.compras = self.read_purchases(documents_period)
        ats.ventas = self.read_sales(documents_period)
        ats.codEstab = self.num_estab_ruc
        ats.ventasEstab = "%.2f" % sales
        ats.ivaComp = "0.00"
        ats_rendered = self.render_xml(ats)
        ok, schema = self.validate_document(ats_rendered)
        buf = StringIO()
        buf.write(ats_rendered)
        value = buf.getvalue().encode("utf-8")
        out = base64.b64encode(value)
        buf.close()
        buf_erro = StringIO()
        buf_erro.write(str(schema.error_log))
        out_erro = base64.encodebytes(buf_erro.getvalue().encode("utf-8"))
        buf_erro.close()

        name = "%s%s%s.XML" % ("AT", month, year)
        data2save = {
            "state": ok and "export" or "export_error",
            "xml_ats": out,
            "fcname": name,
        }
        if not ok:
            data2save.update({"error_data": out_erro, "fcname_errores": "ERRORS.txt"})
        self.write(data2save)

    def _get_sales(self, docs):
        amount_inv = sum(
            docs.filtered(lambda l: l.move_type == "out_invoice").mapped(
                "amount_untaxed"
            )
        )
        amount_ref = sum(
            docs.filtered(lambda l: l.move_type == "out_refund").mapped(
                "amount_untaxed"
            )
        )
        amount_sales = amount_inv - amount_ref
        # print(amount_sales)
        return amount_sales

    def _get_documents(self):
        year_month = self.period.strftime("%Y %m")
        documents = (
            self.env["account.move"]
            .sudo()
            .search(
                [
                    ("state", "=", "posted"),
                    (
                        "move_type",
                        "in",
                        ("out_invoice", "in_invoice", "out_refund", "in_refund"),
                    ),
                ]
            )
        )
        documents_period = documents.filtered(
            lambda l: l.date.strftime("%Y %m") == year_month
        )

        return documents_period

    def read_sales(self, docs):
        sales_inv = docs.filtered(
            lambda l: l.move_type in ("out_invoice", "out_refund")
        )
        sales = []
        for inv in sales_inv:
            line_ice = inv.invoice_line_ids.filtered(
                lambda l: l.tax_ids.filtered(
                    lambda r: r.tax_group_id.l10n_ec_type == "ice"
                )
            )
            line_irbp = inv.invoice_line_ids.filtered(
                lambda l: l.tax_ids.filtered(
                    lambda r: r.tax_group_id.l10n_ec_type == "irbpnr"
                )
            )
            amount_ice = 0.00
            amount_irbpnr = 0.00
            for line in line_ice:
                b = line.tax_ids.filtered(
                    lambda l: l.tax_group_id.l10n_ec_type == "ice"
                ).mapped("amount")
                amount_ice += float(sum([line.price_subtotal * (n / 100) for n in b]))

            for line in line_irbp:
                b = line.tax_ids.filtered(
                    lambda l: l.tax_group_id.l10n_ec_type == "irbpnr"
                ).mapped("amount")
                amount_irbpnr += float(sum([line.quantity * n for n in b]))
            detailsales = {
                "tpIdCliente": tpIdCliente[inv.partner_id.type_identifier],
                "idCliente": inv.partner_id.identifier,
                "parteRelVtas": "NO",
                "partner": inv.partner_id,
                "tipoComprobante": (
                    "04"
                    if inv.voucher_type_ats.code == "41"
                    else str(inv.voucher_type_ats.code).zfill(2)
                ),
                # "tipoEmision": inv.partner_id.is_electronic and "E" or "F",
                # If we send E the software DIMM doesnt calculate the invoice
                # and the sales validation fails, so we send F
                "tipoEmision": "F",
                "numeroComprobantes": 1,
                "baseNoGraIva": sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: l.tax_ids.filtered(lambda t: t.code_edocument == "6")
                    ).mapped("price_subtotal")
                ),
                "baseImponible": sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: not l.tax_ids
                        or l.tax_ids.filtered(lambda t: t.code_edocument == "0")
                    ).mapped("price_subtotal")
                ),
                "baseImpGrav": sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: l.tax_ids.filtered(
                            lambda t: t.code_edocument != "0"
                            and t.code_edocument not in ["6", "7"]
                        )
                    ).mapped("price_subtotal")
                ),
                "montoIva": inv.amount_tax - amount_ice - amount_irbpnr,
                "montoIce": amount_ice,
                "montoIrbpn": amount_irbpnr,
                "valorRetIva": inv.withholding_id.amount_total_vat,
                "valorRetRenta": inv.withholding_id.amount_total_ir,
                "formasDePago": {"formaPago": inv.epayment_id.code},
            }
            sales.append(detailsales)
        sales = sorted(sales, key=itemgetter("idCliente", "tipoComprobante"))
        sales_end = []
        for (ruc, tipo_comprobante), grupo in groupby(
            sales, key=itemgetter("idCliente", "tipoComprobante")
        ):
            baseimp = 0
            nograviva = 0
            montoiva = 0
            montoice = 0
            montoirbpn = 0
            retiva = 0
            impgrav = 0
            retrenta = 0
            numComp = 0
            partner_temp = False
            for i in grupo:
                nograviva += i["baseNoGraIva"]
                baseimp += i["baseImponible"]
                impgrav += i["baseImpGrav"]
                montoiva += i["montoIva"]
                montoice += i["montoIce"]
                montoirbpn += i["montoIrbpn"]
                retiva += i["valorRetIva"]
                retrenta += i["valorRetRenta"]
                numComp += 1
                partner_temp = i["partner"]
            detail = {
                "tpIdCliente": tpIdCliente[partner_temp.type_identifier],
                "idCliente": ruc,
                "parteRelVtas": "NO",
                "tipoComprobante": str(tipo_comprobante).zfill(2),
                "tipoCliente": "01" if partner_temp.company_type == "person" else "02",
                "denoCli": partner_temp.vat,
                # "tipoEmision": inv.partner_id.is_electronic and "E" or "F",
                # If we send E the software DIMM doesnt calculate the invoice
                # and the sales validation fails, so we send F
                "tipoEmision": "F",
                "numeroComprobantes": numComp,
                "baseNoGraIva": "%.2f" % nograviva,
                "baseImponible": "%.2f" % baseimp,
                "baseImpGrav": "%.2f" % impgrav,
                "montoIva": "%.2f" % montoiva,
                "montoIce": "%.2f" % montoice,
                "montoIrbpn": "%.2f" % montoirbpn,
                "valorRetIva": "%.2f" % retiva,
                "valorRetRenta": "%.2f" % retrenta,
                "formasDePago": [{"formaPago": "20"}],
            }
            sales_end.append(detail)

        return sales_end

    def read_purchases(self, docs):
        """
        Procesa:
          * facturas de proveedor
          * liquidaciones de compra
        """
        purchase_inv = docs.filtered(
            lambda l: l.move_type in ("in_invoice", "in_refund")
        )
        purchase = []
        for inv in purchase_inv:
            if inv.is_receipt:
                continue
            if not inv.partner_id.type_identifier == "pasaporte":
                line_ice = inv.invoice_line_ids.filtered(
                    lambda l: l.tax_ids.filtered(
                        lambda r: r.tax_group_id.l10n_ec_type == "ice"
                    )
                )
                line_irbp = inv.invoice_line_ids.filtered(
                    lambda l: l.tax_ids.filtered(
                        lambda r: r.tax_group_id.l10n_ec_type == "irbpnr"
                    )
                )
                amount_ice = 0.00
                amount_irbpnr = 0.00
                for line in line_ice:
                    b = line.tax_ids.filtered(
                        lambda l: l.tax_group_id.l10n_ec_type == "ice"
                    ).mapped("amount")
                    amount_ice += float(
                        sum([line.price_subtotal * (n / 100) for n in b])
                    )

                for line in line_irbp:
                    b = line.tax_ids.filtered(
                        lambda l: l.tax_group_id.l10n_ec_type == "irbpnr"
                    ).mapped("amount")
                    amount_irbpnr += float(sum([line.quantity * n for n in b]))
                amount_iva = float(
                    inv.amount_tax_base_vatb + inv.amount_tax_base_vatsrv
                )
                if inv.move_type == "in_refund":
                    amount_iva = inv.amount_tax
                base_no_gra_iva = sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: l.tax_ids.filtered(lambda t: t.code_edocument == "6")
                    ).mapped("price_subtotal")
                )
                base_imponible = sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: not l.tax_ids
                        or l.tax_ids.filtered(lambda t: t.code_edocument == "0")
                    ).mapped("price_subtotal")
                )
                base_imp_grav = sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: l.tax_ids.filtered(
                            lambda t: t.code_edocument != "0"
                            and t.code_edocument not in ["6", "7"]
                        )
                    ).mapped("price_subtotal")
                )
                base_imp_exe = sum(
                    inv.invoice_line_ids.filtered(
                        lambda l: l.tax_ids.filtered(lambda t: t.code_edocument == "7")
                    ).mapped("price_subtotal")
                )
                detailpurchases = {}
                val_ret = self._get_ret_iva(inv)
                valRetBien10 = val_ret["retBien10"]
                valRetServ20 = val_ret["retServ20"]
                valorRetBienes = val_ret["retBien"]
                valRetServ50 = val_ret["retServ50"]
                valorRetServicios = val_ret["retServ"]
                valRetServ100 = val_ret["retServ100"]
                t_reeb = 0.0
                type_doc = inv.voucher_type_ats.xml_code
                if not type_doc == "41":
                    t_reeb = 0.00
                else:
                    if inv.doc_type == "liq_purchase":
                        t_reeb = 0.0
                    else:
                        t_reeb = inv.amount_untaxed
                type_support = inv.partner_id.ats_support_id.code
                auth = inv.access_key_label
                # inv.epayment_id.code
                name = inv.support_document
                if not name:
                    name = inv.name
                if "-" in name:
                    name = name.replace("-", "")
                detailpurchases.update(
                    {
                        "codSustento": "02" if type_doc == "02" else type_support,
                        "tpIdProv": tpIdProv[inv.partner_id.type_identifier],
                        "idProv": inv.partner_id.identifier,
                        "tipoComprobante": (
                            "04"
                            if type_doc == "41"
                            else ("03" if inv.doc_type == "liq_purchase" else type_doc)
                        ),
                        "parteRel": "NO",
                        "fechaRegistro": self._convert_date(inv.invoice_date),
                        "establecimiento": name[:3],
                        "puntoEmision": name[3:6],
                        "secuencial": name[6:15],
                        "fechaEmision": self._convert_date(inv.invoice_date),
                        "autorizacion": auth,
                        "baseNoGraIva": "%.2f" % base_no_gra_iva,
                        "baseImponible": base_imponible,
                        "baseImpGrav": base_imp_grav,
                        "baseImpExe": "%.2f" % base_imp_exe,
                        "total": inv.amount_total,
                        "montoIce": "%.2f" % amount_ice,
                        "montoIva": "%.2f" % amount_iva,
                        "valRetBien10": "%.2f" % valRetBien10,
                        "valRetServ20": "%.2f" % valRetServ20,
                        "valorRetBienes": "%.2f" % valorRetBienes,
                        "valRetServ50": "%.2f" % valRetServ50,
                        "valorRetServicios": "%.2f" % valorRetServicios,
                        "valorRetServ100": "%.2f" % valRetServ100,
                        "totbasesImpReemb": "%.2f" % t_reeb,
                        "pagoExterior": {
                            "pagoLocExt": "01",
                            "paisEfecPago": "NA",
                            "aplicConvDobTrib": "NA",
                            "pagoExtSujRetNorLeg": "NA",
                        },
                        "formasDePago": [{"formaPago": "20"}],
                        "detalleAir": self.process_lines(inv),
                    }
                )
                bases = base_no_gra_iva + base_imponible + base_imp_grav + base_imp_exe
                if bases + amount_ice + amount_iva > 500:
                    detailpurchases["greater1000"] = "YES"

                if inv.withholding_id:
                    detailpurchases.update({"retencion": True})
                    detailpurchases.update(self.get_withholding(inv.withholding_id))
                if inv.move_type in ["in_refund"]:
                    refund = self.get_refund(inv)
                    if refund:
                        detailpurchases.update({"es_nc": True})
                        detailpurchases.update(refund)

                purchase.append(detailpurchases)
        return purchase

    def get_refund(self, refund):
        invoice = refund.reversed_entry_id

        if invoice:
            name = invoice.support_document
            if not name:
                name = invoice.name
            if "FC-" in name:
                name = name.replace("FC-", "")
            if "-" in name:
                name_sep = name.split("-")
                return {
                    "docModificado": "01",
                    "estabModificado": name_sep[0],
                    "ptoEmiModificado": name_sep[1],
                    "secModificado": name_sep[2],
                    "autModificado": invoice.access_key_label,
                }
            else:
                estab_modificado = name[:3]
                pto_emi_modificado = name[3:6]
                sec_modificado = name[6:]
                return {
                    "docModificado": "01",
                    "estabModificado": estab_modificado,
                    "ptoEmiModificado": pto_emi_modificado,
                    "secModificado": sec_modificado,
                    "autModificado": invoice.access_key_label,
                }

    def get_withholding(self, wh):
        name = wh.name.replace("-", "")
        return {
            "estabRetencion1": name[:3],
            "ptoEmiRetencion1": name[3:6],
            "secRetencion1": name[6:15],
            "autRetencion1": wh.access_key_label,
            "fechaEmiRet1": self._convert_date(wh.date),
        }

    def process_lines(self, inv):
        """
        @temp: {'332': {baseImpAir: 0,}}
        @data_air: [{baseImpAir: 0, ...}]
        """
        lines = inv.withholding_id.lines_withholding
        data_air = []
        temp = {}

        # Verifica si hay líneas, y si no, asigna el valor por defecto
        if not lines:  # Si no hay líneas
            temp["default"] = {
                "baseImpAir": inv.tax_totals["amount_untaxed"],
                "valRetAir": 0,
                "codRetAir": "332",
                "porcentajeAir": 0,
            }
        else:
            for line in lines:
                if line.code_ir:
                    grp = line.code_ir.tax_group_id.l10n_ec_type
                    if grp in ["ret_ir", "no_ret_ir"]:
                        if not temp.get(line.code_ir.code):
                            temp[line.code_ir.code] = {"baseImpAir": 0, "valRetAir": 0}
                        temp[line.code_ir.code]["baseImpAir"] += line.amount_base_ir
                        temp[line.code_ir.code]["codRetAir"] = line.code_ir.code  # noqa
                        temp[line.code_ir.code][
                            "porcentajeAir"
                        ] = line.percent_ir  # noqa
                        temp[line.code_ir.code]["valRetAir"] += abs(line.amount_line_ir)

        for _k, v in temp.items():

            data_air.append(v)
        return data_air

    def _get_ret_iva(self, invoice):
        """
        Return (valRetBien10, valRetServ20,
        valorRetBienes,
        valorRetServicios, valorRetServ100)
        """
        retBien10 = 0
        retServ20 = 0
        retBien = 0
        retServ50 = 0
        retServ = 0
        retServ100 = 0
        tax = invoice.withholding_id
        val_ret = {
            "retBien10": 0,
            "retServ20": 0,
            "retBien": 0,
            "retServ50": 0,
            "retServ": 0,
            "retServ100": 0,
        }
        if tax.code_vat_b:
            if str(tax.percent_vat_b) == "10.0":
                retBien10 += abs(tax.amount_total_vat_b)
                val_ret.update({"retBien10": retBien10})
            else:
                retBien += abs(tax.amount_total_vat_b)
                val_ret.update({"retBien": retBien})
        if tax.code_vat_s:
            if str(tax.percent_vat_s) == "100.0":
                retServ100 += abs(tax.amount_total_vat_s)
                val_ret.update({"retServ100": retServ100})
            elif str(tax.percent_vat_s) == "50.0":
                retServ50 += abs(tax.amount_total_vat_s)
                val_ret.update({"retServ50": retServ50})
            elif str(tax.percent_vat_s) == "20.0":
                retServ20 += abs(tax.amount_total_vat_s)
                val_ret.update({"retServ20": retServ20})
            else:
                retServ += abs(tax.amount_total_vat_s)
                val_ret.update({"retServ": retServ})

        return val_ret

    def _convert_date(self, date_inv):
        """
        fecha: '2012-12-15'
        return: '15/12/2012'
        """
        # f = date_inv.split('-')
        f = date_inv.strftime("%d/%m/%Y")

        return f

    def render_xml(self, ats):
        tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ats_tmpl = env.get_template("ats.xml")
        return ats_tmpl.render(ats)

    def validate_document(self, ats, error_log=False):
        file_path = os.path.join(os.path.dirname(__file__), "XSD/ats.xsd")
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        r = ats.encode("utf-8")
        # print(type(r))
        # print(type(ats))
        root = etree.fromstring(r)
        ok = True

        try:
            xmlschema.assertValid(root)
        except DocumentInvalid:
            ok = False
        return ok, xmlschema

    # @api.model
    # def _get_sales(self, month, year):
    #     sql_sales = "SELECT type, sum(amount_tax+amount_untaxed) AS base\
    #                   FROM account_move \
    #                   WHERE type IN ('out_invoice', 'out_refund') \
    #                   AND state IN ('posted','paid') \
    #                   AND EXTRACT(month FROM 'invoice_date') = %s\
    #                   AND EXTRACT(year FROM 'invoice_date') = %s" % (month, year)
    #     sql_sales += " GROUP BY type"
    #     self.env.cr.execute(sql_sales)
    #     res = self.env.cr.fetchall()
    #     resultado = sum(map(lambda x: x[0] ==
    # 'out_refund' and x[1] * -1 or x[1], res))
    #     return resultado


class DocumentsLine(models.Model):

    _name = "documents.line"
    _description = "Documents lines"

    identifier = fields.Char(string="RUC", readonly=True)

    document_id = fields.Many2one(comodel_name="account.move", string="Documentos")
    ats_id = fields.Many2one(
        comodel_name="account.ats", string="Documentos", ondelete="cascade"
    )

    date = fields.Char(string="Fecha", readonly=True)
    document_type = fields.Selection(
        string="Tipo Documento",
        selection=[
            ("out_invoice", "Factura de Venta"),
            ("in_invoice", "Factura de Compra"),
            ("out_refund", "NC Ventas"),
            ("in_refund", "NC Compras"),
        ],
        readonly=True,
    )
    validation_ats = fields.Text(string="Validación ATS")
    amount_total = fields.Monetary(
        string="Total",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        readonly=True,
        default=lambda self: self._default_currency(),
    )

    def _default_currency(self):
        company = self.env.user.company_id
        # #print("Currency:", company.currency_id)
        return company.currency_id
