# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'INECO - Account Asset',
    'version': '0.1',
    'sequence': 1000,
    'description': """    
    """,
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'website': 'https://www.ineco.co.th',
    'summary': 'ระบบสินทรัพย์',
    'images': [],
    'depends': ["account",
                "account_asset",
                "ineco_thai_v11"
                ],
    'data': [
        'views/account_asset_view.xml'
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
