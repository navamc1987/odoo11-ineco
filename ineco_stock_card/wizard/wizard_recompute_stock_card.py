# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api


class WizardRecomputeStockCard(models.TransientModel):
    _name = 'wizard.recompute.stock.card'
    _description = 'Recompute Stock Cards'

    @api.multi
    def recompute(self):
        active_ids = self._context.get('active_ids', [])
        iscp = self.env['ineco.stock.card.product']
        if active_ids:
            for period in self.env['ineco.stock.card'].browse(active_ids):
                for product in period.product_line_ids:
                    card_product_obj = iscp.search([('product_id', '=', product.product_id.id),
                                                    ('stock_date_to', '<', period.date_from)],
                                                   order='stock_date_to desc',
                                                   limit=1)
                    if card_product_obj:
                        product.bf_quantity = card_product_obj.balance_quantity
                        product.bf_cost = card_product_obj.balance_cost
                        product.bf_value = card_product_obj.balance_value
                    product.button_recompute()

                # period.button_recompute()

        return {'type': 'ir.actions.act_window_close'}
