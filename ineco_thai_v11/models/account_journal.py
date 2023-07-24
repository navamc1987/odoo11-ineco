# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('receive', 'Receivable'), #New
            ('pay', 'Payable'), #New
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.")
    type_vat = fields.Selection([('a', u'VAT'), ('b', u'NO'),],string=u'ประะเภทกิจกรรม')
    input_tax = fields.Boolean(u'กลับภาษี')
    name2 = fields.Char(u'ชื่อสำรอง')
    name_print = fields.Char(u'ชื่อใบสำคัญ')
    gl_Description = fields.Char(u'คำอธิบายรายการ',size=15,)
    description = fields.Text(u'คำอธิบายรายการ', size=50)
    foreign = fields.Boolean(u'ต่างประเทศ')
    ex = fields.Boolean(u'ขายตัวอย่าง')
    expense = fields.Boolean(u'บันทึกค่าใช้จ่าย')

    is_deposit = fields.Boolean(u'มัดจำ')

