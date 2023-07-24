# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import UserError


class InecoBillingVender(models.Model):
    _name = 'ineco.billing.vender'
    _description = 'Billing Vender'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    @api.depends('invoice_ids', 'customer_id')
    def _get_amount(self):
        for i in self:
            out_invoice = 0.00
            out_refund = 0.00
            for invoice in i.invoice_ids:
                out_invoice += invoice.amount_total_signed
            for invoice in i.refund_ids:
                out_refund -= abs(invoice.amount_total_signed)
            i.amount_residual = out_invoice
            i.amount_refund = out_refund
            i.amount_billing = out_invoice + out_refund

    name = fields.Char(string='เลขที่ใบวางบิล', size=32, required=True, copy=False, track_visibility='onchange',
                       default='New')
    to_date = fields.Date(u'จากวันที่', default=fields.Date.context_today, track_visibility='onchange')
    from_date = fields.Date(u'ถึงวันที่', default=fields.Date.context_today, track_visibility='onchange')

    date = fields.Date(string='ลงวันที่', required=True, default=fields.Date.context_today, track_visibility='onchange')
    date_due = fields.Date(string='กำหนดชำระ', track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', string='ลูกค้า', required=True, track_visibility='onchange')
    note = fields.Text(string='หมายเหตุ', track_visibility='onchange')
    state = fields.Selection([('draft', 'ร่าง'),
                              ('post_iv', u'ดึงข้อมูล'),
                              ('post', 'Posted'),
                              ('register_pay', u'ขึ้นเตรียมจ่าย'),
                              ('cancel', u'ยกเลิก')],
                             string=u'State', default='draft')

    invoice_ids = fields.One2many('account.invoice', 'billing_verder_id', string='ใบแจ้งหนี้/ใบกำกับภาษี')
    refund_ids = fields.One2many('account.invoice', 'billing_verder_id_refund', string='ใบลดหนี้')

    amount_residual = fields.Float(compute='_get_amount', string='ยอดหนี้คงค้าง', digits=(12, 2))
    amount_refund = fields.Float(compute='_get_amount', string='ยอดลดหนี้', digits=(12, 2))
    amount_billing = fields.Float(compute='_get_amount', string='รวมเป็นเงิน', digits=(12, 2))
    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม')
    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                                                  'initial demand. When the picking is done this allows '
                                                  'changing the done quantities.')
    pay_id = fields.Many2one('ineco.supplier.payment', string=u'การทำจ่าย')
    pay_state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', related='pay_id.state', readonly=True)

    _sql_constraints = [
        ('name', 'unique( name )', 'เลขที่วางบิลห้ามซ้ำ.')
    ]


    def button_cancel(self):
        if self.state == 'draft':
            self.cancel_all()
            self.write({'state':'cancel'})


    def cancel_all(self):
        for iv in self.invoice_ids:
            iv.billing_verder_id = False
        for rf in self.refund_ids:
            rf.billing_verder_id_refund = False

    @api.one
    def set_draft(self):
        if self.pay_id:
            if self.pay_id.state != 'draft':
                raise UserError("ต้องยกเลิการจ่ายก่อน และต้องอยู่ สถานะ Draft ")
            # self.pay_id.button_cancel()
            # self.pay_id.button_draft()
            if self.pay_id.state == 'draft':
                ql_supplier_line_ids = """
                        DELETE FROM ineco_supplier_payment
                       where id  = %s

                        """ % (self.pay_id.id)
                self._cr.execute(ql_supplier_line_ids)
                self.write({'state': 'draft'})
        else:
            self.write({'state': 'draft'})


    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    @api.multi
    def button_post_iv(self):
        iv = self.env['account.invoice'].search([
            ('partner_id', '=', self.customer_id.id),
            ('state', '=', 'open'),
            ('billing_verder_id','=',False),
            ('type', '=', 'in_invoice'),
            # ('type_vat', '=', self.type_vat),
            ('button_billing_vender_date', '>=', self.to_date),
            ('button_billing_vender_date', '<=', self.from_date),

        ])
        # print(iv)
        for line in iv:
            line.write({'billing_verder_id': self.id,
                        })
        refund = self.env['account.invoice'].search([
            ('partner_id', '=', self.customer_id.id),
            ('type', '=', 'in_refund'),
            ('billing_verder_id_refund', '=', False),
            ('state', '=', 'open'),
            # ('type_vat', '=', self.type_vat),
            ('button_billing_vender_date', '>=', self.to_date),
            ('button_billing_vender_date', '<=', self.from_date),
        ])
        for line in refund:
            line.write({'billing_verder_id_refund': self.id,
                        })

        out_invoice = 0.00
        out_refund = 0.00
        self.amount_billing = 0.0
        for invoice in self.invoice_ids:
            out_invoice += invoice.residual
        for invoice in self.refund_ids:
            out_refund += abs(invoice.residual)
        self.amount_residual = out_invoice
        self.amount_refund = out_refund
        self.amount_billing = out_invoice - out_refund
        self.write({'state': 'post_iv', 'amount_billing': out_invoice - out_refund})

    @api.multi
    def button_post(self):
        if self.name == 'New':
            self.name = self.env['ir.sequence'].next_by_code('ineco.vendor.billing')
            # if self.type_vat == 'a':
            #     self.name = self.env['ir.sequence'].next_by_code('ineco.vendor.billing')
            # if self.type_vat == 'b':
            #     self.name = self.env['ir.sequence'].next_by_code('ineco.vendor.billing2')
        self.write({'state': 'post'})

    @api.multi
    def register_pay(self):
        if self.state != 'register_pay':
            payment = self.env['ineco.supplier.payment']
            journal = self.env['account.journal'].search([('type', '=', 'pay')], limit=1)
            pml = []
            data = {
                'partner_id': self.customer_id.id,
                'journal_id': journal.id,
                'date_due': self.date_due,
                'line_ids': []
            }

            for iv in self.invoice_ids:
                line_data_vals = {
                    # 'payment_id': payment_id.id,
                    'name': iv.id,
                    'amount_total': iv.amount_total,
                    'amount_residual': iv.residual,
                    'amount_receipt': iv.amount_total
                }
                pml.append((0, 0, line_data_vals))

            for refund in self.refund_ids:
                line_data_vals = {
                    # 'payment_id': refund.id,
                    'name': refund.id,
                    'amount_total': refund.amount_total_signed,
                    'amount_residual': refund.amount_total_signed,
                    'amount_receipt': refund.amount_total_signed
                }
                pml.append((0, 0, line_data_vals))
            payment_id = payment.create(data)

            payment_id.sudo().write({'line_ids': pml})
            self.state = 'register_pay'
            self.pay_id = payment_id.id

            view_ref = self.env['ir.model.data'].get_object_reference('ineco_thai_v11',
                                                                      'view_ineco_supplier_payment_form')
            view_id = view_ref and view_ref[1] or False,
            return {
                'type': 'ir.actions.act_window',
                'name': 'ineco.supplier.payment',
                'res_model': 'ineco.supplier.payment',
                'res_id': payment_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'current',
                'nodestroy': True,
            }


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    billing_verder_id = fields.Many2one('ineco.billing.vender', string=u'ใบรับวางบิล', copy=False)
    billing_verder_id_refund = fields.Many2one('ineco.billing.vender', string=u'ใบรับวางบิลลดหนี้', copy=False)

    taxes_id = fields.Many2one('account.tax', string='Taxes',
                               domain=['|', ('active', '=', False), ('active', '=', True)])

    sequence_billing_verder = fields.Integer(string='Sequence', default=10)
    sequence_billing_verder_ref = fields.Integer('No.', compute="_sequence_billing_verder_ref", store=False)

    sequence_billing_refund_verder_ref = fields.Integer('No.', compute="_sequence_billing_refund_verder_ref",
                                                        store=False)

    def cancel_billing_vender(self):
        if self.billing_verder_id:
            self.billing_verder_id = False
        if self.billing_verder_id_refund:
            self.billing_verder_id_refund = False

    @api.depends('billing_verder_id.invoice_ids')
    def _sequence_billing_verder_ref(self):
        for line in self:
            no = 0
            for l in line.billing_verder_id.invoice_ids:
                no += 1
                l.sequence_billing_verder_ref = no

    @api.depends('billing_verder_id_refund.refund_ids')
    def _sequence_billing_refund_verder_ref(self):
        for line in self:
            no = 0
            for l in line.billing_verder_id_refund.refund_ids:
                no += 1
                l.sequence_billing_refund_verder_ref = no

    # @api.onchange('taxes_id')
    def action_invoice_not_iv(self):
        taxes_obj = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('tax_break', '=', True)
        ])
        for ail in self.invoice_line_ids:
            self.taxes_id = taxes_obj.id
            ail.invoice_line_tax_ids = taxes_obj
        return
