from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
from datetime import date
# Ajout de logs pour l'envoi des emails
import logging

# Création d'un logger spécifique
_logger = logging.getLogger(__name__)


class LoanCampaign(models.Model):
    _name = 'loan.campaign'
    _description = 'Campagne de Prêt Scolaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "create_date desc"

    create_date = fields.Date(string='Date création',default=lambda self: fields.Date.today(),readonly=True)
    name = fields.Char(string='Nom de la Campagne', required=True, tracking=True)
    start_date = fields.Date(string='Date de Début', required=True, tracking=True)
    end_date = fields.Date(string='Date de Fin', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('open', 'Ouverte'),
        ('validation', 'Validation'),
        ('suivie', 'Suivi'),
        ('closed', 'Fermée')
    ], default='draft', string='Statut', tracking=True)
    
    total_budget = fields.Integer(string='Budget Prévisionnel', required=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        compute='_default_currency',
        required=True
    )

    budget_restant = fields.Integer(string="Budget Restant", readonly=True, compute='_compute_budget_restant', store=True)
    requested_amount = fields.Integer(string="Montant des demandes", readonly=True)
    validated_amount = fields.Integer(string="Montant validé", readonly=True)
    description = fields.Text(string="Descripion", tracking=True)

    # Information sur le responsable de la campagne
    responsable = fields.Char(string="Nom du Responsable", tracking=True)
    post_responsable = fields.Char(string="Poste du Responsable", tracking=True)


    # Information sur les responsables a contacter en cas d'informations suplementaires
    responsable_1 = fields.Char(string="Responsable 1", readonly=True)
    contact_responsable_1 = fields.Integer(string="Contact Responsable 1", readonly=True)

    responsable_2 = fields.Char(string="Responsable 2", readonly=True)
    contact_responsable_2 = fields.Integer(string="Contact Responsable 2", readonly=True)

    responsable_3 = fields.Char(string="Responsable 3", readonly=True)
    contact_responsable_3 = fields.Integer(string="Contact Responsable 3", readonly=True)

    # ====================== COMPUTE =================================================
    @api.depends('total_budget')
    def _compute_budget_restant(self):
        for campaign in self:
            if campaign.state == 'draft':
                campaign.budget_restant = campaign.total_budget
            # Si la campagne n'est pas en brouillon, on garde le budget_restant actuel
            # car il a pu être modifié par les validations de prêts

    # ====================== CONSTRAINS =================================================
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for campaign in self:
            if campaign.start_date > campaign.end_date:
                raise ValidationError("La date de début doit être avant la date de fin")
            
            if campaign.start_date and campaign.start_date < date.today():
                raise ValidationError("La date de début est déjà passée. Veuillez renseigner une date à venir.")

    # ====================== ACTIONS =================================================
    # EMPECHER LA CREATION D'UNE DEMANDE SI LE  MONTANT 
    @api.constrains('total_budget')
    def _check_total_budget(self):
        for record in self:
            if record.total_budget == 0:
                raise ValidationError(_("Le budget prévisionnel ne peut pas être égal à 0."))


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
                campaign.budget_restant = campaign.total_budget  # Initialise le budget restant
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


    # Action pour lancer le comité de validation
    def action_validate_campaign(self):
        for campaign in self:
            if campaign.state == 'open':
                # Vérifie s'il existe déjà une campagne en validation
                existing_validation_campaign = self.search([
                    ('state', '=', 'validation'),
                    ('id', '!=', campaign.id)
                ], limit=1)
                
                if existing_validation_campaign:
                    raise ValidationError(
                        f"Impossible de mettre cette campagne en validation car la campagne {existing_validation_campaign.name} "
                        f"est déjà en cours de validation. Veuillez d'abord terminer la validation de la campagne en cours."
                    )
                
                # Créer un comité de validation associé à cette campagne
                comite_validation = self.env['comite.validation'].create({
                    'name': f"Comité - {campaign.name}",  # Nom du comité
                    'campaign_id': campaign.id,  # Campagne associée
                })
                
                # Mettre à jour l'état de la campagne
                campaign.state = 'validation'
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Validation en cours',
                        'message': f'La campagne {campaign.name} est en cours de validation. Un comité de validation a été créé : {comite_validation.name}.',
                        'type': 'info',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                        'duration': 5000,
                    }
                }




    # PASSER UNE CAMPAGNE EN ETAT SUIVI 
    def action_suivie_campaign(self):
        for campaign in self:
            if campaign.state == 'validation':
                # Vérification des campagnes existantes...
                existing_suivie_campaign = self.search([
                    ('state', '=', 'suivie'),
                    ('id', '!=', campaign.id)
                ], limit=1)
                
                if existing_suivie_campaign:
                    raise ValidationError(
                        f"Impossible de mettre cette campagne en suivi car la campagne '{existing_suivie_campaign.name}' "
                        f"est déjà en cours de suivi. Veuillez d'abord clôturer la campagne en suivi."
                    )
            
            # Log au début du processus
            _logger.info(f"Début du processus d'envoi d'emails pour la campagne: {campaign.name} (ID: {campaign.id})")
            
            # Rechercher toutes les demandes liées à cette campagne
            loan_applications = self.env['loan.application'].search([('campaign_id', '=', campaign.id)])
            _logger.info(f"Nombre de demandes trouvées: {len(loan_applications)}")
            
            # Recupérer le mail de l'entreprise 
            company_email = self.env.company.email or 'noreply@paa.com'
            
            # Récupérer le modèle d'email
            template = self.env.ref('loan_management.loan_validation_email_template', raise_if_not_found=False)
            
            if not template:
                _logger.error("Template d'email non trouvé: loan_management.loan_validation_email_template")
            else:
                _logger.info(f"Template d'email trouvé: {template.name} (ID: {template.id})")
                
                # Compteurs pour les statistiques
                sent_count = 0
                error_count = 0
                no_email_count = 0
                
                # Envoyer un email à chaque demandeur
                if loan_applications:
                    for application in loan_applications:
                        # On vérifie si le demandeur a un email
                        if application.email:
                            try:
                                # Envoyer l'email
                                _logger.info(f"Tentative d'envoi d'email à {application.email} pour la demande ID: {application.id}")
                                mail_id = template.send_mail(
                                    application.id,
                                    force_send=True,
                                    email_values={
                                        'email_to': application.email,
                                        'email_from': company_email,
                                        }
                                )
                                sent_count += 1
                                _logger.info(f"Email envoyé avec succès (mail_id: {mail_id}) à {application.email}")
                            except Exception as e:
                                error_count += 1
                                _logger.error(f"Erreur lors de l'envoi de l'email à {application.email}: {str(e)}")
                        else:
                            no_email_count += 1
                            _logger.warning(f"Pas d'email trouvé pour la demande ID: {application.id}")
                    
                    # Log des statistiques finales
                    _logger.info(f"Statistiques d'envoi pour la campagne {campaign.name}:")
                    _logger.info(f"- Emails envoyés avec succès: {sent_count}")
                    _logger.info(f"- Emails avec erreur: {error_count}")
                    _logger.info(f"- Demandes sans email: {no_email_count}")
                else:
                    _logger.warning(f"Aucune demande trouvée pour la campagne {campaign.name} (ID: {campaign.id})")
            
            # Mettre à jour le statut de la campagne
            campaign.state = 'suivie'
            _logger.info(f"Campagne {campaign.name} (ID: {campaign.id}) mise en état de suivi")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Suivi',
                    'message': f'La campagne {campaign.name} est en état de suivi. {sent_count} email(s) envoyé(s) aux demandeurs.',
                    'type': 'warning',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                    'duration': 5000,
                }
            }
             

    # Fermeture automatique des campagnes si la période definie est passée
    @api.model
    def check_and_close_campaigns(self):
        """Cron Job: Ferme automatiquement les campagnes dont la date de fin est passée."""
        today = fields.Date.today()
        campaigns_to_close = self.search([('state', '=', 'open'), ('end_date', '<', today)])
        for campaign in campaigns_to_close:
            campaign.state = 'closed'




    # RECUPERER LES INFORMATIONS DES REPSONSABLE QUI DOIVENT FIGURER SUR LE TEMPLATE MAIL 
    @api.model
    def create(self, vals):
        """
        Lorsqu'une nouvelle campagne est créée, récupérer les valeurs de 'paa.config'.
        """
        config = self.env['paa.config'].search([], limit=1)  # Récupère la config (une seule instance)
        if config:
            vals.update({
                'responsable_1': config.responsable_1,
                'contact_responsable_1': config.contact_responsable_1,
                'responsable_2': config.responsable_2,
                'contact_responsable_2': config.contact_responsable_2,
                'responsable_3': config.responsable_3,
                'contact_responsable_3': config.contact_responsable_3,
            })
        return super(LoanCampaign, self).create(vals)


    def _default_currency(self):
        return self.env.company.currency_id