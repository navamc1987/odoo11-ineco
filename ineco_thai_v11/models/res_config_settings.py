# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_account_id = fields.Many2one('account.account', string=u'เงินสด', required=False)
    #Account Receivable
    interest_income_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยรับ', required=False)
    cash_discount_account_id = fields.Many2one('account.account', string=u'ส่วนลดเงินสด', required=False)
    wht_sale_account_id = fields.Many2one('account.account', string=u'ภาษีถูกหัก ณ ที่จ่าย', required=False)
    cheque_sale_account_id = fields.Many2one('account.account', string=u'เช็ครับ', required=False)
    vat_sale_account_id = fields.Many2one('account.account', string=u'ภาษีขาย', required=False)
    unearned_income_account_id = fields.Many2one('account.account', string=u'รายได้รับล่วงหน้า', required=False)
    #Account Payable
    interest_expense_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยจ่าย', required=False)
    cash_income_account_id = fields.Many2one('account.account', string=u'ส่วนลดรับ', required=False)
    wht_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย', required=False)
    wht_purchase_personal_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย (บุคคล)', required=False)
    cheque_purchase_account_id = fields.Many2one('account.account', string=u'เช็คจ่าย', required=False)
    vat_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อ', required=False)
    unearned_expense_account_id = fields.Many2one('account.account', string=u'รายจ่ายล่วงหน้า', required=False)
    vat_purchase_tax_break_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อพัก', required=False)

    get_paid_account_id = fields.Many2one('account.account', string=u'-รับเงินขาด', required=False)
    get_overgrown_account_id = fields.Many2one('account.account', string=u'+รับเงินเกิน', required=False)
    profit_loss_account_id = fields.Many2one('account.account', string=u'+,- กำไรขาดทุนอัตราแลกเปลี่ยน', required=False)
    fee_account_id = fields.Many2one('account.account', string=u'ค่าธรรมเนียม', required=False)



    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            cash_account_id=int(params.get_param('ineco_thai_v11.cash_account_id', default=False)) or False,
            # Account Receivable
            interest_income_account_id=int(params.get_param('ineco_thai_v11.interest_income_account_id', default=False)) or False,
            cash_discount_account_id=int(params.get_param('ineco_thai_v11.cash_discount_account_id', default=False)) or False,
            wht_sale_account_id=int(params.get_param('ineco_thai_v11.wht_sale_account_id', default=False)) or False,
            cheque_sale_account_id=int(params.get_param('ineco_thai_v11.cheque_sale_account_id', default=False)) or False,
            vat_sale_account_id=int(params.get_param('ineco_thai_v11.vat_sale_account_id', default=False)) or False,
            unearned_income_account_id=int(params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
            #Account Payable
            interest_expense_account_id=int(
                params.get_param('ineco_thai_v11.interest_expense_account_id', default=False)) or False,
            cash_income_account_id=int(
                params.get_param('ineco_thai_v11.cash_income_account_id', default=False)) or False,
            wht_purchase_account_id=int(params.get_param('ineco_thai_v11.wht_purchase_account_id', default=False)) or False,
            wht_purchase_personal_account_id=int(params.get_param('ineco_thai_v11.wht_purchase_personal_account_id', default=False)) or False,
            cheque_purchase_account_id=int(
                params.get_param('ineco_thai_v11.cheque_purchase_account_id', default=False)) or False,
            vat_purchase_account_id=int(params.get_param('ineco_thai_v11.vat_purchase_account_id', default=False)) or False,
            unearned_expense_account_id=int(
                params.get_param('ineco_thai_v11.unearned_expense_account_id', default=False)) or False,

            vat_purchase_tax_break_account_id=int(params.get_param('ineco_thai_v11.vat_purchase_tax_break_account_id', default=False)) or False,

            get_paid_account_id=int(params.get_param('ineco_thai_v11.get_paid_account_id', default=False)) or False,
            get_overgrown_account_id=int(params.get_param('ineco_thai_v11.get_overgrown_account_id', default=False)) or False,
            profit_loss_account_id=int(params.get_param('ineco_thai_v11.profit_loss_account_id', default=False)) or False,
            fee_account_id=int(params.get_param('ineco_thai_v11.fee_account_id', default=False)) or False,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.cash_account_id", self.cash_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.interest_income_account_id", self.interest_income_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.cash_discount_account_id", self.cash_discount_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.wht_sale_account_id", self.wht_sale_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.cheque_sale_account_id", self.cheque_sale_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.vat_sale_account_id", self.vat_sale_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.unearned_income_account_id", self.unearned_income_account_id.id or False)
        # Account Payable
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.interest_expense_account_id", self.interest_expense_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.cash_income_account_id", self.cash_income_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.wht_purchase_account_id", self.wht_purchase_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.wht_purchase_personal_account_id", self.wht_purchase_personal_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.cheque_purchase_account_id", self.cheque_purchase_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.vat_purchase_account_id", self.vat_purchase_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.unearned_expense_account_id", self.unearned_expense_account_id.id or False)

        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.vat_purchase_tax_break_account_id",self.vat_purchase_tax_break_account_id.id or False)

        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.get_paid_account_id",
                                                         self.get_paid_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.get_overgrown_account_id",
                                                         self.get_overgrown_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.profit_loss_account_id",
                                                         self.profit_loss_account_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("ineco_thai_v11.fee_account_id",
                                                         self.fee_account_id.id or False)
