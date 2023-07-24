# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time
from datetime import datetime

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WizardBackTax(models.TransientModel):
    _name = "wizard.back.tax"

    @api.multi
    @api.depends('item_ids')
    def _get_amount_tax(self):
        amount_tax = 0.0
        for tax in self.item_ids:
            amount_tax += tax.amount_tax
        self.amount_tax_total = amount_tax

    item_ids = fields.One2many('wizard.back.tax.line', 'order_id', string='Order Lines')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', on_delete="restrict")
    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=False, copy=False, track_visibility='onchange')
    docdat = fields.Date(string='ลงวันที่', required=True, track_visibility='onchange')
    vatprd = fields.Date(string='วันที่ยื่น',required=True)
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
    account_id = fields.Many2one('account.account', string='Account')
    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')

    amount_tax_total = fields.Float(string='ยอดรวมภาษี', compute='_get_amount_tax')
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวัน', required=False)

    @api.model
    def default_get(self, fields):
        res = super(WizardBackTax, self).default_get(
            fields)
        ineco_account_vat_obj = self.env['ineco.account.vat']
        line_ids = self.env.context.get('active_ids', False)
        tax = ineco_account_vat_obj.browse(line_ids)

        # if tax.tax_purchase_ok:
        #     raise UserError("ต้องเป็นภาษีพัก")
        items = []
        for line in tax:
            if not line.vatprd:
                line_data = {
                    'order_id': self.id,
                    'ineco_vat': line.id,
                    'account_id': line.account_id.id,
                    'invoice_id': line.invoice_id.id,
                    'name': line.name,
                    'docdat': line.docdat,
                    'partner_id': line.partner_id.id,
                    'taxid': line.taxid,
                    'depcod': line.depcod,
                    'amount_untaxed': line.amount_untaxed,
                    'amount_tax': line.amount_tax,
                    'amount_total': line.amount_total
                }
                items.append([0, 0, line_data])

        res['invoice_id'] = tax[0].invoice_id.id
        res['name'] = tax[0].name
        res['docdat'] = tax[0].docdat
        res['partner_id'] = tax[0].partner_id.id
        res['depcod'] = tax[0].depcod
        res['taxid'] = tax[0].taxid
        res['amount_untaxed'] = tax[0].amount_untaxed
        res['amount_tax'] = tax[0].amount_tax
        res['amount_total'] = tax[0].amount_total
        res['account_id'] = tax[0].account_id.id
        res['ineco_vat'] = tax[0].id
        res['item_ids'] = items

        return res


    def create_po_tax(self):
        for line in self.item_ids:
            if line.partner_id.id != self.partner_id.id:
                raise UserError(("เจ้าหนี้ไม่ตรงกัน"))

        move = self.env['account.move']
        iml = []
        vats = []
        params = self.env['ir.config_parameter'].sudo()
        vatprd = self.vatprd
        range_obj = self.env['date.range'].search([('date_start', '<=', self.vatprd),
                                                   ('date_end', '>', self.vatprd),
                                                   ])
        if range_obj:
            period_id = range_obj.id
        else:
            period_id = False
        vat_purchase_account_id = int(params.get_param('ineco_thai_v11.vat_purchase_account_id', default=False)) or False,
        for va in self.item_ids:
            va.vatprd = self.vatprd

        for vat in self:
                data = {
                    'vat_type': 'purchase',
                    'name': vat.name,
                    'docdat': vat.docdat,
                    'vatprd': self.vatprd,
                    'period_id': period_id,
                    'partner_id': vat.partner_id.id,
                    'partner_name': vat.partner_id.name,
                    'taxid': vat.taxid,
                    'depcod': vat.depcod,
                    'amount_untaxed': self.amount_untaxed,
                    'amount_tax': self.amount_tax_total,
                    'amount_total': self.amount_total,
                    'invoice_id': vat.invoice_id.id,
                    'tax_purchase_ok': True,
                    'tax_purchase_wait_ok': False,
                }

                vats.append((0, 0, data))

        move_data_vals_0 = {
            'name': u'ยื่นภาษีซื้อ',
            'partner_id': False,
            'invoice_id': False,
            'debit': self.amount_tax_total,
            'credit': 0.0,
            'payment_id': False,
            'account_id': vat_purchase_account_id,
            'vat_ids': vats
        }
        iml.append((0, 0, move_data_vals_0))
        move_data_vals_1 = {
            'name': u'ยื่นภาษีซื้อพัก',
            'partner_id': self.partner_id.id,
            'invoice_id': self.invoice_id.id,
            'debit': 0.0,
            'credit': self.amount_tax_total,
            'payment_id': False,
            'account_id': self.account_id.id,
            'ineco_vat': self.ineco_vat.id
        }
        self.ineco_vat.write({'vatprd':  self.vatprd})
        # self.invoice_id.write({'ineco_reconciled_tax': self.ineco_vat.id})
        iml.append((0, 0, move_data_vals_1))
        move_vals = {
            'ref': u'ยื่นภาษีซื้อ',
            'date':  self.vatprd,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        # new_move.post()

        view_ref = self.env['ir.model.data'].get_object_reference('ineco_thai_v11',
                                                                  'view_ineco_account_move_input_tax_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.account.move.form',
            'res_model': 'account.move',
            'res_id': new_move.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }






class WizardBackTaxLine(models.TransientModel):
    _name = 'wizard.back.tax.line'

    @api.one
    @api.depends('amount_untaxed')
    def _compute_amount_tax(self):
        # print('_compute_tax')
        if self.amount_untaxed or self.amount_tax:
            self.amount_tax = self.amount_untaxed * 0.07

    @api.one
    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_amount_total(self):
        if self.amount_untaxed or self.amount_tax:
            self.amount_total = self.amount_untaxed + self.amount_tax

    order_id = fields.Many2one('wizard.back.tax', string='Line Tax', ondelete='cascade')

    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=True, copy=False, track_visibility='onchange')
    docdat = fields.Date(string='ลงวันที่', required=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี',size=13, required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี',compute='_compute_amount_tax',store=True)
    amount_total = fields.Float(string='ยอดเงินรวม',compute='_compute_amount_total',store=True)


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for line in self:
            line.taxid = line.partner_id.vat
            line.depcod = line.partner_id.branch_no