{
    'name': 'Gestion de Prêt Scolaire',
    'version': '1.0',
    'category': 'Education',
    'sequence': -1,
    'summary': 'Gestion des prêts scolaires avec campagnes et validations.',
        'description': """
            Ce module permet de gérer les prêts scolaires :
            - Création de campagnes sur une période définie.
            - Soumission de demandes par les utilisateurs depuis le site web.
            - Validation ou rejet des demandes par un comité.
            - Suivie des demandes de prêts depuis le site web
        """,
    'author': 'KONE Zissongui Soumaila - 07.07.66.55.40',
    'depends': ['base', 'website', 'mail'],
    'data': [

        'data/data.xml',  
        'data/mail_template.xml', 
        'data/validation_email_template.xml', 
        'data/versement_notification_template.xml', 

        # 'reports/loan_recap_report.xml',

        'views/reversement_views.xml',  
        'views/ligne_versement.xml',  
        'views/loan_campaign_views.xml',  
        'views/loan_application_views.xml',  
        'views/campagne_web_template.xml',  
        'views/demande_pret_web_template.xml',  
        'views/demande_success_template.xml',  
        'views/loan_validation_views.xml',  
        'views/suivie_demande_web_template.xml',  
        'views/employee_views.xml',  
        'views/comite_validation_views.xml',  
        'security/groups_security.xml', 
        'views/direction_employe_views.xml',  
        'views/campaign_error_templates.xml',  
        'views/loan_preview.xml',  
        'views/paa_config_views.xml',  
        'views/dashboard_pret_scolaire_views.xml',  
    ],
    'assets': {
        'web.assets_backend': [


            'loan_management/static/src/css/bordure_input.css',
            'loan_management/static/src/css/custom_colors.css',
            'loan_management/static/src/css/custom_list_view.css',
            'loan_management/static/src/css/custom_modal.css',
            
            # 'loan_management/static/src/js/separateur.js', 
            # 'loan_management/static/src/xml/thousands_separator.xml', 

            # 'loan_management/static/src/components/dashboard/loan_dashboard.js',
            # 'loan_management/static/src/components/dashboard/loan_dashboard.xml',
            # 'loan_management/static/src/xml/thousands_separator.xml',

            # Fichiers des composents employées
            # 'loan_management/static/src/components/employe/employee_list.xml',
            # 'loan_management/static/src/components/employe/employee_list.js',
            # 'loan_management/static/src/components/employe/employee_list.scss',

        ],

        # 'web.assets_backend': [
        #     'loan_management/static/src/js/employee_search.js',
        #     'loan_management/static/src/xml/employee_search.xml',
        # ],

    },
    'controllers': [
        'controllers/main.py', 
        # 'controllers/download.py', 
    ],
    'images': ['static/description/icon.png'],  # Chemin vers l'icône du module
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
