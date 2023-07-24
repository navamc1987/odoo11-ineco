# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _
#from openerp import api, fields, models, _


class InecoGeography(models.Model):
    _name = "ineco.geography"
    _inherit = ['mail.thread']
    _description = "Geography"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, track_visibility='onchange')
    code = fields.Char(string='Code', required=True, copy=False, index=True, track_visibility='onchange')

    active = fields.Boolean('Active', default=True)


class InecoProvince(models.Model):
    _name = "ineco.province"
    _inherit = ['mail.thread']
    _description = "Province"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, track_visibility='onchange')
    code = fields.Char(string='Code', required=True, copy=False, index=True, track_visibility='onchange')
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True, track_visibility='onchange' )

    active = fields.Boolean('Active', default=True)


class InecoAmphur(models.Model):
    _name = "ineco.amphur"
    _inherit = ['mail.thread']
    _description = "Amphur"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, track_visibility='onchange')
    code = fields.Char(string='Code', required=True, copy=False, index=True, track_visibility='onchange')
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True, track_visibility='onchange' )
    province_id = fields.Many2one('ineco.province', string='Province', copy=False, index=True, track_visibility='onchange' )

    active = fields.Boolean('Active', default=True)


class InecoDistrict(models.Model):
    _name = "ineco.district"
    _inherit = ['mail.thread']
    _description = "District"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, track_visibility='onchange')
    code = fields.Char(string='Code', required=True, copy=False, index=True, track_visibility='onchange')
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True, track_visibility='onchange' )
    province_id = fields.Many2one('ineco.province', string='Province', copy=False, index=True, track_visibility='onchange' )
    amphur_id = fields.Many2one('ineco.amphur', string='Amphur', copy=False, index=True, track_visibility='onchange' )

    active = fields.Boolean('Active', default=True)

    @api.multi
    @api.depends('name', 'code', 'geo_id', 'province_id','amphur_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if self._context.get('show_fully', False):
                name = record.name + ' / ' + record.amphur_id.name + ' / ' + record.province_id.name
            res.append((record.id, name))
        return res


class InecoZipcode(models.Model):
    _name = "ineco.zipcode"
    _inherit = ['mail.thread']
    _description = "Zipcode"
    _order = 'name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, track_visibility='onchange')
    province_id = fields.Many2one('ineco.province', string='Province', required=True, copy=False, index=True, track_visibility='onchange' )
    amphur_id = fields.Many2one('ineco.amphur', string='Amphur', copy=False, index=True, track_visibility='onchange' )
    district_id = fields.Many2one('ineco.district', string='District', copy=False, index=True, track_visibility='onchange' )

    active = fields.Boolean('Active', default=True)

