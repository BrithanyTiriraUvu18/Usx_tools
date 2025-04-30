{
    "name": "Ecuador Identification Number",
    "summary": """
    Module to validate and autocomplete fields based on the cedula or ruc
    """,
    "version": "17.0.1.0.0",
    "development_status": "Alpha",
    "category": "Accounting",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "author": "Hernan Espinoza, Joseph Armas / Ads Software",
    "maintainers": ["jhespinoza26"],
    "license": "OPL-1",
    "application": False,
    "installable": True,
    "depends": ["base", "l10n_latam_base"],
    "external_dependencies": {"python": ["stdnum"]},
    "data": [
        "data/partner.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings.xml",
    ],
}
