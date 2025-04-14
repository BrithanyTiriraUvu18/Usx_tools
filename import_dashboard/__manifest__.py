{
    "name": "Import Dashboard",
    "version": "17.0.1.0.0",
    "summary": "Import data into odoo",
    "category": "Extra Tools",
    "author": "Joseph Armas / FenixERP",
    "license": "OPL-1",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "depends": [
        "base",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "wizards/account_move_view.xml",
        "views/import_dashboard.xml",
    ],
    "external_dependencies": {"python": ["xlrd"]},
    "installable": True,
    "application": False,
}
