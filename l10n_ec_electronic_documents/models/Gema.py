import base64
import html
import xml.etree.ElementTree as ET

import requests

from odoo import _, exceptions

from . import urls


class GemaApi:

    # OBTENCION TOKEN
    def get_token(self, user, password):
        full_url = urls.domain + urls.URL_TOKEN
        auth = (user, password)
        try:
            response = requests.get(full_url, auth=auth, timeout=5)
            if response.status_code == 200:
                try:
                    results = response.json()
                    token = results.get("token")
                    return token
                except KeyError:
                    self.env.user.notify_danger(
                        message=_(
                            "Token no encontrado en la respuesta JSON: "
                            "%(response_text)s"
                        )
                        % {"response_text": response.text}
                    )
            else:
                raise Exception("Error de autenticación con Gema")

        except Exception as e:
            raise e

    # ENVIO AL SRI
    def send_sri(self, invoice, token, payload):
        if invoice.env.user.company_id.env_service == "1":
            full_url = urls.domain + urls.URL_SRI
        else:
            full_url = urls.domain + urls.URL_SRI + "?env=prod"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                full_url, json=payload, headers=headers, timeout=50
            )
            results = response.json()
            return results

        except Exception as e:
            raise e

    # OBTENER EL XML
    def get_xml_base64(self, invoice, access_key, token):
        if invoice.env.user.company_id.env_service == "1":
            full_url = urls.domain + urls.URL_XML + access_key
        else:
            full_url = urls.domain + urls.URL_XML + access_key + "?env=prod"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(full_url, headers=headers, timeout=10)

            if response.status_code == 200:
                results = response.json()
                data = results.get("data")
                xml_base64 = data.get("xml")
                return xml_base64
            elif response.status_code == 503:
                raise exceptions.UserError(
                    _("Servicio del SRI no disponible, vuelva a intentarlo más tarde")
                )
            else:
                raise exceptions.UserError(_("No se pudo obtener el xml"))

        except Exception as e:
            raise Exception(e)

    # OBTENER EL RIDE
    def get_ride(self, invoice, xml, token):
        full_url = urls.domain + urls.URL_RIDE
        logo_base64 = invoice.company_id.logo.decode("utf-8")
        xml = self.add_additional_fields(xml, invoice)
        ride_options = self.generate_ride_options(invoice)
        payload = {
            "logo64": logo_base64,
            "xml64": xml,
            "rideOptions": ride_options,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                full_url, json=payload, headers=headers, timeout=15
            )

            if response.status_code == 200:
                results = response.json()
                ride_base64 = results.get("pdfB64")
                return ride_base64
            if response.status_code == 400:
                results = response.json()
                raise Exception("Error al crear el ride: " + results.get("message"))
            else:
                raise exceptions.UserError(_("No se pudo crear el Ride"))
        except Exception as e:
            raise Exception(e)

    def add_additional_fields(self, xml, invoice):
        decoded_data = base64.b64decode(xml)
        xml_data = decoded_data.decode("utf-8")
        root = ET.fromstring(xml_data)
        tributary_info = root.find(".//infoTributaria")
        company = invoice.company_id.partner_id
        if company.phone or company.mobile:
            phone_field = ET.Element("telefono")
            phone_field.text = (
                (company.phone + " ")
                if company.phone
                else "" + company.mobile
                if company.mobile
                else ""
            )
            tributary_info.append(phone_field)
        if company.website:
            web_page = ET.Element("paginaweb")
            web_page.text = company.website
            tributary_info.append(web_page)
        customer_info = ET.Element("infoCliente")
        customer = invoice.partner_id
        if customer.city:
            customer_city = ET.Element("ciudad")
            customer_city.text = customer.city
            customer_info.append(customer_city)
        if customer.phone or customer.mobile:
            customer_phone = ET.Element("telefono")
            customer_phone.text = (
                (customer.phone + " ")
                if customer.phone
                else "" + customer.mobile
                if customer.mobile
                else ""
            )
            customer_info.append(customer_phone)
        if customer.email:
            customer_email = ET.Element("email")
            customer_email.text = customer.email
            customer_info.append(customer_email)
        tributary_info.append(customer_info)
        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        xml_str = xml_bytes.decode("utf-8")
        xml_str = xml_str.replace("ns0:", "ns2:").replace("xmlns:ns0", "xmlns:ns2")
        xml_bytes_final = xml_str.encode("utf-8")
        base64_encoded = base64.b64encode(xml_bytes_final).decode("utf-8")
        return base64_encoded

    def generate_ride_options(self, invoice):
        result = {"disableAuxiliarCode": True}
        company = invoice.company_id
        if company.ride_footer_param:
            result["footer"] = html.unescape(company.ride_footer_param)
        if company.ride_main_color_param:
            result["mainColor"] = company.ride_main_color_param
        if company.ride_disable_payment_timeout_param:
            result["disablePaymentTimeout"] = company.ride_disable_payment_timeout_param
        return result
