# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class SaleMakeAddDebit(models.TransientModel):
    _name = "sale.make.add.debit"


    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวัน', required=True)
    invoice_filter_type_domain = fields.Char(string=u'invoice_filter_type_domain')
    note = fields.Char(string=u'รายละเอียด/บันทึก/สาเหตุ (การเพิ่มหนี้)')

    @api.model
    def default_get(self, fields):
        res = super(SaleMakeAddDebit, self).default_get(fields)
        active_id = self._context.get('active_id', False)
        invoice_obj = self.env['account.invoice']
        line = invoice_obj.search([('id', '=', active_id)])
        res['invoice_filter_type_domain'] = line.journal_id.type
        return res

    @api.multi
    def create_invoices(self):
        active_id = self._context.get('active_id', False)
        invoice_obj = self.env['account.invoice']
        line = invoice_obj.search([('id', '=', active_id)])
        journal_ids = self.env['account.journal'].search([('id', '=', self.journal_id.id)])
        if not journal_ids:
            raise exceptions.UserError(u"ยังไม่มีการสร้างสมุดรายวัน")
        new_move_id = line.copy({
            'journal_id': journal_ids.id,
            'is_add_cus_debit':True,
            'add_refund_invoice_id':line.id,
            'note_debit_dredit': self.note or False
        })
        # action = self.env.ref('ineco_customer_debit_notes.ineco_debit_note_invoice_form').read()[0]
        # action['views'] = [(self.env.ref('ineco_customer_debit_notes.ineco_debit_note_invoice_form').id, 'form')]
        # action['res_id'] = new_move_id.id
        # return action

        view_ref = self.env['ir.model.data'].get_object_reference('ineco_customer_debit_notes', 'ineco_debit_note_invoice_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.debit.note.invoice.form',
            'res_model': 'account.invoice',
            'res_id': new_move_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,

        }
