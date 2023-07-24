# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    tax_break = fields.Boolean(string=u'ภาษีพัก', default=False)
