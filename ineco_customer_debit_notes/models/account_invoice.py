# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, exceptions, fields, models, _

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    add_refund_invoice_id = fields.Many2one('account.invoice', string=u'เพิ่มหนี้')
    is_add_cus_debit = fields.Boolean(string=u'เพิ่มหนี้')

    note_debit_dredit = fields.Text(u'สาเหตุการลดหนี้เพิ่มหนี้')

    @api.multi
    def InecoReconcile(self):
        # account_id = self.partner_id.property_account_receivable_id
        account_id = self.account_id
        if account_id.id != self.refund_invoice_id.account_id.id:
            raise UserError(_(f'ผังลูกหนี้/เจ้าหนี้ ไม่ตรงกัน :ใบกำกับอ้างอิง {account_id.code}-{account_id.name}'))

        invoice_ids = []
        invoice_ids.append(self.refund_invoice_id.id)
        invoice_ids.append(self.id)
        domain = [('account_id', '=', account_id.id),
                  ('invoice_id', 'in', invoice_ids),
                  ('partner_id', '=', self.partner_id.id),
                  ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                  ('amount_residual_currency', '!=', 0.0)]

        move_lines = self.env['account.move.line'].search(domain)

        move_lines.reconcile()

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
            'expense': _('Vendor Expense'),
        }
        result = []
        for inv in self:
            if inv.type not in ('out_invoice', 'in_invoice', 'expense'):
                result.append(
                    (inv.id, "%s ลดหนี้ %s" % (inv.number or TYPES[inv.type], inv.refund_invoice_id.number or '')))
            elif inv.is_add_cus_debit == True:
                result.append(
                    (inv.id,
                     "%s เพิ่มหนี้ %s" % (inv.number or TYPES[inv.type], inv.add_refund_invoice_id.number or '')))
            elif inv.type in ('expense'):
                result.append(
                    (inv.id,
                     "%s บันทึกค่าใช้จ่าย %s" % (inv.number or TYPES[inv.type], inv.name or '')))
            else:
                result.append((inv.id, "%s อ้างอิงเอกสาร %s ใบกำกับ %s - %s" % (
                    inv.number or TYPES[inv.type], inv.name or '', inv.reference or '', inv.origin or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        reference = self.browse()
        origin = self.browse()
        if name:
            recs = self.search([('number', '=', name)] + args, limit=limit)
            reference = self.search([('reference', operator, name)] + args, limit=limit)
            origin = self.search([('origin', operator, name)] + args, limit=limit)
            if reference:
                return reference.name_get()
            if origin:
                return origin.name_get()
        if recs:
            return recs.name_get()
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
            return recs.name_get()
