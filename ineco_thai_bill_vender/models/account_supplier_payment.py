# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError



class InecoSupplierPaymentOther(models.Model):
    _inherit = 'ineco.supplier.payment.other'

    billing_id = fields.Many2one('ineco.billing.vender', string=u'รับวางบิล')


