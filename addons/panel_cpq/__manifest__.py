{
    'name': 'Panel CPQ Demo',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Demo CPQ configurator for acrylic panel pricing, injecting a priced line into Sales quotations.',
    'author': 'Vence',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/panel_cpq_sequence.xml',
        'views/panel_cpq_instance_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
