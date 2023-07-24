# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WizardInputTax(models.TransientModel):
    _name = "wizard.input.tax"

    @api.multi
    @api.depends('item_ids')
    def _get_amount_tax(self):
        amount_tax = 0.0
        for tax in self.item_ids:
            amount_tax += tax.amount_tax
        self.amount_tax = amount_tax

    item_ids = fields.One2many('wizard.input.tax.line', 'order_id', string='Order Lines')
    vatprd = fields.Date(string='วันที่ยื่น')
    amount_tax = fields.Float(string='ยอดเงินรวม', compute='_get_amount_tax', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวัน', required=True)

    @api.model
    def default_get(self, fields):
        res = super(WizardInputTax, self).default_get(
            fields)
        ineco_account_vat_obj = self.env['ineco.account.vat']
        line_ids = self.env.context.get('active_ids', False)
        tax = ineco_account_vat_obj.browse(line_ids)
        items = []
        for line in tax:
            if line.vatprd:
                not_name = u'ยังไม่ตัดจ่าย'
                raise UserError(
                    f'รายการที่จะซื้อภาษีซื้อดำเนินการแล้ว วันที่ยื่น {line.vatprd} เอกสารเลขที่ {line.reconciliation_in.supplier_payment_id.name or not_name}'
                    + '\n' + f'สถานะเอกสาร {line.reconciliation_in.supplier_payment_id.state}')
            if not line.name:
                raise UserError(f'ไม่ได้ระบุเลขที่เอกสารอ้างอิงการตั้งหนี้')
            line_data = {
                'order_id': self.id,
                'ineco_vat': line.id,
                'account_id': line.account_id.id,
                'invoice_id': line.invoice_id.id,
                'name': line.name,
                'docdat': line.docdat,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'taxid': line.taxid,
                'depcod': line.depcod,
                'amount_untaxed': line.amount_untaxed,
                'amount_tax': line.amount_tax,
                'amount_total': line.amount_total
            }
            items.append([0, 0, line_data])
            res['item_ids'] = items
        return res

    def create_po_tax(self):
        move = self.env['account.move']
        iml = []
        vats = []
        params = self.env['ir.config_parameter'].sudo()
        for line in self.item_ids:
            vat_purchase_account_id = int(
                params.get_param('ineco_thai_v11.vat_purchase_account_id', default=False)) or False,
            if self.amount_tax:
                for vat in self.item_ids:
                    data = {
                        'vat_type': 'purchase',
                        'name': vat.name,
                        'docdat': vat.docdat,
                        'vatprd': self.vatprd,
                        'partner_id': vat.partner_id.id,
                        'partner_name': vat.partner_name,
                        'taxid': vat.taxid,
                        'depcod': vat.depcod,
                        'amount_untaxed': vat.amount_untaxed,
                        'amount_tax': vat.amount_tax,
                        'amount_total': vat.amount_total,
                        'invoice_id': vat.invoice_id.id,
                        'tax_purchase_ok': True,
                        'tax_purchase_wait_ok': False,
                        # 'reconciliation_in': vat.id
                    }
                    vats.append((0, 0, data))
                move_data_vals = {
                    'name': u'ยื่นภาษีซื้อ',
                    'partner_id': False,
                    'invoice_id': False,
                    'debit': self.amount_tax,
                    'credit': 0.0,
                    'payment_id': False,
                    'account_id': vat_purchase_account_id,
                    'vat_ids': vats
                }
                iml.append((0, 0, move_data_vals))
            for vat in self.item_ids:
                move_data_vals = {
                    'partner_id': vat.partner_id.id,
                    'invoice_id': vat.invoice_id.id,
                    'debit': 0.0,
                    'credit': vat.amount_tax,
                    'payment_id': False,
                    'account_id': vat.account_id.id,
                    'ineco_vat': vat.ineco_vat.id
                }
                vat.ineco_vat.write({'vatprd': self.vatprd})
                vat.invoice_id.write({'ineco_reconciled_tax': vat.ineco_vat.id})

                iml.append((0, 0, move_data_vals))
            move_vals = {
                'ref': u'ยื่นภาษีซื้อ',
                'date': self.vatprd,
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


class WizardInputTaxLine(models.TransientModel):
    _name = 'wizard.input.tax.line'

    order_id = fields.Many2one('wizard.input.tax', string='Line Tax', ondelete='cascade')
    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', on_delete="restrict")
    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=True, copy=False, track_visibility='onchange')
    docdat = fields.Date(string='ลงวันที่', required=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    partner_name = fields.Char(string=u'ผู้จำหน่าย', required=True, copy=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
