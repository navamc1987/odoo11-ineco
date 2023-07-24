# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import datetime

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import json
import re
import uuid

from lxml import etree
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode

from odoo import api, exceptions, fields, models, _
from odoo.tools import float_is_zero, float_compare, pycompat

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

from odoo.addons import decimal_precision as dp
import logging

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
    'expense': 'general'
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',  # Customer Invoice
    'in_invoice': 'in_refund',  # Vendor Bill
    'out_refund': 'out_invoice',  # Customer Credit Note
    'in_refund': 'in_invoice',  # Vendor Credit Note
    'expense': 'expense',
}


class AccountInvoiceLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'

    stock_move_id = fields.Many2one('stock.move', 'move', readonly=True, copy=False)
    picking_id = fields.Many2one('stock.picking', related='stock_move_id.picking_id', string='picking', store=False,
                                 readonly=True)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _order = "date_invoice desc, number desc"

    @api.model
    def _get_payments_vals(self):
        if not self.payment_move_line_ids:
            return []
        payment_vals = []
        currency_id = self.currency_id
        for payment in self.payment_move_line_ids:
            payment_currency_id = False
            if self.type in ('out_invoice', 'in_refund', 'expense'):
                amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                amount_currency = sum(
                    [p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                               payment.matched_debit_ids]) and payment.matched_debit_ids[
                                              0].currency_id or False
            elif self.type in ('in_invoice', 'out_refund'):
                amount = sum(
                    [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                       p.credit_move_id in self.move_id.line_ids])
                if payment.matched_credit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                               payment.matched_credit_ids]) and payment.matched_credit_ids[
                                              0].currency_id or False
            # get the payment value in invoice currency
            if payment_currency_id and payment_currency_id == self.currency_id:
                amount_to_show = amount_currency
            else:
                amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                        self.currency_id)
            if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                continue
            payment_ref = payment.move_id.name
            invoice_view_id = None
            if payment.move_id.ref:
                payment_ref += ' (' + payment.move_id.ref + ')'
            if payment.invoice_id:
                invoice_view_id = payment.invoice_id.get_formview_id()
            payment_vals.append({
                'name': payment.name,
                'journal_name': payment.journal_id.name,
                'amount': amount_to_show,
                'currency': currency_id.symbol,
                'digits': [69, currency_id.decimal_places],
                'position': currency_id.position,
                'date': payment.date,
                'payment_id': payment.id,
                'account_payment_id': payment.payment_id.id,
                'invoice_id': payment.invoice_id.id,
                'invoice_view_id': invoice_view_id,
                'move_id': payment.move_id.id,
                'ref': payment_ref,
            })
        return payment_vals

    @api.one
    @api.depends()
    def _get_move_lines(self):
        partial_lines = self.env['account.move.line']
        for line in self.move_id.line_ids:
            partial_lines += line
        self.account_move_lines = partial_lines

    @api.model
    def _default_journal(self):
        if self._context.get('expense', False):
            inv_type = self._context.get('type', 'expense')
            inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
            company_id = self._context.get('company_id', self.env.user.company_id.id)
            domain = [
                ('type', 'in', ['purchase']),
                ('expense', '=', True),
                ('company_id', '=', company_id),
            ]
            return self.env['account.journal'].search(domain, limit=1)
        else:
            if self._context.get('default_journal_id', False):
                return self.env['account.journal'].browse(self._context.get('default_journal_id'))
            inv_type = self._context.get('type', 'out_invoice')
            inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
            company_id = self._context.get('company_id', self.env.user.company_id.id)
            domain = [
                ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
                ('company_id', '=', company_id),
            ]
            return self.env['account.journal'].search(domain, limit=1)

    @api.multi
    @api.depends('tax_line_ids')
    def _compute_tax_purchase_wait_ok(self):
        for iv in self:
            move_ids = iv.mapped('tax_line_ids')
            wait_ok = []
            for tax in move_ids:
                wait_ok.append(tax.tax_id.tax_break)
            is_wait_ok = True in wait_ok
            iv.tax_purchase_wait_ok = is_wait_ok

    taxes_id = fields.Many2one('account.tax', string='Taxes')

    account_move_lines = fields.Many2many('account.move.line', string='General Ledgers', compute='_get_move_lines')

    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทกิจกรรม', related='journal_id.type_vat', )
    billing_id = fields.Many2one('ineco.billing', string=u'ใบวางบิล', copy=False)
    deposit_ids = fields.One2many('ineco.customer.payment.deposit', 'invoice_id', string=u'มัดจำ')
    supplier_deposit_ids = fields.One2many('ineco.supplier.payment.deposit', 'invoice_id', string=u'จ่ายมัดจำ')
    partner_code = fields.Char(string=u'รหัส', related='partner_id.ref', readonly=True)
    ineco_reconciled_tax = fields.Many2one('ineco.account.vat', string='ineco_reconciled')
    select_pay = fields.Boolean('ทำจ่าย/รับชำระ')

    expense = fields.Boolean(u'บันทึกค่าใช้จ่าย',
                             related='journal_id.expense',
                             track_visibility='onchange',
                             store=True, readonly=True,
                             related_sudo=False
                             )
    ex_sale = fields.Boolean(u'ขายตัวอย่าง',
                             related='journal_id.ex',
                             track_visibility='onchange',
                             store=True, readonly=True,
                             related_sudo=False
                             )

    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ('expense', u'ค่าใช้จ่าย')
    ], readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')
    # journal_id = fields.Many2one('account.journal', string='Journal',
    #                              required=True, readonly=True, states={'draft': [('readonly', False)]},
    #                              default=_default_journal,
    #                              domain="[('expense', 'in', {'expense': [True],'out_invoice': [False], 'out_refund': [False], 'in_refund': [False], 'in_invoice': [False]}.get(type, [])),('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase'],'expense': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]"
    #                              )

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal,
                                 domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase'],'expense': ['purchase'],'petty': ['petty']}.get(type, [])), ('company_id', '=', company_id)]"
                                 )

    ineco_vat_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีพัก',
                                    domain=[('tax_purchase_wait_ok', '=', True)]
                                    # domain="[('tax_purchase_wait_ok','=',True)]"
                                    )
    ineco_vat_purchase_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีซื้อ',
                                             domain=[('tax_purchase_ok', '=', True), ('move_line_id', '!=', False)]
                                             # domain="[('tax_purchase_wait_ok','=',True)]"
                                             )
    is_vat = fields.Boolean(u'ยื่นยันภาษี', track_visibility='onchange', )

    tax_purchase_wait_ok = fields.Boolean(string=u'Purchase Tax wait', copy=False,
                                          compute="_compute_tax_purchase_wait_ok",
                                          track_visibility='onchange',
                                          store=False)

    ineco_vat_sale_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีซื้อ',
                                         domain=[('tax_sale_ok', '=', True), ('move_line_id', '!=', False)]
                                         # domain="[('tax_purchase_wait_ok','=',True)]"
                                         )

    @api.model
    def daily_update_invoice_open(self, date_invoice, limit):
        print(date_invoice, limit)
        ivs = self.env['account.invoice'].search([('state', '=', 'draft'),
                                                  ('date_invoice', '>=', date_invoice)
                                                  ], limit=limit)
        for iv in ivs:
            print(iv)
            iv.action_invoice_open()

    @api.model
    def daily_update_action_invoice_draft(self):
        ivs = self.env['account.invoice'].search([('state', '!=', 'draft'),
                                                  # ('date_invoice', '>=', date_invoice)
                                                  ])
        for iv in ivs:
            print(iv)
            iv.action_invoice_cancel()
            iv.action_invoice_draft()

    @api.multi
    def action_invoice_cancel_ex(self):
        self.move_id.button_cancel()
        self.action_cancel()
        return True

    @api.multi
    def button_vat_ok(self):
        self.is_vat = True
        return True

    @api.multi
    def button_vat_edit(self):
        self.is_vat = False
        return True

    @api.multi
    def _update_ineco_vatLmol(self, move):
        for vat in self.ineco_vat_ids:
            move_line = self.env['account.move.line'].search([
                ('move_id', '=', move.id),
                ('account_id', '=', vat.account_id.id)])
            vat.write({'tax_purchase_wait_ok': True, 'move_line_id': move_line.id})

    @api.multi
    def InecoCreateVat(self):
        if self.state == 'draft':
            for line in self.tax_line_ids:
                signed = 1
                vat_type = False
                if self.type in ['out_refund', 'in_refund']:
                    signed = -1
                if self.type in ['in_invoice', 'in_refund']:
                    vat_type = 'purchase'
                else:
                    vat_type = 'sale'

                move_line = self.env['account.move.line'].search([
                    ('invoice_id', '=', self.id),
                    ('account_id', '=', line.account_id.id)])

                # print('move_line',move_line,line.account_id.wait)

                vatprd = False
                if line.account_id.wait:

                    vatprd = self.date_invoice
                    range_obj = self.env['date.range'].search([('date_start', '<=', self.date_invoice),
                                                               ('date_end', '>', self.date_invoice),
                                                               ])
                    if range_obj:
                        period_id = range_obj.id
                    else:
                        period_id = False

                    vat_obj = self.env['ineco.account.vat']
                    vat = vat_obj._ineco_create_vat(line=False, inv=self, vatprd=False, period_id=period_id,
                                                    signed=signed,
                                                    vat_type=vat_type, account_id=line.account_id.id)
                    # print('222',vat)

    @api.multi
    def SelectPay(self):
        for record in self:
            record.select_pay = not record.select_pay

    @api.multi
    def check_deposit(self):
        if self.supplier_deposit_ids:
            for de in self.supplier_deposit_ids:
                if de.amount_residual < de.amount_receipt:
                    raise UserError(f'รายการมัดจำยอดชำระมากกว่ายอดคงเหลือ เลขที่{de.name}')
                if de.amount_residual <= 0.0:
                    raise UserError(f'รายการมัดจำถูกต้องใช้ไป หมดแล้ว เลขที่{de.name}')

        if self.deposit_ids:
            for de in self.deposit_ids:
                if de.amount_residual < de.amount_receipt:
                    raise UserError(f'รายการมัดจำยอดชำระมากกว่ายอดคงเหลือ เลขที่{de.name}')
                if de.amount_residual <= 0.0:
                    raise UserError(f'รายการมัดจำถูกต้องใช้ไป หมดแล้ว เลขที่{de.name}')

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.type in ('expense'):
            self.account_id = self.journal_id.default_credit_account_id.id
        return res

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_deposit(self):
        warning = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        deposits = self.env['ineco.supplier.deposit'].search([('partner_id', '=', p.id),
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
                'title': _("มีเงินมัดจ่ายมัดจำ %s") % p.name,
                'message': note2
            }
        res = {}
        if warning:
            res['warning'] = warning

        return res

    @api.onchange('taxes_id')
    def onchange_tax(self):
        for ail in self.invoice_line_ids:
            ail.invoice_line_tax_ids = [(6, 0, [x.id for x in self.taxes_id])]
        return

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.type in ('out_invoice') and self.journal_id.ex:
            dr = self.journal_id.default_debit_account_id.id
            self.account_id = dr

        if self.type in ('out_refund'):
            cr = self.journal_id.default_credit_account_id.id
            dr = self.journal_id.default_debit_account_id.id
            self.account_id = cr
            for ail in self.invoice_line_ids:
                ail.account_id = dr
            return
        if self.type in ('in_refund'):
            cr = self.journal_id.default_credit_account_id.id
            dr = self.journal_id.default_debit_account_id.id
            self.account_id = dr
            for ail in self.invoice_line_ids:
                ail.account_id = cr
            return
        if self.type in ('expense'):
            cr = self.journal_id.default_credit_account_id.id
            dr = self.journal_id.default_debit_account_id.id
            self.account_id = cr
            for ail in self.invoice_line_ids:
                ail.account_id = dr
            return

    @api.multi
    def update_move_foreign(self):
        rate = 0.0
        debit = 0.0
        credit = 0.0
        iml = []

        if self.type in ['out_invoice'] and self.journal_id.foreign:
            account_move_obj = self.env['account.move']
            rate = round((self.rate * self.amount_total), 2)
            for line in self.move_id.line_ids:
                debit += line.debit
            diff_debit = round((debit - rate), 2)
            if diff_debit != 0:
                # self.move_id.button_cancel()
                move_line_debit_obj = self.env['account.move.line'].search([('move_id', '=', self.move_id.id)],
                                                                           order='debit desc', limit=1)
                line_debit = move_line_debit_obj.debit - diff_debit

                move_line_credit_obj = self.env['account.move.line'].search([('move_id', '=', self.move_id.id)],
                                                                            order='credit desc', limit=1)
                line_credit = move_line_credit_obj.credit - diff_debit

                if move_line_debit_obj:
                    move_data_vals = {
                        'id': move_line_debit_obj.id,
                        'debit': 0.0,
                        'credit': abs(diff_debit),
                        'account_id': move_line_debit_obj.account_id.id,
                        'name': 'ส่วนต่าง',
                        # 'invoice_id': self.id
                    }
                    iml.append((0, 0, move_data_vals))
                if move_line_credit_obj:
                    move_data_vals = {
                        'id': move_line_debit_obj.id,
                        'debit': abs(diff_debit),
                        'credit': 0.0,
                        'account_id': move_line_credit_obj.account_id.id,
                        'name': 'ส่วนต่าง',
                        # 'invoice_id': self.id
                    }
                    iml.append((0, 0, move_data_vals))
                self.move_id.sudo().write({'line_ids': iml})
            # self.move_id.post()

    @api.multi
    def action_move_create(self):

        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']
        for inv in self:
            vat = False
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            if not inv.date_due:
                inv.with_context(ctx).write({'date_due': inv.date_invoice})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = \
                    inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total,
                                                                                                                inv.date_invoice)[
                        0]
                res_amount_currency = total_currency
                ctx['date'] = inv.date or inv.date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            for line in move.line_ids:
                signed = 1
                vat_type = False
                if inv.type in ['out_refund', 'in_refund']:
                    signed = -1
                if inv.type in ['in_invoice', 'in_refund']:
                    vat_type = 'purchase'
                else:
                    vat_type = 'sale'

                vatprd = False
                if line.account_id.tax_sale_ok or line.account_id.tax_purchase_ok:
                    vatprd = inv.date_invoice
                if line.account_id.tax_sale_ok or line.account_id.tax_purchase_ok:

                    range_obj = self.env['date.range'].search([('date_start', '<=', inv.date_invoice),
                                                               ('date_end', '>', inv.date_invoice),
                                                               ])
                    if range_obj:
                        period_id = range_obj.id
                    else:
                        period_id = False

                    vat_obj = self.env['ineco.account.vat']
                    vat = vat_obj._ineco_create_vat(line=line, inv=inv, vatprd=vatprd, period_id=period_id,
                                                    signed=signed, vat_type=vat_type, account_id=False)
                self._update_ineco_vatLmol(move)
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            doc_name = ''
            if vat_type == 'sale':
                doc_name = move.name
            else:
                doc_name = inv.reference or ''
            if vat:
                vat.name = doc_name
            # inv.update_move_foreign()
        return True

    @api.multi
    def action_invoice_open(self):
        # if self.partner_id.vat:
        #     lenPid = len(self.partner_id.vat)
        #     if lenPid != 13:
        #         raise ValidationError("คุณใส่ Tax ID %s ตัว ไม่ตรงตามกำหนด (13 ตัวเลข)" % lenPid)
        # if not self.partner_id.vat:
        #     raise UserError("ไม่เลขที่ผู้เสียภาษี")

        if self.tax_purchase_wait_ok and not self.is_vat:
            raise UserError("ต้องสร้างภาษีพักแล้วยืยันก่อน")

        # if self.partner_id.branch_no:
        #     lenTax = len(self.partner_id.branch_no)
        #     if lenTax != 5:
        #         raise ValidationError("คุณใส่ Branch No %s ตัว ไม่ตรงตามกำหนด(5 ตัวเลข)" % lenTax)

        # if not self.partner_id.branch_no:
        #     raise UserError("ไม่ระบุสาขา ลูกค้า /ผู้จำหน่าย")

        if self.type in ('out_invoice'):
            params = self.env['ir.config_parameter'].sudo()
            for invoice in self:
                sql_check_single_tax = """
                 select distinct tax_id from account_invoice_line_tax ailt
                 join account_invoice_line ail on ail.id = ailt.invoice_line_id
                 where ail.invoice_id = %s
                 and tax_id is not null
                 """ % (invoice.id)
                self._cr.execute(sql_check_single_tax)
                taxes = self.env.cr.dictfetchall()
                if len(taxes) > 1:
                    raise UserError("ภาษีมีปัญหา! ใบกำกับใบนี้มีการกำหนดภาษีมากกว่า 1 ชนิด.")
                tax_id = False
                if taxes:
                    tax_id = taxes[0]['tax_id'] or False
                if tax_id:
                    tax_ids = []
                    for des in self.deposit_ids:
                        unearned_income_account_id = int(
                            params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
                        tax_ids.append((4, tax_id, None))
                        line = self.env['account.invoice.line']
                        line.create({
                            'invoice_id': invoice.id,
                            'name': des.name.name,
                            'account_id': unearned_income_account_id,
                            'price_unit': -des.amount_receipt,
                            'invoice_line_tax_ids': tax_ids,
                        })

                    invoice.compute_taxes()
                else:
                    for des in self.deposit_ids:
                        unearned_income_account_id = int(
                            params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
                        line = self.env['account.invoice.line']
                        line.create({
                            'invoice_id': invoice.id,
                            'name': des.name.name,
                            'account_id': unearned_income_account_id,
                            'price_unit': -des.amount_receipt,
                            'invoice_line_tax_ids': False,
                        })
                        self.check_deposit()
                    invoice.compute_taxes()

        if self.type in ('in_invoice'):
            params = self.env['ir.config_parameter'].sudo()
            for invoice in self:
                sql_check_single_tax = """
                 select distinct tax_id from account_invoice_line_tax ailt
                 join account_invoice_line ail on ail.id = ailt.invoice_line_id
                 where ail.invoice_id = %s
                 and tax_id is not null
                 """ % (invoice.id)
                self._cr.execute(sql_check_single_tax)
                taxes = self.env.cr.dictfetchall()
                if len(taxes) > 1:
                    raise UserError("ภาษีมีปัญหา! ใบกำกับใบนี้มีการกำหนดภาษีมากกว่า 1 ชนิด.")
                tax_id = False
                if taxes:
                    tax_id = taxes[0]['tax_id'] or False
                if tax_id:
                    tax_ids = []
                    # for line in invoice.invoice_line_ids:
                    for des in self.supplier_deposit_ids:
                        unearned_income_account_id = int(
                            params.get_param('ineco_thai_v11.unearned_expense_account_id', default=False)) or False,
                        tax_ids.append((4, tax_id, None))
                        line = self.env['account.invoice.line']
                        line.create({
                            'invoice_id': invoice.id,
                            'name': des.name.name,
                            'account_id': unearned_income_account_id,
                            'price_unit': -des.amount_receipt,
                            'invoice_line_tax_ids': tax_ids,
                        })
                        self.check_deposit()
                    invoice.compute_taxes()
                else:
                    for des in self.deposit_ids:
                        unearned_income_account_id = int(
                            params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
                        line = self.env['account.invoice.line']
                        line.create({
                            'invoice_id': invoice.id,
                            'name': des.name.name,
                            'account_id': unearned_income_account_id,
                            'price_unit': -des.amount_receipt,
                            'invoice_line_tax_ids': False,
                        })
                        self.check_deposit()
                    invoice.compute_taxes()

        for invoice in self:
            sql_check_single_tax = """
             select distinct tax_id from account_invoice_line_tax ailt
             join account_invoice_line ail on ail.id = ailt.invoice_line_id
             where ail.invoice_id = %s
             and tax_id is not null
             """ % (invoice.id)
            self._cr.execute(sql_check_single_tax)
            taxes = self.env.cr.dictfetchall()
            if len(taxes) > 1:
                raise UserError("ภาษีมีปัญหา! ใบกำกับใบนี้มีการกำหนดภาษีมากกว่า 1 ชนิด.")
            tax_id = False
            if taxes:
                tax_id = taxes[0]['tax_id'] or False
            if tax_id:
                tax = self.env['account.tax'].browse(tax_id)
                if tax.price_include or tax.include_base_amount:
                    amount_untaxed = 0.0
                    amount_tax = 0.0
                    amount_total = 0.0
                    for line in invoice.invoice_line_ids:
                        amount_total += line.price_total
                    amount_tax = round(amount_total * 7 / 107, 2)
                    amount_untaxed = amount_total - amount_tax
                    diff_amount_untaxed = 0.0
                    diff_amount_tax = 0.0
                    if invoice.amount_untaxed != amount_untaxed:
                        diff_amount_untaxed = invoice.amount_untaxed - amount_untaxed
                    if invoice.amount_tax != amount_tax:
                        diff_amount_tax = invoice.amount_tax - amount_tax
                    sql_invoice = """
                                        update account_invoice
                                        set amount_untaxed = %s, amount_tax = %s, amount_total = %s, residual = %s
                                        where id = %s
                                    """ % (amount_untaxed, amount_tax, amount_total, amount_total, invoice.id)
                    self._cr.execute(sql_invoice)

                    sql_invoice_tax = """
                                    update account_invoice_tax
                                    set  amount = (select amount_tax from account_invoice where id = %s)
                                    where invoice_id = %s
                                                    """ % (invoice.id, invoice.id)
                    self._cr.execute(sql_invoice_tax)
                    if invoice.type in ('out_invoice', 'in_refund'):
                        sql_update_partner = """
                            update account_move_line
                            set debit = %s, amount_currency = %s
                            where account_id = (select account_id from account_invoice where id = %s)
                              and move_id = (select move_id from account_invoice where id = %s)
                        """ % (amount_total, amount_total, invoice.id, invoice.id)
                        self._cr.execute(sql_update_partner)
                        sql_update_tax = """
                            update account_move_line
                            set credit = %s
                            where account_id = (select account_id from account_tax where id = %s)
                              and move_id = (select move_id from account_invoice where id = %s)
                            """ % (amount_tax, tax.id, invoice.id)
                        self._cr.execute(sql_update_tax)
                        sql_update_product = """
                        update account_move_line
                            set credit = credit - %s
                            where id = 
                            (
                                select id from account_move_line
                                where move_id = (select move_id from account_invoice where id = %s)
                                  and account_id = (select account_id from account_invoice_line where invoice_id = %s limit 1) limit 1
                            )
                        """ % (round(diff_amount_untaxed, 2), invoice.id, invoice.id)
                        self._cr.execute(sql_update_product)
                    elif invoice.type in ('in_invoice', 'out_refund'):
                        sql_update_partner = """
                            update account_move_line
                            set credit = %s, amount_currency = %s
                            where account_id = (select account_id from account_invoice where id = %s)
                              and move_id = (select move_id from account_invoice where id = %s)
                        """ % (amount_total, amount_total, invoice.id, invoice.id)
                        self._cr.execute(sql_update_partner)
                        sql_update_tax = """
                            update account_move_line
                            set debit = %s
                            where account_id = (select account_id from account_tax where id = %s)
                              and move_id = (select move_id from account_invoice where id = %s)
                            """ % (amount_tax, tax.id, invoice.id)
                        # print (sql_update_tax)
                        self._cr.execute(sql_update_tax)
                        sql_update_product = """
                        update account_move_line
                            set debit = debit - %s
                            where id = 
                            (
                                select id from account_move_line
                                where move_id = (select move_id from account_invoice where id = %s)
                                  and account_id = (select account_id from account_invoice_line where invoice_id = %s limit 1) limit 1
                            )
                        """ % (round(diff_amount_untaxed, 2), invoice.id, invoice.id)
                        self._cr.execute(sql_update_product)

        res = super(AccountInvoice, self).action_invoice_open()
        return res

    @api.multi
    def action_invoice_cancel(self):
        if self.ineco_reconciled_tax:
            raise ValidationError(u'ไม่สามารถยกเลิกแก้ไขได้ เนื่องจากทำการยืนภาษีซื้อแล้ว')
        res = super(AccountInvoice, self).action_invoice_cancel()
        if self.type in ('out_invoice'):
            for invoice in self:
                for des in self.deposit_ids:
                    sql_line_ids = """
                                         DELETE FROM account_invoice_line
                                        where invoice_id  =  (select id from account_invoice where id  = %s)
                                        and name = '%s'

                                         """ % (invoice.id, des.name.name)
                    self._cr.execute(sql_line_ids)

                    sql_deposit_ids = """
                                         DELETE FROM ineco_customer_payment_deposit
                                        where invoice_id  =  (select id from account_invoice where id  = %s)
                                         """ % (invoice.id)
                    self._cr.execute(sql_deposit_ids)
        if self.type in ('in_invoice'):
            for invoice_s in self:
                for des in self.supplier_deposit_ids:
                    ql_supplier_line_ids = """
                                        DELETE FROM account_invoice_line
                                       where invoice_id  =  (select id from account_invoice where id  = %s)
                                       and name = '%s'
                                        """ % (invoice_s.id, des.name.name)
                    self._cr.execute(ql_supplier_line_ids)
                    sql_supplier_deposit_ids = """
                                        DELETE FROM ineco_supplier_payment_deposit
                                       where invoice_id  =  (select id from account_invoice where id  = %s)
                                        """ % (invoice_s.id)
                    self._cr.execute(sql_supplier_deposit_ids)
        for vat in self.ineco_vat_ids:
            if vat.vatprd:
                raise UserError(f'ภาษีมีการกลับยื่นไปแล้ว \n'
                                f'กรุณายกเลิกราการก่อน')
            vat.unlink()
        self.is_vat = False

        return res

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            tax = tax_line.tax_id
            if tax.amount_type == "group":
                for child_tax in tax.children_tax_ids:
                    done_taxes.append(child_tax.id)
            res.append({
                'invoice_tax_line_id': tax_line.id,
                'tax_line_id': tax_line.tax_id.id,
                'type': 'tax',
                'name': tax_line.name,
                'price_unit': tax_line.amount_total,
                'quantity': 1,
                'price': tax_line.amount_total,
                'account_id': tax_line.account_id.id,
                'account_analytic_id': tax_line.account_analytic_id.id,
                'invoice_id': self.id,
                'tax_ids': [(6, 0, list(done_taxes))] if tax_line.tax_id.include_base_amount else []
            })
            done_taxes.append(tax.id)
        return res

    @api.onchange('cash_rounding_id', 'invoice_line_ids', 'tax_line_ids')
    def _onchange_cash_rounding(self):
        # Drop previous cash rounding lines
        lines_to_remove = self.invoice_line_ids.filtered(lambda l: l.is_rounding_line)
        if lines_to_remove:
            self.invoice_line_ids -= lines_to_remove

        # Clear previous rounded amounts
        # for tax_line in self.tax_line_ids:
        #    if tax_line.amount_rounding != 0.0:
        #        tax_line.amount_rounding = 0.0

        if self.cash_rounding_id and self.type in ('out_invoice', 'out_refund'):
            rounding_amount = self.cash_rounding_id.compute_difference(self.currency_id, self.amount_total)
            if not self.currency_id.is_zero(rounding_amount):
                if self.cash_rounding_id.strategy == 'biggest_tax':
                    # Search for the biggest tax line and add the rounding amount to it.
                    # If no tax found, an error will be raised by the _check_cash_rounding method.
                    if not self.tax_line_ids:
                        return
                    biggest_tax_line = None
                    for tax_line in self.tax_line_ids:
                        if not biggest_tax_line or tax_line.amount > biggest_tax_line.amount:
                            biggest_tax_line = tax_line
                    # biggest_tax_line.amount_rounding += rounding_amount
                elif self.cash_rounding_id.strategy == 'add_invoice_line':
                    # Create a new invoice line to perform the rounding
                    rounding_line = self.env['account.invoice.line'].new({
                        'name': self.cash_rounding_id.name,
                        'invoice_id': self.id,
                        'account_id': self.cash_rounding_id.account_id.id,
                        'price_unit': rounding_amount,
                        'quantity': 1,
                        'is_rounding_line': True,
                        'sequence': 9999  # always last line
                    })

                    # To be able to call this onchange manually from the tests,
                    # ensure the inverse field is updated on account.invoice.
                    if not rounding_line in self.invoice_line_ids:
                        self.invoice_line_ids += rounding_line

    @api.model
    def create(self, vals):
        if not vals.get('date_invoice', False):
            if 'origin' in vals:
                picking = self.env['stock.picking'].sudo().search([('origin', '=', vals['origin'])],
                                                                  order='name desc', limit=1)
                if picking:
                    vals['date_invoice'] = picking.scheduled_date
                else:
                    vals['date_invoice'] = datetime.datetime.now().strftime('%Y-%m-%d')
            else:
                vals['date_invoice'] = datetime.datetime.now().strftime('%Y-%m-%d')
        res = super(AccountInvoice, self).create(vals)
        return res
