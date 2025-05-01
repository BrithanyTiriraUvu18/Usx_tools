import logging
from base64 import b64encode

import requests

_logger = logging.getLogger(__name__)

# LINK = "http://190.152.245.250:9005/fxruc/index.php"


# def get_data_partner(ruc, docType):
#     try:
#         args = {"ruc": ruc, "docType": docType}
#         payload = {}
#         # userAndPass = b64encode(b"username:password").decode("ascii")
#         # headers = { 'Authorization' : 'Basic %s' %  userAndPass }
#         headers = {"Authorization": "Basic c2lzZmVuaXg6QGRzNDUwbmI="}

#         response = requests.request(
#             "GET", LINK, headers=headers, data=payload, params=args, timeout=10
#         )
#         result = response.json()

#         return result
#     except Exception as e:
#         _logger.error("An error occurred: %s", e)
#         # print("Error de Conexion")
LINK = "https://solutions.myfenixcloud.com/cif/document/search"


def getToken():
    loginLink = "https://solutions.myfenixcloud.com/cif/login"
    try:
        userAndPass = b64encode(b"odoo:9^c#P4w@5z!8xY7B}QoE").decode("ascii")
        args = {}
        payload = {}
        headers = {"Authorization": "Basic %s" % userAndPass}
        response = requests.request(
            "GET", loginLink, headers=headers, data=payload, params=args, timeout=1
        )
        result = response.json()
        return result["token"]

    except Exception:
        logging.exception("An error occurred in getToken")


def get_data_partner(ruc, docType):
    try:
        args = {}
        payload = {"contract": 0, "document": ruc}
        token = getToken()
        headers = {"Authorization": "Bearer %s" % token}

        response = requests.request(
            "POST", LINK, headers=headers, data=payload, params=args, timeout=10
        )
        result = response.json()

        return result
    except Exception:
        logging.exception("An error occurred in getToken")
        # print("Error de Conexion")
