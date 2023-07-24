# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    name2 = fields.Char(string=u'Secondary Name', copy=False, track_visibility=True)
    tax_sale_ok = fields.Boolean(string=u'Sale Tax', copy=False, track_visibility=True)
    tax_purchase_ok = fields.Boolean(string=u'Purchase Tax', copy=False, track_visibility=True)
    cheque_in_ok = fields.Boolean(string=u'Cheque In', copy=False, track_visibility=True)
    cheque_out_ok = fields.Boolean(string=u'Cheque Out', copy=False, track_visibility=True)
    deposit_ok = fields.Boolean(string=u'Deposit', copy=False, track_visibility=True)
    wht_purchase_ok = fields.Boolean(string=u'Purchase WHT', copy=False, track_visibility=True)
    wht_sale_ok = fields.Boolean(string=u'Sale WHT', copy=False, track_visibility=True)
    wait = fields.Boolean(string=u'ภาษีซื้อรอนำส่ง', copy=False, track_visibility=True)

    active = fields.Boolean(
        help="The active field allows you to hide the date range without "
             "removing it.", default=True)


    def active_acc(self):
        self.write({'active':False})


