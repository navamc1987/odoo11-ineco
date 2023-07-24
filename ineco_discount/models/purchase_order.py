# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('discount', 'discount_float')
    def _compute_amount(self):
        for line in self:
            price_unit = False
            # This is always executed for allowing other modules to use this
            # with different conditions than discount != 0
            price = line._get_discounted_price_unit()
            if price != line.price_unit:
                # Only change value if it's different
                price_unit = line.price_unit
                line.price_unit = price
            super(PurchaseOrderLine, line)._compute_amount()
            if price_unit:
                line.price_unit = price_unit

    discount = fields.Char(string='Discount %', default=False)
    discount_float = fields.Float(string='Discount(บาท)', required=True, digits=dp.get_precision('Product Price'))

    def _get_discounted_price_unit(self):
        self.ensure_one()
        if self.discount:
            dt = self.discount
            if dt.find('%') != -1:
                price = self.price_unit
                for discount in dt.split('%'):
                    if len(discount) > 0:
                        return price * (1 - float(discount) / 100)
        if self.discount_float > 0.0:
            return self.price_unit - float(self.discount_float)
        return self.price_unit

    @api.multi
    def _get_stock_move_price_unit(self):
        price_unit = False
        price = self._get_discounted_price_unit()
        if price != self.price_unit:
            # Only change value if it's different
            price_unit = self.price_unit
            self.price_unit = price
        price = super(PurchaseOrderLine, self)._get_stock_move_price_unit()
        if price_unit:
            self.price_unit = price_unit
        return price
