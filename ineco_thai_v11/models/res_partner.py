# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import models, fields, api, _


class InecoPartnerContact(models.Model):

    _inherit = 'res.partner'

    fax = fields.Char(string='Fax', track_visibility='onchange')
    branch_no = fields.Char(string='Branch No', size=5, track_visibility='onchange')

    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name = partner.name or ''
            if partner.company_name or partner.parent_id:
                if not name and partner.type in ['invoice', 'delivery', 'other']:
                    name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
                if not partner.is_company:
                    name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, name)
            if partner.is_company:
                if partner.branch_no:
                    if partner.branch_no == '00000':
                        name = u"[ %s ] %s (สำนักงานใหญ่)" % (partner.ref, partner.name)
                    else:
                        name = u"[ %s ] %s (สาขาที่ %s)" % (partner.ref, name, partner.branch_no)
                else:
                    name = u"[ %s ] %s" % (partner.ref, partner.name)
            if self._context.get('show_address_only'):
                name = partner._display_address(without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and partner.email:
                name = "%s <%s>" % (name, partner.email)
            if self._context.get('html_format'):
                name = name.replace('\n', '<br/>')
            res.append((partner.id, name))
        return res

