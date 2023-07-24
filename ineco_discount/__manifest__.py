# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


{
    'name': 'INECO - Discount',
    'version': '0.1',
    'depends': ["base",
                "account",
                "purchase",
                "ineco_thai_v11"
                ],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'เพิ่มเติมระบบส่วนลด',
    'description': """
Feature: 
1. Multiple Discount Customer Invoice, Customer Refund
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
    ],
    'update_xml': [
        'views/invoice_view.xml',
        'views/purchase_views.xml',
        'views/sale_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': [],
}
