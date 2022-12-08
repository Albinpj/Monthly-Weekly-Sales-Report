{
    'name': 'Sale Report',
    'version': '15.0.1.0',
    'sequence': -3001,
    'category': 'Weekly Monthly Sale Report',
    'summary': 'Weekly Monthly Sale Report',
    'application': True,
    'depends': [
        'base',
        'sale_management',
        'contacts',
        'mail',
    ],
    'data': [
        'data/sale_sheduled_action.xml',
        'views/sale_configaration.xml',
        'report/sale_report.xml',
        'report/sale_report_template.xml',
    ],

}
