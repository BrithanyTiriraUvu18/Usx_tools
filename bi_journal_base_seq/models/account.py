import re

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bi_sequence_id = fields.Many2one(
        comodel_name="ir.sequence", string="Entry Sequence", copy=False
    )
    bi_sequence_next_number = fields.Integer(
        string="Next Sequence Number", copy=False, default=1
    )
    bi_refund_sequence_id = fields.Many2one(
        comodel_name="ir.sequence", string="Credit Note Entry Sequence", copy=False
    )
    bi_refund_sequence_next_number = fields.Integer(
        string="Credit Note Next Number", copy=False, default=1
    )

    def write(self, vals):
        res = super(AccountJournal, self).write(vals)
        if "bi_sequence_next_number" in vals and self.type in ("sale", "purchase"):
            for rec in self:
                if rec.bi_sequence_id:
                    if (
                        rec.bi_sequence_id.use_date_range is True
                        and len(rec.bi_sequence_id.date_range_ids) >= 1
                    ):
                        for i in rec.bi_sequence_id.date_range_ids:
                            if i.date_from <= self.write_date.date() <= i.date_to:
                                i.sudo().write(
                                    {
                                        "number_next_actual": vals[
                                            "bi_sequence_next_number"
                                        ]
                                    }
                                )
                    else:
                        rec.bi_sequence_id.sudo().write(
                            {"number_next_actual": vals["bi_sequence_next_number"]}
                        )
        if "bi_refund_sequence_next_number" in vals and self.type in (
            "sale",
            "purchase",
        ):
            for rec in self:
                if rec.bi_sequence_id:
                    if (
                        rec.bi_refund_sequence_id.use_date_range is True
                        and len(rec.bi_refund_sequence_id.date_range_ids) >= 1
                    ):
                        for i in rec.bi_refund_sequence_id.date_range_ids:
                            if i.date_from <= self.write_date.date() <= i.date_to:
                                i.sudo().write(
                                    {
                                        "number_next_actual": vals[
                                            "bi_refund_sequence_next_number"
                                        ]
                                    }
                                )
                    else:
                        rec.bi_refund_sequence_id.sudo().write(
                            {
                                "number_next_actual": vals[
                                    "bi_refund_sequence_next_number"
                                ]
                            }
                        )
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    custom_seq = fields.Boolean(default=False)

    def _compute_name(self):
        for rec in self:
            if (
                rec.journal_id.type in ("sale", "purchase")
                and rec.move_type
                in ("in_invoice", "in_refund", "out_invoice", "out_refund")
                and rec.name in (False, "/")
            ):
                rec.name = "/"
            else:
                res = super(AccountMove, self)._compute_name()
                return res

    def write(self, vals):
        if "state" in vals:
            if vals["state"] in ("posted"):
                for record in self:
                    if record.journal_id.type in ("sale", "purchase"):
                        if (
                            record.move_type
                            in (
                                "out_invoice",
                                "in_invoice",
                                "out_receipt",
                                "in_receipt",
                            )
                            and record.doc_type != "liq_purchase"
                        ):
                            if not record.journal_id.bi_sequence_id:
                                raise ValidationError(_("Add Sequence In Journal"))
                            else:
                                if (
                                    record.journal_id.bi_sequence_id
                                    and record.name in (False, "/")
                                ):
                                    main_seq = (
                                        record.journal_id.bi_sequence_id.next_by_id()
                                    )
                                    if main_seq:
                                        def_seq = main_seq.split("/")
                                        if record.journal_id.bi_sequence_id.prefix:
                                            prefix_split = record.journal_id.bi_sequence_id.prefix.split(
                                                "/"
                                            )
                                            new_seq = False
                                            flag = False
                                            count = 0
                                            for p_split in prefix_split:
                                                if "%(year)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.year)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.year)
                                                elif "%(y)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + record.date.strftime("%y")
                                                        )
                                                    else:
                                                        new_seq = record.date.strftime(
                                                            "%y"
                                                        )
                                                elif "%(month)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.month)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.month)
                                                elif "%(day)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.day)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.day)
                                                elif "%(doy)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(
                                                                record.date.timetuple().tm_yday
                                                            )
                                                        )
                                                    else:
                                                        new_seq = str(
                                                            record.date.timetuple().tm_yday
                                                        )
                                                elif "%(woy)s" == p_split:
                                                    flag = True
                                                    week_number = (
                                                        record.date.isocalendar()[1]
                                                    )
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(week_number)
                                                        )
                                                    else:
                                                        new_seq = str(week_number)
                                                elif "%(weekday)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.weekday())
                                                        )
                                                    else:
                                                        new_seq = str(
                                                            record.date.weekday()
                                                        )
                                                elif "" == p_split:
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + def_seq[count]
                                                        )
                                                    else:
                                                        new_seq = def_seq[count]
                                                else:
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq + "/" + p_split
                                                        )
                                                    else:
                                                        new_seq = p_split
                                                count += 1
                                            if not flag:
                                                name = main_seq
                                            else:
                                                name = new_seq
                                        else:
                                            name = main_seq
                                    else:
                                        name = main_seq

                                    move = self.env["account.move"].search(
                                        [
                                            ("name", "=", name),
                                            ("move_type", "=", record.move_type),
                                        ]
                                    )
                                    if move:
                                        sequence = (
                                            record.journal_id.bi_sequence_id.next_by_id()
                                        )
                                        record.name = sequence
                                    else:
                                        record.name = name
                                    if (
                                        record.journal_id.bi_sequence_id.use_date_range
                                        is True
                                        and len(
                                            record.journal_id.bi_sequence_id.date_range_ids
                                        )
                                        >= 1
                                    ):
                                        for (
                                            i
                                        ) in (
                                            record.journal_id.bi_sequence_id.date_range_ids
                                        ):
                                            if (
                                                i.date_from
                                                <= record.write_date.date()
                                                <= i.date_to
                                            ):
                                                record.journal_id.sudo().write(
                                                    {
                                                        "bi_sequence_next_number": i.number_next
                                                        + 1
                                                    }
                                                )
                                    else:
                                        record.journal_id.sudo().write(
                                            {
                                                "bi_sequence_next_number": record.env[
                                                    "ir.sequence"
                                                ]
                                                .search(
                                                    [
                                                        (
                                                            "id",
                                                            "=",
                                                            record.journal_id.bi_sequence_id.id,
                                                        )
                                                    ]
                                                )
                                                .number_next
                                                + 1
                                            }
                                        )
                        elif record.move_type in ("out_refund", "in_refund"):
                            if not record.journal_id.bi_refund_sequence_id:
                                raise ValidationError(
                                    _("Add Refund/Credit Note Sequence In Journal")
                                )
                            else:
                                if (
                                    record.journal_id.bi_refund_sequence_id
                                    and record.name in (False, "/")
                                ):
                                    main_seq = (
                                        record.journal_id.bi_refund_sequence_id.next_by_id()
                                    )
                                    if main_seq:
                                        def_seq = main_seq.split("/")
                                        if (
                                            record.journal_id.bi_refund_sequence_id.prefix
                                        ):
                                            prefix_split = record.journal_id.bi_refund_sequence_id.prefix.split(
                                                "/"
                                            )
                                            new_seq = False
                                            flag = False
                                            count = 0
                                            for p_split in prefix_split:
                                                if "%(year)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.year)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.year)
                                                elif "%(y)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + record.date.strftime("%y")
                                                        )
                                                    else:
                                                        new_seq = record.date.strftime(
                                                            "%y"
                                                        )
                                                elif "%(month)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.month)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.month)
                                                elif "%(day)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(record.date.day)
                                                        )
                                                    else:
                                                        new_seq = str(record.date.day)
                                                elif "%(doy)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(
                                                                record.date.timetuple().tm_yday
                                                            )
                                                        )
                                                    else:
                                                        new_seq = str(
                                                            record.date.timetuple().tm_yday
                                                        )
                                                elif "%(woy)s" == p_split:
                                                    flag = True
                                                    week_number = (
                                                        record.date.isocalendar()[1]
                                                    )
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(week_number)
                                                        )
                                                    else:
                                                        new_seq = str(week_number)
                                                elif "%(weekday)s" == p_split:
                                                    flag = True
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + str(self.date.weekday())
                                                        )
                                                    else:
                                                        new_seq = str(
                                                            self.date.weekday()
                                                        )
                                                elif "" == p_split:
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq
                                                            + "/"
                                                            + def_seq[count]
                                                        )
                                                    else:
                                                        new_seq = def_seq[count]
                                                else:
                                                    if new_seq:
                                                        new_seq = (
                                                            new_seq + "/" + p_split
                                                        )
                                                    else:
                                                        new_seq = p_split
                                                count += 1
                                            if not flag:
                                                name = main_seq
                                            else:
                                                name = new_seq
                                        else:
                                            name = main_seq
                                    else:
                                        name = main_seq

                                    move = self.env["account.move"].search(
                                        [
                                            ("name", "=", name),
                                            ("move_type", "=", record.move_type),
                                        ]
                                    )
                                    if move:
                                        sequence = (
                                            record.journal_id.bi_refund_sequence_id.next_by_id()
                                        )
                                        record.name = sequence
                                    else:
                                        record.name = name

                                    if (
                                        record.journal_id.bi_refund_sequence_id.use_date_range
                                        is True
                                        and len(
                                            record.journal_id.bi_refund_sequence_id.date_range_ids
                                        )
                                        >= 1
                                    ):
                                        for (
                                            i
                                        ) in (
                                            record.journal_id.bi_refund_sequence_id.date_range_ids
                                        ):
                                            if (
                                                i.date_from
                                                <= record.write_date.date()
                                                <= i.date_to
                                            ):
                                                record.journal_id.sudo().write(
                                                    {
                                                        "bi_refund_sequence_next_number": i.number_next
                                                        + 1
                                                    }
                                                )
                                    else:
                                        record.journal_id.sudo().write(
                                            {
                                                "bi_refund_sequence_next_number": self.env[
                                                    "ir.sequence"
                                                ]
                                                .search(
                                                    [
                                                        (
                                                            "id",
                                                            "=",
                                                            record.journal_id.bi_refund_sequence_id.id,
                                                        )
                                                    ]
                                                )
                                                .number_next
                                                + 1
                                            }
                                        )
            elif vals["state"] in ("draft", "cancel"):
                for rec in self:
                    if rec.journal_id.type in ("sale", "purchase"):
                        rec.name = rec.name

        return super(AccountMove, self).write(vals)


class SequenceMixinInherit(models.AbstractModel):
    _inherit = "sequence.mixin"

    def _constrains_date_sequence(self):
        for record in self:
            seq = record[record._sequence_field]
            if seq:
                prefix = re.search("'(.*)'", seq)
                if prefix:
                    self.name = prefix.group(1)
                else:
                    return super(
                        SequenceMixinInherit, record
                    )._constrains_date_sequence()
