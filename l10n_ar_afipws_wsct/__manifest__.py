# -*- coding: utf-8 -*-
{
    'name': "l10n_ar_afipws_wsct",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Mr Blitz",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 
        'product', 
        'account', 
        'l10n_ar', 
        'l10n_ar_afipws', 
        'l10n_ar_afipws_fe',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_category_view.xml',
        'views/account_move_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

