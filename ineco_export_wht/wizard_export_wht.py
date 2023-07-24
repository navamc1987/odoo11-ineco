# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, exceptions
from datetime import datetime
import pandas as pd
import tempfile
import base64


class WizardExportWht(models.TransientModel):
    _name = 'wizard.export.wht'
    _description = 'Export With Holding Tax'

    date_from = fields.Date(string='From', required=1)
    date_to = fields.Date(string='To', required=1)

    @api.model
    def default_get(self, fields):
        df = datetime.now().strftime('%Y-%m-01')
        dt = datetime.now().strftime('%Y-%m-%d')
        rec = {'date_from': df, 'date_to': dt}
        return rec

    @api.multi
    def export_wht3(self):
        sql = """
select 
  row_number() over (ORDER BY (to_char(iwl.date_doc, 'dd') || '/' || to_char(iwl.date_doc,'MM') || '/' || extract(year from iwl.date_doc)+543)) as sequence,
  rp.vat,
  coalesce(rp.branch_no, '00000') as branch,
  trim(rp.name) as customer_name,
  coalesce(rp.street,'') as tambon,
  coalesce(rp.street2,'') as amphur,
  coalesce(rp.city,'') as city,
  rp.zip,
  to_char(iwl.date_doc, 'dd') || '/' || to_char(iwl.date_doc,'MM') || '/' || extract(year from iwl.date_doc)+543 as date_doc,
  iwl.note as description,
  iwl.percent,
  iwl.base_amount,
  iwl.tax,
  1 as condition
from ineco_wht iw
join res_partner rp on rp.id = iw.partner_id
join ineco_wht_line iwl on iwl.wht_id = iw.id
left join res_country_state rs on rs.id = rp.state_id
where iw.wht_type = 'purchase'
  and iw.date_doc between '{}' and '{}'
  and iw.wht_kind = 'pp4'
order by date_doc, sequence
        """.format(self.date_from, self.date_to)
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        if data:
            fd, filename = tempfile.mkstemp()
            filename = filename + '.csv'
            df = pd.DataFrame(data)
            df.to_csv(filename)
            output = open(filename, "rb")
            result = base64.b64encode(output.read())
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')

            attachment_id = self.env['ir.attachment'].create({
                'name': "wht_holding_3.csv", 'datas_fname': 'wht_holding_3.csv', 'datas': result})
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
            }
        return True

    @api.multi
    def export_wht53(self):
        sql = """
        select 
          row_number() over (ORDER BY (to_char(iwl.date_doc, 'dd') || '/' || to_char(iwl.date_doc,'MM') || '/' || extract(year from iwl.date_doc)+543)) as sequence,
          rp.vat,
          coalesce(rp.branch_no, '00000') as branch,
          trim(rp.name) as customer_name,
          coalesce(rp.street,'') as tambon,
          coalesce(rp.street2,'') as amphur,
          coalesce(rp.city,'') as city,
          rp.zip,
          to_char(iwl.date_doc, 'dd') || '/' || to_char(iwl.date_doc,'MM') || '/' || extract(year from iwl.date_doc)+543 as date_doc,
          iwl.note as description,
          iwl.percent,
          iwl.base_amount,
          iwl.tax,
          1 as condition
        from ineco_wht iw
        join res_partner rp on rp.id = iw.partner_id
        join ineco_wht_line iwl on iwl.wht_id = iw.id
        left join res_country_state rs on rs.id = rp.state_id
        where iw.wht_type = 'purchase'
          and iw.date_doc between '{}' and '{}'
          and iw.wht_kind = 'pp7'
        order by date_doc, sequence
                """.format(self.date_from, self.date_to)
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        if data:
            fd, filename = tempfile.mkstemp()
            filename = filename + '.csv'
            df = pd.DataFrame(data)
            df.to_csv(filename)
            output = open(filename, "rb")
            result = base64.b64encode(output.read())
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')

            attachment_id = self.env['ir.attachment'].create({
                'name': "wht_holding_53.csv", 'datas_fname': 'wht_holding_53.csv', 'datas': result})
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
            }
        return True
