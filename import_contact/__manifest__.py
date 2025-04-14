{
    'name': 'Import Contact',
    'version': '1.0',
    'depends': ['base', 'contacts', 'web', 'import_dashboard'],
    'author': 'Brithany',
    'category': 'Tools',
    'summary': 'Importa contactos desde CSV o XLSX',
    'data': [
        'security/ir.model.access.csv',
        'data/import_dashboard_demo.xml',
        'views/contact_import_wizard_view.xml',
        'views/import_dashboard_menu.xml',
        'views/import_dashboard_kanban_view.xml',
    ],
    'installable': True,
}
