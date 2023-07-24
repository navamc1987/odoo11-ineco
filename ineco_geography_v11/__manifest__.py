# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

{
    'name': 'INECO - Geography',
    'version': '1.0',
    'depends': ["base", "mail", "contacts"],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'เพิ่มเติมโครงสร้างตำบล อำเภอ จังหวัด รหัสไปรษณีย์',
    'description': """
Feature: 
Thailand Geography
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        'views/partner_view.xml',
        # 'data/province_data.xml',
        # 'data/amphur_data.xml',
        # 'data/district_data.xml',
        # 'data/zipcode_data.xml',
        'security/security.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
