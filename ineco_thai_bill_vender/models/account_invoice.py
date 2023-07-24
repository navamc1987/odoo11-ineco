# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


from odoo import api, exceptions, fields, models, _
from datetime import datetime

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

import logging


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    button_billing_vender_date = fields.Date(string=u'วันที่วางบิล')
    # billing_verder_id = fields.Many2one('ineco.billing.vender', string=u'ใบiy[วางบิล', copy=False)

    def action_button_billing_vender(self):
        self.button_billing_vender_date = fields.Date.context_today(self)

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        if not self.button_billing_vender_date:
            self.action_button_billing_vender()
        return res




