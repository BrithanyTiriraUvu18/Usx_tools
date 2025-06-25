###################################################################################
#
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

import json
import re
import io
from datetime import datetime
from email.utils import encode_rfc2231
from werkzeug import urls

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval, time
from odoo.addons.web.controllers.report import ReportController

#Se instala la siguiente libreria
import pikepdf


class CxReportController(ReportController):

    def _get_extra_context_for_single_record(self, report_name, ignore_expr=None):
        ignore_expr = ignore_expr or []
        extra_ctx = {}
        for expr in re.findall(r"%.?\(.*?\)", report_name):
            expr = expr.replace("%", "").strip()[1:-1].strip()
            if "." in expr:
                expr = expr.split(".")[0]
            if expr in ignore_expr:
                continue
            extra_ctx[expr] = "report"
        return extra_ctx

    def _compose_report_file_name(self, docids, report):
        # Usar el modelo para identificar el tipo de documento
        model_name = report.model or "documentos"
        nombre_modelo = {
            "sale.order": "cotizacion",
            "account.move": "factura",
            "purchase.order": "orden_compra",
        }.get(model_name, model_name.replace('.', '_'))

        fecha = datetime.today().strftime("%d-%m-%Y")
        if len(docids) == 1:
            return f"{nombre_modelo}-{fecha}"
        else:
            return f"reporte-{fecha}"

    def _parse_docids(self, docids_str):
        """Parse docids from either comma-separated IDs or a formatted string"""
        try:
            # Primero intentamos interpretarlo como lista de IDs
            return [int(i) for i in docids_str.split(",")]
        except ValueError:
            # Si falla, asumimos que es un formato legible y obtenemos los IDs del contexto
            context = dict(request.env.context)
            if context.get('active_ids'):
                return context['active_ids']
            return []

    @http.route(
        [
            "/report/<converter>/<reportname>",
            "/report/<converter>/<reportname>/<docids>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter != "pdf":
            return super().report_routes(
                reportname, docids=docids, converter=converter, **data
            )

        report_obj = request.env["ir.actions.report"]
        report = report_obj._get_report_from_name(reportname)
        context = dict(request.env.context)

        # Extraer opciones y contexto
        if data.get("options"):
            data.update(json.loads(urls.url_unquote_plus(data.pop("options"))))
        if data.get("context"):
            context.update(json.loads(urls.url_unquote_plus(data.pop("context"))))
        if data.get("cid"):
            context.update(allowed_company_ids=[int(i) for i in data["cid"].split(",")])

        request.env.context = context

        # Manejo de docids
        if docids:
            docids = self._parse_docids(docids)
        elif data.get("ids"):
            docids = json.loads(data["ids"])
        elif data.get("domain"):
            domain = json.loads(data["domain"])
            docids = request.env[report.model].search(domain).ids
        else:
            docids = []

        if docids:
            request.env[report.model].browse(docids).check_access_rule("read")

        report_file_name = self._compose_report_file_name(docids, report)

        # Funcion para procesar por lotes
        chunk_size = 100
        chunks = [docids[i:i + chunk_size] for i in range(0, len(docids), chunk_size)]

        merger = pikepdf.Pdf.new()

        for chunk in chunks:
            pdf_data, _ = report_obj.with_context(**context)._render_qweb_pdf(
                reportname, chunk, data=data
            )
            with pikepdf.open(io.BytesIO(pdf_data)) as pdf:
                merger.pages.extend(pdf.pages)

        output = io.BytesIO()
        merger.save(output)

        return request.make_response(
            output.getvalue(),
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", str(len(output.getvalue()))),
                (
                    "Content-Disposition",
                    "inline; filename*=%s.pdf" % encode_rfc2231(report_file_name, "utf-8"),
                ),
            ],
        )