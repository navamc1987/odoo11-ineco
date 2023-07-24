# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportAction(models.Model):
    _inherit = 'ir.actions.report'

    jasper_url = fields.Char(string='Jasper Server REST URL')
    jasper_report_path = fields.Char(string='Jaser Server Report Path', )
    report_ext = fields.Char(string='Output Format', default='pdf')
    customer_id = fields.Char(string='Customer ID')
    report_id = fields.Char(string='Report ID')
    criteria_field = fields.Char(string='Criteria Field')
    parameter_name = fields.Char(string='Jasper Parameter Name')
    report_type = fields.Selection(selection_add=[("ineco", "Ineco")])

    @api.model
    def render_ineco(self, docids, data):
        data = self
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get('report.report_ineco.abstract')
        if report_model is None:
            raise UserError(_('%s model was not found' % report_model_name))
        return report_model.with_context({
            'active_model': self.model
        }).create_ineco_report(docids, data)

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportAction, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['ineco']
        conditions = [('report_type', 'in', qwebtypes),
                      ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)
