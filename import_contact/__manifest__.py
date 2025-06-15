{
    'name': 'Import Contact',
    "version": "17.0.1.0.0",
    'summary': 'Import contacts from XLSX',
    "category": "Tools",
    "license": "OPL-1",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    'depends': ['base', 'contacts', 'web', 'import_dashboard'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/contact_import_wizard_view.xml',
        'views/import_dashboard_menu.xml',
        'views/import_dashboard_kanban_view.xml',
    ],
    "installable": True,
    "application": False,
}
