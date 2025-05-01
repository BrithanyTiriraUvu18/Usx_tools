from odoo import models


class AccountJournal(models.Model):
    _inherit = ["account.journal"]

    # @api.model
    # def create(self, vals):

    #     journal_type = vals.get("type")
    #     company = (
    #         self.env["res.company"].browse(vals["company_id"])
    #         if vals.get("company_id")
    #         else self.env.company
    #     )
    #     vals["company_id"] = company.id

    #     if journal_type in ("bank", "cash"):
    #         has_liquidity_accounts = vals.get("default_account_id")
    #         has_payment_accounts = vals.get("payment_debit_account_id") or vals.get(
    #             "payment_credit_account_id"
    #         )
    #         has_profit_account = vals.get("profit_account_id")
    #         has_loss_account = vals.get("loss_account_id")
    #         if journal_type == "bank":
    #             acc_list = [
    #                 "1.01.01.02.01",
    #                 "2.01.03.01.03",
    #                 "1.01.01.02.08",
    #                 "1.01.01.02.09",
    #             ]
    #             acc = self.env["account.account"].search([("code", "in", acc_list)])
    #             default_account_id = acc.filtered(lambda l: l.code == acc_list[0])
    #             suspense_account_id = acc.filtered(lambda l: l.code == acc_list[1])
    #             payment_debit_account_id = acc.filtered(lambda l: l.code == acc_list[2])
    #             payment_credit_account_id = acc.filtered(
    #                 lambda l: l.code == acc_list[3]
    #             )

    #         else:
    #             acc_list = [
    #                 "1.01.01.01.01",
    #                 "2.01.03.01.02",
    #                 "1.01.01.01.05",
    #                 "1.01.01.01.06",
    #             ]
    #             if "code" in vals:
    #                 if vals["code"] == "CSHC":
    #                     acc_list = [
    #                         "1.01.01.01.02",
    #                         "2.01.03.01.02",
    #                         "1.01.01.01.07",
    #                         "1.01.01.01.08",
    #                     ]
    #             acc = self.env["account.account"].search([("code", "in", acc_list)])
    #             default_account_id = acc.filtered(lambda l: l.code == acc_list[0])
    #             suspense_account_id = acc.filtered(lambda l: l.code == acc_list[1])
    #             payment_debit_account_id = acc.filtered(lambda l: l.code == acc_list[2])
    #             payment_credit_account_id = acc.filtered(
    #                 lambda l: l.code == acc_list[3]
    #             )

    #         # === Fill missing accounts ===
    #         if not has_liquidity_accounts:
    #             vals["default_account_id"] = default_account_id.id
    #             vals["suspense_account_id"] = suspense_account_id.id

    #         if not has_payment_accounts:
    #             vals["payment_debit_account_id"] = payment_debit_account_id.id
    #             vals["payment_credit_account_id"] = payment_credit_account_id.id

    #         if journal_type == "cash" and not has_profit_account:
    #             vals[
    #                 "profit_account_id"
    #             ] = company.default_cash_difference_income_account_id.id
    #         if journal_type == "cash" and not has_loss_account:
    #             vals[
    #                 "loss_account_id"
    #             ] = company.default_cash_difference_expense_account_id.id

    #     return super(AccountJournal, self).create(vals)
