# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class AccountMove(models.Model):

    _inherit = "account.move"

    payment_ids = fields.One2many('ineco.customer.payment', 'move_id', string=u'รับชำระ',track_visibility='onchange')
    deposit_ids = fields.One2many('ineco.customer.deposit', 'move_id', string=u'รับมัดจำ',track_visibility='onchange')
    date_due = fields.Date(string=u'วันที่รับเงิน', track_visibility='onchange')
    detail = fields.Char(related='line_ids.name', string=u'รายละเอียด')
    invoice_id = fields.Many2one('account.invoice', related='line_ids.invoice_id', string="เลขที่เอกสาร")
    # is_change_number = fields.Boolean(string='เปลี่ยนเลขเอกสาร', default=False)

    @api.multi
    def button_cancel_input(self):
        self.button_cancel()
        for line in self.line_ids:
            line.ineco_vat.write({'vatprd':False})
            line.invoice_id.write({'ineco_reconciled_tax': False})

        self.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def update_move_foreign(self):
        iml = []
        move_data_vals = {
            'debit': 0.0,
            'credit': abs(1),
            'account_id':1,
            'name': 'ส่วนต่าง',
        }
        iml.append((0, 0, move_data_vals))

        move_data_vals = {
            'debit': abs(1),
            'credit': 0.0,
            'account_id':1,
            'name': 'ส่วนต่าง',
            # 'invoice_id': self.id
        }
        iml.append((0, 0, move_data_vals))

        self.move_id.sudo().write({'line_ids': iml})




    @api.multi
    def _post_validate(self):
        res = super(AccountMove, self)._post_validate()
        for move in self:
            if move.line_ids:
                for line in move.line_ids:
                    if line.tax_ok:
                        total_vat = max(line.debit, line.credit)
                        check_vat = 0.0
                        if not (line.move_id.payment_ids or line.move_id.deposit_ids) and line.vat_ids:
                            for vat in line.vat_ids:
                                check_vat += abs(vat.amount_tax)
                            if round(total_vat, 2) != round(check_vat, 2):
                                raise UserError(u'ยอดภาษีไม่ตรง หรือยังคีย์ไม่ครบ')
                    if line.wht_ok:
                        total_wht = max(line.debit, line.credit)
                        check_wht = 0.0
                        if not (line.move_id.payment_ids or line.move_id.deposit_ids) and line.wht_ids:
                            for vat in line.wht_ids:
                                check_wht += vat.tax
                            if round(total_wht, 2) != round(check_wht, 2):
                                raise UserError(u'ยอดภาษีหัก ณ ที่จ่ายไม่ตรง หรือยังคีย์ไม่ครบ')
                    if line.cheque_ids:
                        total_cheque = max(line.debit, line.credit)
                        check_cheque = 0.0
                        if not line.move_id.payment_ids or line.move_id.deposit_ids:
                            for vat in line.cheque_ids:
                                check_cheque += vat.amount
                            if total_cheque != check_cheque:
                                raise UserError(u'ยอดเช็คไม่ตรง หรือยังคีย์ไม่ครบ')
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _order = "debit desc, credit desc"

    @api.one
    @api.depends('account_id')
    def _get_tax(self):
        self.tax_ok = self.account_id.tax_sale_ok or self.account_id.tax_purchase_ok or False

    @api.one
    @api.depends('account_id')
    def _get_cheque(self):
        self.cheque_ok = self.account_id.cheque_in_ok or self.account_id.cheque_out_ok or False

    @api.one
    @api.depends('account_id')
    def _get_wht(self):
        self.wht_ok = self.account_id.wht_sale_ok or self.account_id.wht_purchase_ok or False
        self.wht_sale_ok = self.account_id.wht_sale_ok or False
        self.wht_purchase_ok = self.account_id.wht_purchase_ok or False

    @api.one
    @api.depends('account_id')
    def _get_account_type(self):
        self.receivable_ok = self.account_id.user_type_id.type == 'receivable' or False
        self.payable_ok = self.account_id.user_type_id.type == 'payable' or False

    #inherit
    @api.one
    @api.depends('move_id')
    def _compute_parent_state(self):
        self.parent_state = self.move_id.state

    # inherit (replace old method)
    @api.model
    def default_get(self, fields):
        rec = {}
        if 'line_ids' not in self._context:
            return rec
        balance = 0
        for line in self._context['line_ids']:
            if line[2]:
                balance += line[2].get('debit', 0.0) - line[2].get('credit', 0.0)
        if balance < 0:
            rec.update({'debit': -balance})
        if balance > 0:
            rec.update({'credit': balance})
        return rec

    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')
    vat_ids = fields.One2many('ineco.account.vat', 'move_line_id', string='Vat' , on_delete="restrict")
    wht_ids = fields.One2many('ineco.wht', 'move_line_id', string='With Holding Tax', on_delete="restrict")
    cheque_ids = fields.One2many('ineco.cheque', 'move_line_id', string='Cheques', on_delete="restrict")
    tax_ok = fields.Boolean(string='Tax Ok', compute='_get_tax', readonly=True )
    wht_ok = fields.Boolean(string='WHT Ok', compute='_get_wht', readonly=True)
    wht_sale_ok = fields.Boolean(string='WHT Sale Ok', compute='_get_wht', readonly=True)
    wht_purchase_ok = fields.Boolean(string='WHT Purchase Ok', compute='_get_wht', readonly=True)
    receivable_ok = fields.Boolean(string='Receivable Ok', compute='_get_account_type', readonly=True)
    payable_ok = fields.Boolean(string='Payable Ok', compute='_get_account_type', readonly=True)
    cheque_ok = fields.Boolean(string='Cheque Ok', compute='_get_cheque', readonly=True)
    date_maturity = fields.Date(string='Due date', index=True, required=False,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    foreign = fields.Boolean(u'ต่างประเทศ')
    foreign_receivable = fields.Float(u'รับต่างประเทศ')

    def auto_reconcile_lines(self):
        """
        This function iterates on the recordset given as parameter as long as it
        can find a debit and a credit to reconcile together. It returns the
        recordset of the account move lines that were not reconciled during
        the process.
        :return: account.move.line recordset
        """
        all_moves = self
        while all_moves:
            # print('all_moves',all_moves)
            sm_debit_move, sm_credit_move = all_moves._get_pair_to_reconcile()
            # print(sm_debit_move, sm_credit_move)
            #there is no more pair to reconcile so return what move_line are left
            if not sm_credit_move or not sm_debit_move:
                return all_moves
            company_currency_id = all_moves[0].account_id.company_id.currency_id
            account_curreny_id = all_moves[0].account_id.currency_id
            field = (account_curreny_id and company_currency_id != account_curreny_id) and 'amount_residual_currency' or 'amount_residual'
            if not sm_debit_move.debit and not sm_debit_move.credit:
                #both debit and credit field are 0, consider the amount_residual_currency field because it's an exchange difference entry
                field = 'amount_residual_currency'
            if all_moves[0].currency_id and all([x.currency_id == all_moves[0].currency_id for x in all_moves]):
                #all the lines have the same currency, so we consider the amount_residual_currency field
                field = 'amount_residual_currency'
            if all_moves._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
                field = 'amount_residual'
            elif all_moves._context.get('skip_full_reconcile_check') == 'amount_currency_only':
                field = 'amount_residual_currency'
            #Reconcile the pair together
            amount_reconcile = min(sm_debit_move[field], -sm_credit_move[field])
            #Remove from recordset the one(s) that will be totally reconciled
            if amount_reconcile == sm_debit_move[field]:
                all_moves -= sm_debit_move
            if amount_reconcile == -sm_credit_move[field]:
                all_moves -= sm_credit_move

            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if sm_debit_move.currency_id == sm_credit_move.currency_id:
                if sm_debit_move.currency_id.id:
                    currency = sm_credit_move.currency_id.id
                    amount_reconcile_currency = min(sm_debit_move.amount_residual_currency, -sm_credit_move.amount_residual_currency)

            else:
                if not sm_debit_move.currency_id or not sm_credit_move.currency_id:
                    # If only one of debit_move or credit_move has a secondary currency, also record the converted amount
                    # in that secondary currency in the partial reconciliation. That allows the exchange difference entry
                    # to be created, in case it is needed.
                    company_currency = sm_debit_move.company_id.currency_id
                    currency = sm_debit_move.currency_id or sm_credit_move.currency_id
                    currency_date = sm_debit_move.currency_id and sm_credit_move.date or sm_debit_move.date
                    if sm_credit_move.foreign:
                        amount_reconcile_currency = sm_credit_move.foreign_receivable
                    else:
                        amount_reconcile_currency = company_currency.with_context(date=currency_date).compute(amount_reconcile, currency)
                    currency = currency.id
            if sm_credit_move.foreign:
                amount_reconcile = amount_reconcile
            else:
                amount_reconcile = min(sm_debit_move.amount_residual, -sm_credit_move.amount_residual)

            if all_moves._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
                amount_reconcile_currency = 0.0

            all_move = all_moves.env['account.partial.reconcile'].create({
                'debit_move_id': sm_debit_move.id,
                'credit_move_id': sm_credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })
            # print('all_move',all_move)
        return all_moves

    @api.multi
    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            if line.ref:
                name = "{} ({}) - {} บาท".format(line.move_id.name, line.ref, line.debit or line.credit)
                result.append((line.id, name))
            else:
                name = "{} - {} บาท".format(line.move_id.name, line.debit or line.credit)
                result.append((line.id, name))
        return result
