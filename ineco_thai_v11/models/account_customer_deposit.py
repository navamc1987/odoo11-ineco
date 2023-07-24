# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import UserError


class InecoCustomerDeposit(models.Model):

    _name = 'ineco.customer.deposit'
    _description = 'Customer Deposit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    @api.multi
    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            receipt.amount_receipt = 0.0
            receipt.amount_deposit = 0.0
            for line in receipt.line_ids:
                untaxed = 0.0
                tax = 0.0
                if receipt.tax_type == 'percent':
                    tax = line.amount_untaxed * receipt.amount_type_tax / 100
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed + tax
                else:
                    tax = line.amount_untaxed - (line.amount_untaxed * 100) / (100 + receipt.amount_type_tax)
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed - tax
                receipt.amount_receipt += round(line.amount_receipt, 2)
                receipt.amount_deposit += round(line.amount_untaxed, 2)

    @api.multi
    @api.depends('wht_ids')
    def _get_wht(self):
        for receipt in self:
            receipt.amount_wht = 0.0
            for wht in receipt.wht_ids:
                receipt.amount_wht += wht.tax

    @api.multi
    @api.depends('cheque_ids')
    def _get_cheque(self):
        for receipt in self:
            receipt.amount_cheque = 0.0
            for cheque in receipt.cheque_ids:
                receipt.amount_cheque += cheque.amount

    @api.multi
    @api.depends('vat_ids')
    def _get_vat(self):
        for receipt in self:
            receipt.amount_vat = 0.0
            for vat in receipt.vat_ids:
                receipt.amount_vat += vat.amount_tax

    @api.multi
    @api.depends('other_ids')
    def _get_other(self):
        for receipt in self:
            receipt.amount_other = 0.0
            for vat in receipt.other_ids:
                receipt.amount_other += vat.amount

    @api.multi
    @api.depends('amount_deposit')
    def _get_payment(self):
        for receipt in self:
            receipt.amount_residual = receipt.amount_deposit
            receipt_total = 0.0
            if receipt.payment_ids:
                for payment in receipt.payment_ids:
                    if payment.invoice_id and payment.invoice_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
                    if payment.payment_id and payment.payment_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
            receipt.amount_residual = receipt.amount_deposit - receipt_total

    name = fields.Char(string=u'เลขที่ใบมัดจำ', size=32, required=True, copy=False, track_visibility='onchange',
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today, track_visibility='onchange')
    date_due = fields.Date(string=u'วันที่นัดรับเงิน', required=True, track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', string=u'ลูกค้า', required=True, track_visibility='onchange')
    note = fields.Text(string=u'หมายเหตุ', track_visibility='onchange')
    line_ids = fields.One2many('ineco.customer.deposit.line', 'payment_id', string=u'รายการรับชำระ')
    other_ids = fields.One2many('ineco.customer.deposit.other', 'payment_id', string=u'อื่นๆ')
    amount_receipt = fields.Float(string=u'ยอดรับชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขใบเสร็จ',)
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันรับ', required=True,track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft',track_visibility='onchange')
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', track_visibility='onchange', compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยรับ', track_visibility='onchange', copy=False)
    amount_cash = fields.Float(string=u'เงินสด', track_visibility='onchange', copy=False)
    amount_cheque = fields.Float(string=u'เช็ครับ', track_visibility='onchange', compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', track_visibility='onchange', compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดเงินสด', track_visibility='onchange', copy=False)
    amount_paid = fields.Float(string=u'ยอดรับชำระ', track_visibility='onchange', copy=False)
    amount_other = fields.Float(string=u'อื่นๆ', track_visibility='onchange', compute='_get_other', copy=False)
    cheque_ids = fields.One2many('ineco.cheque', 'customer_deposit_id', string=u'เช็ครับ')
    vat_ids = fields.One2many('ineco.account.vat', 'customer_deposit_id', string=u'ภาษีขาย')
    wht_ids = fields.One2many('ineco.wht', 'customer_deposit_id', string=u'ภาษีหัก ณ ที่จ่าย')
    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True)
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', compute='_get_payment' ) #store=True
    payment_ids = fields.One2many('ineco.customer.payment.deposit', 'name', string=u'ตัดมัดจำ')
    sale_order_id = fields.Many2one('sale.order', string='Sale Orders')
    tax_type = fields.Selection(default='percent', string="ประเภทภาษี", required=True,
                                   selection=[('percent', 'ภาษีแยก'),
                                              ('included', u'ภาษีรวม')])
    amount_type_tax = fields.Float(required=True, digits=(16, 0),default=7)
    amount_deposit = fields.Float(string=u'ยอดรวมมัดจำ', compute='_get_receipts')
    journal_name = fields.Char(u'เปลี่ยนเลขเล่มเอกสาร',track_visibility='onchange')

    @api.multi
    def write(self, vals):
        res = super(InecoCustomerDeposit, self).write(vals)
        for line in self.line_ids:
            # line.test()
            amount = line.amount_untaxed

            ineco_account_vat_obj = self.env['ineco.account.vat']
            # print(self.line_ids)
            vat_data = {
                'customer_deposit_id': self.id,
                'customer_deposit_line_id':line.id,
                'name': self.name,
                'docdat': self.date,
                'partner_id': self.customer_id.id,
                'taxid': self.customer_id.vat or '',
                'depcod': self.customer_id.branch_no or '',
                'amount_untaxed': amount

            }
            ineco_account = self.env['ineco.account.vat'].search([
                ('customer_deposit_line_id', '=', line.id),
                ])

            if not ineco_account:

                if self.tax_type == 'percent':
                    vat_data['amount_untaxed'] = amount
                    vat_data['amount_tax'] = amount * self.amount_type_tax / 100
                    ineco_account_vat_obj.create(vat_data)

                else:
                    vat_data['amount_untaxed'] = (amount * 100) / (100 + self.amount_type_tax)
                    vat_data['amount_tax'] = amount - (amount * 100) / (100 + self.amount_type_tax)
                    ineco_account_vat_obj.create(vat_data)

            ineco_update = self.env['ineco.account.vat'].search([
                ('customer_deposit_line_id', '=', line.id),
                ('amount_untaxed', '!=', amount), ])

            if ineco_update:
                if self.tax_type == 'percent':
                    ineco_update.write({'amount_untaxed': amount})
                    ineco_update.write({'amount_tax':  amount * self.amount_type_tax / 100})
                else:
                    ineco_update.write({'amount_untaxed': (amount * 100) / (100 + self.amount_type_tax)})
                    ineco_update.write({'amount_tax': amount - (amount * 100) / (100 + self.amount_type_tax)})
        return res

    @api.multi
    def button_tax(self):
        amount = 0.0
        for line in self.line_ids:
            amount = line.amount_untaxed
            ineco_account_vat_obj = self.env['ineco.account.vat']
            # print(self.line_ids)
            vat_data = {
                'customer_deposit_id': self.id,
                'name': self.name,
                'docdat':self.date,
                'partner_id':self.customer_id.id,
                'taxid':self.customer_id.vat or '',
                'depcod' : self.customer_id.branch_no or '',
                'amount_untaxed': amount
            }
            if self.tax_type == 'percent':
                vat_data['amount_untaxed'] = amount
                vat_data['amount_tax'] = amount*self.amount_type_tax/100
                ineco_account_vat_obj.create(vat_data)
            else:
                vat_data['amount_untaxed'] = (amount*100)/(100+ self.amount_type_tax)
                vat_data['amount_tax'] = amount - (amount*100)/(100+ self.amount_type_tax)
                ineco_account_vat_obj.create(vat_data)

    @api.multi
    def button_post(self):
        # print(self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other)
        # print(round(self.amount_receipt,2))
        self.ensure_one()
        if round(self.amount_receipt,2) != round(self.amount_cheque,2) + round(self.amount_wht,2) + round(self.amount_cash,2) + round(self.amount_discount,2) + round(self.amount_other,2):
            raise UserError("ยอดไม่สมดุลย์")
        if self.name == 'New':
            self.name = self.env['ir.sequence'].next_by_code('ineco.customer.deposit')
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()
        vat_sale_account_id = int(params.get_param('ineco_thai_v11.vat_sale_account_id', default=False)) or False,
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': self.amount_vat,
                'payment_id': False,
                'account_id': vat_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        unearned_income_account_id = int(params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
        if unearned_income_account_id:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'invoice_id': False,
                'debit': 0.0,
                'credit': self.amount_receipt - self.amount_vat,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cash_account_id = int(params.get_param('ineco_thai_v11.cash_account_id', default=False)) or False,
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_cash,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id=int(params.get_param('ineco_thai_v11.cheque_sale_account_id', default=False)) or False,
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_cheque,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id=int(params.get_param('ineco_thai_v11.cash_discount_account_id', default=False)) or False,
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_discount,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id=int(params.get_param('ineco_thai_v11.wht_sale_account_id', default=False)) or False,
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_wht,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': other.amount > 0 and abs(other.amount) or 0.0,
                'credit': other.amount < 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            iml.append((0, 0, move_data_vals))
        self.state = 'post'
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        new_move.post()
        self.move_id = new_move
        ineco_update = self.env['ineco.account.vat'].search([('customer_deposit_id', '=', self.id)])
        ineco_update.write({'name': self.name})
        self.write({'name': self.move_id.name})
        return True

    @api.multi
    def button_cancel(self):
        self.ensure_one()
        self.move_id.sudo().button_cancel()
        self.state = 'cancel'
        return True

    @api.multi
    def button_draft(self):
        self.ensure_one()
        self.move_id = False
        self.state = 'draft'
        return True

    @api.multi
    def button_journal(self):
        if self.move_id :
            self.move_id.name = self.journal_name
        return True

    # @api.model
    # def create(self, vals):
    #     vals['name'] = self.env['ir.sequence'].next_by_code('ineco.customer.deposit')
    #     receipt_id = super(InecoCustomerDeposit, self.with_context(mail_create_nosubscribe=True)).create(vals)
    #     return receipt_id

class InecoCustomerDepositLine(models.Model):
    _name = 'ineco.customer.deposit.line'
    _description = 'Customer Deposit Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string=u'คำอธิบาย', required=True, index=True, copy=False, track_visibility='onchange')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    # amount_total = fields.Float(string='ยอดเงินรวม')
    payment_id = fields.Many2one('ineco.customer.deposit', string=u'รับมัดจำ')
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State',related='payment_id.state',store=True)

    @api.multi
    def button_trash(self):
        ineco_account = self.env['ineco.account.vat'].search([('customer_deposit_line_id', '=', self.id),])
        sql_ineco_account_vats = """
                        DELETE FROM ineco_account_vat
                        where id  =  %s
                         """ % (ineco_account.id)
        self._cr.execute(sql_ineco_account_vats)

        sql_line_ids = """
                                DELETE FROM ineco_customer_deposit_line
                                where id  =  %s
                                 """ % (self.id)
        self._cr.execute(sql_line_ids)
        return True


class InecoCustomerDepositOther(models.Model):
    _name = 'ineco.customer.deposit.other'
    _description = 'Customer Deposit Other'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    amount = fields.Float(string=u'จำนวนเงิน', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.customer.deposit', string=u'รับมัดจำ')
