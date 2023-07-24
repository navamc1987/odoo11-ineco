# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models
import bahttext
import unicodecsv as csv
from io import BytesIO
import base64


class InecoWhtType(models.Model):
    _name = 'ineco.wht.type'

    name = fields.Char(string='Description', required=True)
    printed = fields.Char(string='To Print')
    sequence = fields.Integer(string='Sequence')

    _sql_constraints = [
        ('ineco_wht_unique', 'unique (sequence)', 'Sequence must be unique!')
    ]


class InecoWhtLine(models.Model):
    _name = 'ineco.wht.line'
    _description = 'With Holding Tax Line'

    @api.one
    @api.depends('percent', 'base_amount')
    def _compute_tax(self):
        if self.percent and self.base_amount:
            self.tax = (self.percent / 100) * self.base_amount

    name = fields.Char(string='คำอธิบาย', track_visibility=True)
    wht_type_id = fields.Many2one('ineco.wht.type', string='ประเภท', required=True, track_visibility=True)
    date_doc = fields.Date(string='วันที่', required=True, default=fields.Datetime.now(), track_visibility=True)
    percent = fields.Float(string='เปอร์เซ็นต์', digits=(12,2), default=3.0, track_visibility=True)
    wht_id = fields.Many2one('ineco.wht', string='With Holding Tax', copy=False, track_visibility=True)
    note = fields.Text(string='หมายเหตุ', track_visibility=True)
    base_amount = fields.Float(string='ฐานภาษี', digits=(12,2), copy=False, track_visibility=True )
    tax = fields.Float(string='ภาษี', digits=(12, 2), compute='_compute_tax',store=True )




class InecoWhtPnd(models.Model):
    _name = 'ineco.wht.pnd'
    _description = "WHT PND"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']


    @api.one
    @api.depends('wht_id')
    def _attachment_count(self):
        self.attach_count = len(self.wht_id)
        self.attach_no = len(self.wht_id) / 6 + 1
        val = val1 = 0.0
        for line in self.wht_id:
            val1 += line.base_amount
            val += line.tax
        self.total_tax = val
        self.total_amount = val1
        self.total_tax_send = val + self.add_amount or 0.0

    name = fields.Char(string='Description', track_visibility=False)
    account_fiscal_year = fields.Many2one('date.range.type', string=u'ปี')
    account_period = fields.Many2one('date.range', string=u'เดือน', domain="[('type_id','=',account_fiscal_year)]")
    date_pnd = fields.Date(string='Date', required=True, track_visibility=False)
    type_normal = fields.Boolean(string='Type Normal', track_visibility=False)
    type_special = fields.Boolean(string='Type Special', track_visibility=False)
    type_no = fields.Boolean(string='Type No', track_visibility=False)
    section_3 = fields.Boolean(string='Section 3', track_visibility=False)
    section_48 = fields.Boolean(string='Section 48', track_visibility=False)
    section_50 = fields.Boolean(string='Section 50', track_visibility=False)
    section_65 = fields.Boolean(string='Section 65', track_visibility=False)
    section_69 = fields.Boolean(string='Section 69', track_visibility=False)
    attach_pnd = fields.Boolean(string='Attach PND', track_visibility=False)
    wht_ids = fields.Many2many('ineco.wht', 'ineco_wht_pnds', 'pnd_id', 'wht_id', 'With holding tax')

    wht_id = fields.One2many('ineco.wht', 'pnd_id', 'With holding tax')

    attach_count = fields.Integer(string='Attach Count', compute='_attachment_count')
    # attach_no = fields.Integer(string='Attach No', compute='_attachment_count')
    attach_no = fields.Integer(string='Attach No',
                               # store=True,
                               default=0)
    total_amount = fields.Float(string='Total Amount', digits=(12, 2), compute='_attachment_count')
    total_tax = fields.Float(string='Total Tax', digits=(12, 2), compute='_attachment_count')
    total_tax_send = fields.Float(string='Tax Send', digits=(12, 2), compute='_attachment_count')
    add_amount = fields.Float(string='Add Amount', digits=(12, 2), default=0.0, track_visibility=False)
    note = fields.Text(string='Note', track_visibility=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    pnd_type = fields.Selection([('pp4', '(4) PP3'), ('pp7', '(7) PP53')], 'PND Type', required=True,
                                select=True, track_visibility=False)
    file_save = fields.Binary('Save File', readonly=True)
    file_name = fields.Char('File Name')

    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft')

    @api.multi
    def button_draft(self):
        self.ensure_one()
        # self.wht_id = False
        self.file_save = False
        self.file_name = False
        self.state = 'draft'
        return True

    @api.multi
    def button_cancel(self):
        self.ensure_one()
        self.wht_id = False
        self.file_save = False
        self.file_name = False
        self.state = 'cancel'
        return True

    def export_pnd3(self):
        for data in self:
            self.get_pnd3()
            sql = """
                select
                    ''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,5,'0')::varchar as sequence,
                    rp.vat,
                    case when rp.branch_no is null then '00000'::varchar
                    else rp.branch_no::varchar end as title_code,
                    ''::varchar as title_name,
                    rp.name,
                    ''::varchar as lastname,
                    rp.street || ' '||rp.street2 as address ,
                    (lpad (
                          extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar(200) as description,
                    ltrim(to_char(iwl.percent, '00.00'))::varchar as percent,
                    ltrim(to_char(iwl.base_amount::numeric,'00000000000.00' ))::varchar as amount_untaxed,
                    ltrim(to_char(round(iwl.percent / 100 * iwl.base_amount, 2)::numeric,'0000000000.00'))::varchar as amount_tax,
                    '1'::varchar as always
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id

                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id

                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id

                    where wht_type = 'purchase'
			        and iw.date_doc BETWEEN (select date_start from date_range where id = %s) and (select date_end from date_range where id = %s) 
                    and iw.wht_kind = '%s'
                    """
            self._cr.execute(sql % (data.account_period.id, data.account_period.id, 'pp4'))
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'

            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd3_' + data.account_period.name.replace('/', '-') + '.txt'  # '.csv'
                        })
            self.state = 'post'

        return True

    def export_pnd53(self):
        for data in self:
            self.get_pnd53()
            sql = """
                      select
                    ''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,5,'0')::varchar as sequence, 
                    rp.vat,
                    case when rp.branch_no is null then '00000'::varchar
                    else rp.branch_no::varchar end as title_code,
                    ''::varchar as titlename,
                    rp.name,

                    rp.street || ' '||rp.street2 as address ,
                    (lpad (
                          extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar(200) as description,
                    ltrim(to_char(iwl.percent, '00.00'))::varchar as percent,
                    ltrim(to_char(iwl.base_amount::numeric,'00000000000.00' ))::varchar as amount_untaxed,
                    ltrim(to_char(round(iwl.percent / 100 * iwl.base_amount, 2)::numeric,'0000000000.00'))::varchar as amount_tax,
                    '1'::varchar as always
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id

                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id

                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id
                    where
                      wht_type = 'purchase'
                      
                      and iw.date_doc BETWEEN (select date_start from date_range where id = %s) and (select date_end from date_range where id = %s) 
                      and iw.wht_kind = '%s'     
                     """
            self._cr.execute(sql % (data.account_period.id, data.account_period.id, 'pp7'))  # pp7
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'
            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd53_' + data.account_period.name.replace('/', '-') + '.txt'  # '.csv'
                        })
            self.state = 'post'

        return True

    def export_pnd3_additional(self):
        for data in self:
            sql = """
                select
                    ''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,5,'0')::varchar as sequence,
                    rp.pid,
                    case when rp.tax_detail is null then '00000'::varchar
                    else rp.tax_detail::varchar end as title_code,
                    ''::varchar as title_name,
                    rp.name,
                    ''::varchar as lastname,
                    rp.street || ' '||rp.street2 as address ,
                    (lpad (
                          extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar as description,
                    ltrim(to_char(iwl.percent, '00.00'))::varchar as percent,
                    ltrim(to_char(iwl.base_amount::numeric,'00000000000.00' ))::varchar as amount_untaxed,
                    ltrim(to_char(round(iwl.percent / 100 * iwl.base_amount, 2)::numeric,'0000000000.00'))::varchar as amount_tax,
                    '1'::varchar as always
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id
                    left join account_voucher av on iw.voucher_id = av.id
                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id
                    left join account_period ap on av.period_id = ap.id
                    left join account_fiscalyear af on ap.fiscalyear_id = af.id
                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id
                    left join account_move_line aml on iw.id = aml.wht_id
                    where
                      wht_type = 'purchase'
                      and ( extract(month from aml.tax_invoice_date3)
                             >
                           extract(month from iw.date_doc) )
                      and case when iw.voucher_id is null then
                            iw.date_doc BETWEEN (select date_start from account_period where id = %s) and (select date_stop from account_period where id = %s)
                           else av.period_id = %s end
                          and iw.wht_kind = '%s'"""

            self._cr.execute(sql % (data.period_tax_id.id, data.period_tax_id.id, data.period_tax_id.id, 'pp4'))  # pp7
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'
            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd3_additional_' + data.period_tax_id.name.replace('/', '-') + '.txt'  # '.csv'
                        })

        return True

    def export_pnd53_additional(self):
        for data in self:
            sql = """
                select
                    ''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,5,'0')::varchar as sequence,
                    rp.pid,
                    case when rp.tax_detail is null then '00000'::varchar
                    else rp.tax_detail::varchar end as title_code,
                    ''::varchar as titlename,
                    rp.name,

                    rp.street || ' '||rp.street2 as address ,
                    (lpad (
                          extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar as description,
                    ltrim(to_char(iwl.percent, '00.00'))::varchar as percent,
                    ltrim(to_char(iwl.base_amount::numeric,'00000000000.00' ))::varchar as amount_untaxed,
                    ltrim(to_char(round(iwl.percent / 100 * iwl.base_amount, 2)::numeric,'0000000000.00'))::varchar as amount_tax,
                    '1'::varchar as always,
                    extract(month from aml.tax_invoice_date3)::text as datetax
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id
                    left join account_voucher av on iw.voucher_id = av.id
                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id
                    left join account_period ap on av.period_id = ap.id
                    left join account_fiscalyear af on ap.fiscalyear_id = af.id
                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id
                    left join account_move_line aml on iw.id = aml.wht_id
                    where
                      wht_type = 'purchase'
                      and ( extract(month from aml.tax_invoice_date3)
                             >
                           extract(month from iw.date_doc) )
                      and case when iw.voucher_id is null then
                            iw.date_doc BETWEEN (select date_start from account_period where id = %s) and (select date_stop from account_period where id = %s)
                           else av.period_id = %s end
                      and iw.wht_kind = '%s'"""
            self._cr.execute(sql % (data.period_tax_id.id, data.period_tax_id.id, data.period_tax_id.id, 'pp7'))  # pp7
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'
            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd53_additional_' + data.period_tax_id.name.replace('/', '-') + '.txt'  # '.csv'
                        })

        return True

    def get_pnd3(self):
        tax = self.env['ineco.wht'].search([
            ('date_doc', '>=', self.account_period.date_start),
            ('date_doc', '<=', self.account_period.date_end),
            ('wht_type', '=', 'purchase'),
            ('wht_kind', '=', 'pp4'),
            # ('pnd_id','=',False)
        ])
        for pnd3 in tax:
            pnd3.pnd_id = self.id

    def get_pnd53(self):
        tax = self.env['ineco.wht'].search([
            ('date_doc', '>=', self.account_period.date_start),
            ('date_doc', '<=', self.account_period.date_end),
            ('wht_type', '=', 'purchase'),
            ('wht_kind', '=', 'pp7'),
            # ('pnd_id','=',False)
        ])
        for pnd53 in tax:
            pnd53.pnd_id = self.id


class InecoWht(models.Model):
    _name = 'ineco.wht'
    _description = 'Fiscal Year'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.one
    @api.depends('line_ids')
    def _compute_amount(self):
        val = val1 = 0.0
        for line in self.line_ids:
            val1 += line.base_amount
            val += line.tax
        self.tax = val
        self.base_amount = val1
        self.tax_text = '- '+bahttext.bahttext(val)+' -'

    @api.one
    @api.depends('company_id')
    def _get_company_vat(self):
        if self.company_id:
            self.company_full_address = (self.company_id.partner_id.street or '') + ' ' + \
                                        (self.company_id.partner_id.street2 or '') + ' '+ \
                                        (self.company_id.partner_id.city or '')

    @api.one
    @api.depends('partner_id')
    def _get_supplier_vat(self):
        self.partner_full_address = (self.partner_id.street or '') + ' ' + \
                                    (self.partner_id.street2 or '') + ' '+ \
                                    (self.partner_id.city or '')

    @api.one
    @api.depends()
    def _get_moveline(self):
        sql = 'select id from account_move_line where wht_id = %s' % (self.id)
        self._cr.execute(sql)
        res = self._cr.fetchone()
        self.move_line_id = res and res[0] or False

    @api.one
    @api.depends('line_ids')
    def _get_line_value(self):
        number5_id = 999
        number6_id = 999
        for line in self.line_ids:
            if line.wht_type_id.id == number5_id:
                self.has_number_5 = True
                self.number5_base_amount = line.base_amount
                self.number5_tax = line.tax
            elif line.wht_type_id.id == number6_id :
                self.has_number_6 = True
                self.number6_base_amount = line.base_amount
                self.number6_tax = line.tax
                self.number6_note = line.note

    name = fields.Char(string='เลขที่', required=True, default='/',track_visibility='onchange')
    date_doc = fields.Date(string='ลงวันที่', required=True,track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    company_vat_no = fields.Char(string='Company Vat No', related='company_id.vat', readonly=True,track_visibility='onchange')

    company_full_address = fields.Char(string='Company Address',
        store=True, readonly=True, compute='_get_company_vat', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='พาร์ทเนอร์', required=True,track_visibility='onchange')
    partner_vat_no = fields.Char(string='Vat No', related='partner_id.vat', readonly=True,track_visibility='onchange')
    partner_full_address = fields.Char(string='Partner',
        store=True, readonly=True, compute='_get_supplier_vat', track_visibility='onchange')
    account_id = fields.Many2one('account.account', string='Account',track_visibility='onchange')
    sequence = fields.Integer(string='Sequence', defaults=100)
    wht_type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='ประเภท')
    wht_kind = fields.Selection([('pp1', '(1) PP1'),
                                  ('pp2', '(2) PP1'),
                                  ('pp3', '(3) PP2'),
                                  ('pp4', '(4) PP3'),
                                  ('pp5', '(5) PP2'),
                                  ('pp6', '(6) PP2'),
                                  ('pp7', '(7) PP53'),
                                  ], string='ภงด.', default='pp7',track_visibility='onchange')
    wht_payment = fields.Selection([('pm1', '(1) With holding tax'),
                                     ('pm2', '(2) Forever'),
                                     ('pm3', '(3) Once'),
                                     ('pm4', '(4) Other'),
                                     ], string='การชำระ', default='pm1',track_visibility='onchange')
    note = fields.Text(string='หมายเหตุ',track_visibility='onchange')
    line_ids = fields.One2many('ineco.wht.line', 'wht_id', string='WHT Lines',track_visibility='onchange')
    base_amount = fields.Float(string='ยอดเงิน', digits=(12,2), compute='_compute_amount',store=True,track_visibility='onchange')
    tax = fields.Float(string='ภาษี', digits=(12,2), compute='_compute_amount',store=True,track_visibility='onchange')
    tax_text = fields.Char(string='Baht Tax', compute='_compute_amount',track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
    ], 'Status', readonly=True, track_visibility='onchange')
    voucher_id = fields.Many2one('account.voucher', string='Voucher',track_visibility='onchange')
    move_line_id = fields.Many2one('account.move.line', string='Move Line', compute='_get_moveline',track_visibility='onchange')
    has_number_5 = fields.Boolean(string='Is No 5', compute='_get_line_value',track_visibility='onchange')
    number5_base_amount = fields.Float(string='Base Amount', compute='_get_line_value', digits=(12,2),track_visibility='onchange')
    number5_tax = fields.Float(string='Tax', compute='_get_line_value', digits=(12,2),track_visibility='onchange')
    has_number_6 = fields.Boolean(string='Is No 6', compute='_get_line_value',track_visibility='onchange')
    number6_base_amount = fields.Float(string='Base Amount', compute='_get_line_value', digits=(12,2),track_visibility='onchange')
    number6_tax = fields.Float(string='Tax', compute='_get_line_value', digits=(12,2),track_visibility='onchange')
    number6_note = fields.Char(string='Note', compute='_get_line_value',track_visibility='onchange')

    move_line_id = fields.Many2one('account.move.line', string='Move Line', on_delete="restrict",track_visibility='onchange')

    customer_payment_id = fields.Many2one('ineco.customer.payment', string='Customer Payment', on_delete="restrict" ,track_visibility='onchange')
    customer_deposit_id = fields.Many2one('ineco.customer.deposit', string='Customer Deposit', on_delete="restrict",track_visibility='onchange')
    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string='Supplier Payment', on_delete="restrict",track_visibility='onchange')
    supplier_deposit_id = fields.Many2one('ineco.supplier.deposit', string='Supplier Deposit', on_delete="restrict",track_visibility='onchange')

    pnd_id = fields.Many2one('ineco.wht.pnd', string=u'แบบยื่นภาษีหัก ณ ที่จ่าย', copy=False, track_visibility='onchange')
    sp_amount = fields.Float(u'ฐานหัก',track_visibility='onchange')

    state_payment = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                                     string=u'สถานะการจ่าย', related='supplier_payment_id.state', )

    move_id = fields.Many2one('account.move',u'JV Move',
                                      related='move_line_id.move_id',
                                      track_visibility='onchange',
                                      store=True, readonly=True,
                                      related_sudo=False
                                      )

    @api.multi
    def button_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True