# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar


class InecoAccountAsset(models.Model):
    _inherit = 'account.asset.asset'
    # _description = 'Asset'

    code_name = fields.Char('Code')
    date_depreciation = fields.Date('Date Depreciation')
    sale_amount = fields.Float(string=u'Sale Amount')
    purchase_value = fields.Float(string=u'Purchase Value')
    percent = fields.Float(string='Percent (%)')
    sale_date = fields.Date(string='Sale Date')
    purchase_date = fields.Date(string='Purchase Date')
    manual_last_depreciation = fields.Float(string='Manual Last Depreciation')
    max_asset_value = fields.Float(string='Max Asset Value', default=0)

    def _compute_board_undone_dotation_nb(self, asset, depreciation_date, total_days):
        undone_dotation_number = asset.method_number
        if asset.method_time == 'end':
            end_date = datetime.strptime(asset.method_end, '%Y-%m-%d')
            undone_dotation_number = 0
            while depreciation_date < end_date:
                depreciation_date = (datetime(depreciation_date.year, depreciation_date.month,
                                              depreciation_date.day) + relativedelta(months=+asset.method_period))
                undone_dotation_number += 1
        if asset.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def _get_last_depreciation_date(self):
        """
        @param id: ids of a account.asset.asset objects
        @return: Returns a dictionary of the effective dates of the last depreciation entry made for given asset ids. If there isn't any, return the purchase date of this asset
        """
        self.env.cr.execute("""
            SELECT a.id as id, COALESCE(MAX(l.date),a.date_depreciation) AS date
            FROM account_asset_asset a
            LEFT JOIN account_move_line l ON (l.asset_id = a.id)
            WHERE a.id IN %s
            GROUP BY a.id, a.date_depreciation """, (tuple(self.id),))
        return dict(self.env.cr.fetchall())

    def _compute_board_amount(self, asset, i, residual_amount, amount_to_depr, undone_dotation_number,
                              posted_depreciation_line_ids, total_days, depreciation_date):
        # by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount - 1.0
        else:
            if asset.method == 'linear':
                if asset.percent:
                    month_days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    sale_date = False
                    year_amount = round((asset.value - 1) * asset.percent / 100, 2)
                    if asset.max_asset_value:
                        year_amount = round((asset.max_asset_value - 1) * asset.percent / 100, 2)
                    day_amount = round(year_amount / total_days, 4)
                    month_amount = day_amount * (month_days - depreciation_date.day + 1)
                    if asset.sale_date:
                        sale_date = datetime.strptime(asset.sale_date, '%Y-%m-%d')
                    if depreciation_date.month == 12 and depreciation_date.year == int(asset.date_depreciation[0:4]):
                        purchase_date = datetime.strptime(asset.date_depreciation, '%Y-%m-%d')
                        end_of_year = datetime.strptime(str(depreciation_date.year) + '-12-31', '%Y-%m-%d')
                        first_year_count = (end_of_year - purchase_date).days + 1
                        first_year_amount = round(
                            round((((asset.value - 1) * asset.percent / 100) / total_days), 4) * (
                                    first_year_count + 1), 2)
                        sql = """
                        select sum(amount) from account_asset_depreciation_line 
                        where asset_id = %s
                          and extract(year from depreciation_date) = %s
                          and extract(month from depreciation_date) <> 12
                          """ % (asset.id, depreciation_date.year)
                        self.env.cr.execute(sql)
                        amount_1_to_11 = self.env.cr.fetchone()[0]
                        if first_year_count < 365:
                            year_amount = round(
                                (((asset.value - 1) * asset.percent) / 100) * first_year_count / (
                                        total_days * 1.0), 2)
                            if asset.max_asset_value:
                                year_amount = round(
                                    (((asset.max_asset_value - 1) * asset.percent) / 100) * first_year_count / (
                                            total_days * 1.0), 2)

                            # print year_amount, total_days, first_year_count, amount_1_to_11
                        amount = year_amount - (amount_1_to_11 or 0.0)
                    elif depreciation_date.month == 12:
                        date_31 = round(round(31 * day_amount, 4), 2) * 6
                        date_30 = round(round(30 * day_amount, 4), 2) * 4
                        date_leap = 0.0
                        if total_days == 366:
                            date_leap = round(round(29 * day_amount, 4), 2)
                        else:
                            date_leap = round(round(28 * day_amount, 4), 2)
                        last_month_amount = date_31 + date_30 + date_leap
                        amount = year_amount - last_month_amount
                    elif asset.sale_date and sale_date and sale_date.year == depreciation_date.year and sale_date.month == depreciation_date.month:
                        amount = round((((asset.value - 1) * asset.percent / 100) / total_days) * (
                                int(asset.sale_date[-2:]) - 1), 2)
                    else:
                        amount = round(round(month_amount, 4), 2)
                else:
                    amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                    if asset.prorata:
                        amount = amount_to_depr / asset.method_number
                        days = total_days - float(depreciation_date.strftime('%j'))
                        if i == 1:
                            amount = (amount_to_depr / asset.method_number) / total_days * days
                        elif i == undone_dotation_number:
                            amount = (amount_to_depr / asset.method_number) / total_days * (total_days - days)
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
                if asset.prorata:
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * days
                    elif i == undone_dotation_number:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * (total_days - days)
        return amount

    @api.multi
    def compute_depreciation_board(self):
        depreciation_lin_obj = self.env['account.asset.depreciation.line']
        currency_obj = self.env['res.currency']
        for asset in self:
            sql = "delete from account_asset_depreciation_line where asset_id = %s" % (asset.id)
            self.env.cr.execute(sql)
            if asset.value_residual == 0.0:
                continue
            posted_depreciation_line_ids = depreciation_lin_obj.search(
                [('asset_id', '=', asset.id), ('move_check', '=', True)], order='depreciation_date desc')
            old_depreciation_line_ids = depreciation_lin_obj.search(
                [('asset_id', '=', asset.id), ('move_id', '=', False)])
            if old_depreciation_line_ids:
                depreciation_lin_obj.unlink(old_depreciation_line_ids)

            amount_to_depr = residual_amount = asset.value_residual
            if asset.prorata:
                depreciation_date = datetime.strptime(
                    self._get_last_depreciation_date([asset.id])[asset.id], '%Y-%m-%d')
            else:
                # depreciation_date = 1st January of purchase year
                purchase_date = datetime.strptime(asset.date_depreciation or asset.purchase_date, '%Y-%m-%d')
                # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if (len(posted_depreciation_line_ids) > 0):
                    last_depreciation_date = datetime.strptime(
                        depreciation_lin_obj.browse(posted_depreciation_line_ids[0],
                                                    ).depreciation_date, '%Y-%m-%d')
                    depreciation_date = (last_depreciation_date + relativedelta(months=+asset.method_period))
                else:
                    depreciation_date = datetime(purchase_date.year, purchase_date.month, purchase_date.day)
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            undone_dotation_number = self._compute_board_undone_dotation_nb(asset, depreciation_date, total_days)
            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                i = x + 1
                # แก้บักคำนวณ 366 ผิดปี
                year = depreciation_date.year
                total_days = (year % 4) and 365 or 366
                amount = self._compute_board_amount(asset, i, residual_amount, amount_to_depr, undone_dotation_number,
                                                    posted_depreciation_line_ids, total_days, depreciation_date)
                residual_amount -= amount
                if residual_amount < 1:
                    amount += residual_amount
                    residual_amount = 1
                vals = {
                    'amount': amount,
                    'asset_id': asset.id,
                    'sequence': i,
                    'name': str(asset.id) + '/' + str(i),
                    'remaining_value': residual_amount,
                    'depreciated_value': round(
                        (asset.value - asset.salvage_value) - (residual_amount + amount), 2),
                    'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                }
                if asset.sale_date:
                    if datetime.strftime(depreciation_date, '%Y-%m-%d') < asset.sale_date:
                        depreciation_lin_obj.create(vals)
                else:
                    depreciation_lin_obj.create(vals)
                # Considering Depr. Period as months
                depreciation_date = (datetime(year, month, 1) + relativedelta(months=+asset.method_period))
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year
        return True

    @api.model
    def recompute_depreciation_schedule(self, *args, **kwargs):
        assets = self.search([('state', '=', 'draft')])
        i = 1
        for asset in assets:
            logging.info('Recompute depreciation schedule for asset {} {}/{}'.format(asset.name, i, len(assets)))
            i += 1
            asset.compute_depreciation_board()
        return True

    @api.model
    def compute_generated_entries(self, date, asset_type=None):
        # Entries generated : one by grouped category and one by asset from ungrouped category
        created_move_ids = []
        type_domain = []
        if asset_type:
            type_domain = [('type', '=', asset_type)]

        # ('state', '=', 'open')
        ungrouped_assets = self.env['account.asset.asset'].search(
            type_domain + [('category_id.group_entries', '=', False)])
        created_move_ids += ungrouped_assets._compute_entries(date, group_entries=False)

        for grouped_category in self.env['account.asset.category'].search(type_domain + [('group_entries', '=', True)]):
            # ('state', '=', 'open')
            assets = self.env['account.asset.asset'].search([('category_id', '=', grouped_category.id)])
            created_move_ids += assets._compute_entries(date, group_entries=True)

        parent_id = False
        if created_move_ids:
            parent_id = created_move_ids[0]
        for move_id in created_move_ids:
            if move_id != parent_id:
                sql_change_parent = "update account_move_line set move_id = %s where move_id = %s" % (
                    parent_id, move_id)
                self.env.cr.execute(sql_change_parent)
                sql_delete_child = "delete from account_move_line  where move_id = %s" % (move_id)
                self.env.cr.execute(sql_delete_child)
                sql_delete_child_parent = "delete from account_move where id = %s" % (move_id)
                self.env.cr.execute(sql_delete_child_parent)
        if parent_id:
            sql_update_reference = """
                update account_move set ref = '%s', 
                amount = (select sum(debit) from account_move_line where move_id = %s) where id = %s""" % ("ค่าเสื่อมราคา", parent_id, parent_id)
            self.env.cr.execute(sql_update_reference)
        return [parent_id]

    @api.multi
    def _compute_entries(self, date, group_entries=False):
        # TODO: Create move line for asset from depreciation line
        pdate = date[:7] + '-01'
        start_date = datetime.strptime(pdate, '%Y-%m-%d')
        end_date = (start_date + relativedelta(months=+1, day=1, days=-1))
        # ('move_check', '=', False)
        depreciation_ids = self.env['account.asset.depreciation.line'].search([
            ('asset_id', 'in', self.ids), ('depreciation_date', '>=', start_date),
            ('depreciation_date', '<=', end_date)
            ])
        batch_size = self.env.context.get('batch_size')
        if group_entries:
            return depreciation_ids.create_grouped_move(post_move=False)
        move_ids = []
        if batch_size:
            for idx in range(0, len(depreciation_ids), batch_size):
                move_ids += depreciation_ids[idx:idx + batch_size].create_move()
                self.env.cr.commit()
        else:
            move_ids += depreciation_ids.create_move(post_move=False)
        return move_ids


class InecoAccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    @api.multi
    def create_move_unused(self):
        context = self._context.copy() or {}
        can_close = False
        asset_obj = self.env['account.asset.asset']
        # period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        asset_ids = []
        for line in self:
            depreciation_date = context.get('depreciation_date') or line.depreciation_date or time.strftime('%Y-%m-%d')
            # period_ids = period_obj.find(depreciation_date)
            company_currency = line.asset_id.company_id.currency_id.id
            current_currency = line.asset_id.currency_id.id
            context.update({'date': depreciation_date})
            amount = currency_obj.compute(current_currency, company_currency, line.amount)
            sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
            reference = 'ASSET'  # line.asset_id.code_name+' '+line.asset_id.name
            move_id = False
            period_obj = self.env['date.range']
            period_ids = period_obj.search(
                [('date_start', '>=', depreciation_date)], order='date_start')
            move_ids = move_obj.search([('is_asset', '=', True), ('period_id', '=', period_ids[0])])
            if move_ids:
                move_id = move_ids[0]
            else:
                asset_name = "/"
                move_vals = {
                    'name': asset_name,
                    'date': depreciation_date,
                    'ref': reference,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': line.asset_id.category_id.journal_id.id,
                    'is_asset': True,
                }
                move_id = move_obj.create(move_vals)
                # print 'Create new move', move_id
            # print 'Move ID', move_id
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            credit_move_ids = move_line_obj.search([('move_id', '=', move_id),
                                                    ('account_id', '=',
                                                     line.asset_id.category_id.account_depreciation_id.id)])
            if not credit_move_ids:
                move_line_obj.create({
                    'name': line.asset_id.code_name or '/',
                    'ref': reference,
                    'move_id': move_id,
                    'account_id': line.asset_id.category_id.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                    'date': depreciation_date,
                })
            else:
                sql_update = """
                    update account_move_line
                    set credit = credit + %s
                    where id = %s
                """ % (amount, credit_move_ids[0])
                self.env.cr.execute(sql_update)
            debit_move_ids = move_line_obj.search([('move_id', '=', move_id),
                                                   ('account_id', '=',
                                                    line.asset_id.category_id.account_expense_depreciation_id.id)])

            if not debit_move_ids:
                move_line_obj.create({
                    'name': line.asset_id.code_name or '/',
                    'ref': reference,
                    'move_id': move_id,
                    'account_id': line.asset_id.category_id.account_expense_depreciation_id.id,
                    'credit': 0.0,
                    'debit': amount,
                    'period_id': period_ids and period_ids[0] or False,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                    'analytic_account_id': line.asset_id.category_id.account_analytic_id.id,
                    'date': depreciation_date,
                    # 'asset_id': line.asset_id.id
                })
            else:
                sql_update = """
                    update account_move_line
                    set debit = debit + %s
                    where id = %s
                """ % (amount, debit_move_ids[0])
                self.env.cr.execute(sql_update)
            self.write(line.id, {'move_id': move_id})
            created_move_ids.append(move_id)
            asset_ids.append(line.asset_id.id)
        # we re-evaluate the assets to determine whether we can close them
        for asset in asset_obj.browse(list(set(asset_ids))):
            if currency_obj.is_zero(asset.currency_id, asset.value_residual):
                asset.write({'state': 'close'})
        return created_move_ids
