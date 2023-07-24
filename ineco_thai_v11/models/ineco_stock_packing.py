# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _, exceptions
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class UpdateHistoryAdjustments(models.Model):
    _name = "update.history.adjustments"

    name = fields.Char('Description', index=True, required=True)
    sequence = fields.Integer('Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], index=True, required=True, )
    ordered_qty = fields.Float('Ordered Quantity')
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    move_id = fields.Many2one('stock.move', 'move')
    location_id = fields.Many2one(
        'stock.location', u'จากสถานที่')
    location_dest_id = fields.Many2one(
        'stock.location', u'ไปสถานที่')
    picking_id = fields.Many2one('stock.picking', 'Transfer Reference')


class StockPicking(models.Model):
    _inherit = "stock.picking"

    date_iv_sup = fields.Date(string='Date IV', copy=False)
    iv_sup_no = fields.Char(string='IV NO', copy=False)
    is_vendor_bill = fields.Boolean(string='is_vendor_bill',
                                    readonly=True, default=False, copy=False)

    customer_invoices = fields.Many2one('account.invoice', u'เลขที่ใบกำกับภาษี', readonly=True, copy=False)
    customer_invoices_state = fields.Selection(string='invoices state',
                                               readonly=True,
                                               related='customer_invoices.state',
                                               selection=[
                                                   ('draft', 'Draft'),
                                                   ('open', 'Open'),
                                                   ('paid', 'Paid'),
                                                   ('cancel', 'Cancelled'),
                                               ])
    date_to_iv = fields.Date(string='Date to iv', copy=False)

    adjustments_ids = fields.One2many('stock.inventory', 'wh_picking_id', string=u'รายการปรับสต๊อก', copy=False)
    adjustments_count = fields.Integer(compute='_compute_adjustments', string=u'จำนวน', default=0, store=True,
                                       copy=False)

    picking_adjust_excess_ids = fields.One2many('stock.picking', 'adjust_excess_id', string=u'กิจกรรมคืนรับเกิน',
                                                copy=False)
    adjust_excess_id = fields.Many2one('stock.picking', string=u'กิจกรรมคืนรับเกิน', track_visibility='onchange',
                                       copy=False)
    picking_adjust_count = fields.Integer(compute='_compute_picking_adjust', string='Receptions', default=0,
                                          store=False)

    history_adjustments_lines = fields.One2many('update.history.adjustments', 'picking_id',
                                                string="History adjustments", copy=False)

    @api.multi
    def up_qty_iv(self, line):
        # print('up_qty_iv')
        qty = 0.0
        iv_line = self.env['account.invoice.line']
        if self.customer_invoices:
            if self.customer_invoices.state == 'draft':
                iv = iv_line.search([('stock_move_id', '=', line.move_id.id)])
                qty = iv.quantity - line.ordered_qty
                iv.write({'quantity': qty})
                iv.quantity = qty
                # print('iv.quantity',iv.quantity)
                iv.invoice_id.compute_taxes()
            else:
                raise UserError(_("ไม่สามารถแก้ไขได้ เนื่องจากมีการตั้งหนี้เรียบร้อยแล้ว กรุณาติดต่อบัญชี"))
        else:
            raise UserError(_("ไม่พบเอกสารดังกล่าว กรุณาติดต่อบัญชี"))

    @api.multi
    def create_picking_adjust(self):
        data = {
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.picking_type_id.default_location_src_id.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'origin': self.origin,
            'partner_id': self.partner_id.id
        }
        picking = self.env['stock.picking'].create(data)
        for line in self.history_adjustments_lines:
            iv_line = self.env['account.invoice.line']
            if self.customer_invoices.state == 'draft':
                iv = iv_line.search([('stock_move_id', '=', line.move_id.id)])
                # print('iv',iv)
                qty = iv.quantity - line.ordered_qty
                iv.write({'quantity': qty})
                iv.quantity = qty
                # print('iv.quantity', iv.quantity)
                iv.invoice_id.compute_taxes()
            # self.up_qty_iv(line)
            defaults = {
                'picking_id': picking.id,
                'picking_type_id': self.picking_type_id.id,
                'sale_line_id': False,
                'location_id': self.picking_type_id.default_location_src_id.id,
                'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'product_uom': line.product_uom.id,
                'name': line.move_id.name,
                'purchase_line_id': line.move_id.purchase_line_id.id,
                'price_unit': line.move_id.price_unit

            }
        self.env['stock.move'].create(defaults)
        picking.action_confirm()

    @api.multi
    @api.depends('picking_adjust_excess_ids')
    def _compute_picking_adjust(self):
        for requisition in self:
            requisition.picking_adjust_count = len(requisition.picking_adjust_excess_ids)

    @api.multi
    def action_view_adjust_excess(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]

        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        iv_ids = self.mapped('picking_adjust_excess_ids')
        # choose the view_mode accordingly
        if not iv_ids or len(iv_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (iv_ids.ids)
        elif len(iv_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = iv_ids.id
        return result

    @api.multi
    @api.depends('adjustments_ids')
    def _compute_adjustments(self):
        for requisition in self:
            requisition.adjustments_count = len(requisition.adjustments_ids)

    @api.multi
    def action_view_adjustments(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_inventory_form')
        result = action.read()[0]

        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        iv_ids = self.mapped('adjustments_ids')
        # choose the view_mode accordingly
        if not iv_ids or len(iv_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (iv_ids.ids)
        elif len(iv_ids) == 1:
            res = self.env.ref('stock.view_inventory_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = iv_ids.id
        return result

    @api.multi
    def button_vendor_bill(self):
        if not self.date_iv_sup:
            raise UserError(_("ไม่ระบุ วันที่ใบกำกับภาษี sup"))
        if not self.iv_sup_no:
            raise UserError(_("ไม่ระบุ เลขที่ใบกำกับภาษี sup"))
        self.is_vendor_bill = True
        stock_move_obj = self.env['stock.move'].search([
            # ('par tner_id', '=', self.partner_id.id),
            ('picking_id', '=', self.id),
            ('state', '=', 'done')
        ])
        for sm in stock_move_obj:
            if sm.purchase_line_id:
                purchase_order_line_obj = self.env['purchase.order.line'].browse(sm.purchase_line_id.id)
                if not purchase_order_line_obj:
                    raise UserError(_("การรับเข้าไม่ได้ผ่านกระบวนการจัดซื้อจัดจ้าง"))

                purchase_obj = self.env['purchase.order'].search([('id', '=', purchase_order_line_obj.order_id.id)])
                journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
                invoice_order_data = {
                    'partner_id': self.partner_id.id,
                    'origin': self.origin,
                    'reference': self.iv_sup_no,
                    'currency_id': purchase_obj.currency_id.id or self.partner_id.property_purchase_currency_id.id,
                    'purchase_id': purchase_obj.id,
                    # 'account_id': self.partner_id.property_account_receivable_id.id,
                    'account_id': self.partner_id.property_account_payable_id.id,
                    'type': 'in_invoice',
                    'date_invoice': self.date_iv_sup,
                    'journal_id': journal_id.id,
                    'name': self.name
                }
                # tax_id = False
                # if purchase_obj.to_ap:
                #     if purchase_order_line_obj.taxes_id:
                #         tax_id =[(6, 0, [x.id for x in purchase_obj.po_type_ids.taxes_id])]
                #     else:
                #         tax_id = False
                # else:
                #     tax_id = [(6, 0, [x.id for x in  purchase_order_line_obj.taxes_id])]
                # tax_id = [(6, 0, [x.id for x in purchase_order_line_obj.taxes_id])]
                invoice_line_data = {
                    'product_id': purchase_order_line_obj.product_id.id,
                    'quantity': sm.quantity_done * purchase_order_line_obj.product_uom.factor,
                    'price_unit': purchase_order_line_obj.price_unit,
                    'purchase_line_id': purchase_order_line_obj.id,
                    'partner_id': self.partner_id.id,
                    'name': purchase_order_line_obj.name or '-',
                    'account_id': purchase_order_line_obj.product_id.property_account_expense_id.id or journal_id.default_debit_account_id.id,
                    'journal_id': journal_id.id,
                    # 'invoice_line_tax_ids': tax_id ,
                    'invoice_line_tax_ids': [(6, 0, [x.id for x in purchase_order_line_obj.taxes_id])],
                    'account_analytic_id': purchase_order_line_obj.account_analytic_id.id,
                    'analytic_tag_ids': [(6, 0, [x.id for x in purchase_order_line_obj.analytic_tag_ids])],
                    # 'request_line_id': purchase_order_line_obj.request_line_id.id,
                    # 'specifications': purchase_order_line_obj.specifications or False
                    'discount2': purchase_order_line_obj.discount,
                    'discount_float': purchase_order_line_obj.discount_float,
                    'stock_move_id': sm.id,
                    'uom_id': sm.product_uom.id
                }
                account_invoice_line_obj = self.env['account.invoice.line']
                invoice_id_obj = self.env['account.invoice'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('state', '=', 'draft'),
                    ('origin', '=', self.origin),
                    ('reference', '=', self.iv_sup_no),
                    ('date_invoice', '=', self.date_iv_sup),
                    ('reference', '=', self.iv_sup_no)
                ])
                if not invoice_id_obj:
                    invoice_id_obj = self.env['account.invoice'].create(invoice_order_data)
                self.customer_invoices = invoice_id_obj.id
                invoice_line_data['invoice_id'] = invoice_id_obj.id
                new_move = account_invoice_line_obj.create(invoice_line_data)
        invoice_id_obj.compute_taxes()
        # if purchase_obj.to_ap:
        #     tax_iv = 0.0
        #     rounding = 0.0
        #     amount_tax = purchase_obj.amount_tax2 - invoice_id_obj.amount_tax
        #     for tax in invoice_id_obj.tax_line_ids:
        #         tax_iv += tax.amount_total
        #     rounding = float(purchase_obj.amount_tax2) - float(tax_iv)
        #     if tax_iv != 0.0 and  rounding != 0.0:
        #         tax.write({'amount_rounding': rounding, 'ineco_amount_rounding': rounding})
        #     invoice_id_obj.onchange_tax_rounding()

    # --------------------------------
    @api.multi
    def button_customer_invoices(self):
        self.is_vendor_bill = True
        stock_move_obj = self.env['stock.move'].search([('picking_id', '=', self.id),
                                                        ('state', '=', 'done')
                                                        ])
        for sm in stock_move_obj:
            journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            sale_order_line_obj = self.env['sale.order.line'].search([('id', '=', sm.sale_line_id.id), ])
            user_id = sale_order_line_obj.order_id.user_id
            po_name = ''
            for sale_line in sale_order_line_obj:

                invoice_order_data = {
                    'partner_id': self.partner_id.id,
                    'origin': self.name,
                    'user_id': user_id.id,
                    'name': self.origin,
                    'currency_id': sale_line.currency_id.id,
                    'account_id': self.partner_id.property_account_receivable_id.id,
                    # 'account_id': self.partner_id.property_account_payable_id.id,
                    'type': 'out_invoice',
                    'date_invoice': self.date_done,
                    'journal_id': journal_id.id
                }
                invoice_line_data = {
                    'product_id': sm.product_id.id,
                    'quantity': sm.product_qty,
                    'price_unit': sale_line.price_unit,
                    'move_id': sm.id,
                    'partner_id': self.partner_id.id,
                    'name': sm.name,
                    'account_id': sm.product_id.property_account_income_id.id,
                    'journal_id': journal_id.id,
                    'picking_id': self.id,
                    'stock_move': sm.id,
                    'sale_line_ids': [(6, 0, [sale_line.id])],
                    'account_analytic_id': sale_line.order_id.analytic_account_id.id or False,
                    'analytic_tag_ids': [(6, 0, [x.id for x in sale_order_line_obj.analytic_tag_ids])],
                    'invoice_line_tax_ids': [(6, 0, [x.id for x in sale_order_line_obj.tax_id])],
                    'stock_move_id': sm.id
                }

            account_invoice_line_obj = self.env['account.invoice.line']
            invoice_id_obj = self.env['account.invoice'].search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'draft'),
                ('origin', '=', self.name), ])

            if not invoice_id_obj:
                invoice_id_obj = self.env['account.invoice'].create(invoice_order_data)

            invoice_line_data['invoice_id'] = invoice_id_obj.id
            new_move = account_invoice_line_obj.create(invoice_line_data)
            self.date_to_iv = datetime.now()
            self.customer_invoices = invoice_id_obj.id
        invoice_id_obj.compute_taxes()

