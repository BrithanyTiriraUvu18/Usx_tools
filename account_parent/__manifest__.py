##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (C) 2020 - Today O4ODOO (Omal Bastin)
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################
{
    "name": "Parent Account (Chart of Account Hierarchy)",
    "summary": (
        "Adds Parent account and ability to open chart "
        "of account list view based on the date and moves"
    ),
    "author": "Omal Bastin / O4ODOO",
    # 'live_test_url': 'https://ap.o4odoo.com/',
    "license": "OPL-1",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "category": "Accounting",
    "version": "17.0.1.1.3",
    "depends": ["account"],
    "data": [
        "security/account_parent_security.xml",
        "security/ir.model.access.csv",
        "views/account_view.xml",
        "views/open_chart.xml",
        # 'data/account_type_data.xml',
        "views/report_coa_hierarchy.xml",
        "views/res_config_view.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_common": [
            "account_parent/static/src/scss/coa_hierarchy.scss",
        ],
        "web.assets_backend": [
            "account_parent/static/src/js/account_parent_backend.js",
            "account_parent/static/src/js/account_type_selection.js",
            "account_parent/static/src/xml/account_parent_backend.xml",
            "account_parent/static/src/xml/account_parent_line.xml",
        ],
    },
    "images": ["static/description/account_parent_9.png"],
    "installable": True,
    "post_init_hook": "_assign_account_parent",
}
