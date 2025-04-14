#-*- coding: utf-8 -*-
{
    'name': 'Biblioteca',
    'version': '1.0',
    'category': 'Tools',
    'description': """
        Módulo para gestionar una biblioteca:
        - Gestión de libros
        - Control de disponibilidad
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/book_views.xml',
        'demo/biblioteca_demo.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}