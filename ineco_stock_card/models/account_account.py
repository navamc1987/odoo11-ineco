# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'
    _description = 'Finish Goods Account'

    inventory_ok = fields.Boolean(string='Goods Valuations', default=False)
