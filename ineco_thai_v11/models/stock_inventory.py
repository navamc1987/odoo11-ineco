# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    wh_picking_id = fields.Many2one('stock.picking', string=u'เลขที่ picking', track_visibility='onchange', copy=False)

    @api.multi
    def history_adjustments(self):
        history = self.env['update.history.adjustments']
        for line in self.line_ids:
            data = {
                'name': 'รับเกินตัดออก',
                'product_id': line.product_id.id,
                'ordered_qty': line.theoretical_qty - line.product_qty,
                'product_uom': line.product_uom_id.id,
                'move_id': line.move_id.id,
                'location_id': line.location_id.id,
                # 'location_dest_id': 8,
                'picking_id': self.wh_picking_id.id}
            Search = history.search([('move_id', '=', line.move_id.id)])
            if not Search:
                History = history.create(data)
        self.wh_picking_id.create_picking_adjust()

    @api.multi
    def action_done(self):
        res = super(StockInventory, self).action_done()
        # self.history_adjustments()
        return res


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    move_id = fields.Many2one('stock.move', 'move', copy=False)
