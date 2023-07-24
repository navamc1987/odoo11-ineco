# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.rrule import (rrule,
                            YEARLY,
                            MONTHLY,
                            WEEKLY,
                            DAILY)
from dateutil.relativedelta import relativedelta


class IecoDateRangeGenerator(models.TransientModel):
    _name = 'ineco.range.generator'

    @api.model
    def _default_company(self):
        return self.env['res.company']._company_default_get('date.range')

    # name_prefix = fields.Char('Range name prefix', required=True)
    date_start = fields.Date(strint='Start date', required=True)

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        default=_default_company)
    unit_of_time = fields.Selection([
        (YEARLY, 'years'),
        (MONTHLY, 'months'),
        (WEEKLY, 'weeks'),
        (DAILY, 'days')], required=True)
    duration_count = fields.Integer('Duration', required=True)
    count = fields.Integer(
        string="Number of ranges to generate", required=True)

    @api.multi
    def _compute_date_ranges(self):
        active_id = self._context.get('active_id', False)
        seq_obj = self.env['ir.sequence']
        seq_id = seq_obj.search([('id', '=', active_id)])
        self.ensure_one()
        vals = rrule(freq=self.unit_of_time, interval=self.duration_count,
                     dtstart=fields.Date.from_string(self.date_start),
                     count=self.count+1)
        vals = list(vals)
        date_ranges = []
        count_digits = len(str(self.count))
        for idx, dt_start in enumerate(vals[:-1]):
            date_start = fields.Date.to_string(dt_start.date())
            # always remove 1 day for the date_end since range limits are
            # inclusive
            dt_end = vals[idx+1].date() - relativedelta(days=1)
            date_end = fields.Date.to_string(dt_end)
            date_ranges.append({
                'sequence_id': seq_id.id,
                'date_from': date_start,
                'date_to': date_end,
                'number_next': 1,
                'company_id': self.company_id.id})
        return date_ranges
    #
    @api.multi
    def action_apply(self):
        date_ranges = self._compute_date_ranges()
        if date_ranges:
            for dr in date_ranges:
                self.env['ir.sequence.date_range'].create(dr)
        #
