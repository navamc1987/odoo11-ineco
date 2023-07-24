# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _


class InecoAccountVat(models.Model):
    _name = "ineco.account.vat"
    _description = "Vat"

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.taxid = self.partner_id.vat or ''
            self.depcod = self.partner_id.branch_no or ''

    move_line_id = fields.Many2one('account.move.line', string='Move Line', on_delete="restrict")
    account_id = fields.Many2one('account.account', string='Account',
                                 related='move_line_id.account_id', track_visibility='onchange', store=True)
    parent_state = fields.Char(string='State', related='move_line_id.parent_state', track_visibility='onchange',
                               store=True)
    customer_payment_id = fields.Many2one('ineco.customer.payment', string='Customer Payment', on_delete="restrict")
    customer_deposit_id = fields.Many2one('ineco.customer.deposit', string='Customer Deposit', on_delete="restrict")
    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string='Supplier Payment', on_delete="restrict")
    supplier_deposit_id = fields.Many2one('ineco.supplier.deposit', string='Supplier Deposit', on_delete="restrict")
    invoice_id = fields.Many2one('account.invoice', string='Invoice', on_delete="restrict")

    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=True, copy=False, track_visibility='onchange')
    docdat = fields.Date(string='ลงวันที่', required=True, track_visibility='onchange')
    vatprd = fields.Date(string='วันที่ยื่น')
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    partner_name = fields.Char(string=u'ผู้จำหน่าย', required=False, copy=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)

    period_id = fields.Many2one('date.range', string=u'งวดที่', copy=False)
    period_type_id = fields.Many2one('date.range.type', string=u'ปี', related='period_id.type_id', store=True)

    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
    late = fields.Boolean(string='ยื่นล่าช้า')
    remark = fields.Char(string='หมายเหตุ', size=30)

    tax_sale_ok = fields.Boolean(string=u'Sale Tax', copy=False, related='account_id.tax_sale_ok',
                                 track_visibility='onchange', store=True)
    tax_purchase_ok = fields.Boolean(string=u'Purchase Tax', copy=False, related='account_id.tax_purchase_ok',
                                     track_visibility='onchange', store=True)
    tax_purchase_wait_ok = fields.Boolean(string=u'Purchase Tax wait', copy=False, related='account_id.wait',
                                          track_visibility='onchange', store=True)
    vat_type = fields.Selection([('sale', u'ภาษีขาย'),
                                 ('purchase', u'ภาษีซื้อ')],
                                string=u'ประเภทภาษี', track_visibility='onchange')

    reconciliation_in = fields.Many2one('ineco.account.vat', string=u'กลับภาษีซื้อ', on_delete="restrict")

    vatrec = fields.Char(string='vatrec', size=1)
    vattyp = fields.Char(string='vattyp', size=1)
    rectyp = fields.Char(string='rectyp', size=1)
    # period_id = fields.Many2one('ineco.account.period', string='งวดภาษี', required=True)
    refnum = fields.Char(string='refnum', size=15)
    newnum = fields.Char(string='newnum', size=10)
    descrp = fields.Char(string='descrp', size=60)
    amt01 = fields.Float(string='amt01', digits=(8, 2))
    vat01 = fields.Float(string='vat01', digits=(8, 2))
    amt02 = fields.Float(string='รายได้จากการขาย', digits=(8, 2))
    vat02 = fields.Float(string='จำนวนภาษีมูลค่าเพิ่ม', digits=(8, 2))
    amtrat0 = fields.Float(string='amtrat0', digits=(8, 2))
    self_added = fields.Char(string='self_added', size=1)
    had_modify = fields.Char(string='had_modify', size=1)
    docstat = fields.Char(string='docstat', size=1)
    orgnum = fields.Integer(string='orgnum')
    prenam = fields.Char(string='prenam', size=15)

    customer_deposit_line_id = fields.Many2one('ineco.customer.deposit.line', string='Customer Deposit line')
    supplier_deposit_line_id = fields.Many2one('ineco.supplier.deposit.line', string='Supplier Deposit line')

    @api.multi
    def write(self, vals):
        res = super(InecoAccountVat, self).write(vals)
        vstr = ''
        if self.tax_purchase_ok:
            vstr = 'ภาษีซื้อ'
        if self.tax_purchase_wait_ok:
            vstr = 'ภาษีซื้อพัก'
        if self.invoice_id:
            self.invoice_id.message_post(body=_(
                f'เปลี่ยนแปลง ประเภท {vstr} ใบกำกับ {self.name} '
                f'วันที่ {self.docdat} วันที่ยื่น {self.vatprd} '
                f'ผู้จำหน่าย {self.partner_name} \n'
                f'เลขประจำตัวผู้เสียภาษี {self.taxid} รหัสสาขา {self.depcod} '
                f' ยอดก่อนภาษี {self.amount_untaxed} ภาษี {self.amount_tax}  ยอดเงินรวม {self.amount_total}'))

        return res

    @api.onchange('docdat', 'vatprd')
    def onchange_period_id(self):
        # self.vatprd = self.docdat
        range_obj = self.env['date.range'].search([('date_start', '<=', self.vatprd),
                                                   ('date_end', '>', self.vatprd),
                                                   ])
        if range_obj:
            self.period_id = range_obj.id
        else:
            self.period_id = False

    @api.multi
    def _ineco_create_vat(self, line=False, inv=False, vatprd=False, period_id=False, signed=False, vat_type=False,
                          account_id=False):
        if line:
            mvl = line.id
            account_id = line.account_id.id
        else:
            mvl = False

        if vatprd:
            vatprd = vatprd
        else:
            vatprd = False

        new_data = {
            'move_line_id': mvl,
            'account_id': account_id,
            'name': inv.reference or '',
            'docdat': inv.date_invoice,
            'vatprd': vatprd,
            'period_id': period_id,
            'partner_id': inv.partner_id.id,
            'partner_name': inv.partner_id.name,
            'taxid': inv.partner_id.vat or '',
            'depcod': inv.partner_id.branch_no or '',
            'amount_untaxed': inv.amount_untaxed_signed,
            'amount_tax': inv.amount_tax * signed,
            'amount_total': inv.amount_total_signed,
            'invoice_id': inv.id,
            'vat_type': vat_type, }
        vat = self.create(new_data)
        return vat

    @api.multi
    def unlink(self):
        tax_break = self.env['ineco.account.vat'].search(
            [('reconciliation_in', '=', self.id)])
        if tax_break:
            tax_break.write({'vatprd': False, 'reconciliation_in': False})
        return super(InecoAccountVat, self).unlink()
