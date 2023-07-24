# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models


class InecoBilling(models.Model):

    @api.multi
    @api.depends('name','date','date_due','customer_id')
    def _get_amount(self):
        out_invoice = 0.00
        out_refund = 0.00
        for invoice in self.invoice_ids:
            out_invoice += invoice.residual
        for invoice in self.refund_ids:
            out_refund -= invoice.residual
        self.amount_residual = out_invoice
        self.amount_refund = out_refund
        self.amount_billing = out_invoice + out_refund

    _name = 'ineco.billing'
    _description = 'Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม')
    name = fields.Char(string='เลขที่ใบวางบิล', size=32, copy=False, track_visibility='onchange')
    date = fields.Date(string='ลงวันที่', required=True, default=fields.Date.context_today, track_visibility='onchange')
    date_due = fields.Date(string='กำหนดชำระ', required=True, track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', string='ลูกค้า', required=True, track_visibility='onchange')
    note = fields.Text(string='หมายเหตุ', track_visibility='onchange')
    invoice_ids = fields.Many2many('account.invoice', 'billing_invoice_rel', 'billing_id', 'invoice_id',
                                    string='ใบแจ้งหนี้/ใบกำกับภาษี')
    refund_ids = fields.Many2many('account.invoice', 'billing_invoice_refund_rel', 'billing_id', 'invoice_id',
                                   string='ใบลดหนี้')
    amount_residual = fields.Float(compute='_get_amount', string='ยอดหนี้คงค้าง', digits=(12, 2),store=True)
    amount_refund = fields.Float(compute='_get_amount', string='ยอดลดหนี้', digits=(12, 2) ,store=True)
    amount_billing = fields.Float(compute='_get_amount', string='รวมเป็นเงิน', digits=(12, 2), store=True)
    change_number = fields.Boolean(string='เปลี่ยนเลขใบวางบิล',)

    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('done', 'Done')],
                             string=u'State', default='draft')

    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                                                  'initial demand. When the picking is done this allows '
                                                  'changing the done quantities.')
    payment = fields.Many2one ('ineco.customer.payment',string=u'เลขรับชำระ')

    @api.multi
    def Select_all_pay(self):
        for iv in self.invoice_ids:
            iv.SelectPay()
        for refund in self.refund_ids:
            refund.SelectPay()



    @api.multi
    def UpDateDone(self):
        self._get_amount()
        if self.amount_residual == 0.0:
            self.write({'state':'done'})




    @api.onchange('type_vat','customer_id')
    def onchange_type_vat(self):
        self.invoice_ids = False
        self.refund_ids = False


    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    _sql_constraints = [
        ('name', 'unique( name )', 'เลขที่วางบิลห้ามซ้ำ.')
    ]

    @api.multi
    def updateInvoice(self):
        # print ('Do Update Billing')
        for billing in self:
            for invoice in billing.invoice_ids:
                #print(invoice.id)
                update_sql = """  
                    update account_invoice
                    set billing_id = %s
                    where id = %s and type = 'out_invoice'
                """ % (billing.id, invoice.id)
                self._cr.execute(update_sql)
            for refund in billing.refund_ids:
                update_sql = """  
                    update account_invoice
                    set billing_id = %s
                    where id = %s and type = 'out_refund'
                """ % (billing.id, refund.id)
                self._cr.execute(update_sql)

    @api.multi
    def clearInvoice(self):
        for billing in self:
            sql = """
                update account_invoice
                set billing_id = null
                where billing_id = %s
            """ % (billing.id)
            self._cr.execute(sql)

    @api.multi
    def write(self, vals):
        self.clearInvoice()
        res = super(InecoBilling, self).write(vals)
        self.updateInvoice()
        return res


    @api.multi
    def action_post(self):
        if self.name == False:
            self.name = self.env['ir.sequence'].next_by_code('ineco.billing')
        self.write({'state':'post'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_create_cus_pay(self):
        payment = self.env['ineco.customer.payment']
        journal = self.env['account.journal'].search([('type', '=', 'receive'),('type_vat','=',self.type_vat)], limit=1)
        pml = []
        data = {
            'customer_id': self.customer_id.id,
            'date_due': self.date_due,
            'journal_id': journal.id,
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
                'amount_total': iv.amount_total,
                'amount_residual': iv.residual,
                'amount_receipt': iv.amount_total
            }
            pml.append((0, 0, line_data_vals))
        payment_id = payment.create(data)
        payment_id.sudo().write({'line_ids': pml})
        self.write({'state':'done','payment':payment_id.id})
        return payment_id



    @api.model
    def create(self, vals):
        # vals['name'] = self.env['ir.sequence'].next_by_code('ineco.billing')
        bill_id = super(InecoBilling, self.with_context(mail_create_nosubscribe=True)).create(vals)
        bill_id.updateInvoice()
        return bill_id

