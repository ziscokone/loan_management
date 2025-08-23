from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging
import re

_logger = logging.getLogger(__name__)


class LoanApplication(models.Model):
    _name = 'loan.application'
    _description = 'Demande de Prêt Scolaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "reference"
    _order = "create_date desc"


    # Champs de la demande
    reference = fields.Char(string='Réference', readonly=True, default='/')
    amount_requested = fields.Integer(string='Montant Demandé',  tracking=True, readonly="campaign_state == 'suivie'")
    approved_amount = fields.Integer(string="Montant Accordé", tracking=True, readonly="campaign_state == 'suivie'")
    email = fields.Char(string='Email', tracking=True, readonly="campaign_state == 'suivie'")
    telephone = fields.Char(string='Téléphone', tracking=True, readonly="campaign_state == 'suivie'")
    create_date = fields.Datetime(
        string='Date Création',
        default=fields.Datetime.now,
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En Attente'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
    ], default='pending', string='État de la Demande', tracking=True)

    modalite_remboursement = fields.Selection(
        [(str(x), f"{x}") for x in range(3, 11)],
        string="Modalité de Remboursement",
        required=True,
        help="Durée du remboursement en mois.",
        readonly="campaign_state == 'suivie'",
        tracking=True
    )
    
    mensualite = fields.Integer(
        string='Mensualité',
        compute='_compute_mensualite',
        store=True,
        help="Montant mensuel à rembourser",
        tracking=True
    )

    montant_restant = fields.Integer(
        string='Montant Restant',
        compute='_compute_montant_restant',
        default=1,
        store=True,
        help="Montant restant à rembourser",
        tracking=True
    )

    remboursement_status = fields.Selection([
        ('en_cours', 'En cours'),
        ('remboursee', 'Remboursée')
    ], string='Statut Remboursement', 
       compute='_compute_remboursement_status', 
       store=True)

    # ---------------------- RELATIONS ---------------------- 
    campaign_id = fields.Many2one('loan.campaign', string='Campagne', tracking=True, readonly="campaign_state == 'suivie'")
    employee_id = fields.Many2one('paa.employee', string='Matricule', tracking=True, readonly="campaign_state == 'suivie'")
    ligne_versement_ids = fields.One2many('ligne.versement', 'loan_application_id')

    employee_loan_history_ids = fields.One2many(
        'loan.application', 
        compute='_compute_employee_loan_history',
        string="Autres prêts de l'employé"
    )

    # Infos Campagne
    campaign_state = fields.Selection(related='campaign_id.state', string='Statut de la Campagne', store=True, readonly=True)

    # Informations sur les responsables qui auront les contacts sur le template mail de confrmation 
    responsable_1 = fields.Char(related="campaign_id.responsable_1", store=True, invisible=True)
    responsable_2 = fields.Char(related="campaign_id.responsable_2", store=True, invisible=True)
    responsable_3 = fields.Char(related="campaign_id.responsable_3", store=True, invisible=True)

    contact_responsable_1 = fields.Integer(related="campaign_id.contact_responsable_1", store=True, invisible=True)
    contact_responsable_2 = fields.Integer(related="campaign_id.contact_responsable_2", store=True, invisible=True)
    contact_responsable_3 = fields.Integer(related="campaign_id.contact_responsable_3", store=True, invisible=True)

    # Infos Employé (readonly=True ajouté pour éviter modification)
    matricule = fields.Char(string='Matricule', size=10, tracking=True, related="employee_id.matricule", store=True, readonly=True)
    nom = fields.Char(string='Nom', size=50, tracking=True, related="employee_id.name", store=True, readonly=True)
    prenoms = fields.Char(string='Prénoms', tracking=True, related="employee_id.prenoms", store=True, readonly=True)
    age = fields.Integer(string="Âge", related="employee_id.age", store=True, readonly=True)
    direction = fields.Char(string="Direction", tracking=True, related="employee_id.direction.name", store=True, readonly=True)
    typecategorie = fields.Char(string='Catégorie', tracking=True, related="employee_id.typecat", store=True, readonly=True)
    sexe = fields.Selection([('masculin', 'Masculin'), ('feminin', 'Féminin')], string='Sexe', tracking=True, related="employee_id.sexe", store=True, readonly=True)
    anciennete = fields.Char(string='Ancienneté', related="employee_id.anciennete_employe_paa", store=True, readonly=True)

    fields_readonly = fields.Boolean(
        string='Champs en lecture seule',
        compute='_compute_readonly_fields',
        invisible=True,
        store=False,
    )

    # ---------------------------------------------- MÉTHODES ------------------------------------------------------ 

    # Fonction pour empêcher la modification  des champs  quand la campagne passe en suivi
    @api.depends('campaign_state')
    def _compute_readonly_fields(self):
        """Calculer si les champs doivent être en lecture seule selon l'état de la campagne."""
        for record in self:
            record.fields_readonly = record.campaign_state == 'suivie'


    @api.depends('employee_id')
    def _compute_employee_loan_history(self):
        for record in self:
            if record.employee_id:
                # Récupérer toutes les demandes de prêt de l'employé, à l'exception de la demande actuelle
                # Utilisation de _origin.id pour les nouveaux enregistrements
                domain = [('employee_id', '=', record.employee_id.id)]
                
                # Vérifier si l'enregistrement a déjà un ID dans la base de données
                if record.id and isinstance(record.id, int):
                    domain.append(('id', '!=', record.id))
                elif record._origin and record._origin.id:
                    domain.append(('id', '!=', record._origin.id))
                    
                record.employee_loan_history_ids = self.search(domain)
            else:
                record.employee_loan_history_ids = False


    def action_validate(self):
        """Valider la demande si la campagne est en mode validation."""
        self.ensure_one()
        if self.campaign_state != 'validation':
            raise UserError("L'action ne peut être réalisée que si le statut de la campagne est en mode validation.")
        return {
            'name': 'Validation de la demande',
            'type': 'ir.actions.act_window',
            'res_model': 'loan.validation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': self._name,
            }
        }


    def action_reject(self):
        """Rejeter la demande si la campagne est en mode validation."""
        if self.campaign_state != 'validation':
            raise UserError("L'action ne peut être réalisée que si le statut de la campagne est 'validation'.")
        for record in self:
            if record.state == 'pending':
                record.state = 'rejected'


    # Génération de sequence lors de la création d'un enregistrement et verifie si une demande existe déjà pour la même campagne, il écrase l'ancienne demande
    @api.model
    def create(self, vals):
        """Générer la référence de la demande et empêcher les doublons"""
        
        # Vérifier s'il existe déjà une demande pour cet employé et cette campagne
        if vals.get('employee_id') and vals.get('campaign_id'):
            existing_loan = self.search([
                ('employee_id', '=', vals.get('employee_id')),
                ('campaign_id', '=', vals.get('campaign_id'))
            ], limit=1)
            
            if existing_loan:
                # Mettre à jour l'enregistrement existant au lieu de créer un nouveau
                _logger.info(
                    "Demande existante trouvée (ID: %s) pour l'employé %s et la campagne %s. Mise à jour...", 
                    existing_loan.id, 
                    vals.get('employee_id'), 
                    vals.get('campaign_id')
                )
                
                # Supprimer les champs qui ne doivent pas être mis à jour
                update_vals = vals.copy()
                update_vals.pop('employee_id', None)  # Ne pas changer l'employé
                update_vals.pop('campaign_id', None)  # Ne pas changer la campagne
                
                # Garder la référence existante si pas de nouvelle référence
                if 'reference' not in update_vals or update_vals.get('reference') == '/':
                    update_vals.pop('reference', None)
                
                existing_loan.write(update_vals)
                return existing_loan
        
        # Si aucun doublon, créer normalement avec génération de référence
        if vals.get('reference', '/') == '/':
            vals['reference'] = self.env['ir.sequence'].next_by_code('loan.application')
        
        return super(LoanApplication, self).create(vals)



    # CALCUL DE LA MENSUALITE 
    @api.depends('amount_requested', 'approved_amount', 'modalite_remboursement')
    def _compute_mensualite(self):
        """Calculer la mensualité en fonction du montant accordé (priorité) ou demandé et de la durée."""
        for record in self:
            if record.modalite_remboursement:
                # Prioriser le montant accordé s'il est défini, sinon utiliser le montant demandé
                montant_base = record.approved_amount if record.approved_amount else record.amount_requested
                if montant_base:
                    record.mensualite = int(montant_base / int(record.modalite_remboursement))
                else:
                    record.mensualite = 0
            else:
                record.mensualite = 0



    @api.onchange('approved_amount')
    def _onchange_approved_amount(self):
        """Recalculer la mensualité quand le montant accordé change."""
        for record in self:
            if record.approved_amount < 0:
                raise ValidationError("Le montant accordé doit être strictement positif.")
            
            if record.approved_amount > record.amount_requested:
                record.approved_amount = record.amount_requested
                raise ValidationError("Le montant accordé ne peut pas dépasser le montant demandé.")


    # PAR DEFAUT ATTRIBUER LE MONTANT DEMANDE AU MONTANT ACCORDE 
    # @api.onchange('approved_amount')
    # def _compute_amount_requested(self):
    #     amount_approved_2 = 0
    #     for record in self:
    #         record.montant_restant = record.approved_amount
    #         amount_approved_2 = record.approved_amount
    #         if record.modalite_remboursement and amount_approved_2:
    #             record.mensualite = int(amount_approved_2 / int(record.modalite_remboursement))
    #         if amount_approved_2 == 0:
    #             record.mensualite = 0



    # FONCTION DE CALCUL DU MONTANT RESTANT A REMBOURSER EN FONCTION DES VERSEMENTS EFFECTUER 
    @api.depends('approved_amount', 'amount_requested', 'ligne_versement_ids', 'ligne_versement_ids.montant_paye')
    def _compute_montant_restant(self):
        """
        Calculer le montant restant en déduisant la somme des versements 
        du montant accordé (priorité) ou du montant demandé
        """
        for record in self:
            total_verse = sum(record.ligne_versement_ids.mapped('montant_paye'))
            # Utiliser le montant accordé s'il est défini, sinon le montant demandé
            montant_base = record.approved_amount if record.approved_amount else record.amount_requested
            montant_restant = montant_base - total_verse

            record.montant_restant = montant_restant if montant_restant > 0 else 0
            
            # Empêcher de nouveaux paiements si le montant restant est 0
            if record.montant_restant == 0:
                for ligne in record.ligne_versement_ids:
                    if not ligne.is_existing:  # Ajoute un champ pour identifier les nouveaux paiements
                        ligne.montant_paye = 0

# ---------------------------------------------------------------------------------------------------------
    # VALIDATION DU CHAMPS EMAIL 
    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if record.email:
                # Vérification que l'email contient des caractères avant et après le '@'
                pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                if not re.match(pattern, record.email):
                    raise ValidationError(_("L'email doit contenir un '@' et un domaine valide (ex: exemple@gmail.com)."))


    # VALIDATION DES CHAMPS  : Coupe le surplus sur les numéros quand on dépasse 10 chiffres
    @api.onchange('telephone')
    def _onchange_telephone(self):
        """ Tronque le numéro à 10 chiffres dès la saisie """
        if self.telephone:
            self.telephone = self.telephone[:10] 
# ---------------------------------------------------------------------------------------------------------

    # AFFIHCER DES RUBANS SUR LES DEMANDES 
    @api.depends('montant_restant')
    def _compute_remboursement_status(self):
        for record in self:
            if record.montant_restant == 0:
                record.remboursement_status = 'remboursee'
            else:
                record.remboursement_status = 'en_cours'



# ENVOIE DE MAIL DE CONFIRMATION 
    def send_confirmation_email(self):
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de confirmation pour la demande %s", self.reference)
            
            template = self.env.ref('loan_management.loan_confirmation_email_template', raise_if_not_found=True)
            if not template:
                _logger.error("Template d'email non trouvé pour la demande %s", self.reference)
                return False
                
            if not self.email:
                _logger.error("Aucune adresse email fournie pour la demande %s", self.reference)
                return False

            # Définir l'adresse email d'envoi
            company_email = self.env.company.email or 'noreply@paa.com'  # Email par défaut
            
            _logger.info("Informations d'envoi:")
            _logger.info("- Template ID: %s", template.id)
            _logger.info("- Application ID: %s", self.id)
            _logger.info("- Email destinataire: %s", self.email)
            _logger.info("- Email expéditeur: %s", company_email)

            try:
                mail_id = template.send_mail(
                    self.id, 
                    force_send=True,
                    email_values={
                        'email_to': self.email,
                        'email_from': company_email
                    }
                )
                
                _logger.info(
                    "Mail envoyé avec succès pour la demande %s (ID mail: %s)", 
                    self.reference, 
                    mail_id
                )
                return True
                
            except Exception as mail_error:
                _logger.error(
                    "Erreur spécifique d'envoi de mail: %s", 
                    str(mail_error),
                    exc_info=True
                )
                return False
                
        except Exception as e:
            _logger.error(
                "Erreur générale lors de l'envoi du mail pour la demande %s: %s", 
                self.reference, 
                str(e),
                exc_info=True
            )
            return False


# NOTIFICATION PAR MAIL : VALIDATION D'UNE DEMANDE 
    def send_validation_email(self):
        """Envoyer un email de notification pour informer l'agent du montant accordé."""
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de validation pour la demande %s", self.reference)
            
            # Utiliser un nouveau template pour la validation
            template = self.env.ref('loan_management.loan_validation_email_template', raise_if_not_found=True)
            if not template:
                _logger.error("Template d'email de validation non trouvé pour la demande %s", self.reference)
                return False
                
            if not self.email:
                _logger.error("Aucune adresse email fournie pour la demande %s", self.reference)
                return False

            company_email = self.env.company.email or 'noreply@paa.com'
            
            _logger.info("Informations d'envoi du mail de validation:")
            _logger.info("- Template ID: %s", template.id)
            _logger.info("- Application ID: %s", self.id)
            _logger.info("- Email destinataire: %s", self.email)
            _logger.info("- Montant accordé: %s", self.approved_amount)

            # mail_id = template.send_mail(
            #     self.id, 
            #     force_send=True,
            #     email_values={
            #         'email_to': self.email,
            #         'email_from': company_email,
            #         'subject': f'Validation de votre demande de prêt {self.reference}',
            #     }
            # )
            
            _logger.info(
                "Mail de validation envoyé avec succès pour la demande %s (ID mail: %s)", 
                self.reference, 
                # mail_id
            )
            return True
                
        except Exception as e:
            _logger.error(
                "Erreur lors de l'envoi du mail de validation pour la demande %s: %s", 
                self.reference, 
                str(e),
                exc_info=True
            )
            return False


# -----------------------------------------------------------------------------------------------------------------------------

    # CONTRAINTE DE SAISIE DES NOMBRES NEGATIF 
    @api.onchange('amount_requested')
    def _check_amount_requested(self):
        for record in self:
            if record.amount_requested < 0:
                raise ValidationError("Le montant demandé doit être strictement positif.")

            if record.amount_requested >= 10000000:
                record.amount_requested = 0
                raise ValidationError("Le montant montant demandé ne peut pas dépasser 10 000 000 FCFA.")

    @api.constrains('approved_amount')
    def _check_approved_amount(self):
        for record in self:
            if record.approved_amount > record.amount_requested:
                raise ValidationError("Le montant accordé ne peut pas dépasser le montant demandé !")


    @api.onchange('approved_amount')
    def _check_amount_approved(self):
        for record in self:
            if record.approved_amount < 0 :
                raise ValidationError("Le montant accordé doit être strictement positif.")


    @api.onchange('approved_amount')
    def _verify_amount_approved(self):
        for record in self:
            if record.approved_amount > record.amount_requested :
                record.approved_amount = record.amount_requested 
                raise ValidationError("Le montant accordé ne peut pas depasser le montant demandé.")
# -----------------------------------------------------------------------------------------------------------------------------

    @api.model
    def get_amounts_stats(self, domain=None):
        """Obtenir le total des montants demandés et approuvés selon le domaine fourni."""
        if domain is None:
            domain = []
            
        applications = self.search(domain)
        
        return {
            'total_requested': sum(applications.mapped('amount_requested')),
            'total_approved': sum(applications.mapped('approved_amount')),
        }




        