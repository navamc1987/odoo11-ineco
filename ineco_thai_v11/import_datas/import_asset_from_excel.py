import xlrd
import csv

book = xlrd.open_workbook("asset.xls")
## Asset Type
asset_type_header = ['name', 'journal_id', 'account_asset_id', 'account_depreciation_id',
                     'account_depreciation_expense_id', 'method_number', 'method_period', 'group_entries', 'account_analytic_id']
asset_header = ['name', 'category_id', 'code', 'date', 'date_depreciation', 'code_name', 'value', 'salvage_value',
                'value_residual', 'percent', 'method_number', 'method_period', 'purchase_value']
asset_type_data = []
asset_type_list = []
asset_data = []
for sheet_idx in range(book.nsheets):
    sh = book.sheet_by_index(sheet_idx)
    category = sh.cell_value(5, 0) or sh.cell_value(5, 1)
    category = category.strip()
    for row in range(sh.nrows):
        department = ''
        if row > 5:
            if sh.cell_value(row, 0):
                if sheet_idx in (3, 4, 5, 6, 7, 9):
                    department = sh.cell_value(row, 3)[:3]
                    new_category = "{}-{}".format(department, category)
                    if not new_category in asset_type_list:
                        analytic = False
                        if department.replace('-','') in ['ADM','MK','PLA']:
                            analytic = department.replace('-','')
                        asset_type_list.append(new_category)
                        data = {
                            'name': new_category,
                            'journal_id': 'สมุดรายวันทั่วไป-ทรัพย์สิน',
                            'account_asset_id': '1420-02',
                            'account_depreciation_id': '1420-02',
                            'account_depreciation_expense_id': '5590-01',
                            'method_number': 20,
                            'method_period': 1,
                            'group_entries': 1,
                            'account_analytic_id': analytic
                        }
                        asset_type_data.append(data)
                    data = {
                        'name': sh.cell_value(row, 1),
                        'category_id': new_category,
                        'code': sh.cell_value(row, 3),
                        'date': sh.cell_value(row, 5),
                        'date_depreciation': sh.cell_value(row, 5),
                        'code_name': sh.cell_value(row, 3),
                        'value': sh.cell_value(row, 6),
                        'value_residual': sh.cell_value(row, 9),
                        'purchase_value': sh.cell_value(row, 9),
                        'method_period': 1,
                        'percent': sh.cell_value(row, 8)
                    }
                else:
                    department = sh.cell_value(row, 2)[:3]
                    new_category = "{}-{}".format(department, category)
                    if not new_category in asset_type_list:
                        analytic = False
                        if department.replace('-', '') in ['ADM', 'MK', 'PLA']:
                            analytic = department.replace('-','')
                        asset_type_list.append(new_category)
                        data = {
                            'name': new_category,
                            'journal_id': 'สมุดรายวันทั่วไป-ทรัพย์สิน',
                            'account_asset_id': '1420-02',
                            'account_depreciation_id': '1420-02',
                            'account_depreciation_expense_id': '5590-01',
                            'method_number': 20,
                            'method_period': 1,
                            'group_entries': 1,
                            'account_analytic_id': analytic
                        }
                        asset_type_data.append(data)
                    data = {
                        'name': sh.cell_value(row, 1),
                        'category_id': new_category,
                        'code': sh.cell_value(row, 2),
                        'date': sh.cell_value(row, 4),
                        'date_depreciation': sh.cell_value(row, 4),
                        'code_name': sh.cell_value(row, 2),
                        'value': sh.cell_value(row, 5),
                        'value_residual': sh.cell_value(row, 8),
                        'purchase_value': sh.cell_value(row, 8),
                        'method_period': 1,
                        'percent': sh.cell_value(row, 7)
                    }
                if type(data['value_residual']) is float:
                    year = int(data['date'].replace('.', '')[-2:]) + 2500 - 543
                    month = data['date'][3:5]
                    day = data['date'][:2]
                    data['date'] = '{}-{}-{}'.format(year, month, day)
                    data['date_depreciation'] = '{}-{}-{}'.format(year, month, day)
                    # data['date_depreciation'] = '2022-06-01'
                    # data['value_residual'] = round(data['value'] - data['value_residual'], 2)
                    data['method_number'] = int(100/data['percent'])*12
                    asset_data.append(data)

with open('asset_type.csv', 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=asset_type_header)
    writer.writeheader()
    writer.writerows(asset_type_data)
with open('asset.csv', 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=asset_header)
    writer.writeheader()
    writer.writerows(asset_data)

# Asset Data
