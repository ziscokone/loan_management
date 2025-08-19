{
    'name': 'Gestion de Prêt Mutuel',
    'version': '1.0',
    'category': 'Finance',
    'sequence': -1,
    'summary': 'Gestion des prêts mutuels du Port Autonome d\' Abidjan.',
        'description': """
            Ce module permet de gérer les prêts mutuels :
            - Création de campagnes sur une période définie.
            - Soumission de demandes par les utilisateurs depuis le site web.
            - Validation ou rejet des demandes par les acteurs.
        """,
    'author': 'KONE Zissongui Soumaila - 07.07.66.55.40',
    'depends': ['base', 'website', 'mail'],
    # 'depends': ['base', 'website', 'mail'],
    'data': [
        'security/groups_security.xml', 

        # SEQUENCES ET MAILS 
        'data/data.xml',  
        'data/mail_template.xml',
        'data/mail_template_inscription.xml',
        'data/mail_rejet.xml',
        'data/mail_check_withdrawal.xml',

        'views/mutual_campaign.xml',  
        'views/loan_mutual_views.xml',  
        'views/employee_views.xml',  
        # 'views/demandes_validation_se.xml',  
        'views/demande_pret_web_template.xml',  
        'views/demande_success_template.xml',  
        'views/dashboard_mutual.xml',  
        'views/ligne_versement.xml',  
        'views/mapaa_config_views.xml',  
        'views/direction_employe_views.xml',  
        'views/campaign_error_templates.xml',  
        'views/loan_preview.xml',  
        'views/versement_mutual_views.xml',  
    ],

    'assets': {
        'web.assets_backend': [
            'loan_mutual/static/src/css/bordure_input.css',
            'loan_mutual/static/src/css/custom_colors.css',
            'loan_mutual/static/src/css/custom_list_view.css',
            'loan_mutual/static/src/css/custom_modal.css',
        ],
    },

    'controllers': [
        'controllers/main.py', 
    ],

    'images': ['static/description/icon.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
