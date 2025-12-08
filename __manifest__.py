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
        
        # Vistas existentes
        'views/slide_views.xml',
        'views/student_dashboard.xml',
        'views/teacher_dashboard.xml',
        
        # Nuevas vistas de modelos backend
        'views/historial_progreso_views.xml',
        'views/ruta_aprendizaje_views.xml',
        'views/arals_dashboard_views.xml',
        
        # Plantillas frontend QWeb
        'views/arals_frontend_templates.xml',
        
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'web/static/lib/Chart/Chart.js',
            'tesis_website_slide_arals/static/src/js/arals_frontend.js',
            'tesis_website_slide_arals/static/src/css/arals_frontend.css',
        ],
        'web.assets_backend': [
            'tesis_website_slide_arals/static/src/css/arals_frontend.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
