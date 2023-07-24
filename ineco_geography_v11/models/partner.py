# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    district_id = fields.Many2one('ineco.district', string='District', index=True, ondelete='restrict')
    amphur_id = fields.Many2one('ineco.amphur', string='Amphur', index=True, ondelete='restrict')
    province_id = fields.Many2one('ineco.province', string='Province', index=True, ondelete='restrict')
    use_thai_style = fields.Boolean(string='Thai Address', default=True)

    @api.onchange('district_id')
    def onchange_district_id(self):
        if self.district_id:
            self.amphur_id = self.district_id.amphur_id.id
            self.province_id = self.district_id.province_id.id
            self.street2 = self.district_id.name + ' ' + self.district_id.amphur_id.name
            self.city = self.district_id.province_id.name
            zip = self.env['ineco.zipcode'].search([('district_id', '=', self.district_id.id),
                                              ('amphur_id', '=', self.district_id.amphur_id.id),
                                              ('province_id', '=', self.district_id.province_id.id)])
            if zip:
                self.zip = zip.name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: