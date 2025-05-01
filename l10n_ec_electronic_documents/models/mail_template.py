import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields):
        self.ensure_one()
        res = super().generate_email(res_ids, fields)
        access_key_label = ""
        try:
            multi_mode = True
            if isinstance(res_ids, int):
                res_ids = [res_ids]
                multi_mode = False

            if self.model not in [
                "account.move",
                "account.withholding",
                "account.guide",
            ]:
                return res

            records = self.env[self.model].browse(res_ids)
            for record in records:
                access_key_label = record.access_key_label
                record_data = res[record.id] if multi_mode else res
                attachments = []
                if (
                    record.move_type
                    in ("out_invoice", "out_refund", "withholding", "referral_guide")
                    or record.doc_type in ("liq_purchase")
                ) and (record.state == "posted" or record.state == "done"):
                    company = record.company_id
                    if not company.ride_name_param:
                        pdf_name = str(record.access_key_label) + ".pdf"
                        xml_name = str(record.access_key_label) + ".xml"
                    else:
                        new_seq = False
                        flag = False
                        count = 0
                        name_file_split = company.ride_name_param.split("/")
                        for p_split in name_file_split:
                            if "%(year)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + str(record.date.year)
                                else:
                                    new_seq = str(record.date.year)
                            elif "%(y)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + record.date.strftime("%y")
                                else:
                                    new_seq = record.date.strftime("%y")
                            elif "%(key)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + record.access_key_label
                                else:
                                    new_seq = record.access_key_label
                            elif "%(month)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + str(record.date.month)
                                else:
                                    new_seq = str(record.date.month)
                            elif "%(day)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + str(record.date.day)
                                else:
                                    new_seq = str(record.date.day)
                            elif "%(doy)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = (
                                        new_seq
                                        + "/"
                                        + str(record.date.timetuple().tm_yday)
                                    )
                                else:
                                    new_seq = str(record.date.timetuple().tm_yday)
                            elif "%(woy)s" == p_split:
                                flag = True
                                week_number = record.date.isocalendar()[1]
                                if new_seq:
                                    new_seq = new_seq + "/" + str(week_number)
                                else:
                                    new_seq = str(week_number)
                            elif "%(weekday)s" == p_split:
                                flag = True
                                if new_seq:
                                    new_seq = new_seq + "/" + str(record.date.weekday())
                                else:
                                    new_seq = str(record.date.weekday())
                            elif "" == p_split:
                                if new_seq:
                                    new_seq = new_seq + "/" + name_file_split[count]
                                else:
                                    new_seq = name_file_split[count]
                            else:
                                if new_seq:
                                    new_seq = new_seq + "/" + p_split
                                else:
                                    new_seq = p_split
                            count += 1
                        if not flag:
                            name_file = name_file_split
                        else:
                            name_file = new_seq
                        name_file = str(name_file).replace("/", "")
                        ride_name = str(name_file).replace(".pdf", "")
                        pdf_name = ride_name + ".pdf"
                        xml_name = ride_name + ".xml"

                    if record.ride:
                        attachments += [
                            (pdf_name, record.ride),
                            (xml_name, record.xml_ride),
                        ]
                if attachments:
                    record_data.setdefault("attachments", [])
                    record_data["attachments"] = attachments
        except Exception:
            _logger.warning("error in the access Key: %s" % access_key_label)
        return res
