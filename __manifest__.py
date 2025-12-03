{
    'name': 'Website Slides Adaptive Learning',
    'version': '1.0',
    'category': 'Website/eLearning',
    'summary': 'Extensión adaptativa para el módulo de eLearning',
    'description': """Capacidades adaptativas para website_slides""",
    'author': 'Tu Nombre',
    'website': 'https://www.tuwebsite.com',
    'depends': ['website_slides'],
    'data': [
        'security/ir.model.access.csv',
        'views/slide_views.xml',
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
