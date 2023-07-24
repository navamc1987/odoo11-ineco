# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime


class WizardSellCash(models.TransientModel):
    _name = "wizard.sell.cash"
    # _description = "Make deposit by Sales"
    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม')


    @api.multi
    def create_pay(self):
        active_id = self._context.get('active_id', False)
        invoice_obj = self.env['account.invoice']
        iv = invoice_obj.search([('id', '=', active_id)])
        billing = self.env['ineco.billing']
        billing_id = billing.create({
            'type_vat': self.type_vat,
            'customer_id': iv.partner_id.id,
            'date_due': datetime.now(),
            'date':datetime.now(),
            'invoice_ids':[(6, 0, [iv.id])]
        })
        billing_id.action_post()
        pay_id = billing_id.action_create_cus_pay()
        view_ref = self.env['ir.model.data'].get_object_reference('ineco_thai_v11', 'view_ineco_customer_payment_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.customer.payment.form',
            'res_model': 'ineco.customer.payment',
            'res_id': pay_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,

        }
