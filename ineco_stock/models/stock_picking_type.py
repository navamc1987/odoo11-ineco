# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved


from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_compare, float_is_zero
from odoo import api, fields, models, _
import datetime
from odoo.addons import decimal_precision as dp


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    is_group = fields.Boolean(string='is group', default=False)

    def action_create_group(self):
        cat = self.env.ref('ineco_stock.module_ineco_stock_picking_typ')
        data = {
            'name': self.name,
            'category_id': cat.id
        }
        group = self.env['res.groups'].create(data)
        self.is_group = True
        model_id = self.env.ref('ineco_stock.model_stock_picking_type')
        data_rule = {
            'name': self.name,
            'model_id': model_id.id,
            'groups': [(6, 0, [group.id])],
            'domain_force': "[('id','in',[%s])]" % (self.id)
        }
        rule = self.env['ir.rule'].create(data_rule)
