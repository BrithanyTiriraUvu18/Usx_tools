{
    "name": "SRI Charts for Ecuador V17",
    "version": "17.0.1.0.0",
    "category": "Generic Modules/Accounting",
    "license": "OPL-1",
    "depends": [
        "base",
        "account",
        "account_parent",
    ],
    "author": "Hernan Espinoza",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "data": [
        "security/ir.model.access.csv",
        "views/account_sri_charts_view.xml",
        "views/account_tax_view.xml",
        "views/account_tax_group_views.xml",
        "views/res_partner_view.xml",
        "views/account_sri_menuitems.xml",
        "views/account_move_view.xml",
        "data/sri_charts.xml",
        # Chart of Accounts FenixERP
        "data/account.account-fenix.csv",
        # # Taxes
        "data/account_tax_group_data.xml",
        "data/account_tax_tag_data.xml",
        "data/ice_tags.xml",
        "data/account_tax_template_vat_data.xml",
        "data/account_tax_template_withhold_profit_data.xml",
        "data/account_tax_withhold_vat_data.xml",
        # # ICE
        "data/account_tax_template_ice_data.xml",
        # Taxes FenixERP
        "data/account_fiscal_position_erp_template.xml",
        # A.T.S
        "views/account_ats_view_menu.xml",
        "views/account_voucher_type_view.xml",
        "views/account_ats_support_view.xml",
        "views/account_ats_view.xml",
        "data/account.voucher.type.csv",
        "data/tax_ats_support_data.xml",
        "data/account_journal_data.xml",
        "data/res.country.state.csv",
    ],
    "pre_init_hook": "pre_init_hook",
}
