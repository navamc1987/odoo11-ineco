# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import odoo.addons.decimal_precision as dp
from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError



class wizard_split_move_line(models.TransientModel):
    _name = "wizard.split.vat.line"



    quantity = fields.Float('vat', required=True)

    _defaults = {
        'quantity': 1.0,
    }

    def split(self):
        active_id = self._context.get('active_id', False)
        purchase_obj = self.env['ineco.account.vat']
        line = purchase_obj.search([('id', '=', active_id)])
        for move in line:
            if self.quantity < 1:
                raise UserError(_("ยอดTAXไม่เข้าเงื่อนไช"))

            if move.amount_tax < self.quantity:
                raise UserError(_("ยอดเกินยอด split"))
            data = {
                'move_line_id': False,
                'account_id': line.account_id.id,
                'name': '',
                'docdat': line.docdat,
                'vatprd': move.vatprd,
                'period_id': line.period_id.id,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_name,
                'taxid': line.taxid or '',
                'depcod': line.depcod or '',
                'amount_untaxed': 0.0,
                'amount_total': 0.0,
                'invoice_id': line.invoice_id.id,
                'tax_purchase_ok': move.tax_purchase_ok,
                'tax_purchase_wait_ok': move.tax_purchase_wait_ok,

                'amount_tax': self.quantity,
                }
            new_move_id = line.copy(data)
            if move.tax_purchase_ok:
                new_move_id.write({'move_line_id': move.move_line_id.id,})
            move.write({'amount_tax': move.amount_tax - self.quantity,
                       })

            # message = _(
            #     "This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (
            #           invoice_type[invoice.type], invoice.id, invoice.number)
            # refund_invoice.message_post(body=message)
            vstr = ''
            if move.tax_purchase_ok:
                vstr = 'ภาษีซื้อ'
            if move.tax_purchase_wait_ok:
                vstr = 'ภาษีซื้อพัก'
            move.invoice_id.message_post(body=_(f'ทำการ split {vstr} จำนวน {self.quantity}'))
            return True

        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        # }
