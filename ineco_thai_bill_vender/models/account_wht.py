# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
import bahttext
import unicodecsv as csv
from io import BytesIO
import base64

class InecoWht(models.Model):
    _inherit = 'ineco.wht'

    billing_id = fields.Many2one('ineco.billing.vender', string=u'รับวางบิล')



