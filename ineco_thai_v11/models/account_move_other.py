# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _description = "Account Entry"
    _order = 'date desc, id desc'
    _inherit = ['account.move', 'mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.multi
    def _get_default_journal(self):
        if self.env.context.get('default_journal_type'):
            return self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id),
                                                       ('type', '=', self.env.context['default_journal_type'])],
                                                      limit=1).id

    name = fields.Char(string='Number', required=True, copy=False, default='/', track_visibility='onchange')
    ref = fields.Char(string='Reference', copy=False, track_visibility='onchange')
    date = fields.Date(required=True, states={'posted': [('readonly', True)]}, index=True,
                       default=fields.Date.context_today, track_visibility='onchange')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 states={'posted': [('readonly', True)]}, default=_get_default_journal,
                                 track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, string="Currency",
                                  track_visibility='onchange')
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status',
                             required=True, readonly=True, copy=False, default='draft', track_visibility='onchange',
                             help='All manually created new journal entries are usually in the status \'Unposted\', '
                                  'but you can set the option to skip that status on the related journal. '
                                  'In that case, they will behave as journal entries automatically created by the '
                                  'system on document validation (invoices, bank statements...) and will be created '
                                  'in \'Posted\' status.')
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items',
                               states={'posted': [('readonly', True)]}, copy=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', compute='_compute_partner_id', string="Partner", store=True,
                                 readonly=True, track_visibility='onchange')
    amount = fields.Monetary(compute='_amount_compute', store=True, track_visibility='onchange')
    narration = fields.Text(string='Internal Note', track_visibility='onchange')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True,
                                 readonly=True, track_visibility='onchange')
    matched_percentage = fields.Float('Percentage Matched', compute='_compute_matched_percentage', digits=0, store=True,
                                      readonly=True, help="Technical field used in cash basis method",
                                      track_visibility='onchange')
    # Dummy Account field to search on account.move by account_id
    dummy_account_id = fields.Many2one('account.account', related='line_ids.account_id', string='Account', store=False,
                                       readonly=True, track_visibility='onchange')
    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile', track_visibility='onchange',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation. "
             "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")
