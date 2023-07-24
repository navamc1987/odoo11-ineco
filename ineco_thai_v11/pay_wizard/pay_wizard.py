# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class PayWizard(models.TransientModel):
    _name = "pay.wizard"

    item_ids = fields.One2many('pay.wizard.line', 'order_id', string='Order Lines')
    customer_id = fields.Many2one('res.partner', string='ลูกค้า', required=True, readonly=True ,track_visibility='onchange')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       track_visibility='onchange')
    date_due = fields.Date(string=u'วันที่รับเงิน', required=True, track_visibility='onchange')

    @api.model
    def default_get(self, fields):
        res = super(PayWizard, self).default_get(fields)
        ineco_billing_obj = self.env['ineco.billing']
        line_ids = self.env.context.get('active_ids', False)
        billing = ineco_billing_obj.browse(line_ids)
        items = []
        for iv in billing.invoice_ids:
            if iv.amount_total_signed != 0.0 and iv.select_pay:
                line_data_vals = {
                    'name': iv.id,
                    'date_invoice': iv.date_invoice,
                    'amount_total': iv.amount_total_signed,
                    'amount_residual': iv.residual_signed,
                    'amount_receipt': iv.residual_signed,
                }
                items.append([0, 0, line_data_vals])

        for refund in billing.refund_ids:
            if refund.amount_total_signed != 0.0 and refund.select_pay:
                line_data_vals = {
                    'name': refund.id,
                    'date_invoice': refund.date_invoice,
                    'amount_total': refund.amount_total_signed,
                    'amount_residual': refund.residual_signed,
                    'amount_receipt': refund.residual_signed,
                }
                items.append([0, 0, line_data_vals])

        res['customer_id'] = billing.customer_id.id
        res['item_ids'] = items
        return res

    @api.multi
    def action_create_cus_pay(self):
        payment = self.env['ineco.customer.payment']
        journal = self.env['account.journal'].search([('type', '=', 'receive')],limit=1)
        pml = []
        data = {
            'customer_id': self.customer_id.id,
            'date_due': self.date_due,
            'date':self.date,
            'journal_id': journal.id,
            'line_ids': []
        }
        for iv in self.item_ids:
            line_data_vals = {
                # 'payment_id': payment_id.id,
                'name': iv.name.id,
                'amount_total': iv.name.amount_total_signed,
                'amount_residual': iv.name.residual_signed,
                'amount_receipt': iv.amount_receipt
            }
            pml.append((0, 0, line_data_vals))
        payment_id = payment.create(data)
        payment_id.write({'line_ids': pml})
        view_ref = self.env['ir.model.data'].get_object_reference('ineco_thai_v11', 'view_ineco_customer_payment_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.customer.payment.form',
            'res_model': 'ineco.customer.payment',
            'res_id': payment_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }


class PayWizardLine(models.TransientModel):
    _name = 'pay.wizard.line'

    order_id = fields.Many2one('pay.wizard', string='pay', ondelete='cascade')
    name = fields.Many2one('account.invoice', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    date_invoice = fields.Date(string=u'ลงวันที่',)
    amount_total = fields.Float(string=u'ยอดตามบิล', )
    amount_residual = fields.Float(string=u'ยอดค้างชำระ',)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')