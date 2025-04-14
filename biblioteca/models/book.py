#-*- coding: utf-8 -*-  
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Book(models.Model):
    _name = 'library.book'
    _description = 'Libro de la Biblioteca'

    name = fields.Char(string='Título', required=True)
    author = fields.Char(string='Autor')
    isbn = fields.Char(string='ISBN', required=True)
    publication_date = fields.Date(string='Fecha de Publicación')
    pages = fields.Integer(string='Número de Páginas')
    publisher = fields.Char(string='Editorial')
    available = fields.Boolean(string='Disponible', default=True)

    #en esta parte se valida el isbn a que no permite el usuario editar a mas de 13 caracteres
    @api.onchange('isbn')
    def _onchange_isbn_length(self):
        if self.isbn and len(self.isbn) != 13:
            raise ValidationError("El ISBN debe tener exactamente 13 caracteres.")
