# -*- coding: utf-8 -*-
# Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
# All Right Reserved

{
    'name': 'INECO Thai v11',
    'version': '1.0',
    'depends': ["account", "account_invoicing", "account_cancel", "ineco_geography_v11",
                "mail", "portal", "sale_management", "purchase", "date_range",
                ],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'summary': 'ระบบบัญชีไทย',
    'description': """
Feature: 
Thai Accounting on Odoo 11
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        'security/ir.model.access.csv',
        'security/acc_security.xml',
        'data/wht_data.xml',
        'data/sequence.xml',
        'data/menu_data.xml',

        'wizard_cancel_admin/cancel_admin_cash_view.xml',
        'wizard_back_tax/wizard_back_view.xml',
        'wizard_spit_vat/wizard_split_move_line_view.xml',
        'wizard_adjustments/wh_wizard_adjustments_view.xml',
        'wizard_adjustments_con/wizard_adjustments_con_view.xml',
        'wizard_edit_inv_no/wizard_edit_inv_no.xml',
        'wizard_input_tax/wizard_tax_view.xml',
        'views/account_account_view.xml',
        'views/account_move_view.xml',
        'views/account_wht_view.xml',
        'views/account_cheque_view.xml',
        'pay_wizard/pay_wizard_view.xml',
        'views/account_billing_view.xml',
        'views/account_customer_payment_view.xml',
        'views/account_journal_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_customer_deposit_view.xml',
        'views/account_invoice_view.xml',
        'views/account_supplier_payment_view.xml',
        'views/account_supplier_deposit_view.xml',
        'views/res_partner_view.xml',
        'views/account_vat_purchase_view.xml',
        'wizard/sale_make_deposit_view.xml',

        'views/account_tax.xml',

        'views/ineco_stock_packing_view.xml',
        'refund_wizard/account_invoice_refund_view.xml',

        'views_expense/vender_expense_record.xml',
        'views_expense/vender_expense_payment_view.xml'

    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
