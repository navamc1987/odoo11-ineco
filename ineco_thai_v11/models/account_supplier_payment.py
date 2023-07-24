# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class InecoSupplierPayment(models.Model):
    _name = 'ineco.supplier.payment'
    _description = 'Supplier Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            receipt.amount_receipt = 0.0
            for line in receipt.line_ids:
                receipt.amount_receipt += line.amount_receipt

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
    @api.depends('amount_deposit', 'amount_wht', 'amount_vat', 'amount_discount', 'amount_other',
                 'amount_receipt'
                 )
    def _get_amount_paid(self):
        paid = 0.0
        for pay in self:
            self.amount_paid = pay.amount_receipt - (
                        pay.amount_deposit + pay.amount_wht + pay.amount_vat + pay.amount_discount + pay.amount_other)

    @api.multi
    @api.depends('vat_ids')
    def _get_tax_break(self):
        for receipt in self:
            amount_tax = 0.0
            for iv in receipt.vat_ids:
                amount_tax += iv.amount_tax
            receipt.amount_tax_break = amount_tax

    name = fields.Char(string=u'เลขที่', size=32, required=True, copy=False, track_visibility='onchange',
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       track_visibility='onchange')
    date_due = fields.Date(string=u'วันจ่ายเงิน', required=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string=u'ผู้จำหน่าย', required=True, track_visibility='onchange')
    note = fields.Text(string=u'หมายเหตุ', track_visibility='onchange')
    line_ids = fields.One2many('ineco.supplier.payment.line', 'payment_id', string=u'รายการจ่ายชำระ')
    other_ids = fields.One2many('ineco.supplier.payment.other', 'payment_id', string=u'อื่นๆ')
    deposit_ids = fields.One2many('ineco.supplier.payment.deposit', 'payment_id', string=u'มัดจำ')

    amount_receipt = fields.Float(string=u'ยอดจ่ายชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขเอกสาร', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันจ่าย', required=True,
                                 track_visibility='onchange')
    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม', related='journal_id.type_vat', )
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft', track_visibility='onchange')
    amount_deposit = fields.Float(string=u'ยอดมัดจำ', track_visibility='onchange', compute='_get_deposit', copy=False)
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', track_visibility='onchange', compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยจ่าย', track_visibility='onchange', copy=False)
    amount_cash = fields.Float(string=u'เงินสด', track_visibility='onchange', copy=False)
    amount_cheque = fields.Float(string=u'เช็คจ่าย', track_visibility='onchange', compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', track_visibility='onchange', compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดรับ', track_visibility='onchange', copy=False)
    amount_paid = fields.Float(string=u'ยอดจ่ายชำระ', track_visibility='onchange', copy=False,
                               compute='_get_amount_paid', digits=(16, 2))
    amount_other = fields.Float(string=u'อื่นๆ', track_visibility='onchange', compute='_get_other', copy=False)
    cheque_ids = fields.One2many('ineco.cheque', 'supplier_payment_id', string=u'เช็คจ่าย', copy=False)
    vat_ids = fields.One2many('ineco.account.vat', 'supplier_payment_id', string=u'ภาษีซื้อ', copy=False)
    wht_ids = fields.One2many('ineco.wht', 'supplier_payment_id', string=u'ภาษีหัก ณ ที่จ่าย', copy=False)

    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True, copy=False, track_visibility='onchange')

    amount_tax_break = fields.Float(string=u'ยอดภาษีพัก', track_visibility='onchange', compute='_get_tax_break',
                                    copy=False)
    # Followers
    partner_ids = fields.Many2one('res.partner', string=u'ส่งเรื่องให้ผู้อนุมัติ')
    channel_ids = fields.Many2one('mail.channel', string='ส่งเข้ากลุ่มChat')
    expense = fields.Boolean(u'ชำระค่าใช้จ่าย',
                             related='journal_id.expense',
                             track_visibility='onchange',
                             store=True, readonly=True,
                             related_sudo=False
                             )

    @api.onchange('partner_id', )
    def _onchange_partner_deposit(self):
        warning = {}
        deposits = self.env['ineco.supplier.deposit'].search([('partner_id', '=', self.partner_id.id),
                                                              ('amount_residual', '!=', 0.0)])
        note = []
        for de in deposits:
            message = f'เลขที่เอกสารมัดจำ {de.name} คงเหลือ {de.amount_residual} บาท '
            note.append(message)
        note2 = ''
        for n in note:
            note2 += n + '\n'
        if deposits:
            warning = {
                'title': _("มีเงินมัดจ่ายมัดจำ %s") % self.partner_id.name,
                'message': note2
            }
        res = {}
        if warning:
            res['warning'] = warning
        return res

    @api.multi
    def button_get_iv(self):
        cumtomer_pay = self.env['ineco.supplier.payment.line']
        invoices = self.env['account.invoice'].search([
            ('partner_id', '=', self.partner_id.id),
            ('residual_signed', '!=', 0),
            ('state', 'not in', ('draft', 'cancel', 'paid')),
            ('type', 'in', ('in_invoice', 'in_refund')),
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
            cumtomer_pay = self.env['ineco.supplier.payment.line'].search([
                ('name', '=', invoice.id), ('payment_id', '=', self.id)
            ])
            if not cumtomer_pay:
                cumtomer_pay.create(data)

    @api.multi
    def button_post_tax(self):
        for pay in self.line_ids:
            pay.button_tax_break()


    @api.multi
    def button_post(self):
        self.add_follower_id()
        self.ensure_one()
        # รับชำระ+ดอกเบี้ยรับ = อื่นๆ +เงินสด+ภาษีหักถูก ณ ที่จ่าย+เช็ครับ+ส่วนลดเงินสด+ยอดมัดจำ
        if round(self.amount_receipt + self.amount_interest, 2) != round(
                self.amount_deposit + self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other,
                2):
            raise UserError("ยอดไม่สมดุลย์")
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()

        # Credit Side
        vat_sale_account_id = int(params.get_param('ineco_thai_v11.vat_purchase_account_id', default=False)) or False,
        vat_sale_break = self.env['account.tax'].search([
            ('tax_break', '=', True), ('type_tax_use', '=', 'purchase'),
            ('active', '=', True)])

        if self.vat_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': 0.0,
                'credit': self.amount_tax_break,
                'payment_id': False,
                'account_id': vat_sale_break.account_id.id,
            }
            iml.append((0, 0, move_data_vals))

        # vats = []
        # for vat in self.vat_ids:
        #     vats.append((1, vat.id, vat))
        # print('vats',vats)
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_account_id,
                # 'vat_ids': vats
            }
            iml.append((0, 0, move_data_vals))

        interest_income_account_id = int(
            params.get_param('ineco_thai_v11.interest_expense_account_id', default=False)) or False,
        if self.amount_interest:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': self.amount_interest,
                'credit': 0.0,
                'payment_id': False,
                'account_id': interest_income_account_id,
            }
            iml.append((0, 0, move_data_vals))
        if self.expense:
            for ai in self.line_ids:
                receivable_account_id = ai.name.account_id.id
                pass
        else:
            receivable_account_id = self.partner_id.property_account_payable_id.id
        # print(receivable_account_id)
        for ai in self.line_ids:
            move_data_vals = {
                'partner_id': self.partner_id.id,
                'invoice_id': ai.name.id,
                'debit': ai.amount_receipt > 0 and abs(ai.amount_receipt) or 0.0,
                'credit': ai.amount_receipt < 0 and abs(ai.amount_receipt) or 0.0,
                'payment_id': False,
                'account_id': receivable_account_id,
            }
            iml.append((0, 0, move_data_vals))

        # Debit Side

        unearned_income_account_id = int(
            params.get_param('ineco_thai_v11.unearned_expense_account_id', default=False)) or False,
        if self.amount_deposit:
            move_data_vals = {
                'partner_id': self.partner_id.id,
                'invoice_id': False,
                'credit': self.amount_deposit,
                'debit': 0.0,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            iml.append((0, 0, move_data_vals))

        cash_account_id = int(params.get_param('ineco_thai_v11.cash_account_id', default=False)) or False,
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': self.amount_cash,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = int(
            params.get_param('ineco_thai_v11.cheque_purchase_account_id', default=False)) or False,
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': self.amount_cheque,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = int(
            params.get_param('ineco_thai_v11.cash_income_account_id', default=False)) or False,
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': self.amount_discount,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            iml.append((0, 0, move_data_vals))

        if self.partner_id.company_type is 'company':
            wht_sale_account_id = int(
                params.get_param('ineco_thai_v11.wht_purchase_account_id', default=False)) or False,
        elif self.partner_id.company_type is 'person':
            wht_sale_account_id = int(
                params.get_param('ineco_thai_v11.wht_purchase_personal_account_id', default=False)) or False,

        # wht_sale_account_id=int(params.get_param('ineco_thai_v11.wht_purchase_account_id', default=False)) or False,
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'credit': self.amount_wht,
                'debit': 0.0,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                'invoice_id': False,
                'debit': other.amount < 0 and abs(other.amount) or 0.0,
                'credit': other.amount > 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            iml.append((0, 0, move_data_vals))


        self.state = 'post'
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'date_due': self.date_due,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
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
            domain = [('account_id', '=', receivable_account_id),
                      ('invoice_id', '=', ai.name.id),
                      ('partner_id', '=', self.partner_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]
            move_lines = self.env['account.move.line'].search(domain)
            move_lines.reconcile()
        self.write({'name': self.move_id.name})
        for vat in self.vat_ids:
            move_line = self.env['account.move.line'].search([
                ('move_id', '=', self.move_id.id),
                ('account_id', '=',int(vat_sale_account_id[0]))])
            vat.write({'tax_purchase_wait_ok': True, 'move_line_id': move_line.id})
            vat.reconciliation_in.vatprd = self.date
        return True

    @api.multi
    def button_approve(self):
        self.state = 'approve'
        return True

    @api.multi
    def button_post_2(self):
        self.move_id.post()
        self.state = 'post'
        invoice_ids = []
        for ai in self.line_ids:
            invoice_ids.append(ai.name.id)
        domain = [('account_id', '=', self.partner_id.property_account_payable_id.id),
                  '|', ('invoice_id', 'in', invoice_ids), ('move_id', '=', self.move_id.id),
                  ('partner_id', '=', self.partner_id.id),
                  ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                  ('amount_residual_currency', '!=', 0.0)]

        move_lines = self.env['account.move.line'].search(domain)
        # self.ensure_one()
        move_lines.reconcile()

    @api.multi
    def add_follower_id(self):
        Model = self.env['ineco.supplier.payment'].search([('id', '=', self.id)])
        ch_obj = self.env['mail.channel']
        ch = ch_obj.sudo().search([('name', 'ilike', 'อนุมัติจ่ายประจำวัน')
                                   ], limit=1)
        self.channel_ids = ch
        if self.partner_ids or ch and hasattr(Model, 'message_subscribe'):
            records = Model
            records.message_subscribe(self.partner_ids.ids, self.channel_ids.ids, force=False)
        return False

    @api.multi
    def button_04_cancel(self):
        self.ensure_one()
        s = self.name.encode('utf-8')
        b = r'แจ้งเรื่อง ขออนุมัติจ่าย เลขที่ ' + self.name + " ผู้จำหน่าย " + self.partner_id.name + "  จำนวน " + \
            str(round(round(self.amount_receipt, 2) + round(self.amount_interest, 2), 2)) + " บาท"
        self.message_post(body=b, subject=s, subtype='mt_comment')

    @api.multi
    def button_cancel(self):
        for vat in self.vat_ids:
            vat.reconciliation_in.vatprd = False
            vat.reconciliation_in = False

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
        for vat in self.vat_ids:
            vat.invoice_id.write({'ineco_reconciled_tax': False})
            vat.unlink()
        self.move_id.sudo().button_cancel()
        self.state = 'draft'
        for line in self.line_ids:
            line.tax_break = 0.0
        return True

    @api.model
    def create(self, vals):
        receipt_id = super(InecoSupplierPayment, self.with_context(mail_create_nosubscribe=True)).create(vals)
        # receipt_id.button_get_iv()
        return receipt_id


class InecoSupplierPaymentDeposit(models.Model):
    _name = 'ineco.supplier.payment.deposit'
    _description = 'Supplier Payment Deposit'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_receipt
            # self.amount_residual = self.name.amount_residual

    @api.onchange('amount_receipt', 'amount_residual')
    # @api.depends('deposit_ids')
    def onchange_amount_receipt(self):
        if self.amount_receipt > self.amount_residual:
            raise UserError("ตัดยอดเกิน")

    name = fields.Many2one('ineco.supplier.deposit', string=u'ใบมัดจำ', required=True, copy=False, index=True,
                           track_visibility='onchange')
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, track_visibility='onchange')
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', related='name.amount_residual',
                                   copy=False, track_visibility='onchange')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'รับชำระ')
    invoice_id = fields.Many2one('account.invoice', string=u'ใบแจ้งหนี้/ใบกำกับภาษี')
    date_invoice = fields.Date(string=u'ลงวันที่', related='invoice_id.date_invoice')
    state_invoice = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string=u'สถานะ', related='invoice_id.state')

    state_payment = fields.Selection([
        ('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel'),
    ], string=u'สถานะจ่าย', related='payment_id.state')


class InecoSupplierPaymentLine(models.Model):
    _name = 'ineco.supplier.payment.line'
    _description = 'Supplier Payment Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_total_signed
            self.amount_residual = self.name.residual_signed
            self.amount_receipt = self.name.residual_signed

    # def _get_tax_break(self):
    #     for iv in self:
    #         if not iv.name.ineco_reconciled_tax:
    #             for line in iv.name.tax_line_ids:
    #                 if line.tax_id.tax_break:
    #                     iv.is_tax_break = True
    #                 else:
    #                     iv.is_tax_break = False

    @api.multi
    @api.depends('name')
    def _get_tax_break(self):
        for iv in self:
            tax_break = 0.0
            for line in iv.name:
                iv.is_tax_break = line.tax_purchase_wait_ok

    name = fields.Many2one('account.invoice', string=u'เลขที่เอกสาร', required=True, copy=False, index=True,
                           track_visibility='onchange')
    reference = fields.Char(string=u'ใบแจ้งหนี้/ใบกำกับภาษี', related='name.reference', readonly=True)
    date_invoice = fields.Date(string=u'ลงวันที่', related='name.date_invoice', readonly=True)
    # billing_id = fields.Many2one('ineco.billing', string=u'เลขที่ใบวางบิล', related='name.billing_id', copy=False,
    #                             index=True, track_visibility='onchange', readonly=True)
    user_id = fields.Many2one('res.users', string=u'พนักงานขาย', index=True, track_visibility='onchange')
    tax_break = fields.Float(string=u'ภาษีพัก',
                             # compute="_get_tax_break", store=True,
                             copy=False, track_visibility='onchange')
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, track_visibility='onchange')
    amount_residual = fields.Float(string=u'ยอดค้างชำระ', copy=False, track_visibility='onchange')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, track_visibility='onchange')
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'รับชำระ')
    is_tax_break = fields.Boolean(u'มีภาษีพัก', compute='_get_tax_break',store=True,
                             copy=False, track_visibility='onchange' )
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', related='payment_id.state', store=True)

    @api.multi
    def button_tax_break(self):
        for iv in self:
            tax_break = 0.0
            range_obj = self.env['date.range'].search([('date_start', '<=', iv.payment_id.date),
                                                       ('date_end', '>', iv.payment_id.date),
                                                       ])
            if range_obj:
                period_id = range_obj.id
            else:
                period_id = False
            for line in iv.name.ineco_vat_ids:
                if not line.vatprd:
                    tax_break += line.amount_tax
                    data = {
                        'supplier_payment_id': iv.payment_id.id,
                        'invoice_id': iv.name.id,
                        'move_line_id':False,
                        'name': iv.name.reference or u'โปรดระบุ',
                        'period_id': period_id,
                        'docdat': line.docdat,
                        'vatprd': iv.payment_id.date,
                        'partner_id': line.partner_id.id,
                        'partner_name': line.partner_name,
                        'taxid': line.taxid,
                        'depcod': line.depcod or '00000',
                        'amount_untaxed': line.amount_untaxed,
                        'amount_tax': line.amount_tax,
                        'amount_total': line.amount_total,
                        'reconciliation_in':line.id,
                        'tax_sale_ok':False,
                        'tax_purchase_wait_ok': False,
                        'tax_purchase_ok': True,
                    }
                    new_move_id = line.copy(data)
                    # line.write({
                    #             # 'vatprd': iv.payment_id.date,
                    #             'tax_sale_ok':False,
                    #     'tax_purchase_wait_ok': True,'tax_purchase_ok': False,})
            iv.tax_break = tax_break
            return True




class InecoSupplierPaymentOther(models.Model):
    _name = 'ineco.supplier.payment.other'
    _description = 'Supplier Payment Other'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    @api.depends('name', 'dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = cr - dr

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           track_visibility='onchange')
    dr = fields.Float(string=u'Dr', copy=False, track_visibility='onchange')
    cr = fields.Float(string=u'Cr', copy=False, track_visibility='onchange')

    amount = fields.Float(string=u'จำนวนเงิน', copy=False, track_visibility='onchange',
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'จ่ายชำระ')
