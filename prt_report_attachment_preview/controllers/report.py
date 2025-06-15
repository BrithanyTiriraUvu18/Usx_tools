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
from email.utils import encode_rfc2231
from werkzeug import urls

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval, time
from odoo.addons.web.controllers.report import ReportController

from PyPDF2 import PdfMerger
import io

 
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
        report_name = "report"
        if docids:
            records = request.env[report.model].browse(docids)
            record_count = len(docids)
            if record_count == 1 and report.sudo().print_report_name:
                print_report_name = report.sudo().print_report_name
                extra_ctx = self._get_extra_context_for_single_record(
                    print_report_name,
                    ignore_expr=["object", "time"],
                )
                report_name = safe_eval(
                    print_report_name,
                    {
                        "object": records,
                        "time": time,
                        **extra_ctx,
                    },
                )
            else:
                report_name = f"{report.name} x{record_count}"
        else:
            report_name = report.name
        return report_name

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

        # Extrae opciones y contexto
        if data.get("options"):
            data.update(json.loads(urls.url_unquote_plus(data.pop("options"))))
        if data.get("context"):
            context.update(json.loads(urls.url_unquote_plus(data.pop("context"))))
        if data.get("cid"):
            context.update(allowed_company_ids=[int(i) for i in data["cid"].split(",")])

        request.env.context = context

        # Manejo de IDs
        if docids:
            docids = [int(i) for i in docids.split(",")]
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

        #NUEVO: procesar en lotes
        chunk_size = 100
        chunks = [docids[i:i + chunk_size] for i in range(0, len(docids), chunk_size)]

        merger = PdfMerger()

        for chunk in chunks:
            pdf_data, _ = report_obj.with_context(**context)._render_qweb_pdf(
                reportname, chunk, data=data
            )
            merger.append(io.BytesIO(pdf_data))

        output = io.BytesIO()
        merger.write(output)
        merger.close()

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
