# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


{
    'name': 'INECO - Export WHT',
    'version': '0.1',
    'depends': ["base",
                "ineco_thai_v11"
                ],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
'summary': 'เพิ่มเติมส่งออกข้อมูลหัก ณ ที่จ่ายนำส่งสรรพากร',
    'description': """
Feature: 
1. Export PND3 & 53
    """,
    'website': 'https://www.ineco.co.th',
    'data': [
    ],
    'update_xml': [
        'wizard_export_wht_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': [],
}
