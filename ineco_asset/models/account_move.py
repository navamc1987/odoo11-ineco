# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InecoAccountMove(models.Model):
    _inherit = 'account.move'

    is_asset = fields.Boolean(string='Asset Voucher')
