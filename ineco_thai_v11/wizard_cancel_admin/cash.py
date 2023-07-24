# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

import time

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime


class WizardCancelAdmin(models.TransientModel):
    _name = "wizard.cancel.admin"


    @api.multi
    def button_cancel(self):
        record_ids = self._context.get('active_ids')
        for record in record_ids:
            self.env['account.invoice'].browse(record).action_invoice_cancel_ex()
        return True