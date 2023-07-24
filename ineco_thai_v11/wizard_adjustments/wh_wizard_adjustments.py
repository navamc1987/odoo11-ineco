# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WhWizardAdjustments(models.TransientModel):
    _name = "wh.wizard.adjustments"

    item_ids = fields.One2many('wh.wizard.adjustments.line', 'order_id', string='Order Lines')
    location_id = fields.Many2one('stock.location', "Location", )

    @api.model
    def default_get(self, fields):
        res = super(WhWizardAdjustments, self).default_get(fields)
        picking_obj = self.env['stock.picking']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        items = []
        for line in picking_ids.move_lines:
            move_line = line.mapped('move_line_ids')
            for move in move_line:
                line_data = {
                    'order_id': self.id,
                    'move_id': move.move_id.id,
                    'lot_id': move.lot_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty':move.qty_done,
                    'qty_done': False,
                    'product_name':line.product_id.name,
                    'lot_name': move.lot_id.name,

                }
                items.append([0, 0, line_data])
                res['item_ids'] = items
        res['location_id'] = picking_ids.location_dest_id.id
        return res

    @api.multi
    def create_adjustments(self):
        picking_obj = self.env['stock.picking']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        Inventory = self.env['stock.inventory']
        for line in self.item_ids:
            inventory = Inventory.search([('name','=',('INV: %s') % (picking_ids.name)),('location_id','=',self.location_id.id),('state','=','confirm')])
            if not inventory:
                inventory = Inventory.create({
                    'name': ('INV: %s') % (picking_ids.name),
                    'filter': 'partial',
                    'product_id': False,
                    'location_id': self.location_id.id,
                    'lot_id': False,
                    'wh_picking_id': picking_ids.id,
                    # 'line_ids': [(0, 0, inventory_line_data)],
                })
                inventory.action_start()

                quants = self.env['stock.quant'].sudo().search([('product_id', '=', line.product_id.id),
                                                               ('location_id', '=', self.location_id.id),
                                                               ('lot_id', '=', line.lot_id.id),
                                                               ('quantity', '>', 0.0)], order='in_date', limit=1)

                if not quants:
                    raise UserError(("ไม่พบสินค้าในระบบ กรุณาติดต่อผู้มีอำนาจตัดสินใจ"))
                else:
                    product = quants.lot_id.product_id.with_context(location=self.location_id.id, lot_id=line.lot_id.id)
                    th_qty = product.qty_available
                    InventoryLine = self.env['stock.inventory.line'].create({
                        'inventory_id': inventory.id,
                        'product_qty': line.qty_done,
                        'location_id': self.location_id.id,
                        'product_id':  line.product_id.id,
                        'product_uom_id':  line.product_id.uom_id.id,
                        'theoretical_qty': line.product_uom_qty,
                        'prod_lot_id':  line.lot_id.id,
                        'move_id': line.move_id.id
                    })
                    # print(InventoryLine.theoretical_qty,line.product_uom_qty)


class WhWizardAdjustmentsLine(models.TransientModel):
    _name = 'wh.wizard.adjustments.line'


    order_id = fields.Many2one('wh.wizard.adjustments', string='Picking Order', ondelete='cascade')
    move_id = fields.Many2one('stock.move', 'move', ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Product',store=True,ondelete="cascade",)
    product_name = fields.Char('Product',)
    lot_id = fields.Many2one('stock.production.lot', 'Lot',store=True)
    lot_name = fields.Char('Lot', related='lot_id.name')
    product_uom_qty = fields.Float(u'จำนวนรับจริง',store=True)
    qty_done = fields.Float(u'ปรับให้เป็น',required=True)

    @api.onchange('qty_done')
    def onchange_qty_done(self):
        for line in self:
            if line.qty_done > line.product_uom_qty:
                raise UserError(("เกินจำนวนไม่รับจริง"))
                line.qty_done=False
            if line.qty_done < 0.0:
                raise UserError(("ปรับได้ตำสุดคือ 0 "))
                line.qty_done=False