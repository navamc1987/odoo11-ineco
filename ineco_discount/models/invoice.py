# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import itertools
from lxml import etree

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    discount2 = fields.Char(string='Discount %', default=False)
    price_total = fields.Float(string='Total', compute='_compute_price',
                               digits=dp.get_precision('Account'))
    discount_float = fields.Float(string='Discount(บาท)', required=False, default=0.0,
                                  digits=dp.get_precision('Product Price'))
    difference = fields.Boolean('difference')
    difference_price_subtotal = fields.Float(string='Amount', store=True, readonly=False, help="Total difference")

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date', 'discount_float')
    def _compute_price(self):
        # if self.invoice_id.ineco_amount_rounding == 0.0:
        price = 0.0
        currency = self.invoice_id and self.invoice_id.currency_id or None
        if self.discount2 or self.discount_float:
            if self.discount2:
                dt = self.discount2
                if dt.find('%') != -1:
                    price = self.price_unit
                    for discount in dt.split('%'):
                        if len(discount) > 0:
                            price = price * (1 - float(discount) / 100)
            if self.discount_float:
                price = (self.price_unit - float(self.discount_float))
            taxes = False
            if self.invoice_line_tax_ids:
                taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                              partner=self.invoice_id.partner_id)
            self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
            self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                price_subtotal_signed = self.invoice_id.currency_id.with_context(
                    date=self.invoice_id._get_currency_rate_date()).compute(price_subtotal_signed,
                                                                            self.invoice_id.company_id.currency_id)
            sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            self.price_subtotal_signed = price_subtotal_signed * sign
        else:
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            taxes = False
            if self.invoice_line_tax_ids:
                taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                              partner=self.invoice_id.partner_id)
            if not self.difference:
                self.price_subtotal = price_subtotal_signed = taxes[
                    'total_excluded'] if taxes else self.quantity * price
            else:
                self.price_subtotal = price_subtotal_signed = self.difference_price_subtotal
            self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                price_subtotal_signed = self.invoice_id.currency_id.with_context(
                    date=self.invoice_id._get_currency_rate_date()).compute(price_subtotal_signed,
                                                                            self.invoice_id.company_id.currency_id)
            sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            # if not self.difference:
            self.price_subtotal_signed = price_subtotal_signed * sign
        # self.invoice_id.update_smh()


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    ineco_amount_rounding = fields.Float(u'ปรับทศนิยม')

    def _prepare_invoice_line_from_po_line(self, line):
        vals = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(
            line)
        vals['discount2'] = line.discount
        return vals

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        price_unit = 0.0
        for line in self.invoice_line_ids:
            if line.discount2 or line.discount_float:
                if line.discount2:
                    dt = line.discount2
                    if dt.find('%') != -1:
                        price = line.price_unit
                        for discount in dt.split('%'):
                            if len(discount) > 0:
                                price_unit = price * (1 - float(discount) / 100)
                if line.discount_float:
                    price_unit = (line.price_unit - float(line.discount_float))

            else:
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id,
                                                          self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.multi
    def compute_taxes(self):
        """Function used in other module to compute the taxes on a fresh invoice created (onchanges did not applied)"""
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        if self.ineco_amount_rounding == 0.0:
            for invoice in self:
                self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False",
                                 (invoice.id,))
                if self._cr.rowcount:
                    self.invalidate_cache()

                # Generate one tax line per tax, however many invoice lines it's applied to
                tax_grouped = invoice.get_taxes_values()

                # Create new tax lines
                for tax in tax_grouped.values():
                    account_invoice_tax.create(tax)

            # dummy write on self to trigger recomputations
            return self.with_context(ctx).write({'invoice_line_ids': []})

    @api.onchange('invoice_line_ids', 'tax_line_ids')
    def onchange_tax_rounding(self):
        for tax_line in self.tax_line_ids:
            self.ineco_amount_rounding = tax_line.amount_rounding
            # self.write({'ineco_amount_rounding':tax_line.amount_rounding})

    def difference(self):
        total = 0.0
        for line in self.invoice_line_ids:
            total += line.price_total
            # '%.3f' % pi
        d = (total - self.amount_total)
        difference = ('%.2f' % d)
        return difference