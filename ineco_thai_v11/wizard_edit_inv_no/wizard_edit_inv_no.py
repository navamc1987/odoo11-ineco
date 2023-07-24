# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WizardEditInvNo(models.TransientModel):
    _name = "wizard.edit.inv.no"

    date_iv_sup = fields.Date(string='Date IV', copy=False)
    iv_sup_no = fields.Char(string='IV NO', copy=False)

    @api.model
    def default_get(self, fields):
        res = super(WizardEditInvNo, self).default_get(fields)
        picking_obj = self.env['stock.picking']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        res['date_iv_sup'] = picking_ids.date_iv_sup
        res['iv_sup_no'] = picking_ids.iv_sup_no
        return res

    @api.multi
    def create_edit(self):
        picking_obj = self.env['stock.picking']
        request_line_ids = self.env.context.get('active_ids', False)
        picking_ids = picking_obj.browse(request_line_ids)
        if picking_ids:
            if picking_ids.customer_invoices.state == 'draft':
                picking_ids.customer_invoices.write({'date_invoice': self.date_iv_sup,
                                                     'reference': self.iv_sup_no})
                picking_ids.write({'date_iv_sup': self.date_iv_sup,
                                   'iv_sup_no': self.iv_sup_no})
            else:
                raise UserError(_("ไม่สามารถแก้ไขได้ เนื่องจากมีการตั้งหนี้เรียบร้อยแล้ว กรุณาติดต่อบัญชี"))
        else:
            UserError(_("ไม่พบเอกสารตั้งหนี้ กรุณาติดต่อบัญชี"))
