# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    deposit_ids = fields.One2many('ineco.customer.deposit', 'sale_order_id', string='Deposits')

    @api.multi
    def action_view_deposit(self):
        deposits = self.mapped('deposit_ids')
        action = self.env.ref('ineco_thai_v11.action_ineco_customer_deposit').read()[0]
        if len(deposits) > 1:
            action['domain'] = [('id', 'in', deposits.ids)]
        elif len(deposits) == 1:
            action['views'] = [(self.env.ref('ineco_thai_v11.view_ineco_customer_deposit_form').id, 'form')]
            action['res_id'] = deposits.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
