# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved
{
    'name': "INECO - Vendor Bill",
    'description': """
    """,
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'เพิ่มเติมใบวางบิลผู้จำหน่าย',
    'website': "https://www.ineco.co.th",
    'version': '0.1',
    'depends': ['base', 'account', 'account_cancel', 'ineco_thai_v11'],
    'data': [

        'security/purchase.xml',
        'view/account_billing_view.xml',
        'view/ineco_vender_bill_view.xml'

    ],
    'demo': [
    ],
}
