# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo.addons.web.controllers import main as report
from odoo.http import route, request

import json


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == 'ineco':
            report = request.env['ir.actions.report']._get_report_from_name(
                reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])
            pdf = report.with_context(context).render_ineco(
                docids, data=data
            )[0]
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
                (
                    'Content-Disposition',
                    'attachment; filename=' + reportname + '.pdf'
                )
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return super(ReportController, self).report_routes(
            reportname, docids, converter, **data
        )
