# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'INECO - Debit Notes',
    'version': '1.0',
    'depends': ["account", "account_invoicing", "account_cancel", "ineco_thai_v11", "base"],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'เพิ่มเติมใบเพิ่มหนี้ลูกหนี้',
    'description': """
Feature: 
Thai Accounting on Odoo 11
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        'wizard/sale_make_deposit_view.xml',
        'wizard_sell_cash/sell_cash_view.xml',
        'views/account_invoice_view.xml',
        'views/customer_debit_notes.xml',
        'views/vender_debit_notes.xml',
        'views/vender_credit_notes_view.xml'

    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}
