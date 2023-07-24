# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from io import BytesIO
from odoo import models
import requests
from inecocores.core import Service
import logging
import base64

_logger = logging.getLogger(__name__)


class ReportInecoAbstract(models.AbstractModel):
    _name = 'report.report_ineco.abstract'

    def create_ineco_report(self, docids, data):
        if data.parameter_name and data.criteria_field and data.report_id and data.customer_id:
            service = Service()
            field_in = data.criteria_field or ''
            file_data = False
            criteries = field_in + ' in ' + str(tuple(sorted(docids)))
            criteries = criteries.replace(',)', ')')

            params = {
                'js_parameter_name': data.parameter_name,
                'js_parameter_value': criteries,
            }

            report = service.call_report(customerId=data.customer_id, reportId=data.report_id, parameters=params)

            if report['status'] == 'ok':
                file_data = base64.b64decode(report['output'])
            if file_data:
                return file_data, 'ineco'
            else:
                return False, 'ineco'
        else:
            return False, 'ineci'
