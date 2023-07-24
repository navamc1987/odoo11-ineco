# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    cn_type = fields.Selection([('1', u'ปริมาณ'), ('2', u'มูลค่า')], string=u'ผลกระทบต้นทุน', default='1')
