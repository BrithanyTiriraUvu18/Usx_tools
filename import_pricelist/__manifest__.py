{
    'name': 'Lista de Precios',
    'version': '1.0',
    'depends': ['base', 'product', 'web' , 'import_dashboard'],
    'author': 'Brithany',
    'category': 'Tools',
    'summary': 'Importar Lista de precios desde CSV o XLSX',
    'data': [
         'security/ir.model.access.csv',
         'wizards/pricelist_import_wizard_view.xml',
         'views/import_dashboard_kanban_view.xml',
         'views/import_dashboard_menu.xml',
    ],
    'installable': True,
}
