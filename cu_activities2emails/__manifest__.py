# -*- coding: utf-8 -*-
# 22/02/2023 - Çağatay Üresin

{
    "name": "CU Activities 2 Emails",
    "version": "15.1",
    "category": "Custom",
    "sequence": -2,
    "summary": "New activities created are sent to emails as invitations.",
    "description": "In this way, your email provider's calendar is synchronized with your Odoo calendar in terms of "
    "activities.",
    "website": "https://cagatayuresin.com",
    "maintainer": "Çağatay ÜRESİN - <cagatayuresin@gmail.com>",
    "depends": [
        "base",
        "mail"
    ],
    "data": [
        # "security/ir.model.access.csv",
        "data/cu_activities2emails_cron.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "license": "OPL-1",
}
