from odoo import _, models, fields, api
from odoo.exceptions import UserError, ValidationError
import base64
import io
import re
import csv
import xlsxwriter
from openpyxl import load_workbook

class ImportContactWizard(models.TransientModel):
    _name = 'import.contact.wizard'
    _description = 'Import Contact Wizard'

    file = fields.Binary(string="Archivo", required=False)
 
    def action_test(self):
        if not self.file:
            raise UserError(_("Debe subir un archivo XLSX."))

        # Decodificar archivo
        try:
            workbook = load_workbook(io.BytesIO(base64.b64decode(self.file)))
        except Exception:
            raise UserError(_("Error al leer el archivo. Asegúrese de que sea un archivo válido XLSX."))

        sheet = workbook.active
        data = [row for row in sheet.iter_rows(min_row=2, values_only=True)]

        # Validar datos
        errors = self.validate_data(data)
        if errors:
            formatted_errors = "\n".join(f"• {e}" for e in errors)
            raise UserError(_("Errores encontrados en los registros:\n\n") + formatted_errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validación exitosa',
                'message': '¡Todo parece correcto en el archivo!',
                'type': 'success',
                'sticky': False,
            }
        }

    def validate_data(self, data):
        errors = []
        names_seen = set()
        trade_names_seen = set()

        # Cargar datos existentes para validaciones cruzadas
        existing_tags = set(self.env['res.partner.category'].search([]).mapped('name'))
        existing_accounts = set(self.env['account.account'].search([]).mapped('name'))
        existing_terms = set(self.env['account.payment.term'].search([]).mapped('name'))
        existing_pricelists = set(self.env['product.pricelist'].search([]).mapped('name'))

        for i, row in enumerate(data[1:], start=3):  # Saltar encabezado y fila de ejemplo
            if len(row) < 18:
                errors.append(f"Fila {i}: Número de columnas insuficiente (se esperaban 18).")
                continue

            (
                es_empresa_str, es_cliente_str, es_proveedor_str, nombre, nombre_comercial,
                tipo_identificacion, identifier, direccion_completa,
                telefono, movil, correo_electronico,
                sitio_web, etiquetas_str, cuenta_por_cobrar, cuenta_por_pagar,
                terminos_pago, lista_precios, documentos_electronicos_str
            ) = row

            def validar_true_false(value, field_name):
                normalized_value = str(value).strip().lower()
                if normalized_value not in ['true', 'false']:
                    errors.append(
                        f"Fila {i}: The field '{field_name}' must be either True or False (case-insensitive)."
                    )

            validar_true_false(es_empresa_str, 'Es Empresa')
            validar_true_false(es_cliente_str, 'Es Cliente')
            validar_true_false(es_proveedor_str, 'Es Proveedor')
            validar_true_false(documentos_electronicos_str, 'Documentos Electrónicos')

            if not nombre or not str(nombre).strip():
                errors.append(f"Fila {i}: El campo Nombre no debe estar vacío.")
            else:
                name_clean = str(nombre).strip().lower()
                if name_clean in names_seen:
                    errors.append(f"Fila {i}: El nombre '{nombre}' está duplicado en el archivo Excel.")
                else:
                    names_seen.add(name_clean)

            if nombre_comercial and str(nombre_comercial).strip():
                trade_clean = str(nombre_comercial).strip().lower()
                if trade_clean in trade_names_seen:
                    errors.append(f"Fila {i}: El nombre comercial '{nombre_comercial}' está duplicado en el archivo Excel.")
                else:
                    trade_names_seen.add(trade_clean)

            if not tipo_identificacion or tipo_identificacion.strip().upper() not in ['CEDULA', 'RUC', 'PASAPORTE']:
                errors.append(f"Fila {i}: Tipo Identificación debe ser 'CEDULA', 'RUC' o 'PASAPORTE'.")

            if not identifier or not str(identifier).isdigit() or not (10 <= len(str(identifier)) <= 13):
                errors.append(f"Fila {i}: Cédula/RUC/Pasaporte debe ser un número entre 10 y 13 dígitos.")

            if not direccion_completa or not str(direccion_completa).strip():
                errors.append(f"Fila {i}: El campo Dirección completa no debe estar vacío.")

            # Validación de teléfono (obligatorio) - Simplificada
            telefono_str = str(telefono or '').strip()
            if not telefono_str:
                errors.append(f"Fila {i}: El campo Teléfono no debe estar vacío.")
            elif not telefono_str.startswith('+593') and not telefono_str.startswith('09'):
                errors.append(f"Fila {i}: Teléfono inválido. Debe empezar con '+593' o '09'.")
            else:
                # Eliminar espacios y verificar la longitud
                telefono_str = telefono_str.replace(" ", "")
                if not (10 <= len(telefono_str) <= 20):
                    errors.append(f"Fila {i}: El teléfono debe tener entre 10 y 20 caracteres.")

            # Validación de móvil (opcional) - Simplificada
            movil_str = str(movil or '').strip()
            if movil_str:
                if not movil_str.startswith('+593') and not movil_str.startswith('09'):
                    errors.append(f"Fila {i}: Móvil inválido. Debe empezar con '+593' o '09'.")
                else:
                    # Eliminar espacios y verificar la longitud
                    movil_str = movil_str.replace(" ", "")
                    if not (10 <= len(movil_str) <= 20):
                        errors.append(f"Fila {i}: El móvil debe tener entre 10 y 20 caracteres.")

            if not correo_electronico or not str(correo_electronico).strip():
                errors.append(f"Fila {i}: El campo Correo Electrónico no debe estar vacío.")

            # Validación de etiquetas
            if etiquetas_str:
                etiquetas = [e.strip() for e in str(etiquetas_str).split(',') if e.strip()]
                for tag in etiquetas:
                    if tag not in existing_tags:
                        errors.append(f"Fila {i}: La etiqueta '{tag}' no existe en Odoo.")

            # Validar cuenta por cobrar
            cuenta_cobrar_str = str(cuenta_por_cobrar or '').strip()
            if cuenta_cobrar_str and cuenta_cobrar_str not in existing_accounts:
                errors.append(f"Fila {i}: La cuenta por cobrar '{cuenta_cobrar_str}' no existe en Odoo.")

            # Validar cuenta por pagar
            cuenta_pagar_str = str(cuenta_por_pagar or '').strip()
            if cuenta_pagar_str and cuenta_pagar_str not in existing_accounts:
                errors.append(f"Fila {i}: La cuenta por pagar '{cuenta_pagar_str}' no existe en Odoo.")

            # Validar término de pago
            terminos_pago_str = str(terminos_pago or '').strip()
            if terminos_pago_str and terminos_pago_str not in existing_terms:
                errors.append(f"Fila {i}: El término de pago '{terminos_pago_str}' no existe en Odoo.")

            # Validar lista de precios
            lista_precios_str = str(lista_precios or '').strip()
            if lista_precios_str and lista_precios_str not in existing_pricelists:
                errors.append(f"Fila {i}: La lista de precios '{lista_precios_str}' no existe en Odoo.")

        return errors

    def action_export_template(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Formatos
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter',
            'align': 'center', 'border': 1, 'bg_color': '#D9E1F2'
        })
        example_format = workbook.add_format({
            'font_color': '#0070C0',
            'valign': 'vcenter', 'align': 'left', 'border': 1
        })
        header_observations_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter',
            'align': 'center', 'border': 1, 'bg_color': '#4CAF50', 'color': 'white'
        })
        observations_format = workbook.add_format({
            'text_wrap': True, 'valign': 'top', 'align': 'left',
            'border': 1, 'bg_color': '#F9F9F9'
        })

        # Definición de datos - Actualizado (sin Número Identificación ni Apoyo Fiscal)
        headers = [
            'Es Empresa', 'Es Cliente', 'Es Proveedor', 'Nombre', 'Nombre Comercial',
            'Tipo Identificación', 'Cédula/RUC', 'Dirección completa',
            'Teléfono', 'Móvil', 'Correo Electrónico',
            'Sitio Web', 'Etiquetas', 'Cuenta por cobrar', 'Cuenta por pagar',
            'Términos de pago', 'Lista de precios', 'Documentos Electrónicos'
        ]

        example_data = [
            'True', 'True', 'False', 'Empresa Ejemplo S.A.', 'Comercial Ejemplo',
            'CEDULA', '0912345678', 'Pichincha/Quito/Av. Amazonas/Edificio ABC',
            '+59322345678', '+593998765432', 'info@empresa.com', 'https://empresa.com',
            'Importador,Cliente VIP', 'ANTICIPO EMPLEADOS', 'ANTICIPOS DE CLIENTES',
            'Pago inmediato', 'Lista de precios estándar', 'True'
        ]

        observaciones = [
            'Es Empresa: "True" si es una empresa, "False" si es una persona.',
            'Es Cliente: "True" si será cliente, "False" si no.',
            'Es Proveedor: "True" si será proveedor, "False" si no.',
            'Nombre: Obligatorio, nombre principal del contacto o empresa.',
            'Nombre Comercial: Opcional, nombre alternativo si lo tiene.',
            'Tipo Identificación: "CEDULA", "RUC" o "PASAPORTE".',
            'Cédula/RUC: Número entre 10 y 13 dígitos, solo numérico (sin letras ni símbolos).',
            'Dirección completa: Dirección física del contacto o empresa.',
            'Teléfono: Formato internacional, empieza con "+", solo números y espacios, longitud entre 10 y 20 caracteres.',
            'Móvil: Formato internacional, igual que teléfono (comienza con "+", solo números y espacios).',
            'Correo Electrónico: Obligatorio, debe ingresar una dirección válida.',
            'Sitio Web: Opcional, puede ingresar la página web del contacto.',
            'Etiquetas: Opcional, nombres separados por comas (deben existir en el sistema).',
            'Cuenta por cobrar: Nombre exacto de la cuenta contable para clientes.',
            'Cuenta por pagar: Nombre exacto de la cuenta contable para proveedores.',
            'Términos de pago: Nombre exacto del término de pago definido en el sistema.',
            'Lista de precios: Nombre exacto de la lista de precios.',
            'Documentos Electrónicos: "True" si maneja facturación electrónica, "False" si no.'
        ]

        # Hoja 1: Plantilla Contactos
        worksheet = workbook.add_worksheet('Plantilla Contactos')
        worksheet.set_column(0, len(headers) - 1, 25)

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        for col_num, value in enumerate(example_data):
            worksheet.write(1, col_num, value, example_format)

        # Hoja 2: Observaciones
        worksheet2 = workbook.add_worksheet('Observaciones')
        worksheet2.set_column('A:A', 80)

        worksheet2.write('A1', 'Observaciones', header_observations_format)
        for row, obs in enumerate(observaciones, start=1):
            worksheet2.write(row, 0, obs, observations_format)

        # Cerrar
        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_contactos.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'import.contact.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_import(self):
        if not self.file:
            raise UserError("Debe subir un archivo XLSX.")

        file_data = base64.b64decode(self.file)

        try:
            workbook = load_workbook(io.BytesIO(file_data))
        except Exception:
            raise UserError("Error al leer el archivo. Asegúrese de que sea un archivo válido XLSX.")

        sheet = workbook.active
        data = [row for row in sheet.iter_rows(min_row=2, values_only=True)]

        errors = []
        updated_names = []
        contacts_created = 0

        for i, row in enumerate(data[1:], start=3):
            try:
                if len(row) < 18:
                    errors.append(f"Fila {i}: Número de columnas insuficiente.")
                    continue

                (
                    es_empresa_str, es_cliente_str, es_proveedor_str, name, commercial_name,
                    tipo_identificacion, cedula_ruc, direccion_completa,
                    phone, mobile, email,
                    website, tags_str, cuenta_cobrar, cuenta_pagar,
                    termino_pago, lista_precio, documentos_electronicos_str
                ) = row

                tipo_identificacion = str(tipo_identificacion or '').strip().upper()
                cedula_ruc = str(cedula_ruc or '').strip()

                identification_mapping = {
                    'CEDULA': 'cedula',
                    'RUC': 'ruc',
                    'PASAPORTE': 'passport',
                }
                type_identifier = identification_mapping.get(tipo_identificacion)
                if not type_identifier:
                    errors.append(f"Fila {i}: Tipo de Identificación inválido '{tipo_identificacion}'.")
                    continue

                is_company = str(es_empresa_str).strip().lower() == 'true'
                is_customer = str(es_cliente_str).strip().lower() == 'true'
                is_supplier = str(es_proveedor_str).strip().lower() == 'true'
                is_electronic = str(documentos_electronicos_str).strip().lower() == 'true'

                contact_model = self.env['res.partner']
                existing_contact = contact_model.search([
                    ('identifier', '=', cedula_ruc),
                    ('type_identifier', '=', type_identifier),
                ], limit=1)

                country = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
                address_data = self.parse_full_address(direccion_completa, country)

                tag_ids = []
                if tags_str:
                    tag_names = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                    tag_ids = self.env['res.partner.category'].search([('name', 'in', tag_names)]).ids

                payment_term_id = self.env['account.payment.term'].search([('name', 'ilike', termino_pago)], limit=1)
                pricelist_id = self.env['product.pricelist'].search([('name', 'ilike', lista_precio)], limit=1)
                cuenta_cobrar_id = self.env['account.account'].search([('name', 'ilike', cuenta_cobrar or 'ANTICIPO EMPLEADOS')], limit=1)
                cuenta_pagar_id = self.env['account.account'].search([('name', 'ilike', cuenta_pagar or 'ANTICIPOS DE CLIENTES')], limit=1)

                vals = {
                    'name': name,
                    'trade_name': commercial_name,
                    'is_company': is_company,
                    'phone': phone,
                    'mobile': mobile,
                    'email': email,
                    'website': website,
                    'category_id': [(6, 0, tag_ids)] if tag_ids else False,
                    'customer_rank': 1 if is_customer else 0,
                    'supplier_rank': 1 if is_supplier else 0,
                    'identifier': cedula_ruc,
                    'type_identifier': type_identifier,
                    'is_electronic': is_electronic,
                    'street': address_data.get('street', ''),
                    'street2': address_data.get('street2', ''),
                    'city': address_data.get('city', ''),
                    'zip': address_data.get('zip', ''),
                    'state_id': address_data.get('state_id', False),
                    'country_id': address_data.get('country_id', country.id if country else False),
                    'property_payment_term_id': payment_term_id.id if payment_term_id else False,
                    'property_product_pricelist': pricelist_id.id if pricelist_id else False,
                    'property_account_receivable_id': cuenta_cobrar_id.id if cuenta_cobrar_id else False,
                    'property_account_payable_id': cuenta_pagar_id.id if cuenta_pagar_id else False,
                }

                if existing_contact:
                    existing_contact.write(vals)
                    updated_names.append(existing_contact.name)
                else:
                    contact_model.create(vals)
                    contacts_created += 1

            except Exception as e:
                errors.append(f"Fila {i}: Error al crear/modificar contacto: {str(e)}")

        if errors:
            formatted_errors = "\n".join(f"• {e}" for e in errors)
            raise UserError("Errores durante la importación:\n\n" + formatted_errors)

        messages = []
        if contacts_created:
            messages.append(f"Se importaron correctamente {contacts_created} contactos nuevos.")
        if updated_names:
            lista = "\n".join(f"• {n}" for n in updated_names)
            messages.append(f"Se actualizaron {len(updated_names)} contactos existentes:\n{lista}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resultado de importación',
                'message': "\n\n".join(messages) if messages else "No se realizaron cambios.",
                'type': 'success',
                'sticky': False,
            }
        }

    def parse_full_address(self, full_address, country):
        address = {
            'street': '',
            'street2': '',
            'city': '',
            'zip': '',
            'state_id': False,
            'country_id': country.id if country else False
        }

        if full_address and '/' in full_address:
            parts = str(full_address).strip().split('/')

            if len(parts) >= 1:
                state_name = parts[0].strip()
                state = self.env['res.country.state'].search([
                    ('name', 'ilike', state_name),
                    ('country_id', '=', country.id)
                ], limit=1) if country else False
                address['state_id'] = state.id if state else False

            if len(parts) >= 2:
                address['city'] = parts[1].strip()
            if len(parts) >= 3:
                address['street2'] = parts[2].strip()
            if len(parts) >= 4:
                address['street'] = parts[3].strip()

        elif full_address:
            address['street'] = full_address.strip()

        return address
