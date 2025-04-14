# -*- coding: utf-8 -*-

{
    'name': 'Odoo Academia',
    'description': """
        Modulo para gestionar la formación:
        -Cursos
        -Sesiones
        -Asistentes
        """,
    'author': 'Odoo',
    'website': 'https://www.odoo.com',
    'version': '1.0',
    'category': 'Training',
    #depends': ['base',], #en esta parte se coloca otro modulo q se llama contacts
    'depends': ['sale', 'website'], #en esta parte heredo Ventas

    'data': [ 
        'security/academy_security.xml',
        'security/ir.model.access.csv',
        'views/course_views.xml',
        'views/session_views.xml',
        'views/sale_views_inherit.xml',
        'report/session_report_templates.xml',
        'report/report_session.xml',  # Este es el nuevo
        'views/product_views_inherit.xml',
        'wizard/sale_wizard_view.xml',
        'data/academy_demo.xml',
        'views/academy_web_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
