# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import fields, models, _
from odoo.exceptions import UserError
from io import BytesIO
import base64
import requests


class AccountReportbillingVender(models.TransientModel):
    _name = "account.billing.vender.report"


    range_id = fields.Many2one('date.range.type', string=u'ปี',
                               required=True,
                               # track_visibility='always'
                               )
    period_id = fields.Many2one('date.range', string=u'งวดที่', copy=False ,
                                required=True,
                                domain="[('type_id', '=', range_id)]"
                                )

    def print_ineco_report(self):
        url = 'http://34.87.83.73:8080/jasperserver/rest_v2/reports'
        report_path = '/kk/account/report/report_billing_vender'
        user = 'jasperadmin'
        password = 'xitgmLwmp'
        parameter = str(self.period_id.id)
        rest_url_2 = (
                url + report_path + '.pdf?period_id=' + parameter + '&j_username=' + user + '&j_password=' + password)

        r = requests.get(rest_url_2)
        r.status_code
        r.headers['content-type']
        r.encoding
        f = BytesIO()
        f.write(r.content)
        file_data = base64.b64encode(f.getvalue())
        result = file_data
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.create(
            {'name': "data.pdf", 'datas_fname': 'data.pdf', 'datas': result, 'type': 'binary'})
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }