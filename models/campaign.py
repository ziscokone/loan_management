from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class MutualCampaign(models.Model):
    _name = 'mutual.campaign'
    _description = 'Campagne de Prêt Mutuel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "create_date desc"


    # ======================= CAHMPS DE LA BASE DE DONNEES =================================
    create_date = fields.Date(string='Date création',default=lambda self: fields.Date.today(),readonly=True)
    name = fields.Char(string='Nom de la Campagne', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('open', 'Ouverte'),
        ('suivie', 'Suivi'),
        ('closed', 'Fermée')
    ], default='draft', string='Statut', tracking=True)

    mois = fields.Selection([
        ('janvier', 'Janvier'),
        ('fevrier', 'Février'),
        ('mars', 'Mars'),
        ('avril', 'Avril'),
        ('mai', 'Mai'),
        ('juin', 'Juin'),
        ('juillet', 'Juillet'),
        ('aout', 'Août'),
        ('septembre', 'Septembre'),
        ('octobre', 'Octobre'),
        ('novembre', 'Novembre'),
        ('decembre', 'Décembre'),
    ], string='Mois', required=True)
    # BUDGET 
    total_budget = fields.Integer(string='Budget Prévisionnel', default=10000000,required=True, tracking=True) 
    budget_restant = fields.Integer(string='Budget Restant', compute="_compute_budget_restant", store=True, readonly=True,tracking=True)
    budget_depasse = fields.Integer(string='Budget Depassé',readonly=True, tracking=True)

    description = fields.Text(string="Description", tracking=True)
    responsable = fields.Char(string="Nom du Responsable", tracking=True)
    post_responsable = fields.Char(string="Poste du Responsable", tracking=True)


    # Information sur les responsables a contacter en cas d'informations suplementaires
    responsable_1 = fields.Char(string="Responsable 1", readonly=True)
    contact_responsable_1 = fields.Integer(string="Contact Responsable 1", readonly=True)

    responsable_2 = fields.Char(string="Responsable 2", readonly=True)
    contact_responsable_2 = fields.Integer(string="Contact Responsable 2", readonly=True)

    responsable_3 = fields.Char(string="Responsable 3", readonly=True)
    contact_responsable_3 = fields.Integer(string="Contact Responsable 3", readonly=True)

    responsable_4 = fields.Char(string="Responsable 4", readonly=True)
    contact_responsable_4 = fields.Integer(string="Contact Responsable 4", readonly=True)
    # ====================== ACTIONS =================================================

    #Ouvrir une campagne : Une et une seule campagne reste ouverte
    def action_open_campaign(self):
        """Ouvre la campagne si elle est en brouillon."""
        # Vérifie s'il existe déjà une campagne ouverte
        existing_open_campaign = self.search([
            ('state', '=', 'open'),
            ('id', '!=', self.id)  # Exclut la campagne actuelle
        ], limit=1)
        
        if existing_open_campaign:
            raise ValidationError(
                f"Impossible d'ouvrir cette campagne car la campagne '{existing_open_campaign.name}' "
                f"est déjà ouverte. Veuillez d'abord clôturer la campagne en cours."
            )
        
        for campaign in self:
            if campaign.state == 'draft':
                campaign.state = 'open'
                
                # Création du message toast
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ouverture de campagne',
                        'message': f'La campagne {campaign.name} est ouverte.',
                        'type': 'success',  # Types possibles : success, warning, danger, info
                        'sticky': False,  # False = temporaire, True = permanent
                        'next': {'type': 'ir.actions.act_window_close'},
                        'duration': 5000,  # Durée en millisecondes (5 secondes)
                    }
                }
    

    # ACTION DE SUIVIE D'UNE CAMPAGNE 
    def action_suivie_campaign(self):
        for campaign in self:
            if campaign.state == 'open':
                # Vérifie s'il existe déjà une campagne en suivi
                existing_suivie_campaign = self.search([
                    ('state', '=', 'suivie'),
                    ('id', '!=', campaign.id)
                ], limit=1)
                
                if existing_suivie_campaign:
                    raise ValidationError(
                        f"Impossible de mettre cette campagne en suivi car la campagne '{existing_suivie_campaign.name}' "
                        f"est déjà en cours de suivi. Veuillez d'abord clôturer la campagne en suivi."
                    )
                
                campaign.state = 'suivie'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Suivi',
                        'message': f'La campagne {campaign.name} est en état de suivi',
                        'type': 'warning',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                        'duration': 5000,
                    }
                }
                

    # Clôturer une campagne
    def action_close_campaign(self):
        """Clôture la campagne si elle est ouverte."""
        for campaign in self:
            if campaign.state == 'suivie':
                campaign.state = 'closed'
                # Création du message toast
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Fermeture de campagne',
                        'message': f'La campagne {campaign.name} Clôturée.',
                        'type': 'danger',  # Types possibles : success, warning, danger, info
                        'sticky': False,  # False = temporaire, True = permanent
                        'next': {'type': 'ir.actions.act_window_close'},
                        'duration': 5000,  # Durée en millisecondes (5 secondes)
                    }
                }


    # AFFECTER LA VALEUR DU BUDGET PREVISIONNEL PAR DEFAUT AU BUDGET RESTANT 
    @api.depends('total_budget')
    def _compute_budget_restant(self):
        for record in self:
            if not record.budget_restant:  # Ne met à jour que si budget_restant est vide
                record.budget_restant = record.total_budget





    # RECUPERER LES INFORMATIONS DES REPSONSABLE QUI DOIVENT FIGURER SUR LE TEMPLATE MAIL 
    @api.model
    def create(self, vals):
        """
        Lorsqu'une nouvelle campagne est créée, récupérer les valeurs de 'paa.config'.
        """
        config = self.env['mapaa.config'].search([], limit=1)  # Récupère la config (une seule instance)
        if config:
            vals.update({
                'responsable_1': config.responsable_1,
                'contact_responsable_1': config.contact_responsable_1,
                'responsable_2': config.responsable_2,
                'contact_responsable_2': config.contact_responsable_2,
                'responsable_3': config.responsable_3,
                'contact_responsable_3': config.contact_responsable_3,
                'responsable_4': config.responsable_4,
                'contact_responsable_4': config.contact_responsable_4,
            })
        return super(MutualCampaign, self).create(vals)