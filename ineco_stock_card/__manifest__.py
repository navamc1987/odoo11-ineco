# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


{
    'name': 'INECO - Account Stock Card',
    'version': '0.1',
    'depends': ["account", "ineco_thai_v11"],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'เพิ่มเติมสต๊อกการ์ดสำหรับบัญชีต้นทุน',
    'description': """
Feature: 
Stock Card
หลังจากติดตั้งให้ เรียก function_profit_loss.sql และ query_stock_transaction_odoo_v11.sql บน pg_admin ด้วย
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        'security.xml',
        'views/stock_card_view.xml',
        # 'views/account_account_view.xml',
        'wizard/wizard_recompute_stock_card_view.xml',
        'views/account_invoice_view.xml',
        'views/product_product_view.xml',
    ],
    'update_xml': [
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
