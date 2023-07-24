# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api, _
import math
from os.path import expanduser
import logging


class ProductProduct(models.Model):
    _inherit = 'product.product'

    disable_stock_card = fields.Boolean('Disable Stock Card', default=False)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    use_fg_standard_cost = fields.Boolean(string='Use Final Standard Cost', default=False)

    @api.multi
    def button_replace_lot_cost(self):
        for data in self:
            if data.use_fg_standard_cost:
                product_ids = self.env['product.product'].search([('categ_id', 'child_of', data.ids)])
                for product in product_ids:
                    if product.standard_price:
                        sql = """
                            update ineco_stock_card_lot
                            set cost = {}
                            where product_id = {} and extract(year from date) = extract(year from now())
                        """.format(product.standard_price, product.id)
                        self._cr.execute(sql)
