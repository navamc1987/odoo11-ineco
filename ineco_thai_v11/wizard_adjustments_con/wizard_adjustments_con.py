# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions ,_
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WhWizardAdjustmentsCon(models.TransientModel):
    _name = "wh.wizard.adjustments.con"

    item_ids = fields.One2many('wh.wizard.adjustments.con.line', 'order_id', string='Order Lines')
    location_id = fields.Many2one('stock.location', "Location", )

    @api.model
    def default_get(self, fields):
        res = super(WhWizardAdjustmentsCon, self).default_get(fields)
        picking_obj = self.env['stock.picking']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        items = []
        for line in picking_ids.move_lines:
            move_line = line.mapped('move_line_ids')
            for move in move_line:
                line_data = {
                    'order_id': self.id,
                    'move_id': line.id,
                    'lot_id': move.lot_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty':move.qty_done,
                    'qty_done': False,
                }
                items.append([0, 0, line_data])
                res['item_ids'] = items
        res['location_id'] = picking_ids.location_dest_id.id
        return res

    @api.multi
    def create_picking_adjust_excess(self):
        picking_obj = self.env['stock.picking']
        move = self.env['stock.move']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        for p in picking_ids:
            for line in self.item_ids:

                if line.product_id.type == 'product':
                    raise UserError(_("ไม่สามารถทำรายการเมนูนี้ำด้เนื่องสินค้าจักเก็บสต๊อก"))

                picking_data = {
                    'origin': p.origin,
                    'state': 'draft',
                    'partner_id': p.partner_id.id,
                    'picking_type_id': picking_ids.picking_type_id.id,
                    'location_id': picking_ids.location_dest_id.id,
                    'location_dest_id': picking_ids.picking_type_id.default_location_src_id.id,
                    'is_ok_move': True

                }
                move_data = {
                    'name': p.origin or line.move_id.name,
                    'product_id': line.product_id.id,
                    'date_expected': p.scheduled_date,
                    'product_uom_qty': line.qty_done,
                    'product_uom': line.product_id.uom_id.id,
                    'partner_id': p.partner_id.id,
                    'restrict_partner_id': p.partner_id.id,
                    'price_unit': False,
                    'origin': p.origin,
                    'picking_type_id': picking_ids.picking_type_id.id,
                    'picking_id': False,
                    'location_id': picking_ids.location_dest_id.id,
                    'location_dest_id': picking_ids.picking_type_id.default_location_src_id.id,

                }
                picking = self.env['stock.picking'].search([
                    ('partner_id', '=', p.partner_id.id),
                    ('origin', '=', p.origin),
                    ('state', '=', 'draft'),
                    ('picking_type_id', '=', picking_ids.picking_type_id.id)

                ])
                if not picking:
                    picking_data['date'] = p.scheduled_date
                    picking_data['scheduled_date'] = p.scheduled_date
                    picking = self.env['stock.picking'].create(picking_data)
                    picking.adjust_excess_id = p.id

                move_data['picking_id'] = picking.id
                new_move = move.create(move_data)

                # product_uom_qty = line.move_id.qc_move - line.qty_done
                # line.move_id.qc_move = product_uom_qty

        # picking.action_confirm()
        # picking.action_assign()
        # view_ref = self.env['ir.model.data'].get_object_reference('stock', 'view_picking_form')
        # view_id = view_ref and view_ref[1] or False,
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'stock.picking',
        #     'res_model': 'stock.picking',
        #     'res_id': picking.id,
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'view_id': view_id,
        #     'target': 'current',
        #     'nodestroy': True,
        #
        # }


class WhWizardAdjustmentsConLine(models.TransientModel):
    _name = 'wh.wizard.adjustments.con.line'


    order_id = fields.Many2one('wh.wizard.adjustments.con', string='Picking Order', ondelete='cascade')
    move_id = fields.Many2one('stock.move', 'move', ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Product',related='move_id.product_id',store=True,ondelete="cascade",)
    lot_id = fields.Many2one('stock.production.lot', 'Lot',store=True)
    product_uom_qty = fields.Float(u'จำนวนรับจริง',store=True)
    qty_done = fields.Float(u'ปรับออก',required=True)

    @api.onchange('qty_done')
    def onchange_qty_done(self):
        for line in self:
            if line.qty_done > line.product_uom_qty:
                raise UserError(("เกินจำนวนไม่รับจริง"))
                line.qty_done=False
            if line.qty_done < 0.0:
                raise UserError(("ปรับได้ตำสุดคือ 0 "))
                line.qty_done=False