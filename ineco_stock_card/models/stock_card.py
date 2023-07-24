# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
import math
from os.path import expanduser
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class InecoStockCard(models.Model):
    _name = 'ineco.stock.card'
    _description = 'Stock Card'

    name = fields.Char(string='Stock Period', required=1, track_visibility='onchange')
    period_id = fields.Many2one('date.range', string='Account Period', track_visibility='onchange')
    date_from = fields.Date(string='Date From', required=True, track_visibility='onchange')
    date_to = fields.Date(string='Date To', required=True, track_visibility='onchange')
    cost_method = fields.Selection([('fifo', 'FiFo'), ('average', 'Average')], string='Cost Method', default='fifo')
    note = fields.Text(string='Note')
    product_line_ids = fields.One2many('ineco.stock.card.product', 'stock_period_id', string='Product Lines')
    begining_values = fields.Float('Begining Values', compute='_get_stock_values')
    ending_values = fields.Float('Ending Values', compute='_get_stock_values')
    close_date = fields.Date(string='Close Date')
    last_update_stock = fields.Datetime(string='Last Update Stock')

    @api.model
    def refresh_stock(self, *args, **kwargs):
        periods = self.env['ineco.stock.card'].search([('close_date', '=', False)])
        for period in periods:
            period.button_compute()
        return True

    @api.multi
    def close_period(self):
        for data in self:
            data.close_date = datetime.datetime.now().strftime('%Y-%m-%d')

    @api.onchange('period_id')
    def onchange_period(self):
        self.date_from = self.period_id.date_start
        self.date_to = self.period_id.date_end
        if not self.name:
            self.name = self.period_id.name

    @api.multi
    def _get_stock_values(self):
        for data in self:
            begin_value = 0.0
            end_value = 0.0
            for line in data.product_line_ids:
                begin_value += line.bf_value
                end_value += line.balance_value
            data.begining_values = begin_value
            data.ending_values = end_value

    def _compute_product(self, product_id, from_date, to_date, domain_move_in_loc, domain_move_out_loc):
        stock_move = self.env['stock.move']
        # print domain_move_in_loc, domain_move_out_loc
        in_balance = stock_move.read_group([('product_id', '=', product_id),
                                            ('state', '=', 'done'),
                                            ('date', '<=', from_date)] + domain_move_in_loc,
                                           ['product_id', 'product_qty'], ['product_id'])
        out_balance = stock_move.read_group([('product_id', '=', product_id),
                                             ('state', '=', 'done'),
                                             ('date', '<=', to_date)] + domain_move_out_loc,
                                            ['product_id', 'product_qty'], ['product_id'])

        in_balance = in_balance and in_balance[0]['product_qty'] or 0.0
        out_balance = out_balance and out_balance[0]['product_qty'] or 0.0
        return in_balance - out_balance

    @api.multi
    def button_import_express(self):
        delete_sql = """
            delete from ineco_stock_card_product where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql)
        delete_sql2 = """
            delete from ineco_stock_card_product_line where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql2)
        products = self.env['product.product'].search([('type', '=', 'product')], order='default_code')
        card_product = self.env['ineco.stock.card.product']
        card_line = self.env['ineco.stock.card.product.line']
        iscp = self.env['ineco.stock.card.product']
        for product in products:
            new_product_card = {
                'name': product.name,
                'product_id': product.id,
                'stock_period_id': self.id,
            }
            stock_bf = {}
            if self.date_from[5:7] == '01':
                sql_bf = """
                select 
                  begbal as bf_qty,
                  begval as bf_amount,  
                  round((begval) / case when begbal > 0 then begbal else 1 end, 4) as bf_priceunit,
                  begbal+qty1 as balance_quantity,
                  begval+val1 as balance_amount,  
                  round((begval + val1) / case when (begbal + qty1) > 0 then (begbal+qty1) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '02':
                sql_bf = """
                select 
                  begbal+qty1 as bf_qty,
                  begval+val1 as bf_amount,  
                  round((begval+val1) / case when begbal+val1 > 0 then begbal+val1 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2 as balance_quantity,
                  begval+val1+val2 as balance_amount,  
                  round((begval+val1+val2) / case when (begbal+qty1+qty2) > 0 then (begbal+qty1+qty2) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '03':
                sql_bf = """
                select 
                  begbal+qty1+qty2 as bf_qty,
                  begval+val1+val2 as bf_amount,  
                  round((begval+val1+val2) / case when begbal+val1+val2 > 0 then begbal+val1+val2 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3 as balance_quantity,
                  begval+val1+val2+val3 as balance_amount,  
                  round((begval+val1+val2+val3) / case when (begbal+qty1+qty2+qty3) > 0 then (begbal+qty1+qty2+qty3) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '04':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3 as bf_qty,
                  begval+val1+val2+val3 as bf_amount,  
                  round((begval+val1+val2+val3) / case when begbal+val1+val2+val3 > 0 then begbal+val1+val2+val3 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4 as balance_quantity,
                  begval+val1+val2+val3+val4 as balance_amount,  
                  round((begval+val1+val2+val3+val4) / case when (begbal+qty1+qty2+qty3+qty4) > 0 then (begbal+qty1+qty2+qty3+qty4) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '05':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4 as bf_qty,
                  begval+val1+val2+val3+val4 as bf_amount,  
                  round((begval+val1+val2+val3+val4) / case when begbal+val1+val2+val3+val4 > 0 then begbal+val1+val2+val3+val4 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5 as balance_quantity,
                  begval+val1+val2+val3+val4+val5 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5) / case when (begbal+qty1+qty2+qty3+qty4+qty5) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '06':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5 as bf_qty,
                  begval+val1+val2+val3+val4+val5 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5) / case when begbal+val1+val2+val3+val4+val5 > 0 then begbal+val1+val2+val3+val4+val5 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '07':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6) / case when begbal+val1+val2+val3+val4+val5+val6 > 0 then begbal+val1+val2+val3+val4+val5+val6 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '08':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7) / case when begbal+val1+val2+val3+val4+val5+val6+val7 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '09':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '10':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '11':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '12':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11+val12 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11+val12) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)

            self._cr.execute(sql_bf)
            for stock_bf1 in self._cr.dictfetchall():
                new_product_card['bf_quantity'] = stock_bf1['bf_qty'] or 0.0
                new_product_card['bf_cost'] = stock_bf1['bf_priceunit'] or 0.0
                new_product_card['bf_value'] = stock_bf1['bf_amount'] or 0.0
                new_product_card['balance_quantity'] = stock_bf1['balance_quantity'] or 0.0
                new_product_card['balance_cost'] = stock_bf1['balance_cost'] or 0.0
                new_product_card['balance_value'] = stock_bf1['balance_amount'] or 0.0
                stock_bf = stock_bf1
                # beging_value += stock_bf1['bf_amount']
                # ending_value += stock_bf1['balance_amount']

            new_card_id = card_product.create(new_product_card)
            card_product_obj = iscp.search([('product_id', '=', product.id), ('stock_date_to', '<', self.date_from)],
                                           order='stock_date_to desc', limit=1)
            sql_stock_transaction = """
            select 
              docdat,
              docnum,
              seqnum,
              case when posopr in ('0','1','2','5') then xtrnqty else 0 end as in_qty,
              case when posopr in ('0','1','2','5') then xunitpr else 0 end as in_unitprice,
              case when posopr in ('0','1','2','5') then xtrnval else 0 end as in_amount,
              case when posopr in ('6','7','8','9') then xtrnqty else 0 end as out_qty,
              case when posopr in ('6','7','8','9') then xunitpr else 0 end as out_unitprice,
              case when posopr in ('6','7','8','9') then xtrnval else 0 end as out_amount,
              refnum,
              people
            from express_stcrd_dbf
            where 
              stkcod = '%s'
              and docdat between '%s' and '%s'
            order by docdat, case when left(docnum,2) = 'IV' then 3 when left(docnum,2) = 'RI' then 1 else 2 end, docnum
            """ % (product.default_code, self.date_from, self.date_to)
            balance = new_card_id.bf_quantity
            cost = new_card_id.bf_cost
            amount = new_card_id.bf_value
            if product.date_stock == self.date_from:
                balance = product.balance_quantity
                cost = product.cost_price
                amount = product.cost_amount
            if card_product_obj:  # Get value from Balanced
                balance = card_product_obj.balance_quantity
                cost = card_product_obj.balance_cost
                amount = card_product_obj.balance_value
            else:  # Get value from Express
                balance = new_card_id.bf_quantity
                cost = new_card_id.bf_cost
                amount = new_card_id.bf_value
            l_in_qty = 0.0
            l_out_qty = 0.0
            self._cr.execute(sql_stock_transaction)
            transactions = self._cr.fetchall()
            last_card_line = False
            for docdat, docnum, seqnum, in_qty, in_unitprice, in_amount, out_qty, out_unitprice, out_amount, refnum, people in transactions:
                new_card_line = {}
                new_card_line['date'] = docdat
                new_card_line['stock_period_id'] = self.id
                new_card_line['product_line_id'] = new_card_id.id
                new_card_line['product_id'] = product.id
                new_card_line['document_number'] = docnum
                new_card_line['date_invoice'] = docdat
                new_card_line['in_quantity'] = in_qty
                new_card_line['in_cost'] = in_unitprice
                new_card_line['in_value'] = in_amount
                new_card_line['out_quantity'] = out_qty
                new_card_line['out_cost'] = out_unitprice
                new_card_line['out_value'] = out_amount
                new_card_line['name'] = refnum
                new_card_line['partner_name'] = people
                if in_qty:  # Incoming
                    balance += round(l_in_qty, 3)
                    l_in_qty += round(l_in_qty, 3)
                    amount += round(in_amount, 4)
                    if balance:
                        cost = round(amount / balance, 4)
                if out_qty:  # Outgoing
                    balance = round(balance, 3) - round(out_qty, 3)
                    l_out_qty += round(out_qty, 3)
                    amount -= round(out_amount, 4)
                    if balance:
                        cost = round(amount / balance, 4)
                new_card_line['balance_quantity'] = balance
                new_card_line['balance_cost'] = cost
                new_card_line['balance_value'] = amount
                last_card_line = card_line.create(new_card_line)
            if last_card_line:
                new_card_id.write({'balance_quantity': last_card_line.balance_quantity,
                                   'in_quantity': in_qty,
                                   'out_quantity': out_qty,
                                   'balance_cost': last_card_line.balance_cost,
                                   'balance_value': last_card_line.balance_value})
        return True

    @api.multi
    def button_import_express_bf(self):
        products = self.env['product.product'].search([('type', '=', 'product')], order='default_code')
        card_product = self.env['ineco.stock.card.product']
        card_line = self.env['ineco.stock.card.product.line']
        iscp = self.env['ineco.stock.card.product']
        stock_move = self.env['stock.move']
        invoice_obj = self.env['account.invoice']
        for product in products:
            new_product_card = {
                'name': product.name,
                'product_id': product.id,
                'stock_period_id': self.id,
            }
            new_card_id = card_product.create(new_product_card)
        home = expanduser("~")
        r = open(home + '/STBALLC.TXT', 'r')
        for line in r.readlines():
            code = line[2:13]
            if code[:1].isalpha():
                # print (code)
                amount = float(line[-25:].replace(' ', '').replace(',', ''))
                cost = float(line[-46:][:22].replace(' ', '').replace(',', ''))
                quantity = float(
                    line[-66:][:15].replace(' ', '').replace(',', '').replace('\xc2', '').replace('\xb4', ''))
                product_line = card_product.search(
                    [('product_id.default_code', '=', code), ('stock_period_id', '=', self.id)])
                if product_line:
                    # product_line.write({'bf_quantity': quantity, 'bf_cost': cost, 'bf_value': amount })
                    product_line.write({'balance_quantity': quantity, 'balance_cost': cost, 'balance_value': amount})

    @api.multi
    def button_import_express_bf2(self):
        delete_sql = """
            delete from ineco_stock_card_product where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql)
        delete_sql2 = """
            delete from ineco_stock_card_product_line where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql2)
        products = self.env['product.product'].search([('type', '=', 'product')], order='default_code')
        card_product = self.env['ineco.stock.card.product']
        card_line = self.env['ineco.stock.card.product.line']
        iscp = self.env['ineco.stock.card.product']
        stock_move = self.env['stock.move']
        invoice_obj = self.env['account.invoice']

        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self.env['product.product']._get_domain_locations()

        in_loc = []
        warehouses = self.env['stock.warehouse'].search([])
        for warehouse in warehouses:
            in_loc += [x.id for x in
                       self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.id)])]

        for product in products:
            new_product_card = {
                'name': product.name,
                'product_id': product.id,
                'stock_period_id': self.id,
            }
            stock_bf = {}
            if self.date_from[5:7] == '01':
                sql_bf = """
                select 
                  begbal as bf_qty,
                  begval as bf_amount,  
                  round((begval) / case when begbal > 0 then begbal else 1 end, 4) as bf_priceunit,
                  begbal+qty1 as balance_quantity,
                  begval+val1 as balance_amount,  
                  round((begval + val1) / case when (begbal + qty1) > 0 then (begbal+qty1) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '02':
                sql_bf = """
                select 
                  begbal+qty1 as bf_qty,
                  begval+val1 as bf_amount,  
                  round((begval+val1) / case when begbal+val1 > 0 then begbal+val1 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2 as balance_quantity,
                  begval+val1+val2 as balance_amount,  
                  round((begval+val1+val2) / case when (begbal+qty1+qty2) > 0 then (begbal+qty1+qty2) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '03':
                sql_bf = """
                select 
                  begbal+qty1+qty2 as bf_qty,
                  begval+val1+val2 as bf_amount,  
                  round((begval+val1+val2) / case when begbal+val1+val2 > 0 then begbal+val1+val2 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3 as balance_quantity,
                  begval+val1+val2+val3 as balance_amount,  
                  round((begval+val1+val2+val3) / case when (begbal+qty1+qty2+qty3) > 0 then (begbal+qty1+qty2+qty3) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '04':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3 as bf_qty,
                  begval+val1+val2+val3 as bf_amount,  
                  round((begval+val1+val2+val3) / case when begbal+val1+val2+val3 > 0 then begbal+val1+val2+val3 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4 as balance_quantity,
                  begval+val1+val2+val3+val4 as balance_amount,  
                  round((begval+val1+val2+val3+val4) / case when (begbal+qty1+qty2+qty3+qty4) > 0 then (begbal+qty1+qty2+qty3+qty4) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '05':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4 as bf_qty,
                  begval+val1+val2+val3+val4 as bf_amount,  
                  round((begval+val1+val2+val3+val4) / case when begbal+val1+val2+val3+val4 > 0 then begbal+val1+val2+val3+val4 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5 as balance_quantity,
                  begval+val1+val2+val3+val4+val5 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5) / case when (begbal+qty1+qty2+qty3+qty4+qty5) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '06':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5 as bf_qty,
                  begval+val1+val2+val3+val4+val5 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5) / case when begbal+val1+val2+val3+val4+val5 > 0 then begbal+val1+val2+val3+val4+val5 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '07':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6) / case when begbal+val1+val2+val3+val4+val5+val6 > 0 then begbal+val1+val2+val3+val4+val5+val6 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '08':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7) / case when begbal+val1+val2+val3+val4+val5+val6+val7 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '09':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '10':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '11':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)
            elif self.date_from[5:7] == '12':
                sql_bf = """
                select 
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11 as bf_qty,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 as bf_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11) / case when begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 > 0 then begbal+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11 else 1 end, 4) as bf_priceunit,
                  begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12 as balance_quantity,
                  begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11+val12 as balance_amount,  
                  round((begval+val1+val2+val3+val4+val5+val6+val7+val8+val9+val10+val11+val12) / case when (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12) > 0 then (begbal+qty1+qty2+qty3+qty4+qty5+qty6+qty7+qty8+qty9+qty10+qty11+qty12) else 1 end ,4) as balance_cost 
                from express_stloc_dbf
                where stkcod = '%s' and loccod = '01' """ % (product.default_code)

            self._cr.execute(sql_bf)
            for stock_bf1 in self._cr.dictfetchall():
                new_product_card['bf_quantity'] = stock_bf1['bf_qty'] or 0.0
                new_product_card['bf_cost'] = stock_bf1['bf_priceunit'] or 0.0
                new_product_card['bf_value'] = stock_bf1['bf_amount'] or 0.0
            new_card_id = card_product.create(new_product_card)
            balance = new_card_id.bf_quantity or 0.0
            cost = 'bf_cost' in new_product_card and new_product_card['bf_cost'] or 0.0
            in_qty = 0.0
            out_qty = 0.0
            for move in stock_move.search([('product_id', '=', product.id), ('state', '=', 'done'),
                                           ('date', '>=', self.date_from), ('date', '<=', self.date_to)], order='date'):
                new_card_line = {
                    'name': move.origin or ' ',
                    'stock_period_id': self.id,
                    'product_line_id': new_card_id.id,
                    'product_id': product.id,
                    'date': move.date,
                    'partner_id': move.picking_id and move.picking_id.partner_id and move.picking_id.partner_id.id or False,
                }
                if move.origin:
                    invoice = invoice_obj.search([('origin', '=', move.origin),
                                                  ('state', 'not in', ('draft', 'cancel'))])
                    if len(invoice) > 0:
                        invoice = invoice[0]
                    if invoice.supplier_invoice_number:
                        new_card_line['document_number'] = invoice.supplier_invoice_number or invoice.reference
                        new_card_line['date_invoice'] = invoice.date_invoice
                        new_card_line['invoice_id'] = invoice.id
                        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id),
                                                                                ('product_id', '=', product.id)])
                        if invoice_line and len(invoice_line) > 1:
                            invoice_line = invoice_line[0]
                        new_card_line['in_cost'] = invoice_line.price_unit * invoice.exchange_rate
                        new_card_line['in_value'] = new_card_line['in_cost'] * move.product_qty
                        cost = ((balance * cost) + new_card_line['in_value']) / (balance + move.product_qty)

                if 'document_number' not in new_card_line and move.picking_id:
                    invoice = invoice_obj.search([('origin', '=', move.picking_id.name),
                                                  ('state', 'not in', ('draft', 'cancel'))])
                    if invoice:
                        new_card_line['document_number'] = invoice.number or False
                        new_card_line['date_invoice'] = invoice.date_invoice
                        new_card_line['invoice_id'] = invoice.id

                if 'document_number' not in new_card_line:
                    new_card_line['document_number'] = ' '

                if not (move.location_dest_id.id in in_loc and
                        move.location_id.id in in_loc):
                    if move.location_dest_id.id in in_loc:
                        new_card_line['in_quantity'] = move.product_qty
                        balance += move.product_qty
                        in_qty += move.product_qty
                        if 'in_quantity' in new_card_line and 'in_cost' not in new_card_line:
                            new_card_line['in_cost'] = product.standard_price
                            new_card_line['in_value'] = move.product_qty * product.standard_price
                            cost = ((balance * cost) + new_card_line['in_value']) / (balance + move.product_qty)

                    if move.location_dest_id.id not in in_loc:
                        new_card_line['out_quantity'] = move.product_qty
                        new_card_line['out_cost'] = cost
                        new_card_line['out_value'] = cost * move.product_qty
                        balance -= move.product_qty
                        out_qty += move.product_qty
                    new_card_line['balance_quantity'] = balance
                    new_card_line['balance_cost'] = cost
                    new_card_line['balance_value'] = balance * cost
                    card_line.create(new_card_line)
            new_card_id.write({'balance_quantity': balance, 'in_quantity': in_qty, 'out_quantity': out_qty,
                               'balance_cost': cost, 'balance_value': balance * cost})

        return True

    @api.multi
    def button_compute_bof(self):
        for data in self:
            for product in data.product_line_ids:
                product.button_compute_bof()
                product.button_recompute()

    @api.multi
    def button_recompute(self):
        for data in self:
            for product in data.product_line_ids:
                # product.button_update_bf()
                balance_qty = product.bf_quantity
                # cost = product.bf_cost
                balance_value = product.bf_value
                balance_cost = product.bf_cost
                sql = """
                    select 
                      balance_cost,
                      balance_quantity,
                      balance_value
                    from
                      ineco_stock_card_product_line
                    where product_id = %s and stock_period_id = %s
                      order by date desc, sequence desc limit 1
                """ % (product.product_id.id, data.id)
                self._cr.execute(sql)
                result = self._cr.dictfetchone()
                if result:
                    balance_value = result['balance_value']
                    balance_cost = result['balance_cost']
                    balance_qty = result['balance_quantity']
                product.balance_quantity = balance_qty
                product.balance_cost = balance_cost
                product.balance_value = balance_value
        return True

    # ใช้ตัวนี้อยู่
    @api.multi
    def button_compute(self):
        stock_move = self.env['stock.move']
        card_line = self.env['ineco.stock.card.product.line']
        iscp = self.env['ineco.stock.card.product']
        invoice_obj = self.env['account.invoice']
        products = self.env['product.product'].search([('type', '=', 'product'),
                                                       ('disable_stock_card', '!=', True)],
                                                      order='default_code')
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self.env['product.product']._get_domain_locations()
        # print domain_move_in_loc
        warehouses = self.env['stock.warehouse'].search([])
        in_loc = []
        for warehouse in warehouses:
            in_loc += [x.id for x in
                       self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.id)])]
        # print (in_loc)
        # out_loc = [x.id for x in self.env['stock.location'].search(domain_move_out_loc)]
        card_product = self.env['ineco.stock.card.product']
        delete_sql = """
            delete from ineco_stock_card_product where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql)
        delete_sql2 = """
            delete from ineco_stock_card_product_line where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql2)
        # Clear ยอด Issue ของ Stock Card
        delete_sql3 = """
            delete from ineco_stock_card_lot_issue where date >= '{}'
        """.format(self.date_from)
        self._cr.execute(delete_sql3)
        # Clear ยอด Stock Card Lot ของ Stock Card
        delete_sql4 = """
            delete from ineco_stock_card_lot where date >= '{}'
        """.format(self.date_from)
        self._cr.execute(delete_sql4)

        for product in products:
            update_balance_sql4 = """
                update ineco_stock_card_lot
                set balance = raw.quantity - raw.issue
                from (
                select 
                  id, 
                  quantity, 
                  (select sum(quantity) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) as issue,
                  balance 
                from ineco_stock_card_lot a
                where product_id = {} 
                  and quantity-(select sum(quantity) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) > 0) raw
                where ineco_stock_card_lot.id = raw.id
            """.format(product.id)
            self._cr.execute(update_balance_sql4)

            card_product_obj = iscp.search([('product_id', '=', product.id),
                                            ('stock_date_to', '<', self.date_from)],
                                           order='stock_date_to desc', limit=1)

            new_product_card = {
                'name': product.name,
                'product_id': product.id,
                'stock_period_id': self.id,
            }
            if card_product_obj:
                # card_product_obj = self.env['ineco.stock.card.product'].browse(passed_stock)
                new_product_card['bf_quantity'] = card_product_obj.balance_quantity
                new_product_card['bf_cost'] = card_product_obj.balance_cost
                new_product_card['bf_value'] = card_product_obj.balance_value

            # 2019-11-06 (Fixed error หา bf_quantity ไม่เจอ)
            if not new_product_card.get('bf_quantity', False):
                new_product_card['bf_quantity'] = 0
            if not new_product_card.get('bf_cost', False):
                new_product_card['bf_cost'] = 0
            if not new_product_card.get('bf_value', False):
                new_product_card['bf_value'] = 0
            new_card_id = card_product.create(new_product_card)
            new_card_id.button_recompute()

        self.last_update_stock = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ตัวล่าสุดตัวนี้อยู่
    @api.multi
    def button_compute_20220723(self):
        stock_move = self.env['stock.move']
        card_line = self.env['ineco.stock.card.product.line']
        iscp = self.env['ineco.stock.card.product']
        invoice_obj = self.env['account.invoice']
        products = self.env['product.product'].search([('type', '=', 'product'),
                                                       ('disable_stock_card', '!=', True)],
                                                      order='default_code')
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self.env['product.product']._get_domain_locations()
        # print domain_move_in_loc
        warehouses = self.env['stock.warehouse'].search([])
        in_loc = []
        for warehouse in warehouses:
            in_loc += [x.id for x in
                       self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.id)])]
        # print (in_loc)
        # out_loc = [x.id for x in self.env['stock.location'].search(domain_move_out_loc)]
        card_product = self.env['ineco.stock.card.product']
        delete_sql = """
            delete from ineco_stock_card_product where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql)
        delete_sql2 = """
            delete from ineco_stock_card_product_line where stock_period_id = %s
        """ % self.id
        self._cr.execute(delete_sql2)
        # Clear ยอด Issue ของ Stock Card
        delete_sql3 = """
            delete from ineco_stock_card_lot_issue where date >= '{}'
        """.format(self.date_from)
        self._cr.execute(delete_sql3)
        # Clear ยอด Stock Card Lot ของ Stock Card
        delete_sql4 = """
            delete from ineco_stock_card_lot where date >= '{}'
        """.format(self.date_from)
        self._cr.execute(delete_sql4)

        for product in products:
            _logger.info("คำนวณสินค้าคงเหลือ {}".format(product.default_code))
            update_balance_sql4 = """
                update ineco_stock_card_lot
                set balance = raw.quantity - raw.issue
                from (
                select 
                  id, 
                  quantity, 
                  (select sum(quantity) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) as issue,
                  balance 
                from ineco_stock_card_lot a
                where product_id = {} 
                  and quantity-(select sum(quantity) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) > 0) raw
                where ineco_stock_card_lot.id = raw.id
            """.format(product.id)
            self._cr.execute(update_balance_sql4)

            new_product_card = {
                'name': product.name,
                'product_id': product.id,
                'stock_period_id': self.id,
            }
            # สำหรับบันทึกยอดยกมาเข้าระบบครั้งแรก
            # if product.date_stock == self.date_from:
            #     new_product_card['bf_quantity'] = product.balance_quantity
            #     new_product_card['bf_cost'] = product.cost_price
            #     new_product_card['bf_value'] = product.cost_amount
            # ineco.stock.card.product iscp
            card_product_obj = iscp.search([('product_id', '=', product.id),
                                            ('stock_date_to', '<', self.date_from)],
                                           order='stock_date_to desc', limit=1)

            if card_product_obj:
                # card_product_obj = self.env['ineco.stock.card.product'].browse(passed_stock)
                new_product_card['bf_quantity'] = card_product_obj.balance_quantity
                new_product_card['bf_cost'] = card_product_obj.balance_cost
                new_product_card['bf_value'] = card_product_obj.balance_value

            # 2019-11-06 (Fixed error หา bf_quantity ไม่เจอ)
            if not new_product_card.get('bf_quantity', False):
                new_product_card['bf_quantity'] = 0
            if not new_product_card.get('bf_cost', False):
                new_product_card['bf_cost'] = 0
            if not new_product_card.get('bf_value', False):
                new_product_card['bf_value'] = 0

            # else:
            #    new_product_card['bf_quantity'] = self._compute_product(product.id, self.date_from, self.date_to,
            #                                                         domain_move_in_loc, domain_move_out_loc)
            # print (new_product_card)
            new_card_id = card_product.create(new_product_card)
            balance = new_card_id.bf_quantity or 0.0
            cost = 'bf_cost' in new_product_card and new_product_card['bf_cost'] or 0.0
            in_qty = 0.0
            out_qty = 0.0
            bf_balance_qty = new_product_card['bf_quantity']
            bf_balance_value = new_product_card['bf_value']
            # cost = new_product_card['bf_cost']

            # sql = """
            # select
            #   a.id,
            #   a.stkcod,
            #   a.docdat::date as docdat,
            #   a.price,
            #   a.quantity,
            #   a.docnum,
            #   a.partner_id,
            #   a.invoice_id,
            #   0.00 as fifo_cost
            #   --(select fifo_price from query_fifo_price where query_fifo_price.id = a.id and stkcod=a.stkcod and fifo_price > 0 limit 1) as fifo_cost
            # from query_stock_transaction_odoo a
            # where stkcod = '%s' and a.docdat between '%s' and '%s'
            # order by stkcod, docdat, quantity desc
            # """ % (product.default_code, self.date_from, self.date_to)
            sql = """
            select 
              min(a.id) as id,
              a.stkcod,
              a.docdat::date as docdat,
              a.price,
              round(sum(a.quantity),3) as quantity,
              a.docnum,
              a.partner_id,
              a.invoice_id,
              0.00 as fifo_cost
            from query_stock_transaction_odoo a
            where stkcod = '%s' and a.docdat between '%s' and '%s'
			group by stkcod, docdat, price, docnum,partner_id,invoice_id
            order by stkcod, docdat, quantity desc
            """ % (product.default_code, self.date_from, self.date_to)
            self._cr.execute(sql)
            moves = self._cr.dictfetchall()
            sequence = 0
            for move in moves:
                invoice_id = False
                sequence += 10
                new_card_line = {
                    'sequence': sequence,
                    'name': move['docnum'] or ' ',
                    'stock_period_id': self.id,
                    'product_line_id': new_card_id.id,
                    'product_id': product.id,
                    'date': move['docdat'],
                    'partner_id': move['partner_id'] or False,
                }
                if move['docnum']:
                    new_card_line['document_number'] = move['docnum'] or 'ไม่ทราบเอกสาร'
                    new_card_line['date_invoice'] = move['docdat']
                    new_card_line['invoice_id'] = move['invoice_id']
                    invoice_id = self.env['account.invoice'].browse(move['invoice_id'])

                if move['quantity'] >= 0:
                    # หาตู้นทุนสินค้าสำเร็จรูปจากใบเบิกที่เลขที่เดียวกับใบผลิต
                    if not move['invoice_id']:
                        # product_cost_sql = """
                        #     select
                        #         (select fifo_price from query_fifo_price where query_fifo_price.id = a.id and stkcod=a.stkcod and fifo_price > 0 limit 1) as fifo_cost
                        #     from query_stock_transaction_odoo a
                        #     where docnum = '{}' and quantity < 0
                        # """.format(move['docnum'])
                        product_cost_sql = """
                            select abs(coalesce(sum(out_value),0.00)) as out_cost from ineco_stock_card_product_line
                            where name = '{}' and out_value < 0 limit 1""".format(move['docnum'])
                        self._cr.execute(product_cost_sql)
                        productions = self._cr.dictfetchall()
                        if productions and productions[0]['out_cost']:
                            # move['price'] = productions[0]['out_cost'] or 0.00
                            # เฉลี่ยต้นทุนสินค้าสำเร็จรูป
                            move['price'] = round(productions[0]['out_cost'] / move['quantity'], 4)
                    else:
                        invoice_id = self.env['account.invoice'].browse(move['invoice_id'])
                        if invoice_id.type == 'in_refund':
                            # ถ้าเป็นส่งคืนสินค้าให้ Supplier ให้เราราคาที่ตั้งเจ้าหนี้มา
                            if invoice_id.origin:
                                origin = invoice_id.origin
                                invoice_line = self.env['account.invoice.line'].search(
                                    [('number', '=', origin), ('product_id', '=', product.id)])
                                if invoice_line:
                                    move['price'] = invoice_line.price_unit
                        elif invoice_id.type == 'out_refund':
                            # แต่ถ้าเป็นส่งรับคืนสินค้าจากลูกค้าา ให้เอาราคาต้นทุนของ Invoice ที่ส่งให้ลูกค้านั้นๆ
                            if invoice_id.origin:
                                origin = invoice_id.origin
                                issue_obj = self.env['ineco.stock.card.lot.issue']
                                issue = issue_obj.search([('name', '=', origin), ('stock_card_lot_id', '!=', False)],
                                                         limit=1)
                                if issue:
                                    move['price'] = issue.stock_card_lot_id.cost
                    new_card_line['in_cost'] = move['price']
                    new_card_line['in_quantity'] = move['quantity']
                    new_card_line['in_value'] = move['price'] * move['quantity']
                    if not invoice_id or (invoice_id and invoice_id.cn_type == '1'):
                        in_qty += move['quantity']
                        bf_balance_qty += move['quantity']
                        bf_balance_value += move['price'] * move['quantity']
                    else:
                        bf_balance_value += move['price'] * move['quantity']
                    new_lot_data = {
                        'name': move['docnum'],
                        'date': move['docdat'],
                        'quantity': move['quantity'],
                        'cost': move['price'],
                        'balance': move['quantity'],
                        'product_id': product.id,
                        'stock_card_id': self.id
                    }
                    lot_obj = self.env['ineco.stock.card.lot']
                    lot = lot_obj.search([('name', '=', move['docnum']), ('product_id', '=', product.id)])
                    # ตรวสอบ LOT ถ้าหากไม่พบให้สร้าง LOT ให่ ถ้าพบเพิ่มจำนวนเข้า LOT
                    if not lot:
                        lot_obj.create(new_lot_data)
                    else:
                        lot.write({'quantity': lot.quantity + move['quantity']})
                    #                'balance': lot.balance+move['quantity']})

                if move['quantity'] < 0:
                    lot_stock = self.env['ineco.stock.card.lot'].search(
                        [('product_id', '=', product.id), ('balance', '>', 0.00)], order='date, name')  # balance
                    # _logger.warning(msg="{} {}".format('Issue', 'OK'))
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        issue_qty = 0
                    else:
                        issue_qty = move['quantity']
                    out_qty = 0.0
                    out_cost = 0.0
                    out_value = 0.0
                    while issue_qty < 0 and lot_stock:
                        issue_obj = self.env['ineco.stock.card.lot.issue']
                        is_partial = False
                        for stock in lot_stock:
                            # ตรวจสอบสินค้าบางตัวเท่านั้น
                            # if move['stkcod'] == 'T-QIA-001-1':
                            #     _logger.error(
                            #         msg='T-QIA-001-1 {} {}'.format(round(stock.balance, 2), round(abs(issue_qty), 2)))
                            if round(stock.balance, 3) >= round(abs(issue_qty), 3):
                                new_issue = {
                                    'name': move['docnum'],
                                    'date': move['docdat'],
                                    'quantity': abs(issue_qty),
                                    'stock_card_lot_id': stock.id,
                                    'refer_id': move['id']
                                }
                                issue_obj.create(new_issue)
                                issue_qty = 0
                                out_qty = issue_qty
                                out_cost = stock.cost
                                out_value = stock.cost * issue_qty
                                # if product.default_code == 'C-GAD-001-1':
                                #     print(move['id'])
                                break
                            else:
                                issue_qty += stock.balance
                                out_qty += stock.balance
                                out_value += (stock.balance * stock.cost)
                                out_cost += out_value / out_qty
                                new_issue = {
                                    'name': move['docnum'],
                                    'date': move['docdat'],
                                    'quantity': stock.balance,
                                    'stock_card_lot_id': stock.id,
                                    'refer_id': move['id']
                                }
                                issue_obj.create(new_issue)
                                is_partial = True
                                # if product.default_code == 'C-GAD-001-1':
                                #     print(move['id'])
                        break
                        # _logger.error(msg="{} {}".format(product.id, out_cost))
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        new_card_line['out_quantity'] = 0
                        out_cost = 0.00
                    else:
                        new_card_line['out_quantity'] = move['quantity']
                        if move['docnum']:
                            check_total_sql = """
                                select sum(a.quantity) as total from ineco_stock_card_lot_issue a
                                join ineco_stock_card_lot b on b.id = a.stock_card_lot_id
                                where a.name = '""" + move['docnum'] + """' and refer_id = {}""".format(move['id'])
                            self._cr.execute(check_total_sql)
                            moves = self._cr.dictfetchall()
                            if moves and moves[0]['total']:
                                # print(move['docnum'], move['id'])
                                if move['docnum']:
                                    out_sql = r"""
                                        select round(sum(b.cost * a.quantity)/coalesce(sum(a.quantity),1.00),4) as out_cost from ineco_stock_card_lot_issue a
                                        join ineco_stock_card_lot b on b.id = a.stock_card_lot_id
                                        where a.name = '""" + move['docnum'] + """' and refer_id = {}""".format(
                                        move['id'])
                                    self._cr.execute(out_sql)
                                    moves = self._cr.dictfetchall()
                                    if moves and moves[0]['out_cost']:
                                        if product.categ_id.use_fg_standard_cost:
                                            _logger.info(
                                                'User Standard Cost Compute {}'.format(product.default_code))
                                            out_cost = 0.00
                                        else:
                                            out_cost = moves[0]['out_cost']
                                    # print(out_cost, moves[0])
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        new_card_line['out_cost'] = 0.0
                        new_card_line['out_value'] = move['price'] * move['quantity']
                    else:
                        new_card_line['out_cost'] = out_cost or new_product_card['bf_cost']
                        new_card_line['out_value'] = (out_cost or new_product_card['bf_cost']) * move['quantity']
                    if not invoice_id or (invoice_id and invoice_id.cn_type == '1'):
                        # ลดปริมาณ
                        out_qty += move['quantity']
                        bf_balance_qty += move['quantity']
                        bf_balance_value += round(round((out_cost) * move['quantity'] * 100) / 100, 2)
                    else:
                        # ลดมูลค่า
                        bf_balance_value += move['price'] * move['quantity']
                        # bf_balance_value += (out_cost) * move['quantity']
                        bf_balance_value = round(bf_balance_value, 2)

                new_card_line['balance_quantity'] = bf_balance_qty
                if bf_balance_qty:
                    new_card_line['balance_cost'] = bf_balance_value / bf_balance_qty
                    cost = bf_balance_value / bf_balance_qty
                new_card_line['balance_value'] = bf_balance_value

                # แก้ไขหากจำนวน = 0 ให้มูลค่า และ คงเหลือเป็น 0 ด้วย
                if new_card_line['balance_quantity'] == 0.0:
                    new_card_line['balance_cost'] = 0.0
                    new_card_line['balance_value'] = 0.0
                    bf_balance_value = 0.0
                ###

                if not 'document_number' in new_card_line:
                    new_card_line['document_number'] = 'ปรับปรุง'
                card_line.create(new_card_line)
            if moves:
                if -1.0 <= bf_balance_value <= 1.00:
                    if not product.categ_id.use_fg_standard_cost:
                        bf_balance_qty = 0.00
                    cost = 0.00
                    bf_balance_value = 0.00
                new_card_id.write({'balance_quantity': bf_balance_qty, 'in_quantity': in_qty, 'out_quantity': out_qty,
                                   'balance_cost': cost, 'balance_value': bf_balance_value})
            else:
                if bf_balance_qty and bf_balance_value:
                    # cost = bf_balance_value / bf_balance_qty
                    cost = new_product_card['bf_cost']
                    new_card_id.write(
                        {'balance_quantity': bf_balance_qty, 'in_quantity': in_qty, 'out_quantity': out_qty,
                         'balance_cost': cost, 'balance_value': bf_balance_value})
                elif bf_balance_qty:
                    new_card_id.write(
                        {'balance_quantity': bf_balance_qty})
        self.last_update_stock = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @api.multi
    def button_generate_lot(self):
        sql_delete_data = "delete from ineco_stock_card_lot where stock_card_id = {}".format(self.id)
        self._cr.execute(sql_delete_data)
        for product in self.product_line_ids:
            if product.balance_quantity > 0:
                new_lot_data = {
                    'name': 'ยอดยกมา {}'.format(self.name),
                    'date': product.stock_date_from,
                    'quantity': product.balance_quantity,
                    'cost': product.balance_cost,
                    'balance': product.balance_quantity,
                    'product_id': product.product_id.id,
                    'stock_card_id': self.id
                }
                lot_obj = self.env['ineco.stock.card.lot']
                new_lot = lot_obj.create(new_lot_data)

    @api.multi
    def unlink(self):
        issue_obj = self.env['ineco.stock.card.lot.issue'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to)])
        if issue_obj:
            issue_obj.unlink()
        # ให้ลบ Stock Card Lot เพิ่มเติม 2020-12-09
        lot_obj = self.env['ineco.stock.card.lot'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to)])
        if lot_obj:
            lot_obj.unlink()
        return super(InecoStockCard, self).unlink()

    @api.one
    def button_update_fg_standard_cost(self):
        for product in self.product_line_ids:
            if product.product_id.categ_id.use_fg_standard_cost:
                if product.balance_quantity and product.product_id.standard_price:
                    product.write({
                        'balance_cost': round(product.product_id.standard_price, 2),
                        'balance_value': round(product.balance_quantity * round(product.product_id.standard_price, 2),
                                               2)
                    })

    @api.multi
    def correct_stock_card_lot(self):
        for stock_card in self:
            for product in stock_card.product_line_ids:
               product.button_update_lot_stock_equal_bof()


class InecoStockCardProduct(models.Model):
    _name = 'ineco.stock.card.product'
    _description = 'Stock Card Product'

    name = fields.Char(string='Description')
    stock_period_id = fields.Many2one('ineco.stock.card', string='Stock Period', ondelete='cascade')
    stock_date_from = fields.Date(string='Date From', related='stock_period_id.date_from', store=True, readonly=True)
    stock_date_to = fields.Date(string='Date to', related='stock_period_id.date_to', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, track_visibility='onchange')
    bf_quantity = fields.Float(string=u'จำนวน (ยกมา)', digits=(12, 3))
    bf_cost = fields.Float(string=u'ต้นทุน/หน่วย (ยกมา)', digits=(12, 4))
    bf_value = fields.Float(string=u'มูลค่า (ยกมา)', digits=(12, 2))
    in_quantity = fields.Float(string='In Qty', digits=(12, 3))
    in_cost = fields.Float(string='Cost', digits=(12, 4))
    in_value = fields.Float(string='Values', digits=(12, 2))
    out_quantity = fields.Float(string='Out Qty', digits=(12, 3))
    out_cost = fields.Float(string='Cost', digits=(12, 4))
    out_value = fields.Float(string='Values', digits=(12, 2))
    balance_quantity = fields.Float(string=u'จำนวน (ยกไป)', digits=(12, 3))
    balance_cost = fields.Float(string=u'ต้นทุน/หน่วย (ยกไป)', digits=(12, 4))
    balance_value = fields.Float(string=u'มูลค่า (ยกไป)', digits=(12, 2))
    line_ids = fields.One2many('ineco.stock.card.product.line', 'product_line_id', string='Lines')
    manual_ids = fields.One2many('ineco.stock.card.product.manual', 'product_line_id', string='Manual Lines')

    @api.multi
    def button_open(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        record_url = base_url + "/web#id=" + str(
            self.id) + "&view_type=form&model=" + self._name  # +"&menu_id=XXX&action=YYY"
        client_action = {
            'type': 'ir.actions.act_url',
            'name': "Stock Card",
            'target': 'new',
            'url': record_url,
        }
        return client_action
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': _('Stock Card'),
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': self._name,
        #     'res_id': self.id,
        #     'target': '_blank',
        # }

    @api.multi
    def button_recompute_old(self):
        for product in self:
            # ปรับยอดยกมา จากยอดยกไปงวดก่อนหน้า
            product.button_update_bf()
            balance_qty = product.bf_quantity
            cost = product.bf_cost
            balance_value = product.bf_value
            for line in product.line_ids:
                if line.in_quantity or line.in_value:
                    # หา Cost ไม่ได้จากการสั่งซื้อ
                    if not line.cn_type or (line.cn_type and line.cn_type == '1'):  # ปริมาณ
                        if not line.in_cost:
                            # line.in_cost = line.product_id.standard_price
                            line.in_cost = 0.00
                        if line.in_quantity:
                            line.in_value = line.in_quantity * line.in_cost
                            balance_value += (line.in_quantity * line.in_cost)
                            # สร้าง Stock Card หรือปรับปรุงข้อมูล ถ้ามีการรับสินค้าเพิ่มในระบบ
                            lot_obj = self.env['ineco.stock.card.lot']
                            lot = lot_obj.search([('name', '=', line.document_number)])
                            if lot:
                                lot.write({
                                    'date': line.date,
                                    'quantity': line.in_quantity,
                                    'cost': line.in_cost
                                })
                            else:
                                new_lot_data = {
                                    'name': line.document_number,
                                    'date': line.date,
                                    'quantity': line.in_quantity,
                                    'cost': line.in_cost,
                                    'balance': line.in_quantity,
                                    'product_id': line.product_id.id,
                                    'stock_card_id': product.stock_period_id.id
                                }
                                new_lot = lot_obj.create(new_lot_data)
                        else:
                            balance_value += line.in_value
                        balance_qty += line.in_quantity
                        # cost = ((balance * cost) + new_card_line['in_value']) / (balance + move.product_qty)
                        cost = round(balance_value / balance_qty, 4)
                    else:  # มูลค่า
                        # line.in_quantity = 0.00
                        balance_value += line.in_value
                        cost = round(balance_value / balance_qty, 4)
                if line.out_quantity or line.out_value:
                    # line.out_cost = cost
                    if not line.cn_type or (line.cn_type and line.cn_type == '1'):  # ปริมาณ
                        if not line.out_cost:
                            # print('Default cost on out qty', line.document_number)
                            # line.out_cost = line.product_id.standard_price
                            line.out_cost = cost
                        if line.out_quantity:
                            line.out_value = line.out_cost * line.out_quantity
                            balance_value += (line.out_cost * line.out_quantity)
                            issue_obj = self.env['ineco.stock.card.lot.issue']
                            issue = issue_obj.search([('name', '=', line.document_number)])
                            if issue:
                                issue.write({
                                    'date': line.date,
                                    'quantity': abs(line.out_quantity)
                                })
                        else:
                            balance_value += line.out_value
                        # ปรับข้อมูลเศษ
                        if round(balance_value, 2) == -0.01:
                            balance_value = 0.0
                        balance_qty += line.out_quantity
                        # ยกเลิก เพราะจะเอายอดยกมาบันทึกทับยอดเก่า
                        # line.out_cost = cost
                    else:  # มูลค่า
                        # line.out_quantity = 0.00
                        balance_value += line.out_value
                        # ยกเลิก เพราะจะเอายอดยกมาบันทึกทับยอดเก่า
                        # line.out_cost = cost
                line.balance_quantity = balance_qty
                if balance_qty:
                    line.balance_cost = balance_value / balance_qty
                else:
                    line.balance_cost = 0.0
                line.balance_value = balance_value
            product.balance_quantity = balance_qty
            if balance_qty:
                product.balance_cost = balance_value / balance_qty
            else:
                product.balance_cost = 0.0
            product.balance_value = balance_value
        return True

    @api.multi
    def button_recompute(self):
        # ปุ่มคำนวนสินค้าเป็นตัวๆ (ใช้จริง)
        for product in self:
            _logger.info('คำนวณยอดยกไปยกมา {}'.format(product.product_id.default_code))
            # ปรับยอด Balance
            # product.correct_stock_lot_balance()
            # ปรับยอดยกมา จากยอดยกไปงวดก่อนหน้า
            product.button_update_bf()
            balance_qty = product.bf_quantity
            # ลบ Stock Card ในเดือนนั้น
            delete_sql = "delete from ineco_stock_card_lot where date >= '{}' and product_id = {}".format(
                self.stock_date_from, self.product_id.id)
            self._cr.execute(delete_sql)

            # delete_sql = """
            #     delete from ineco_stock_card_product where stock_period_id = %s and product_id = %s
            # """ % (self.stock_period_id.id, self.product_id.id)
            # self._cr.execute(delete_sql)

            # ลบ Transaction ทิ้ง (ต้องไม่ลบ Manual โดย จนท.)
            delete_sql2 = """
                delete from ineco_stock_card_product_line 
                where partner_id is not null and stock_period_id is not null 
                    and stock_period_id = %s and product_id = %s and is_manual = False
            """ % (self.stock_period_id.id, self.product_id.id)
            self._cr.execute(delete_sql2)

            # Clear ยอด Issue ของ Stock Card
            delete_sql3 = """
                delete from ineco_stock_card_lot_issue where id in (
                select a.id from ineco_stock_card_lot_issue a
                join ineco_stock_card_lot b on b.id = a.stock_card_lot_id
                where b.product_id = {} and a.date > '{}')            
            """.format(self.product_id.id, self.stock_date_from)
            self._cr.execute(delete_sql3)

            update_balance_sql4 = """
            update ineco_stock_card_lot
            set balance = raw.quantity - raw.issue
            from (
            select 
              id, 
              quantity, 
              (select coalesce(sum(quantity),0.00) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) as issue,
              balance 
            from ineco_stock_card_lot a
            where product_id = {} 
              and quantity-(select coalesce(sum(quantity),0.00) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id) > 0) raw
            where ineco_stock_card_lot.id = raw.id and ineco_stock_card_lot.force_zero is null
            """.format(self.product_id.id)
            self._cr.execute(update_balance_sql4)

            # กระบวนการประมวลผล Stock Card
            card_line = self.env['ineco.stock.card.product.line']
            iscp = self.env['ineco.stock.card.product']
            card_product = self.env['ineco.stock.card.product']
            warehouses = self.env['stock.warehouse'].search([])
            in_loc = []
            for warehouse in warehouses:
                in_loc += [x.id for x in
                           self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.id)])]

            new_product_card = {
                'name': product.name,
                'product_id': product.product_id.id,
                'stock_period_id': self.stock_period_id.id,
            }

            # if product.product_id.date_stock == self.stock_date_from:
            #     new_product_card['bf_quantity'] = product.balance_quantity
            #     new_product_card['bf_cost'] = product.cost_price
            #     new_product_card['bf_value'] = product.cost_amount
            # else:
            #     new_product_card['bf_quantity'] = product.bf_quantity
            #     new_product_card['bf_cost'] = product.bf_cost
            #     new_product_card['bf_value'] = product.bf_value

            new_product_card['bf_quantity'] = product.bf_quantity
            new_product_card['bf_cost'] = product.bf_cost
            new_product_card['bf_value'] = product.bf_value

            card_product_obj = iscp.search([('product_id', '=', product.product_id.id),
                                            ('stock_date_to', '<', self.stock_date_from)],
                                           order='stock_date_to desc', limit=1)

            if not new_product_card['bf_quantity'] and card_product_obj:
                # card_product_obj = self.env['ineco.stock.card.product'].browse(passed_stock)
                new_product_card['bf_quantity'] = card_product_obj.balance_quantity
                new_product_card['bf_cost'] = card_product_obj.balance_cost
                new_product_card['bf_value'] = card_product_obj.balance_value

            # 2019-11-06 (Fixed error หา bf_quantity ไม่เจอ)
            if not new_product_card.get('bf_quantity', False):
                new_product_card['bf_quantity'] = 0
            if not new_product_card.get('bf_cost', False):
                new_product_card['bf_cost'] = 0
            if not new_product_card.get('bf_value', False):
                new_product_card['bf_value'] = 0

            # else:
            #    new_product_card['bf_quantity'] = self._compute_product(product.id, self.date_from, self.date_to,
            #                                                         domain_move_in_loc, domain_move_out_loc)
            # print (new_product_card)

            # new_card_id = card_product.create(new_product_card)
            # balance = new_card_id.bf_quantity or 0.0

            cost = 'bf_cost' in new_product_card and new_product_card['bf_cost'] or 0.0
            in_qty = 0.0
            out_qty = 0.0
            bf_balance_qty = new_product_card['bf_quantity']
            bf_balance_value = new_product_card['bf_value']

            sql = """
                select * from (
                (select 
                  min(a.id) as id,
                  a.stkcod,
                  a.docdat::date as docdat,
                  a.price,
                  round(sum(a.quantity),3) as quantity,
                  a.docnum,
                  a.partner_id,
                  a.invoice_id,
                  0.00 as fifo_cost,
                  case when sum(a.quantity) > 0 then 0 else 1 end as type
                from query_stock_transaction_odoo a
                where stkcod = '%s' and a.docdat::date between '%s' and '%s'
                group by stkcod, docdat, price, docnum,partner_id,invoice_id
                order by stkcod, docdat, docnum)
                union
                (select 
                    a.id,
                    pp.default_code as stkcod,
                    a.date_invoice as docdat,
                    case when a.in_quantity > 0 then a.in_cost else a.out_cost end as price,
                    case when a.in_quantity > 0 then a.in_quantity else a.out_quantity end as quantity,
                    a.document_number as docnum,
                    null as partner_id,
                    null as invoice_id,
                    1.0 as fifo_cost,
                    case when a.in_quantity > 0 then 0 else 1 end as type
                from ineco_stock_card_product_manual a
                join product_product pp on a.product_id = pp.id
                where product_line_id in 
                    (select id from ineco_stock_card_product where stock_period_id = %s and product_id = %s)) 
                ) as raw                                                        
                order by stkcod, docdat, type, docnum, price desc
                """ % (
                product.product_id.default_code, self.stock_date_from, self.stock_date_to, self.stock_period_id.id,
                self.product_id.id)
            # if product.product_id.default_code == 'L-SAC-073-4':
            #     print(sql)
            self._cr.execute(sql)
            moves = self._cr.dictfetchall()
            sequence = 0
            delete_sql2 = """
                delete from ineco_stock_card_product_line where product_line_id = %s 
            """ % (self.id)
            self._cr.execute(delete_sql2)
            for move in moves:
                # if move['docnum'] == 'MOC-2102-007':
                #     pass
                invoice_id = False
                sequence += 10
                new_card_line = {
                    'sequence': sequence,
                    'name': move['docnum'] or ' ',
                    'stock_period_id': self.stock_period_id.id,
                    'product_line_id': self.id,
                    'product_id': product.product_id.id,
                    'date': move['docdat'],
                    'partner_id': move['partner_id'] or False,
                }
                if move['docnum']:
                    new_card_line['document_number'] = move['docnum'] or 'ไม่ทราบเอกสาร'
                    new_card_line['date_invoice'] = move['docdat']
                    new_card_line['invoice_id'] = move['invoice_id']
                    invoice_id = self.env['account.invoice'].browse(move['invoice_id'])

                if move['quantity'] >= 0:
                    # หาตู้นทุนสินค้าสำเร็จรูปจากใบเบิกที่เลขที่เดียวกับใบผลิต
                    if not move['invoice_id']:
                        product_cost_sql = """
                                select abs(sum(out_value)) as out_cost from ineco_stock_card_product_line
                                where name = '{}' and out_value < 0 limit 1""".format(move['docnum'])
                        self._cr.execute(product_cost_sql)
                        productions = self._cr.dictfetchall()
                        if move['fifo_cost'] > 0.00:
                            # มีการคีย์ Manual ด้านล่าง
                            # print('1', move['price'])
                            move['price'] = move['price']
                        elif productions and productions[0]['out_cost']:
                            # move['price'] = productions[0]['out_cost'] or 0.00
                            # เฉลี่ยต้นทุนต่อหน่วย ที่ได้รับจากการสั่งผลิต
                            move['price'] = round(productions[0]['out_cost'] / move['quantity'], 4)
                            # ยังมีปัญหาตรงนี้
                            # move['price'] = round(productions[0]['out_cost'], 4)
                        if not move['price']:
                            # เมื่อมีการปรับ Stock แล้วมูลค่าเป็นศูนย์
                            sql_find_first_value = """
                                (select in_cost from ineco_stock_card_product_line a
                                where product_id = {} and in_quantity > 0
                                   and a.date between '{}' and '{}'
                                order by date limit 1) 
                            """.format(product.product_id.id, self.stock_date_from, self.stock_date_to)
                            self._cr.execute(sql_find_first_value)
                            first_move = self._cr.dictfetchall()
                            if first_move and first_move[0]['in_cost']:
                                move['price'] = first_move[0]['in_cost']
                    else:
                        invoice_id = self.env['account.invoice'].browse(move['invoice_id'])
                        if invoice_id.type == 'in_refund':
                            # ถ้าเป็นส่งคืนสินค้าให้ Supplier ให้เราราคาที่ตั้งเจ้าหนี้มา
                            if invoice_id.origin:
                                origin = invoice_id.origin
                                invoice_line = self.env['account.invoice.line'].search(
                                    [('number', '=', origin), ('product_id', '=', product.product_id.id)])
                                if invoice_line:
                                    move['price'] = invoice_line.price_unit
                        elif invoice_id.type == 'out_refund':
                            # แต่ถ้าเป็นส่งรับคืนสินค้าจากลูกค้าา ให้เอาราคาต้นทุนของ Invoice ที่ส่งให้ลูกค้านั้นๆ
                            if invoice_id.origin:
                                origin = invoice_id.origin
                                issue_obj = self.env['ineco.stock.card.lot.issue']
                                issue = issue_obj.search([('name', '=', origin), ('stock_card_lot_id', '!=', False)],
                                                         limit=1)
                                if issue:
                                    move['price'] = issue.stock_card_lot_id.cost
                    new_card_line['in_cost'] = move['price']
                    new_card_line['in_quantity'] = move['quantity']
                    new_card_line['in_value'] = move['price'] * move['quantity']
                    if not invoice_id or (invoice_id and invoice_id.cn_type == '1'):
                        in_qty += move['quantity']
                        bf_balance_qty += move['quantity']
                        _logger.info('Balance Qty {} {}+{}'.format(bf_balance_qty, bf_balance_qty, move['quantity']))
                        bf_balance_value += move['price'] * move['quantity']
                    else:
                        bf_balance_value += move['price'] * move['quantity']
                    new_lot_data = {
                        'name': move['docnum'],
                        'date': move['docdat'],
                        'quantity': move['quantity'],
                        'cost': move['price'],
                        'balance': move['quantity'],
                        'product_id': product.product_id.id,
                        'stock_card_id': self.stock_period_id.id
                    }
                    lot_obj = self.env['ineco.stock.card.lot']
                    lot = lot_obj.search([('name', '=', move['docnum']), ('product_id', '=', product.product_id.id)])
                    # ตรวสอบ LOT ถ้าหากไม่พบให้สร้าง LOT ให่ ถ้าพบเพิ่มจำนวนเข้า LOT
                    if not lot:
                        lot_obj.create(new_lot_data)
                    else:
                        # เพิ่มเติมกรณีรับสินค้าของแถม ราคา 0 บาท
                        if len(lot) > 1:
                            lot = lot[0]
                        lot.write({'quantity': lot.quantity + move['quantity']})

                if move['quantity'] < 0:
                    lot_stock = self.env['ineco.stock.card.lot'].search(
                        [('product_id', '=', product.product_id.id), ('balance', '>', 0.00)],
                        order='date, name')  # balance
                    # _logger.warning(msg="{} {}".format('Issue', 'OK'))
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        issue_qty = 0
                    else:
                        issue_qty = move['quantity']
                    out_qty = 0.0
                    out_cost = 0.0
                    out_value = 0.0
                    out_cost_last = 0.0
                    while issue_qty < 0 and lot_stock:
                        issue_obj = self.env['ineco.stock.card.lot.issue']
                        is_partial = False
                        for stock in lot_stock:
                            # ตรวจสอบสินค้าบางตัวเท่านั้น
                            # if move['stkcod'] == 'T-QIA-001-1':
                            #     _logger.error(
                            #         msg='T-QIA-001-1 {} {}'.format(round(stock.balance, 2), round(abs(issue_qty), 2)))
                            if round(stock.balance, 3) >= round(abs(issue_qty), 3):
                                new_issue = {
                                    'name': move['docnum'],
                                    'date': move['docdat'],
                                    'quantity': abs(issue_qty),
                                    'stock_card_lot_id': stock.id,
                                    'refer_id': move['id']
                                }
                                issue_obj.create(new_issue)
                                issue_qty = 0
                                out_qty = issue_qty
                                out_cost = stock.cost
                                out_value = stock.cost * issue_qty
                                # if product.default_code == 'C-GAD-001-1':
                                #     print(move['id'])
                                break
                            else:
                                issue_qty += stock.balance
                                out_qty += stock.balance
                                out_value += (stock.balance * stock.cost)
                                out_cost += out_value / out_qty
                                new_issue = {
                                    'name': move['docnum'],
                                    'date': move['docdat'],
                                    'quantity': stock.balance,
                                    'stock_card_lot_id': stock.id,
                                    'refer_id': move['id']
                                }
                                issue_obj.create(new_issue)
                                is_partial = True
                                # if product.default_code == 'C-GAD-001-1':
                                #     print(move['id'])
                            if out_cost:
                                out_cost_last = out_cost
                        # _logger.error(msg="{} {}".format(move['docnum'], out_cost_last))
                        break
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        new_card_line['out_quantity'] = 0
                        out_cost = 0.00
                    else:
                        new_card_line['out_quantity'] = move['quantity']
                        # select round(sum(b.cost * a.quantity) / sum(a.quantity), 4) as out_cost from ineco_stock_card_lot_issue a
                        # print(move)
                        out_sql = """
                                select round(sum(b.cost * a.quantity)/sum(a.quantity),4) as out_cost from ineco_stock_card_lot_issue a
                                join ineco_stock_card_lot b on b.id = a.stock_card_lot_id
                                where a.name = '{}' and refer_id = {}""".format(move['docnum'], move['id'])
                        self._cr.execute(out_sql)
                        moves = self._cr.dictfetchall()
                        if moves and moves[0]['out_cost']:
                            if product.product_id.categ_id.use_fg_standard_cost:
                                _logger.info('User Standard Cost Compute {}'.format(product.product_id.default_code))
                                out_cost = 0.00
                            else:
                                out_cost = moves[0]['out_cost']
                                # _logger.info('User custom {} cost at {}'.format(product.product_id.default_code, move['docnum'] ))
                    if invoice_id and invoice_id.cn_type == '2':
                        # ลดมูลค่า
                        new_card_line['out_cost'] = 0.0
                        new_card_line['out_value'] = move['price'] * move['quantity']
                    else:
                        # สต๊อก Lot หมดแล้ว out_cost = 0.00
                        _logger.info("1 {} : 2 {}".format(out_cost, out_cost_last))
                        new_card_line['out_cost'] = out_cost or out_cost_last
                        new_card_line['out_value'] = (out_cost or out_cost_last) * move['quantity']
                        # new_card_line['out_cost'] = out_cost or new_product_card['bf_cost']
                        # new_card_line['out_value'] = (out_cost or new_product_card['bf_cost']) * move['quantity']
                    if not invoice_id or (invoice_id and invoice_id.cn_type == '1'):
                        # ลดปริมาณ
                        out_qty += move['quantity']
                        bf_balance_qty += move['quantity']
                        _logger.info('Balance Qty {} {}+{}'.format(bf_balance_qty, bf_balance_qty, move['quantity']))
                        bf_balance_value += round(round((out_cost) * move['quantity'] * 100) / 100, 2)
                        # print('A', new_card_line['document_number'], bf_balance_value, out_cost, move['quantity'])
                    else:
                        # ลดมูลค่า
                        bf_balance_value += move['price'] * move['quantity']
                        # bf_balance_value += (out_cost) * move['quantity']
                        bf_balance_value = round(bf_balance_value, 2)

                new_card_line['balance_quantity'] = bf_balance_qty
                if bf_balance_qty:
                    new_card_line['balance_cost'] = bf_balance_value / bf_balance_qty
                    cost = bf_balance_value / bf_balance_qty
                new_card_line['balance_value'] = bf_balance_value
                # แก้ไขหากจำนวน = 0 ให้มูลค่า และ คงเหลือเป็น 0 ด้วย
                if new_card_line['balance_quantity'] == 0.0:
                    new_card_line['balance_cost'] = 0.0
                    new_card_line['balance_value'] = 0.0
                    bf_balance_value = 0.0
                ###

                if not 'document_number' in new_card_line:
                    new_card_line['document_number'] = 'ปรับปรุง'
                if new_card_line['balance_quantity'] == 0.0 and new_card_line['balance_cost'] == 0.0 \
                        and new_card_line['balance_value'] == 0.0:
                    lot = self.env['ineco.stock.card.lot'].sudo().search([
                        ('product_id', '=', new_card_line['product_id']),
                        ('date', '<=', new_card_line['date']),
                        ('balance', ">", 0.0)
                    ])
                    if lot:
                        # for l in lot:
                        #     l.button_compute()
                        lot.write({'balance': 0.0, 'force_zero': 1})
                card_line.create(new_card_line)

            if moves:
                if bf_balance_qty == 0.00:
                    cost = 0.00
                    bf_balance_value = 0.00
                if -1.0 <= bf_balance_value <= 1.00:
                    if not product.product_id.categ_id.use_fg_standard_cost:
                        bf_balance_qty = 0.00
                    cost = 0.00
                    bf_balance_value = 0.00
                self.write(
                    {'balance_quantity': bf_balance_qty, 'in_quantity': in_qty, 'out_quantity': out_qty,
                     'balance_cost': cost, 'balance_value': bf_balance_value})
            else:
                if bf_balance_qty and bf_balance_value:
                    cost = new_product_card['bf_cost']

                    self.write(
                        {'balance_quantity': bf_balance_qty, 'in_quantity': in_qty, 'out_quantity': out_qty,
                         'balance_cost': cost, 'balance_value': bf_balance_value})
                elif bf_balance_qty:
                    self.write({'balance_quantity': bf_balance_qty})
        return True

    @api.multi
    def button_recompute_local(self):
        # ปุ่มคำนวณเฉพาะหน้าปัจจุบัน
        for product in self:
            _logger.info("คำนวณยอดเฉพาะหน้านี้ {}".format(product.product_id.default_code))
            bf_qty = product.bf_quantity
            bf_cost = product.bf_cost
            bf_value = product.bf_value
            for line in product.line_ids:
                in_qty = line.in_quantity
                in_cost = line.in_cost
                in_value = round(line.in_quantity * in_cost, 2)
                out_qty = line.out_quantity
                out_cost = line.out_cost
                out_value = round(line.out_quantity * out_cost, 2)
                if in_qty:
                    bf_qty += in_qty
                    bf_value += in_value
                    if bf_qty > 0.00:
                        bf_cost = round(bf_value / bf_qty, 4)
                    else:
                        bf_cost = 0.00
                    lot_datas = self.env['ineco.stock.card.lot'].sudo().search(
                        [('name', '=', line.document_number), ('product_id', '=', product.product_id.id)])
                    if lot_datas and in_cost:
                        if len(lot_datas) > 1:
                            lot_datas = lot_datas[0]
                        lot_datas.write({
                            'date': line.date_invoice,
                            'cost': in_cost
                        })
                elif out_qty:
                    bf_qty += out_qty
                    bf_value += out_value
                    if bf_qty > 0.00:
                        bf_cost = round(bf_value / bf_qty, 4)
                    else:
                        bf_cost = 0.00
                    if bf_value < 0.00:
                        bf_cost = 0.00
                        bf_value = 0.00
                line.write({
                    'in_value': in_value,
                    'out_value': out_value,
                    'balance_cost': bf_cost,
                    'balance_quantity': bf_qty,
                    'balance_value': bf_value
                })
            product.write({
                'balance_quantity': bf_qty,
                'balance_cost': bf_cost,
                'balance_value': bf_value,
            })

        return True

    @api.multi
    def button_compute_remaining(self):
        for data in self:
            for line in data.line_ids:
                line.compute_remaining()

    @api.multi
    def button_compute_bof(self):
        lot_obj = self.env['ineco.stock.card.lot']
        line_product_obj = self.env['ineco.stock.card.product.line']
        for data in self:
            start_date = data.stock_date_from[:4] + '-01-01'
            delete_sql = "delete from ineco_stock_card_lot where date >= '{}'".format(start_date)
            self._cr.execute(delete_sql)
            sql = """
                select
                        a.id,
                        a.stock_date_from as date,
                        'BF-' || extract(year from a.stock_date_from) as document_number,
                        a.bf_quantity as in_quantity,
                        a.bf_cost as in_cost,
                        0.00 as out_quantity,
                        0.00 as out_cost
                from ineco_stock_card_product a
                where product_id = {}  and a.stock_date_from = '{}'
                union
                select
                       a.id,
                       a.date,
                       a.document_number,
                       a.in_quantity, a.in_cost,
                       a.out_quantity, a.out_cost
                from ineco_stock_card_product_line a
                join ineco_stock_card_product b on b.id = a.product_line_id
                where --product_line_id in (48148,50106,51978)
                    a.product_id = {} and a.date >= '{}'
                order by date, out_quantity, document_number""".format(data.product_id.id, start_date,
                                                                       data.product_id.id, start_date)
            # print(sql)
            self._cr.execute(sql)
            for stock_card in self._cr.dictfetchall():
                new_stock_card = {
                    'id': stock_card['id'],
                    'date': stock_card['date'],
                    'doc': stock_card['document_number'],
                    'in_qty': stock_card['in_quantity'],
                    'in_cost': stock_card['in_cost'],
                    'out_qty': stock_card['out_quantity'] or 0.00,
                    'out_cost': stock_card['out_cost'] or 0.00
                }
                if new_stock_card['in_qty'] > 0:
                    lot_obj.create({
                        'name': stock_card['document_number'],
                        'date': stock_card['date'],
                        'quantity': stock_card['in_quantity'],
                        'cost': stock_card['in_cost'],
                        'issue': 0.00,
                        'product_id': data.product_id.id,
                        'balance': stock_card['in_quantity']
                    })
                elif new_stock_card['out_qty'] < 0:
                    lot_ids = lot_obj.search([('product_id', '=', data.product_id.id), ('balance', '>', 0.00)],
                                             order='date')
                    balance = abs(new_stock_card['out_qty'])
                    cost_avg = 0.0
                    avg_count = 0.0
                    for lot in lot_ids:
                        if lot.balance >= balance:
                            lot.issue = lot.issue + balance
                            lot.balance = lot.balance - balance

                            line = line_product_obj.search([('id', '=', stock_card['id'])])
                            if not cost_avg:
                                line.out_cost = lot.cost
                            else:
                                line.out_cost = (cost_avg + (lot.cost * balance)) / (avg_count + balance)
                            line.out_value = line.out_cost * line.out_quantity
                            break
                        else:
                            # print('Partial Lot', lot.name, lot.balance, balance)
                            lot.issue = 0.00
                            line = line_product_obj.search([('id', '=', stock_card['id'])])
                            line.out_cost = lot.cost
                            line.out_value = line.out_cost * line.out_quantity
                            cost_avg += (lot.cost * lot.balance)
                            avg_count += lot.balance

                            # line.balance_cost = (line.balance_value - line.out_value) / line.balance_quantity
                            balance = balance - lot.balance
                            lot.balance = 0.00
                        # self._cr.commit()
                # print(new_stock_card)

    @api.multi
    def button_update_bf(self):
        for product in self:
            sql_old_unsued = """
                select 
                  balance_cost,
                  balance_quantity,
                  balance_value
                from
                  ineco_stock_card_product_line
                where product_id = %s and stock_period_id in (
                    select
                        id
                    from ineco_stock_card
                    where date_to <= '%s'
                    order by date_to desc limit 1
                )
                  order by date desc, sequence desc limit 1
            """ % (product.product_id.id, product.stock_date_from)
            sql = """
                select 
                  balance_cost,
                  balance_quantity,
                  balance_value
                from
                  ineco_stock_card_product
                where product_id = %s and stock_period_id in (
                    select
                        id
                    from ineco_stock_card
                    where date_to <= '%s'
                    order by date_to desc limit 1
                )
            """ % (product.product_id.id, product.stock_date_from)
            self._cr.execute(sql)
            result = self._cr.dictfetchone()
            if result:
                balance_value = result['balance_value']
                balance_cost = result['balance_cost']
                balance_qty = result['balance_quantity']
                product.bf_quantity = balance_qty
                product.bf_cost = balance_cost
                product.bf_value = balance_value
            else:
                sql = """
                 select
                  balance_cost,
                  balance_quantity,
                  balance_value
                from
                  ineco_stock_card_product
                where product_id = %s and stock_date_to <= '%s'
                  order by stock_date_to desc limit 1""" % (product.product_id.id, product.stock_date_from)
                self._cr.execute(sql)
                result = self._cr.dictfetchone()
                if result:
                    balance_value = result['balance_value']
                    balance_cost = result['balance_cost']
                    balance_qty = result['balance_quantity']
                    product.bf_quantity = balance_qty
                    product.bf_cost = balance_cost
                    product.bf_value = balance_value
        return True

    @api.multi
    def correct_stock_lot_balance(self):
        for product in self:
            sql = """
                update ineco_stock_card_lot
                set balance = quantity
                where id in (
                select
                    id
                from (
                select
                    id,
                    quantity,
                    coalesce((select sum(quantity) from ineco_stock_card_lot_issue where stock_card_lot_id = a.id), 0.00) as issue
                from 
                    ineco_stock_card_lot a
                ) raw
                where issue = 0 and product_id = {}
                )            """.format(product.product_id.id)
            self._cr.execute(sql)

    @api.multi
    def button_update_lot_stock_equal_bof(self):
        for product in self:
            bf_qty = product.bf_quantity
            date_from = product.stock_date_from
            date_to = product.stock_date_to
            issue_obj = self.env['ineco.stock.card.lot.issue']
            delete_issue_sql = """
                delete from ineco_stock_card_lot_issue
                where id in (
                select a.id from ineco_stock_card_lot_issue a
                join ineco_stock_card_lot b on b.id = a.stock_card_lot_id
                where b.product_id = {} and a.date between '{}' and '{}')
            """.format(product.product_id.id, date_from, date_to)
            self._cr.execute(delete_issue_sql)
            # print(date_from, date_to)
            delete_lot_sql = """
                delete from ineco_stock_card_lot where product_id = {} and date between '{}' and '{}'
            """.format(product.product_id.id, date_from, date_to)
            self._cr.execute(delete_lot_sql)
            qty = 0.00
            for lot in self.env['ineco.stock.card.lot'].search([('product_id', '=', product.product_id.id)],
                                                               order='date desc'):
                lot._compute_balance()
                qty += lot.balance
            diff = qty - bf_qty
            date_issue = datetime.datetime.strptime(date_from, '%Y-%m-%d') - timedelta(days=1)
            for lot in self.env['ineco.stock.card.lot'].search(
                    [('product_id', '=', product.product_id.id), ('balance', '>', 0.0)], order='date'):
                if diff:
                    if diff >= lot.balance:
                        diff -= lot.balance
                        new_issue = {
                            'stock_card_lot_id': lot.id,
                            'date': date_issue.strftime('%Y-%m-%d'),
                            'quantity': lot.balance,
                            'name': 'System Generated',
                        }
                        issue_obj.create(new_issue)
                    else:
                        new_issue = {
                            'stock_card_lot_id': lot.id,
                            'date': date_issue.strftime('%Y-%m-%d'),
                            'quantity': diff,
                            'name': 'System Generated',
                        }
                        diff = 0
                        issue_obj.create(new_issue)


class InecoStockCardProductLine(models.Model):
    _name = 'ineco.stock.card.product.line'
    _description = 'Stock Card Product Line'

    name = fields.Char(string='Description')
    stock_period_id = fields.Many2one('ineco.stock.card', string='Stock Period')
    product_line_id = fields.Many2one('ineco.stock.card.product', string='Product Line', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, track_visibility='onchange')
    date = fields.Date(string='Date', required=True, track_visibility='onchange')
    date_invoice = fields.Date(string=u'Date Invoice', track_visibility='onchange')
    invoice_id = fields.Many2one('account.invoice', string=u'Invoice')
    cn_type = fields.Selection([('1', u'ปริมาณ'), ('2', u'มูลค่า')], related='invoice_id.cn_type',
                               string=u'ผลกระทบต้นทุน')
    invoice_number = fields.Char(string='Invoice Number')
    document_number = fields.Char(string='Document No', required=True, track_visibility='onchange')
    in_quantity = fields.Float(string='In', digits=(12, 3))
    in_cost = fields.Float(string='Cost', digits=(12, 4))
    in_value = fields.Float(string='Values', digits=(12, 2))
    out_quantity = fields.Float(string='Out', digits=(12, 3))
    out_cost = fields.Float(string='Cost', digits=(12, 4))
    out_value = fields.Float(string='Values', digits=(12, 2))
    balance_quantity = fields.Float(string='Balance', digits=(12, 3))
    balance_cost = fields.Float(string='Cost', digits=(12, 4))
    balance_value = fields.Float(string='Values', digits=(12, 2))
    partner_id = fields.Many2one('res.partner', string=u'Partner')
    partner_name = fields.Char(string='Partner Name')
    sequence = fields.Integer(string='Seq', default=10)

    issue_ids = fields.One2many('ineco.stock.card.product.line.issue', 'receive_product_line_id', string='Issues')
    remain_qty = fields.Float(string='Remaining Qty', compute='_get_remaining_qty')

    # เป็นข้อมูลที่จัดการโดย จนท.
    is_manual = fields.Boolean(string='Custom', default=False)

    _order = 'product_line_id, date, sequence'

    @api.one
    def _get_remaining_qty(self):
        self.remain_qty = 0.00
        if self.in_quantity:
            remain = 0.00
            for issue in self.issue_ids:
                remain += issue.issue_qty
            self.remain_qty = self.in_quantity - remain

    @api.one
    def compute_remaining(self):
        issue_ids = self.env['ineco.stock.card.product.line'].search([('product_line_id', '=', self.product_line_id.id),
                                                                      ('out_quantity', '>', 0.00)], order='date')
        remain = self.remain_qty
        # for issue in issue_ids:
        #     if not issue in self.issue_ids:
        #         if issue.out_quantity <= remain

    @api.multi
    def unlink(self):
        if self.out_quantity:
            issue_obj = self.env['ineco.stock.card.lot.issue']
            if self.document_number:
                issue_obj.search([('name', '=', self.document_number)]).unlink()
        return super(InecoStockCardProductLine, self).unlink()

    @api.multi
    def write(self, vals):
        if 'date' in vals:
            if self.out_quantity:
                sql_update = """
                    update stock_picking
                    set date = '%s'
                    where id = (
                    select sp.id from stock_move sm
                    join stock_picking sp on sp.id = sm.picking_id
                    join stock_location sl1 on sl1.id = sm.location_id
                    join stock_location sl2 on sl2.id = sm.location_dest_id
                    where sp.origin = '%s' and sl2.name = 'Production' limit 1)                
                """ % (vals['date'], self.document_number)
                self._cr.execute(sql_update)
            elif self.in_quantity:
                sql_update = """
                    update stock_picking
                    set date = '%s'
                    where id = (
                    select sp.id from stock_move sm
                    join stock_picking sp on sp.id = sm.picking_id
                    join stock_location sl1 on sl1.id = sm.location_id
                    join stock_location sl2 on sl2.id = sm.location_dest_id
                    where sp.origin = '%s' and sl1.name = 'Production' limit 1)                
                """ % (vals['date'], self.document_number)
                self._cr.execute(sql_update)
        res = super(InecoStockCardProductLine, self).write(vals)
        return res


class InecoStockCardProductLineIssue(models.Model):
    _name = 'ineco.stock.card.product.line.issue'
    _description = 'Issue of stock card product line (Receive)'

    name = fields.Char(string='Description')
    receive_product_line_id = fields.Many2one('ineco.stock.card.product.line', string='Receive Product Line')
    issue_product_line_id = fields.Many2one('ineco.stock.card.product.line', string='Issue Product Line')
    issue_qty = fields.Float(string='Issue Qty', digits=(12, 3))


class InecoStockCardLot(models.Model):
    _name = 'ineco.stock.card.lot'
    _description = 'Stock Card Lots'

    name = fields.Char(string=u'Lot No')
    date = fields.Date(string=u'Lot Date')
    quantity = fields.Float(string=u'Quantity', digits=(12, 3))
    cost = fields.Float(string=u'Cost', digits=(12, 4))
    issue = fields.Float(string=u'Issue', compute='_compute_balance', store=False)
    product_id = fields.Many2one('product.product', string='Product')
    balance = fields.Float(string='Balance', compute='_compute_balance', store=True)
    stock_card_id = fields.Many2one('ineco.stock.card', string='Stock Card')
    issue_ids = fields.One2many('ineco.stock.card.lot.issue', 'stock_card_lot_id', 'Issues')
    force_zero = fields.Boolean(string='Force Zero', defaut=False)

    _order = 'product_id, date, quantity'

    @api.one
    @api.depends('issue_ids.quantity', 'quantity', 'name', 'date')
    def _compute_balance(self):
        self.issue = sum(line.quantity for line in self.issue_ids)
        self.balance = round(self.quantity, 3) - round(self.issue, 3)

    @api.multi
    def button_compute(self):
        self.balance = round(self.quantity, 3) - round(self.issue, 3)


class InecoStockCardLotIssue(models.Model):
    _name = 'ineco.stock.card.lot.issue'
    _description = 'Lot Issue'

    name = fields.Char(string=u'Document Number')
    date = fields.Date(string=u'Date Issue')
    quantity = fields.Float(string=u'Quantity', digits=(12, 4))
    stock_card_lot_id = fields.Many2one('ineco.stock.card.lot', 'Card Lot Id')
    refer_id = fields.Integer(string='Refer ID')


class InecoStockCardProductManual(models.Model):
    _name = 'ineco.stock.card.product.manual'
    _description = 'Stock Card Product Manual'

    name = fields.Char(string='Description')
    stock_period_id = fields.Many2one('ineco.stock.card', string='Stock Period')
    product_line_id = fields.Many2one('ineco.stock.card.product', string='Product Line', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, track_visibility='onchange')
    date = fields.Date(string='Date', required=True, track_visibility='onchange')
    date_invoice = fields.Date(string=u'Date Invoice', track_visibility='onchange')
    invoice_number = fields.Char(string='Invoice Number')
    document_number = fields.Char(string='Document No', required=True, track_visibility='onchange')
    in_quantity = fields.Float(string='In', digits=(12, 3))
    in_cost = fields.Float(string='Cost', digits=(12, 4))
    in_value = fields.Float(string='Values', digits=(12, 2))
    out_quantity = fields.Float(string='Out', digits=(12, 3))
    out_cost = fields.Float(string='Cost', digits=(12, 4))
    out_value = fields.Float(string='Values', digits=(12, 2))
    sequence = fields.Integer(string='Seq', default=10)
