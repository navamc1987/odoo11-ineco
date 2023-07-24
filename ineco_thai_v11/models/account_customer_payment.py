# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import UserError


class InecoCustomerPayment(models.Model):
    _name = 'ineco.customer.payment'
    _description = 'Customer Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    @api.multi
    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            gl_receivable = 0.0
            clear_debtor = 0.0
            gl_difference = 0.0
            receipt.amount_receipt = 0.0
            for line in receipt.line_ids:
                receipt.amount_receipt += line.amount_receipt
                gl_receivable += line.gl_receivable
                clear_debtor += line.clear_debtor
                gl_difference += line.difference
            receipt.gl_receivable = gl_receivable
            receipt.clear_debtor = clear_debtor
            receipt.gl_difference = gl_difference

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
    @api.depends('deposit_ids')
    def _get_deposit(self):
        for receipt in self:
            receipt.amount_deposit = 0.0
            for deposit in receipt.deposit_ids:
                receipt.amount_deposit += deposit.amount_receipt

    @api.multi
    @api.depends('other_ids')
    def _get_other(self):
        for receipt in self:
            receipt.amount_other = 0.0
            for vat in receipt.other_ids:
                receipt.amount_other += vat.amount

    @api.multi
    @api.depends('transfer_ids')
    def _get_transfer(self):
        for receipt in self:
            receipt.amount_transfer = 0.0
            for vat in receipt.transfer_ids:
                receipt.amount_transfer += vat.amount

    @api.multi
    @api.depends('exchange_rate_ids')
    def _compute_profit_loss(self):
        dr = 0.0
        cr = 0.0
        for loss in self:
            for line in loss.exchange_rate_ids:
                dr += line.dr
                cr += line.cr
            loss.profit_loss = cr - dr




    name = fields.Char(string=u'เลขที่ใบเสร็จ', size=32, required=True, copy=False, track_visibility='onchange',
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       track_visibility='onchange')
    date_due = fields.Date(string=u'วันที่รับเงิน', required=True, track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', string=u'ลูกค้า', required=True, track_visibility='onchange')
    note = fields.Text(string=u'หมายเหตุ', track_visibility='onchange')
    line_ids = fields.One2many('ineco.customer.payment.line', 'payment_id', string=u'รายการรับชำระ')
    other_ids = fields.One2many('ineco.customer.payment.other', 'payment_id', string=u'อื่นๆ')

    transfer_ids = fields.One2many('ineco.customer.payment.transfer', 'payment_id', string=u'เงินโอน')

    deposit_ids = fields.One2many('ineco.customer.payment.deposit', 'payment_id', string=u'มัดจำ')

    exchange_rate_ids = fields.One2many('ineco.customer.payment.exchange.rate', 'payment_id', string=u'กำไรขาดทุนอัตราแลกเปี่ยน')

    amount_receipt = fields.Float(string=u'ยอดรับชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขใบเสร็จ', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันรับ', required=True, track_visibility='onchange')
    foreign = fields.Boolean(u'ต่างประเทศ', related='journal_id.foreign', )
    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม', related='journal_id.type_vat', )
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft')
    amount_deposit = fields.Float(string=u'ยอดมัดจำ', track_visibility='onchange', compute='_get_deposit', copy=False)
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', track_visibility='onchange', compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยรับ', track_visibility='onchange', copy=False)
    amount_cash = fields.Float(string=u'เงินสด', track_visibility='onchange', copy=False)
    amount_cheque = fields.Float(string=u'เช็ครับ', track_visibility='onchange', compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', track_visibility='onchange', compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดเงินสด', track_visibility='onchange', copy=False)
    amount_paid = fields.Float(string=u'ยอดรับชำระ', track_visibility='onchange', copy=False)
    amount_other = fields.Float(string=u'อื่นๆ', track_visibility='onchange', compute='_get_other', copy=False)
    amount_transfer = fields.Float(string=u'เงินโอน', track_visibility='onchange', compute='_get_transfer', copy=False)

    get_paid = fields.Float(string=u'-รับเงินขาด', track_visibility='onchange', copy=False)
    get_overgrown = fields.Float(string=u'+รับเงินเกิน', track_visibility='onchange', copy=False)



    profit_loss = fields.Float(string=u'+,- กำไรขาดทุนอัตราแลกเปลี่ยน', track_visibility='onchange', copy=False,
                               compute="_compute_profit_loss", store=True)
    fee = fields.Float(string=u'ค่าธรรมเนียม', track_visibility='onchange', copy=False)

    cheque_ids = fields.One2many('ineco.cheque', 'customer_payment_id', string=u'เช็ครับ', copy=False)
    vat_ids = fields.One2many('ineco.account.vat', 'customer_payment_id', string=u'ภาษีขาย', copy=False)
    wht_ids = fields.One2many('ineco.wht', 'customer_payment_id', string=u'ภาษีหัก ณ ที่จ่าย', copy=False)

    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True, copy=False, track_visibility='onchange')

    amount_tax_break = fields.Float(string=u'ยอดภาษีพัก', track_visibility='onchange',
                                    # compute='_get_tax_break',
                                    copy=False)

    rate = fields.Float(digits=(12, 4), default=1.0, help='The rate of the currency to the currency of rate 1',
                        track_visibility='onchange')

    gl_receivable = fields.Float(string=u'GLลูกหนี้', copy=False, track_visibility='onchange',
                                 compute='_get_receipts')
    clear_debtor = fields.Float(string=u'ล้างลูกหนี้', copy=False, track_visibility='onchange',
                                compute='_get_receipts')
    gl_difference = fields.Float(string=u'ส่วนต่าง', copy=False, track_visibility='onchange',
                                 compute='_get_receipts')

    @api.multi
    def button_get_iv(self):
        cumtomer_pay = self.env['ineco.customer.payment.line']
        invoices = self.env['account.invoice'].search([
            ('partner_id', '=', self.customer_id.id),
            ('residual_signed', '!=', 0),
            ('state', 'not in', ('draft', 'cancel', 'paid')),
            ('type', 'in', ('out_invoice', 'out_refund')),
        ], order='id desc')
        for invoice in invoices:
            data = {
                'name': invoice.id,
                'user_id': invoice.user_id.id,
                'payment_id': self.id,
                'amount_total': invoice.amount_total_signed,
                'amount_residual': invoice.residual_signed,
                'amount_receipt': invoice.residual_signed
            }
            cumtomer_pay = self.env['ineco.customer.payment.line'].search([
                ('name', '=', invoice.id), ('payment_id', '=', self.id)
            ])
            if not cumtomer_pay:
                cumtomer_pay.create(data)

    @api.multi
    def check_deposit(self):
        for de in self.deposit_ids:
            if de.amount_residual < de.amount_receipt:
                raise UserError(f'รายการมัดจำยอดชำระมากกว่ายอดคงเหลือ เลขที่{de.name}')
            if de.amount_residual <= 0.0:
                raise UserError(f'รายการมัดจำถูกต้องใช้ไป หมดแล้ว เลขที่{de.name}')

    def post_thai(self):
        self.ensure_one()
        self.check_deposit()
        # รับชำระ+ดอกเบี้ยรับ = อื่นๆ +เงินสด+ภาษีหักถูก ณ ที่จ่าย+เช็ครับ+ส่วนลดเงินสด+ยอดมัดจำ
        if round(self.amount_receipt + self.amount_interest, 2) != round(
                self.amount_deposit + self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other + self.amount_transfer,
                2):
            raise UserError("ยอดไม่สมดุลย์")
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()

        # Credit Side
        vat_sale_account_id = int(params.get_param('ineco_thai_v11.vat_sale_account_id', default=False)) or False,
        ## กลับภาษีพัก
        vat_sale_break = self.env['account.tax'].search([
            ('tax_break', '=', True), ('type_tax_use', '=', 'sale'),
            ('active', '=', True)])
        if self.amount_tax_break:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': self.amount_tax_break,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_break.account_id.id,
            }
            iml.append((0, 0, move_data_vals))
        for vat in self.vat_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': vat.amount_tax,
                'payment_id': False,
                'account_id': vat_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        ## กลับภาษีพัก

        interest_income_account_id = int(
            params.get_param('ineco_thai_v11.interest_income_account_id', default=False)) or False,
        if self.amount_interest:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': self.amount_interest,
                'payment_id': False,
                'account_id': interest_income_account_id,
            }
            iml.append((0, 0, move_data_vals))
        receivable_account_id = self.customer_id.property_account_receivable_id.id
        for ai in self.line_ids:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'invoice_id': ai.name.id,
                'debit': ai.amount_receipt < 0 and abs(ai.amount_receipt) or 0.0,
                'credit': ai.amount_receipt > 0 and abs(ai.amount_receipt) or 0.0,
                'payment_id': False,
                'account_id': receivable_account_id,
            }
            iml.append((0, 0, move_data_vals))

        # Debit Side

        unearned_income_account_id = int(
            params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
        if self.amount_deposit:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_deposit,
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
        cheque_sale_account_id = int(params.get_param('ineco_thai_v11.cheque_sale_account_id', default=False)) or False,
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
        cash_discount_account_id = int(
            params.get_param('ineco_thai_v11.cash_discount_account_id', default=False)) or False,
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
        wht_sale_account_id = int(params.get_param('ineco_thai_v11.wht_sale_account_id', default=False)) or False,
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


        # # เงินขาด
        # sale_get_paid_account_id = int(params.get_param('ineco_thai_v11.get_paid_account_id', default=False)) or False,
        # if self.get_paid:
        #     move_data_vals = {
        #         'partner_id': False,
        #         'invoice_id': False,
        #         'credit': 0.0,
        #         'debit': self.get_paid,
        #         'payment_id': False,
        #         'account_id': sale_get_paid_account_id,
        #     }
        #     iml.append((0, 0, move_data_vals))
        #
        # # เงินเกิน
        # sale_get_overgrown_account_id = int(
        #     params.get_param('ineco_thai_v11.get_overgrown_account_id', default=False)) or False,
        # if self.get_overgrown:
        #     move_data_vals = {
        #         'partner_id': False,
        #         'invoice_id': False,
        #         'credit': self.get_overgrown,
        #         'debit': 0.0,
        #         'payment_id': False,
        #         'account_id': sale_get_overgrown_account_id,
        #     }
        #     iml.append((0, 0, move_data_vals))

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

        for transfer in self.transfer_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': transfer.amount > 0 and abs(transfer.amount) or 0.0,
                'credit': transfer.amount < 0 and abs(transfer.amount) or 0.0,
                'payment_id': False,
                'account_id': transfer.name.id,
            }
            iml.append((0, 0, move_data_vals))
        self.state = 'post'
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'date_due': self.date_due,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
        }

        if not self.move_id:
            new_move = move.create(move_vals)
            if self.name != 'New':
                new_move.name = self.name
            new_move.sudo().write({'line_ids': iml})
            new_move.post()
            self.move_id = new_move
        else:
            self.move_id.line_ids = False
            self.move_id.sudo().write({'line_ids': iml})
            self.move_id.post()
        for ai in self.line_ids:
            domain = [('account_id', '=', self.customer_id.property_account_receivable_id.id),
                      ('invoice_id', '=', ai.name.id),
                      ('partner_id', '=', self.customer_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]
            move_lines = self.env['account.move.line'].search(domain)
            move_lines.reconcile()
        self.write({'name': self.move_id.name})
        for line in self.line_ids:
            line.UpDateDone()
        return True

    def post_foreign(self):
        currency_id = False
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()

        # if self.profit_loss != self.gl_difference:
        #     raise UserError(f'กำไรขาดทุนจากอัตราแลกเปลี่ยนไม่สมดุล')

        # Credit Side
        vat_sale_account_id = int(params.get_param('ineco_thai_v11.vat_sale_account_id', default=False)) or False,
        ## กลับภาษีพัก
        vat_sale_break = self.env['account.tax'].search([
            ('tax_break', '=', True), ('type_tax_use', '=', 'sale'),
            ('active', '=', True)])
        if self.amount_tax_break:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': round(self.amount_tax_break,2),
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_break.account_id.id,
                'currency_id': currency_id
            }
            # print('move_data_vals1',move_data_vals)

            iml.append((0, 0, move_data_vals))
        for vat in self.vat_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': round(vat.amount_tax,2),
                'payment_id': False,
                'account_id': vat_sale_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals2', move_data_vals)
            iml.append((0, 0, move_data_vals))
        ## กลับภาษีพัก

        interest_income_account_id = int(
            params.get_param('ineco_thai_v11.interest_income_account_id', default=False)) or False,
        if self.amount_interest:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': round(self.amount_interest, 2),
                'payment_id': False,
                'account_id': interest_income_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals3', move_data_vals)
            iml.append((0, 0, move_data_vals))
        receivable_account_id = self.customer_id.property_account_receivable_id.id
        for ai in self.line_ids:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'invoice_id': ai.name.id,
                'debit': 0.0,
                'credit': round(ai.gl_receivable, 2) or 0.0,
                'payment_id': False,
                'account_id': receivable_account_id,
                'foreign': True,
                'foreign_receivable': ai.amount_receipt
                # 'currency_id': ai_currency_id,
            }
            # print('move_data_vals4', move_data_vals)
            iml.append((0, 0, move_data_vals))

        # Debit Side

        unearned_income_account_id = int(
            params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
        if self.amount_deposit:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'invoice_id': False,
                'credit': 0.0,
                'debit': round(self.amount_deposit, 2),
                'payment_id': False,
                'account_id': unearned_income_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals5', move_data_vals)
            iml.append((0, 0, move_data_vals))

        cash_account_id = int(params.get_param('ineco_thai_v11.cash_account_id', default=False)) or False,
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': round((self.amount_cash * self.rate), 2),
                'payment_id': False,
                'account_id': cash_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals6', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = int(params.get_param('ineco_thai_v11.cheque_sale_account_id', default=False)) or False,
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': round(self.amount_cheque, 2),
                'payment_id': False,
                'account_id': cheque_sale_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals7', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = int(
            params.get_param('ineco_thai_v11.cash_discount_account_id', default=False)) or False,
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': round(self.amount_discount, 2),
                'payment_id': False,
                'account_id': cash_discount_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals8', move_data_vals)
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id = int(params.get_param('ineco_thai_v11.wht_sale_account_id', default=False)) or False,
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': 0.0,
                'debit': round(self.amount_wht, 2),
                'payment_id': False,
                'account_id': wht_sale_account_id,
                'currency_id': currency_id
            }
            # print('move_data_vals9', move_data_vals)
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': other.amount > 0 and round(abs(other.amount),2)  or 0.0,
                'credit': other.amount < 0 and round(abs(other.amount),2) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
                'currency_id': currency_id
            }
            # print('move_data_vals10', move_data_vals)
            iml.append((0, 0, move_data_vals))

        for transfer in self.transfer_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': transfer.amount > 0 and round(abs(transfer.amount),2) or 0.0,
                'credit': transfer.amount < 0 and round(abs(transfer.amount),2)  or 0.0,
                'payment_id': False,
                'account_id': transfer.name.id,
                'currency_id': currency_id
            }
            # print('move_data_vals11', move_data_vals)
            iml.append((0, 0, move_data_vals))
        for exchange in self.exchange_rate_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': round(exchange.dr,2),
                'credit': round(exchange.cr,2),
                'payment_id': False,
                'account_id': exchange.name.id,
                'currency_id': currency_id
            }
            # print('move_data_vals11', move_data_vals)
            iml.append((0, 0, move_data_vals))
        self.state = 'post'
        move_vals = {
            # 'ref': self.name,
            'date': self.date,
            'date_due': self.date_due,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
            'currency_id': currency_id
        }
        # print('iml,iml',iml)
        if not self.move_id:
            new_move = move.create(move_vals)
            if self.name != 'New':
                new_move.name = self.name
            new_move.sudo().write({'line_ids': iml})
            new_move.post()
            self.move_id = new_move
        else:
            self.move_id.line_ids = False
            self.move_id.sudo().write({'line_ids': iml})
            self.move_id.post()
        for ai in self.line_ids:
            domain = [('account_id', '=', self.customer_id.property_account_receivable_id.id),
                      ('invoice_id', '=', ai.name.id),
                      ('partner_id', '=', self.customer_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)
                      ]
            move_lines = self.env['account.move.line'].search(domain)
            move_lines.reconcile()
        self.write({'name': self.move_id.name})
        for line in self.line_ids:
            line.UpDateDone()
        return True

    @api.multi
    def button_post(self):
        if self.foreign == False:
            self.post_thai()
        if self.foreign == True:
            self.post_foreign()

    @api.multi
    def button_cancel(self):
        for aml in self.move_id.line_ids:
            if aml.account_id.reconcile:
                reconcile = self.env['account.partial.reconcile'].search(['|', ('credit_move_id', '=', aml.id),
                                                                          ('debit_move_id', '=', aml.id)
                                                                          ])
                reconcile.sudo().unlink()
        self.move_id.sudo().button_cancel()
        self.move_id.sudo().unlink()
        self.state = 'cancel'
        return True

    @api.multi
    def button_draft(self):
        self.ensure_one()
        self.move_id.button_cancel()
        self.state = 'draft'
        return True

    @api.model
    def create(self, vals):
        # vals['name'] = self.env['ir.sequence'].next_by_code('ineco.customer.payment')
        receipt_id = super(InecoCustomerPayment, self.with_context(mail_create_nosubscribe=True)).create(vals)
        # receipt_id.button_get_iv()
        return receipt_id

    @api.multi
    def button_post_tax(self):
        for iv in self.line_ids:
            for acc in iv.name:
                for tax in acc.tax_line_ids.tax_id:
                    if tax.tax_break:
                        vat_data = {
                            'name': acc.number,
                            'invoice_id': acc.id,
                            'docdat': self.date,
                            'partner_id': acc.partner_id.id,
                            'taxid': acc.partner_id.vat,
                            'depcod': acc.partner_id.branch_no,
                            'amount_untaxed': acc.amount_untaxed,
                            'amount_tax': acc.amount_tax,
                            'amount_total': acc.amount_total,
                            'customer_payment_id': self.id
                        }
                        vat = self.env['ineco.account.vat'].search([
                            ('invoice_id', '=', acc.id), ])
                        ineco_vat = self.env['ineco.account.vat'].create(vat_data)
        return True


class InecoCustomerPaymentDeposit(models.Model):
    _name = 'ineco.customer.payment.deposit'
    _description = 'Customer Payment Deposit'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_receipt
            self.amount_residual = self.name.amount_residual

    @api.onchange('amount_receipt', 'amount_residual')
    # @api.depends('deposit_ids')
    def onchange_amount_receipt(self):
        if self.amount_receipt > self.amount_residual:
            raise UserError("ตัดยอดเกิน")

    name = fields.Many2one('ineco.customer.deposit', string=u'ใบมัดจำ', required=True, copy=False, index=True,
                           track_visibility='onchange')
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, track_visibility='onchange')
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', copy=False, track_visibility='onchange')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
    invoice_id = fields.Many2one('account.invoice', string=u'ใบแจ้งหนี้/ใบกำกับภาษี')
    # customer_id = fields.Many2one('res.partner', string=u'ลูกค้า', required=True, track_visibility='onchange')


class InecoCustomerPaymentLine(models.Model):
    _name = 'ineco.customer.payment.line'
    _description = 'Customer Payment Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_total_signed
            self.amount_residual = self.name.residual_signed
            # self.amount_receipt = self.name.residual_signed
            self.rate = self.name.rate
            self.foreign = self.payment_id.foreign

    @api.depends('name', 'amount_receipt')
    def _compute_gl_receivable(self):
        difference = 0.0
        for iv in self:
            iv.gl_receivable = iv.update_gl_receivable()
            iv.clear_debtor = iv.amount_receipt * iv.payment_id.rate
            difference = (iv.payment_id.rate - iv.rate) * iv.amount_receipt
            iv.difference = difference

    name = fields.Many2one('account.invoice', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    date_invoice = fields.Date(string=u'ลงวันที่', related='name.date_invoice', readonly=True)
    billing_id = fields.Many2one('ineco.billing', string=u'เลขที่ใบวางบิล', related='name.billing_id', copy=False,
                                 index=True, track_visibility='onchange', readonly=True)
    user_id = fields.Many2one('res.users', string=u'พนักงานขาย', index=True, track_visibility='onchange')
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, track_visibility='onchange')
    amount_residual = fields.Float(string=u'ยอดค้างชำระ', copy=False, track_visibility='onchange')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
    gl_receivable = fields.Float(string=u'GLลูกหนี้', copy=False, track_visibility='onchange',
                                 # compute='_compute_gl_receivable' ,
                                 digits=(12, 2),
                                 store=True)
    clear_debtor = fields.Float(string=u'ล้างลูกหนี้', copy=False, track_visibility='onchange',
                                compute='_compute_gl_receivable',digits=(12, 2)

                                )
    difference = fields.Float(string=u'ส่วนต่าง', copy=False, track_visibility='onchange',
                              compute='_compute_gl_receivable',digits=(12, 2),
                              )
    rate = fields.Float(string=u'Rate IV')

    foreign = fields.Boolean(u'ต่างประเทศ')

    @api.multi
    def UpDateDone(self):
        if self.billing_id:
            self.billing_id.UpDateDone()

    @api.onchange()
    def update_gl_receivable(self):
        qty = 0.0
        qty = self.amount_receipt * self.rate
        # print('update_gl_receivable',qty)
        # account = self.name.account_id.id
        # move = self.env['account.move.line'].search([('invoice_id', '=', self.name.id),
        #                                              ('account_id','=',account)])
        # for gl in move:
        #     qty += gl.debit
        return qty

    # self.customer_id.property_account_receivable_id.id


class InecoCustomerPaymentOther(models.Model):
    _name = 'ineco.customer.payment.other'
    _description = 'Customer Payment Other'
    _order = 'dr'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    @api.depends('name','dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = dr - cr


    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    dr = fields.Float(string=u'Dr', copy=False, track_visibility='onchange')
    cr = fields.Float(string=u'Cr', copy=False, track_visibility='onchange')
    amount = fields.Float(string=u'จำนวนเงิน', copy=False, track_visibility='onchange',
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')

    # @api.onchange('dr', 'cr')
    # def _onchange_amount(self):
    #     self.amount = self.cr - self.dr
    #     # self.amount = -self.cr



class InecoCustomerPaymentTransfer(models.Model):
    _name = 'ineco.customer.payment.transfer'
    _description = 'Customer Payment Transfer'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    @api.depends('name', 'dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = dr - cr

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    dr = fields.Float(string=u'Dr', copy=False, track_visibility='onchange')
    cr = fields.Float(string=u'Cr', copy=False, track_visibility='onchange')

    amount = fields.Float(string=u'จำนวนเงิน', copy=False, track_visibility='onchange',
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')


class InecoCustomerPaymentExchangeRate(models.Model):
    _name = 'ineco.customer.payment.exchange.rate'
    _description = 'Customer Payment Transfer'
    _order = 'dr'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    dr = fields.Float(string=u'Dr', copy=False, track_visibility='onchange')
    cr = fields.Float(string=u'Cr', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
