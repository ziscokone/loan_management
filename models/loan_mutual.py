from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError
from num2words import num2words # Bibliothèque qui traquit les chiffres en lettres
from dateutil.relativedelta import relativedelta
import re
import logging
_logger = logging.getLogger(__name__)


class LoanMutual(models.Model):
    _name = 'loan.mutual'
    _description = 'Demande de Prêt Mutuel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "reference"
    _order = "create_date asc"


    # Champs de la demande
    reference = fields.Char(string='Réference', readonly=True, default='/')

    amount_requested = fields.Integer(string='Montant Demandé', required=True, tracking=True)
    amount_to_be_refunded = fields.Integer(string='Montant à Remboursé', readonly=True, compute="_compute_file_fees_amount_requested", store=True, tracking=True)
    amount_to_be_refunded_ps = fields.Integer(string='Montant à Remboursé', readonly=True, compute="_compute_file_fees_approved_amount", store=True, tracking=True)
    amount_requested_words = fields.Char(string="Montant en lettres", compute="_compute_amount_word", readonly=True, store=True)

    file_fees = fields.Integer(string='Frais Dossier', store=True)
    agent_agree = fields.Boolean(string='Agent est d\' accord', default=False)

    email = fields.Char(string='Email', tracking=True)
    telephone = fields.Char(string='Téléphone', tracking=True)
    telephone_2 = fields.Char(string='Téléphone 2 ', tracking=True)
    create_date = fields.Datetime(string='Date Création',default=fields.Datetime.now,readonly=True)

    start_date_deduction = fields.Char(string='Mois Début Prélèvement')
    start_date_deduct = fields.Date(string='Date Début Precompte')
    start_date_year_decution = fields.Integer(string='Année Début Precompte', compute='_compute_year', store=True)

    cotite = fields.Binary(string='Quotité (PDF)' , attachment=True)
    piece_identite = fields.Binary(string="Image", attachment=True)

    type_pret = fields.Selection([('credits_express', 'CREDIT EXPRESS'), ('credits_projets', 'CREDIT PROJETS')], default='credits_express', required=True, string ="Type de Prêts")
    demande_exceptionnelle = fields.Boolean(string='Demande Exceptionnelle', tracking=True)
    state = fields.Selection([
        ('pending', 'En Attente'),
        ('in_treatment', 'En Traitement PS'),
        ('se_validation', 'Validation SE'), 
        ('pca_validation', 'Validation PCA'),
        ('approved', 'Approuvé'), 
        ('check_delivery', 'Remise de Chèque'),
        ('check_withdrawn', 'Chèque Retiré'), 
        ('check_cancel', 'Chèque Annulé'),
        ('rejected', 'Rejeté'), 
    ], string='État', default='pending', tracking=True)
    montant_restant = fields.Integer(
        string='Montant Restant',
        compute='_compute_montant_restant',
        default=1,
        store=True,
        help="Montant restant à rembourser",
        tracking=True
    )
    is_on_sale = fields.Boolean(string="Soldé", default=False)

    modalite_remboursement = fields.Selection([(str(x), f"{x} mois") for x in range(1, 11)],string="Modalités de Remboursement",required=True,tracking=True)
    motif_demande = fields.Text(string="Motif de la Demande", tracking=True)

    # INFO SUR LA PERSONNE QUI SOUMET LA DEMANDE AU SERVICE PRET SOCIAUX 
    submitted_by = fields.Many2one('res.users', string='Soumis par', readonly=True)
    submission_date = fields.Datetime(string='Date de Soumission', readonly=True)
    reason_for_check_rejection = fields.Text(string="Motif d'annulation")
    can_edit_secretaire = fields.Boolean(string="Peut éditer la section secretaire",compute="_compute_can_edit_secretaire")


    # INFO COORDONNEES PRET SOCIAUX 
    approved_amount = fields.Integer(string="Montant Accordé", tracking=True, store=True, readonly=False)
    amount_reimbursed = fields.Integer(string="Valeur Réelle du Prêt", tracking=True)
    transferable_portion = fields.Integer(string="Quotité Cessible", tracking=True, default=0)
    mensualite = fields.Integer(string='Mensualité',store=True, compute='_compute_mensualite', tracking=True)
    traitement_date = fields.Datetime(string='Date de Traitement', readonly=True)
    can_edit_mapaa = fields.Boolean(string="Peut éditer la section MA-PAA",compute="_compute_can_edit_mapaa")


    # INFO DU SECRETAIRE EXECUTIF
    loan_granted = fields.Boolean(string='Prêt Accordé', tracking=True)
    loan_not_granted = fields.Boolean(string='Prêt Non Accordé', tracking=True) 
    motif_rejet_readonly = fields.Boolean(string='Motif du Rejet', tracking=True, invisible=True) 
    rejection_reason = fields.Text(string="Motif du rejet", tracking=True)
    reason_for_sending_to_accounting = fields.Text(String="Motif d'envoie à la Comptabilité", readonly=True, tracking=True)
    final_approved_amount = fields.Integer(string="Montant Définitif Accordé" , tracking=True)
    final_approved_amount_update = fields.Boolean(string="Montant Définitif modifié", default=False, compute='_compute_amount_final', store=True)
    amount_to_be_refunded_se = fields.Integer(string='Montant Définitif à Rembourser', readonly=True, compute="_compute_file_fees_final_approved_amount", store=True, tracking=True)
    is_rejection = fields.Boolean(string="Est rejeté", default=False)
    can_edit_se = fields.Boolean(string="Peut éditer la section PCA",compute="_compute_can_edit_se")

    # INFO PCA 
    observation_pca = fields.Text(string="Observations", tracking=True)
    submitted_pca = fields.Many2one('res.users', string='Soumis par', readonly=True)
    submission_date_pca = fields.Datetime(string='Date de Validation du PCA', readonly=True)
    approved_amount_pca = fields.Integer(string="Montant Accordé", compute="_compute_amount_final_pca")
    can_edit_pca = fields.Boolean(string="Peut éditer la section PCA",compute="_compute_can_edit_pca")
    amount_to_be_refunded_pca = fields.Integer(string='Montant Définitif à Remboursé', readonly=True, compute="_compute_file_fees_approved_amount_pca", store=True, tracking=True)


    # INFO COMPTABILITE 
    date_emission_cheque = fields.Datetime(string='Date d\'Emission du Chèque', readonly=True)
    check_amount = fields.Integer(string="Montant du Chèque", tracking=True, compute="_compute_check_amount", store=True)
    observation_comptabilite = fields.Text(string="Observations", tracking=True)
    check_number = fields.Integer(string="N° Chèque", tracking=True)
    can_edit_compta = fields.Boolean(string="Peut éditer la section Comptabilité",compute="_compute_can_edit_compta")

    # ---------------------- RELATIONS EMPLOYEE---------------------- 
    employee_id = fields.Many2one('paa.employee', string='Matricule', tracking=True)

    # ---------------------- RELATIONS CAMPAGNE---------------------- 
    campaign_id = fields.Many2one('mutual.campaign', string='Campagne', tracking=True, invisible=True)
    budget_previsionnel = fields.Integer(string='Budget Prévisionnel', size=10, tracking=True, related="campaign_id.total_budget", store=True, readonly=True)
    budget_restant = fields.Integer(string='Budget Prévisionnel', size=10, tracking=True, related="campaign_id.budget_restant", store=True, readonly=True)


    # ---------------------- RELATIONS VERSEMENT ---------------------- 
    ligne_versement_ids = fields.One2many('ligne.versement', 'loan_mutual_id')


    # ---------------------- Champs de Calcul de budget  ---------------------- 
    budget_restant_ps = fields.Integer(string="Montant Retranché PS", default=0, compute="_compute_budget_restant_ps", store=True)
    budget_restant_se = fields.Integer(string="Ajustement Budget SE", default=0, store=True)


    # Infos Employé (readonly=True ajouté pour éviter modification)
    matricule = fields.Char(string='Matricule', size=10, tracking=True, related="employee_id.matricule", store=True, readonly=True)
    nom = fields.Char(string='Nom', size=50, tracking=True, related="employee_id.name", store=True, readonly=True)
    prenoms = fields.Char(string='Prénoms', tracking=True, related="employee_id.prenoms", store=True, readonly=True)
    age = fields.Integer(string="Âge", related="employee_id.age", store=True, readonly=True)
    direction = fields.Char(string="Direction", tracking=True, related="employee_id.direction.name", store=True, readonly=True)
    typecategorie = fields.Char(string='Catégorie', tracking=True, related="employee_id.typecat", store=True, readonly=True)
    sexe = fields.Selection([('masculin', 'Masculin'), ('feminin', 'Féminin')], string='Sexe', tracking=True, related="employee_id.sexe", store=True, readonly=True)
    anciennete = fields.Integer(string='Ancienneté', related="employee_id.anciennete", store=True, readonly=True)


    # Informations sur les responsables qui auront les contacts sur le template mail de confrmation 
    responsable_1 = fields.Char(related="campaign_id.responsable_1", store=True, invisible=True)
    responsable_2 = fields.Char(related="campaign_id.responsable_2", store=True, invisible=True)
    responsable_3 = fields.Char(related="campaign_id.responsable_3", store=True, invisible=True)

    contact_responsable_1 = fields.Integer(related="campaign_id.contact_responsable_1", store=True, invisible=True)
    contact_responsable_2 = fields.Integer(related="campaign_id.contact_responsable_2", store=True, invisible=True)
    contact_responsable_3 = fields.Integer(related="campaign_id.contact_responsable_3", store=True, invisible=True)

    # ================================================== METHODES ===============================================================
    @api.model
    def create(self, vals):
        """Générer la référence de la demande et vérifier les contraintes"""
        if vals.get('reference', '/') == '/':
            vals['reference'] = self.env['ir.sequence'].next_by_code('loan.mutual')

        # AFFECTER LE MONTANT APPROUVER PAR LA COMMISSION PRET AU MONTANT DEFINITF CHEZ LA SE 
        if 'approved_amount' in vals and 'final_approved_amount' not in vals:
            vals['final_approved_amount'] = vals['approved_amount']

        self._check_loan_constraints(vals)
        return super(LoanMutual, self).create(vals)

    def write(self, vals):
        """Vérifier les contraintes lors de la modification"""
        for record in self:
            new_vals = record._convert_to_write(vals)  # Fusionner les valeurs modifiées avec l'existant
            record._check_loan_constraints(new_vals)
        
        return super(LoanMutual, self).write(vals)

    def _check_loan_constraints(self, vals):
        """Vérifie les contraintes sur les prêts"""

        # Si l'enregistrement n'est pas encore sauvegardé (a un ID temporaire)
        if not isinstance(self.id, int):
            return True  # Ignorer les validations pour les nouveaux enregistrements
            
        employee_id = vals.get('employee_id', self.employee_id.id)
        campaign_id = vals.get('campaign_id', self.campaign_id.id)
        demande_exceptionnelle = vals.get('demande_exceptionnelle', self.demande_exceptionnelle)

        if not demande_exceptionnelle:
            if employee_id and campaign_id:
                # Vérifier si l'employé a déjà une demande pour cette campagne
                existing_loan = self.env['loan.mutual'].search([
                    ('employee_id', '=', employee_id),
                    ('campaign_id', '=', campaign_id),
                    ('id', '!=', self.id)  # Exclure l'enregistrement en cours de modification
                ], limit=1)

                if existing_loan:
                    raise ValidationError(_("Vous avez déjà une demande de prêt pour cette campagne."))

                # Vérifier si l'employé a une demande non soldée
                unsettled_loan = self.env['loan.mutual'].search([
                    ('employee_id', '=', employee_id),
                    ('is_on_sale', '=', False),
                    ('montant_restant', '>', 0),
                    ('id', '!=', self.id)  # Exclure l'enregistrement en cours de modification
                ], limit=1)

                if unsettled_loan:
                    montant_formatte = "{:,.0f}".format(unsettled_loan.montant_restant).replace(',', ' ')
                    raise ValidationError(_(
                    "Désolé, vous avez une demande de prêt non soldée.\n"
                    "🔹 Référence: {ref}\n"
                    "💰 Montant restant: {montant} FCFA"
                ).format(ref=unsettled_loan.reference,  montant=montant_formatte))

# -----------------------------------------------------------------------------------------------------------------------------
    # CONTRAINTE DE SAISIE DES NOMBRES NEGATIF 
    @api.onchange('amount_requested')
    def _check_amount_requested(self):
        for record in self:
            if record.amount_requested < 0:
                raise ValidationError("Le montant demandé doit être strictement positif.")


    @api.onchange('approved_amount')
    def _check_amount_approved(self):
        for record in self:
            if record.approved_amount < 0 :
                raise ValidationError("Le montant accordé doit être strictement positif.")

    # RENDRE LE CHAMPS FRAIS DOSSIERS EDITABLE POUR LA SECRETAIRE POUR TOUS FRAIS > 1 500 000
    @api.depends('file_fees')
    def _compute_is_file_fees_editable(self):
        for record in self:
            record.is_file_fees_editable = record.file_fees > 1500000

# -----------------------------------------------------------------------------------------------------------------------------
    # CALCULE DES FRAIS DE DOSSIERS EN FONCTION DU MONTANT DEMANDE 
    @api.depends('amount_requested')
    def _compute_file_fees_amount_requested(self):
        for record in self:
            amount = record.amount_requested or 0
            if amount <= 300000:
                record.file_fees = 10000
            elif amount <= 500000:
                record.file_fees = 15000
            elif amount <= 800000:
                record.file_fees = 20000
            elif amount <= 1000000:
                record.file_fees = 25000
            elif amount <= 2000000:
                record.file_fees = 50000
            else:
                record.file_fees = 75000
            record.amount_to_be_refunded = amount + record.file_fees
            record.approved_amount = record.amount_requested
            record.final_approved_amount = record.amount_requested
            record.approved_amount_pca = record.amount_requested
            record.amount_to_be_refunded_ps = record.amount_to_be_refunded
            record.amount_to_be_refunded_se = record.amount_to_be_refunded
            record.amount_to_be_refunded_pca = record.amount_to_be_refunded


    # CALCUL DES FRAIS DE DOSSIER EN FONCTION DU MONTANT ACCORDE PAR LE PCA : APRES AVOIR TROUVER LA TRANCHE ON RECALCUL LA MENSUALITE ET METTRE A JOUR LE MONTANT RESTANT 
    @api.depends('approved_amount')
    def _compute_file_fees_approved_amount(self):
        for record in self:
            if record.approved_amount and record.approved_amount != record.amount_requested:
                amount = record.approved_amount or 0
                if amount <= 300000:
                    record.file_fees = 10000
                elif amount <= 500000:
                    record.file_fees = 15000
                elif amount <= 800000:
                    record.file_fees = 20000
                elif amount <= 1000000:
                    record.file_fees = 25000
                elif amount <= 2000000:
                    record.file_fees = 50000
                else:
                    record.file_fees = 75000

                record.amount_to_be_refunded_ps = record.approved_amount + record.file_fees
                record.final_approved_amount = record.approved_amount
                record.approved_amount_pca = record.final_approved_amount
                record.montant_restant = record.amount_to_be_refunded_ps
                record.amount_to_be_refunded_se = record.amount_to_be_refunded_ps
                record.amount_to_be_refunded_pca = record.amount_to_be_refunded_ps

                record._compute_mensualite()
            else:
                record._compute_file_fees_amount_requested()


    # CALCUL DES FRAIS DE DOSSIER EN FONCTION DU MONTANT ACCORDE PAR LA SE  : APRES AVOIR TROUVER LA TRANCHE ON RECALCUL LA MENSUALITE ET METTRE A JOUR LE MONTANT RESTANT 
    @api.depends('final_approved_amount')
    def _compute_file_fees_final_approved_amount(self):
        for record in self:
            if record.final_approved_amount and record.final_approved_amount != record.approved_amount:
                amount = record.final_approved_amount or 0
                if amount <= 300000:
                    record.file_fees = 10000
                elif amount <= 500000:
                    record.file_fees = 15000
                elif amount <= 800000:
                    record.file_fees = 20000
                elif amount <= 1000000:
                    record.file_fees = 25000
                elif amount <= 2000000:
                    record.file_fees = 50000
                else:
                    record.file_fees = 75000

                record.amount_to_be_refunded_se = record.final_approved_amount + record.file_fees
                record.approved_amount_pca = record.final_approved_amount
                record.amount_to_be_refunded_pca = record.amount_to_be_refunded_se
                record.montant_restant = record.amount_to_be_refunded_se
                record._compute_mensualite()
            else:
                record.amount_to_be_refunded_se = record.amount_to_be_refunded
                if not (record.approved_amount_pca and record.approved_amount_pca != record.final_approved_amount):
                    record.amount_to_be_refunded_pca = record.amount_to_be_refunded_se


    # CALCUL DES FRAIS DE DOSSIER EN FONCTION DU MONTANT ACCORDE PAR LE PCA : APRES AVOIR TROUVER LA TRANCHE ON RECALCUL LA MENSUALITE ET METTRE A JOUR LE MONTANT RESTANT 
    @api.depends('approved_amount_pca')
    def _compute_file_fees_approved_amount_pca(self):
        for record in self:
            if record.approved_amount_pca and record.approved_amount_pca != record.final_approved_amount:
                amount = record.approved_amount_pca or 0
                if amount <= 300000:
                    record.file_fees = 10000
                elif amount <= 500000:
                    record.file_fees = 15000
                elif amount <= 800000:
                    record.file_fees = 20000
                elif amount <= 1000000:
                    record.file_fees = 25000
                elif amount <= 2000000:
                    record.file_fees = 50000
                else:
                    record.file_fees = 75000
                record.amount_to_be_refunded_pca = record.approved_amount_pca + record.file_fees
                record.montant_restant = record.amount_to_be_refunded_pca
                record._compute_mensualite()
            else:
                record.amount_to_be_refunded_pca = record.amount_to_be_refunded_se or record.amount_to_be_refunded


# ----------------------------------------------------------------------------------------------------------------------------
    # FONCTION DE CALCUL DU MONTANT RESTANT A REMBOURSER EN FONCTION DES VERSEMENTS EFFECTUER 
    @api.depends('amount_to_be_refunded', 'amount_to_be_refunded_se', 'amount_to_be_refunded_pca', 'approved_amount', 'final_approved_amount', 'approved_amount_pca', 'ligne_versement_ids', 'ligne_versement_ids.montant_paye', 'is_on_sale')
    def _compute_montant_restant(self):
        """
        Calculer le montant restant en déduisant la somme des versements
        du montant à rembourser approprié (amount_to_be_refunded, amount_to_be_refunded_se, ou amount_to_be_refunded_pca)
        et empêcher les nouveaux versements si le montant restant est 0.
        """
        for record in self:
            # Choisir le montant de référence
            if record.approved_amount_pca and record.approved_amount_pca != record.final_approved_amount:
                montant_reference = record.amount_to_be_refunded_pca or 0
                _logger.debug(f"Utilisation de amount_to_be_refunded_pca={montant_reference} pour {record.reference}")
            elif record.final_approved_amount and record.final_approved_amount != record.approved_amount:
                montant_reference = record.amount_to_be_refunded_se or 0
                _logger.debug(f"Utilisation de amount_to_be_refunded_se={montant_reference} pour {record.reference}")
            else:
                montant_reference = record.amount_to_be_refunded or 0
                _logger.debug(f"Utilisation de amount_to_be_refunded={montant_reference} pour {record.reference}")

            # Calculer le total des versements
            total_verse = sum(record.ligne_versement_ids.mapped('montant_paye'))

            # Calculer le montant restant
            montant_restant = montant_reference - total_verse
            record.montant_restant = montant_restant if montant_restant > 0 else 0
            _logger.debug(f"Montant restant pour {record.reference}: {record.montant_restant} (référence={montant_reference}, versé={total_verse})")

            # Empêcher de nouveaux paiements si le montant restant est 0
            if record.montant_restant == 0:
                record.is_on_sale = True
                for ligne in record.ligne_versement_ids:
                    if not ligne.is_existing:  # Ajoute un champ pour identifier les nouveaux paiements
                        ligne.montant_paye = 0
            else:
                record.is_on_sale = False
# ----------------------------------------------------------------------------------------------------------------------------

    # METTRE LE MONTANT ACCORDE DANS LE CHAMPS DU MONTANT CHECQUE 
    @api.depends('approved_amount_pca', 'final_approved_amount', 'approved_amount', 'amount_to_be_refunded')
    def _compute_check_amount(self):
        for record in self:
            if record.approved_amount_pca and record.approved_amount_pca != record.final_approved_amount:
                record.check_amount = record.amount_to_be_refunded_pca
            elif record.final_approved_amount and record.final_approved_amount != record.approved_amount:
                record.check_amount = record.amount_to_be_refunded_se
            elif record.approved_amount and record.approved_amount != record.amount_requested:
                record.check_amount = record.amount_to_be_refunded_ps
            else:
                record.check_amount = record.amount_to_be_refunded
            if record.approved_amount > record.amount_requested:
                raise ValidationError("Le montant accordé ne peut excéder le montant demandé.")
            max_amount = 2000000 if record.demande_exceptionnelle else 1500000
            if record.approved_amount > max_amount:
                raise ValidationError(f"Le montant demandé doit être compris entre 0 et {max_amount:,} FCFA.")

# ----------------------------------------------------------------------------------------------------------------------------

# Verifier si le montant definiti est diferent du montant accordé 
    @api.depends('final_approved_amount', 'approved_amount')
    def _compute_amount_final(self):
        for record in self:
            if record.final_approved_amount is not False and record.approved_amount is not False:
                record.final_approved_amount_update = record.final_approved_amount < record.approved_amount
            else:
                record.final_approved_amount_update = False


    @api.depends('approved_amount')
    def _compute_amount_final_se(self):
        for record in self:
            record.final_approved_amount = record.approved_amount

    @api.depends('final_approved_amount')
    def _compute_amount_final_pca(self):
        for record in self:
            record.approved_amount_pca = record.final_approved_amount
# ----------------------------------------------------------------------------------------------------------------------------

    # CONTRAINTE SUR LE CHAMPS NUMERO DE CHEQUE 
    @api.constrains('check_number')
    def _check_number_length(self):
        for record in self:
            if record.check_number and record.check_number > 9999999999:  # 10 chiffres max
                raise ValidationError("Le numéro de chèque ne doit pas dépasser 10 chiffres.")

# -----------------------------------------------------------------------------------------------------------------------------

    # VALIDATION DES CHAMPS  : Coupe le surplus sur les numéros quand on dépasse 10 chiffres
    @api.onchange('telephone')
    def _onchange_telephone(self):
        """ Tronque le numéro à 10 chiffres dès la saisie """
        if self.telephone:
            self.telephone = self.telephone[:10] 

    # VALIDATION DU CHAMPS EMAIL 
    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if record.email:
                # Vérification que l'email contient des caractères avant et après le '@'
                pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                if not re.match(pattern, record.email):
                    raise ValidationError(_("L'email doit contenir un '@' et un domaine valide (ex: exemple@gmail.com)."))

# -----------------------------------------------------------------------------------------------------------------------------
    # TRADUCTION DES CHIFFRES EN LETTRES 
    @api.depends('amount_requested')
    def _compute_amount_word(self):
        for record in self:
            if record.amount_requested:
                montant_lettres = num2words(record.amount_requested, lang='fr').capitalize()
                record.amount_requested_words = f"{montant_lettres} FCFA"
            else:
                record.amount_requested_words = ""
# -----------------------------------------------------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------------------------------------------------

    # SOUMITION DE LA DEMANDE PAR LES GROUPES SECRETARIATS & S.A 
    def action_submit(self):
        """Soumettre la demande"""
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretariat_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour soumettre une demande.')
        
        # Vérifier si la campagne est "open"
        if self.campaign_id and self.campaign_id.state != 'open':
            raise UserError("La soumission est impossible car la campagne n'est pas ouverte.")


        # Vérifier si les fichiers sont chargés avant de soumettre
        if not self.cotite or not self.piece_identite:
            raise UserError('Veuillez vérifier que la pièce d\'identité et le fichier de quotité sont valides.')


        # Envoi de l'email avant la soumission
        self.send_validation_email()

        self.write({
            'state': 'in_treatment',
            'submitted_by': self.env.user.id,
            'submission_date': fields.Datetime.now()
        })


    # RETRAIT DE CHEQUE 
    def action_check_withdrawn(self):
        """retrait de chèque"""
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretariat_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour confirmer le retrait de chèque.')

        # Ouvrir l'assistant de rejet
        return{
            'name': 'Retrait de Chèque',
            'type': 'ir.actions.act_window',
            'res_model': 'check.withdrawn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.id,
            }
            }


    # ANNULER CHEQUE 
    def action_cancel_withdrawn(self):
        """Annulation de chèque"""
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretariat_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour confirmer le retrait de chèque.')

        # Ouvrir l'assistant de rejet
        return{
            'name': 'Motif d\' Annulation du Chèque',
            'type': 'ir.actions.act_window',
            'res_model': 'check.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.id,
            }
            }
# -----------------------------------------------------------------------------------------------------------------------------

    # TRAITEMENT DE LA DEMANDE PAR LE SERVICE PRET SOCIAUX 
    def action_set_in_treatment(self):
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.commission__pret_sociaux_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour traiter une demande.')


        if self.transferable_portion == 0:
            raise UserError("Impossible d'envoyer la demande à la SE car Le champ Quotité cessible est vide. Veuillez le renseigner avant de continuer.")

        self.write({
            'state': 'se_validation',
            'submitted_pca': self.env.user.id,
            'submission_date_pca': fields.Datetime.now()
        })

        # APPEL DE LA FONTION POUR METTRE LE BUDEGT A JOUR 
        self.update_campaign_budget()

# -----------------------------------------------------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------------------------------------------------
    # ENVOIE DE LA DEMANDE A LA COMPTABILITE PAR LA SE  DIRECTEMENT EN CAS D'ABSCENCE DU PCA : sending_to_accounting
    def action_sending_to_accounting(self):
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour valider une demande.')

        # Ouvrir l'assistant de rejet
        return{
            'name': 'Envoie de la demande à la Comptabilité',
            'type': 'ir.actions.act_window',
            'res_model': 'sending.to.accounting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.id,
            }
            }


    # VALIDATION PAR LE PCA 
    def action_set_pca_validation(self):
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour valider une demande.')

        for record in self:
            # Vérifier si le champ qotite_cessible est vide ou non renseigné
            if not record.loan_granted or self.loan_not_granted:
                raise UserError("Impossible d'envoyer la demande au PCA car aucun accord de prêt n'est cocher. Veuillez cocher un  avant de continuer.")

        for record in self:
            record.state = 'pca_validation'

# -----------------------------------------------------------------------------------------------------------------------------


    # REMISE DE CHEQUE PAR LA COMPTABILITE
    def action_check_delivery(self):
        # Vérification si le montant du chèque est saisi
        if not self.check_amount:
            raise UserError('Le montant du chèque doit être saisi avant de valider la demande.')

        # Vérification des droits d'accès
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.comptabilite_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour valider une demande.')

        for record in self:
            # Vérifier si le champ N°Chèque est vide ou non renseigné
            if not record.check_number:
                raise UserError("Impossible d'emettre le Chèque sans avoir saisir le N° du Chèque. Veuillez renseigner avant de continuer.")

        # Mise à jour de l'état et autres champs
        self.write({
            'state': 'check_delivery',
            'submitted_pca': self.env.user.id,
            'date_emission_cheque': fields.Datetime.now()
        })

# -----------------------------------------------------------------------------------------------------------------------------

    # APPROUVEE UNE DEMANDE 
    def action_approve(self):
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour approuver une demande.')

        # Check if state is 'approved' or 'check_delivery'
        if self.state in ['approved', 'check_delivery']:
            raise UserError('Impossible de valider cette demande.')

        self.write({
            'state': 'approved',
            'submitted_pca': self.env.user.id,
            'submission_date_pca': fields.Datetime.now()
        })

# -----------------------------------------------------------------------------------------------------------------------------


    # ENVOYER LES DEMANDES EXCEPTIONNELLE DIRECTION AU PCA 
    def action_send_to_pca(self):
        """Envoyer directement la demande exceptionnelle au PCA"""
        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretariat_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour soumettre une demande au PCA.')

        self.write({
            'state': 'pca_validation',
            'submitted_by': self.env.user.id,
            'submission_date': fields.Datetime.now()
        })

# -----------------------------------------------------------------------------------------------------------------------------


    # REJETER UNE DEMANDE 
    def action_reject(self):

        # EMPECHER LES MEMBRE DU GROUPE PRET SOCIAUX DE REJETER UNE DEMANDE DEJA VALIDER PAR LADITE GROUPE 
        if self.state == 'se_validation' and self.env.user.has_group('loan_mutual.commission__pret_sociaux_pret_mutuel'):
            raise UserError("Vous ne pouvez pas rejeter une demande en statut 'Validation SE'.")

        # EMPECHER LES MEMBRE DU GROUPE SE DE REJETER UNE DEMANDE DEJA VALIDER PAR LADITE GROUPE 
        if self.state == 'pca_validation' and self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel'):
            raise UserError("Vous ne pouvez pas rejeter une demande en statut 'PCA Validation'.")

    
        # EMPECHER LES MEMBRE DU GROUPE *PCA DE REJETER UNE DEMANDE DEJA VALIDER PAR LADITE GROUPE 
        if self.state == 'approved' and self.env.user.has_group('loan_mutual.pca_pret_mutuel'):
            raise UserError("Vous ne pouvez pas rejeter une demande déjà approuvée.")

        if not (self.env.user.has_group('loan_mutual.super_admin_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretaire_executive_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.secretariat_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.commission__pret_sociaux_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.manager_pret_mutuel') or 
                self.env.user.has_group('loan_mutual.pca_pret_mutuel')):
            raise UserError('Vous n\'avez pas les droits pour rejeter une demande.')

        # Check if state is 'approved' or 'check_delivery'
        if self.state in ['approved', 'check_delivery']:
            raise UserError('Impossible de rejeter cette demande.')

        # RESTAURER LE BUDGET DE LA CAMPAGNE
        if(self.state == 'se_validation' or self.state == 'pca_validation'):
            if(self.rejection_reason != ""): 
                self.restore_campaign_budget()

        # Envoie de mail de rejet
        self.send_rejection_email()

        # Ouvrir l'assistant de rejet
        return{
            'name': 'Motif du rejet',
            'type': 'ir.actions.act_window',
            'res_model': 'loan.mutual.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.id,
            }
            }

# --------------------------------------------------------------------------------------------------------------------
    # CONTROLLER LES CASES A COCHER DES DEUX CHAMPS 
    @api.onchange('loan_granted')
    def _onchange_loan_granted(self):
        if self.loan_granted:
            self.motif_rejet_readonly = True
            self.loan_not_granted = False
        else:
            self.motif_rejet_readonly = False


    @api.onchange('loan_not_granted')
    def _onchange_loan_not_granted(self):
        if self.loan_not_granted:
            self.loan_granted = False
# --------------------------------------------------------------------------------------------------------------------

    # CALCUL DE LA MENSUALITE  
    @api.depends('amount_to_be_refunded', 'amount_to_be_refunded_se', 'amount_to_be_refunded_pca', 'modalite_remboursement')
    def _compute_mensualite(self):
        for record in self:
            if record.modalite_remboursement:
                if record.approved_amount_pca and record.approved_amount_pca != record.final_approved_amount:
                    amount = record.amount_to_be_refunded_pca or 0
                elif record.final_approved_amount and record.final_approved_amount != record.approved_amount:
                    amount = record.amount_to_be_refunded_se or 0
                elif record.approved_amount and record.approved_amount != record.amount_requested:
                    amount = record.amount_to_be_refunded_ps or 0
                else:
                    amount = record.amount_to_be_refunded or 0
                record.mensualite = int(amount / int(record.modalite_remboursement))
            else:
                record.mensualite = 0

# ---------------------------------- CONTROLE DES EDITIONS DE ZONES --------------------------------------------------

    # FONCTION QUI EMPECHE LES AUTRES MEMBRES DE MODIFIER L'ESPACE DE MAPAA
    @api.depends_context('uid')
    def _compute_can_edit_mapaa(self):
        """Détermine si l'utilisateur actuel peut éditer les champs MA-PAA."""
        for record in self:
            user = self.env.user
            record.can_edit_mapaa = any([
                user.has_group('loan_mutual.super_admin_pret_mutuel'),
                user.has_group('loan_mutual.manager_pret_mutuel'),
                user.has_group('loan_mutual.commission__pret_sociaux_pret_mutuel')
            ]) if user else False

# -----------------------------------------------------------------------------------------------------------------------------

    # FONCTION QUI EMPECHE LES AUTRES MEMBRES DE MODIFIER L'ESPACE DE MAPAA
    @api.depends_context('uid')
    def _compute_can_edit_pca(self):
        """Détermine si l'utilisateur actuel peut éditer les champs PCA."""
        for record in self:
            user = self.env.user
            record.can_edit_pca = any([
                user.has_group('loan_mutual.super_admin_pret_mutuel'),
                user.has_group('loan_mutual.manager_pret_mutuel'),
                user.has_group('loan_mutual.pca_pret_mutuel')
            ]) if user else False

# -----------------------------------------------------------------------------------------------------------------------------

    @api.depends_context('uid')
    def _compute_can_edit_se(self):
        """Détermine si l'utilisateur actuel peut éditer les champs de la secretaire exécutive."""
        for record in self:
            user = self.env.user
            record.can_edit_se = any([
                user.has_group('loan_mutual.super_admin_pret_mutuel'),
                user.has_group('loan_mutual.manager_pret_mutuel'),
                user.has_group('loan_mutual.secretaire_executive_pret_mutuel')
            ]) if user else False


    @api.depends_context('uid')
    def _compute_can_edit_secretaire(self):
        """Détermine si l'utilisateur actuel peut éditer les champs de la secretaire."""
        for record in self:
            user = self.env.user
            record.can_edit_secretaire = any([
                user.has_group('loan_mutual.super_admin_pret_mutuel'),
                user.has_group('loan_mutual.manager_pret_mutuel')
            ]) if user else False


    @api.depends_context('uid')
    def _compute_can_edit_compta(self):
        """Détermine si l'utilisateur actuel peut éditer les champs de la comptabilité."""
        for record in self:
            user = self.env.user
            record.can_edit_compta = any([
                user.has_group('loan_mutual.super_admin_pret_mutuel'),
                user.has_group('loan_mutual.manager_pret_mutuel'),
                user.has_group('loan_mutual.comptabilite_pret_mutuel')
            ]) if user else False


# ----------------------------DETERMINER L'ANNEE DE DEBUT PRECOMPTE --------------------------------------------------------
    @api.depends('start_date_deduct')
    def _compute_year(self):
        for record in self:
            if record.start_date_deduct:
                record.start_date_year_decution = record.start_date_deduct.year
            else:
                record.start_date_year_decution = 0
# ----------------------------------FIN DE CONTROLE DES EDITIONS DE ZONES --------------------------------------------------

    @api.depends('approved_amount', 'final_approved_amount', 'approved_amount_pca')
    def _compute_budget_restant_ps(self):
        for record in self:
            approved = record.approved_amount or 0
            final_approved = record.final_approved_amount or 0
            pca_approved = record.approved_amount_pca or 0
            
            # Si c'est un nouveau record
            if not isinstance(record.id, int):
                record.budget_restant_ps = approved
                return
                
            # Si le PCA a modifié le montant
            if pca_approved < final_approved and pca_approved > 0:
                # Le montant retranché est le montant approuvé par le PCA
                record.budget_restant_ps = pca_approved

            # Si la SE a modifié le montant mais pas le PCA
            elif final_approved < approved:
                # Le montant retranché est le montant final approuvé par la SE
                record.budget_restant_ps = final_approved

            # Sinon, utiliser le montant approuvé initial
            else:
                record.budget_restant_ps = approved


    # ================= METTRE A JOUR LE BUDGET DE LA CAMPAGNE EN RETRANCHANT LE MONTANT A REMBOURSER AU NIVEAU DU COMMISSION DE PRET  =========
# Mise à jour du budget initial par le service prêt sociaux
    def update_campaign_budget(self):
        """Met à jour le budget de la campagne en retranchant approved_amount."""
        for record in self:
            campagne = record.campaign_id
            if not campagne:
                raise UserError("Aucune campagne associée à cette demande.")

            montant = record.approved_amount or 0

            # Vérifier si un ajustement SE a déjà été fait
            if record.budget_restant_se == 0 and record.final_approved_amount == record.approved_amount:
                new_budget = campagne.budget_restant - montant
                budget_depasse = max(0, -new_budget)
                new_budget = max(0, new_budget)

                campagne.write({
                    'budget_restant': new_budget,
                    'budget_depasse': budget_depasse
                })

                # Ne définissez que budget_restant_se
                # budget_restant_ps sera calculé automatiquement
                record.write({
                    'budget_restant_se': 0
                })
                _logger.debug(f"Budget mis à jour pour {record.reference}: retranché {montant}, budget_restant={new_budget}")
            else:
                _logger.debug(f"Aucun retranchement initial pour {record.reference}: ajustement SE déjà présent")


# -------------------------------------------------------------------------------------------------------------------------------------------

    # FONCTION POUR METTRE A JOUR LE BUDGET SI LA SE MODIFIE LE MONTANT 
    @api.onchange('final_approved_amount')
    def _onchange_final_approved_amount(self):
        for record in self:
            if record.final_approved_amount > record.approved_amount:
                raise UserError("Le montant définitif accordé ne peut pas être supérieur au montant demandé par le mutualiste.")
            record.update_campaign_budget_se()
            return {
                'value': {
                    'budget_restant_se': record.budget_restant_se
                }
            }

    # Fonction de mise à jour du budget par la SE
    def update_campaign_budget_se(self):
        for record in self:
            campagne = record.campaign_id
            if not campagne:
                raise UserError("Aucune campagne associée à cette demande.")
            
            approved = record.approved_amount or 0
            final_approved = record.final_approved_amount or 0
            
            # Annuler l'ajustement précédent si nécessaire
            if record.budget_restant_se > 0:
                campagne.write({
                    'budget_restant': campagne.budget_restant - record.budget_restant_se,
                    'budget_depasse': max(0, campagne.budget_depasse + record.budget_restant_se)
                })
                _logger.debug(f"Annulation de l'ajustement précédent pour {record.reference}: retiré {record.budget_restant_se}")
            
            # Calculer le nouvel ajustement
            difference = 0
            if final_approved < approved:
                difference = approved - final_approved
                new_budget = campagne.budget_restant + difference
                budget_depasse = max(0, campagne.budget_depasse - difference)
                new_budget = max(0, new_budget)
                
                campagne.write({
                    'budget_restant': new_budget,
                    'budget_depasse': budget_depasse
                })
                _logger.debug(f"Ajustement budget SE pour {record.reference}: ajouté {difference}, budget_restant={new_budget}")
            
            # Mettre à jour uniquement budget_restant_se
            # budget_restant_ps sera mis à jour automatiquement via _compute_budget_restant_ps
            record.write({
                'budget_restant_se': difference
            })
            

    # FONCTION POUR METTRE A JOUR LE BUDGET SI LE PCA  MODIFIE LE MONTANT 
    @api.onchange('approved_amount_pca')
    def _onchange_approved_amount_pca(self):
        for record in self:
            if record.approved_amount_pca > record.final_approved_amount:
                raise UserError("Le montant accordé par le PCA ne peut pas être supérieur au montant accordé par la SE.")
            if record.approved_amount_pca < record.final_approved_amount:
                record.update_campaign_budget_pca()

    def update_campaign_budget_pca(self):
        for record in self:
            campagne = record.campaign_id
            
            if not campagne:
                raise UserError("Aucune campagne associée à cette demande.")
            
            approved = record.final_approved_amount or 0
            final_approved = record.approved_amount_pca or 0

            if final_approved < approved:
                difference = approved - final_approved
                new_budget = campagne.budget_restant + difference  # Ajoutez la différence au budget restant
                budget_depasse = max(0, campagne.budget_depasse - difference)
                new_budget = max(0, new_budget)

                campagne.write({
                    'budget_restant': new_budget,
                    'budget_depasse': budget_depasse
                })
                
                _logger.debug(f"Ajustement budget PCA pour {record.reference}: ajouté {difference}, budget_restant={new_budget}")
                
                # Aucun besoin de mettre à jour budget_restant_ps ici
                # Il sera automatiquement mis à jour grâce à _compute_budget_restant_ps


    # Restauration du budget en cas de rejet
    def restore_campaign_budget(self):
        """Restaure le budget de la campagne en ajoutant le montant net retranché."""
        for record in self:
            campagne = record.campaign_id
            if not campagne:
                raise UserError("Aucune campagne associée à cette demande.")
            
            amount_to_restore = record.budget_restant_ps or 0
            if amount_to_restore > 0:
                new_budget = campagne.budget_restant + amount_to_restore
                budget_depasse = max(0, campagne.budget_depasse - amount_to_restore)
                new_budget = max(0, new_budget)
                
                campagne.write({
                    'budget_restant': new_budget,
                    'budget_depasse': budget_depasse
                })
                
                _logger.debug(f"Budget restauré pour {record.reference}: ajouté {amount_to_restore}, budget_restant={new_budget}")
            
            # Réinitialiser les champs
            record.write({
                'budget_restant_se': 0,
                'final_approved_amount': record.approved_amount  # Remettre final_approved_amount à approved_amount
            })


    #   EN CAS DE SUPPRESSION D' UNE DEMANDE : RESTAURER LE MONANT DU BUDGET DE LA CAMPAGNE 
    def unlink(self):
        """ Surcharge de la suppression pour restaurer le budget avant de supprimer la demande """
        for record in self:
            campagne = record.campaign_id  # Vérifie si une campagne est associée
            
            # Vérification de la condition avant de restaurer le budget
            if campagne and campagne.budget_restant < campagne.total_budget:
                record.restore_campaign_budget()

        # Appel de la méthode d'origine pour supprimer la demande
        return super(LoanMutual, self).unlink()

# ---------------------------------------------------------------------------------------------------------------------

    # MAIL DE DEMANDE DE PRET MUTUEL : l'employé reçoit un mail après sa demande de prêt 
    def send_confirmation_email(self):
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de confirmation pour la demande %s", self.reference)
            
            template = self.env.ref('loan_mutual.loan_confirmation_email_template', raise_if_not_found=True)
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


    # MAIL DE DEMANDE DE PRET MUTUEL : l'employé reçoit un mail après sa demande de prêt 
    def send_validation_email(self):
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de confirmation pour la demande %s", self.reference)
            
            template = self.env.ref('loan_mutual.loan_validation_email_template', raise_if_not_found=True)
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

    # ------------------------------- Fin mail de demande de prêt ------------------------

    # ENVOIE LE MAIL DE REJET UNE FOIS QU' ON DONNE LE MOTIF
    @api.depends('is_rejection')
    def _compute_amount_words(self):
        for record in self:
            if record.is_rejection:
                record.rejection_reason= record.rejection_reason
                record.send_rejection_email()


    # MAIL DE RETRAIT DE CHEQUE 
    # Ajoutez ces méthodes dans la classe LoanMutual pour permettre l'envoi d'email depuis le modèle principal si nécessaire

    def send_check_withdrawal_email(self):
        """Envoie un email de confirmation de retrait de chèque directement depuis le modèle LoanMutual"""
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de confirmation de retrait pour la demande %s", self.reference)
            
            template = self.env.ref('loan_mutual.check_withdrawal_email_template', raise_if_not_found=True)
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
                    "Mail de confirmation de retrait envoyé avec succès pour la demande %s (ID mail: %s)", 
                    self.reference, 
                    mail_id
                )
                return True
                
            except Exception as mail_error:
                _logger.error(
                    "Erreur d'envoi de mail de confirmation de retrait: %s", 
                    str(mail_error),
                    exc_info=True
                )
                return False
                
        except Exception as e:
            _logger.error(
                "Erreur générale lors de l'envoi du mail de confirmation de retrait pour la demande %s: %s", 
                self.reference, 
                str(e),
                exc_info=True
            )
            return False


    # MAIL DE REJET 
    def send_rejection_email(self):
        self.ensure_one()
        try:
            _logger.info("Début de l'envoi du mail de rejet pour la demande %s", self.reference)
            
            template = self.env.ref('loan_mutual.loan_rejection_email_template', raise_if_not_found=True)
            if not template:
                _logger.error("Template d'email de rejet non trouvé pour la demande %s", self.reference)
                return False
                
            if not self.email:
                _logger.error("Aucune adresse email fournie pour la demande %s", self.reference)
                return False

            # Définir l'adresse email d'envoi
            company_email = self.env.company.email or 'noreply@paa.com'  # Email par défaut
            
            _logger.info("Informations d'envoi de mail de rejet:")
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
                    "Mail de rejet envoyé avec succès pour la demande %s (ID mail: %s)", 
                    self.reference, 
                    mail_id
                )
                
                # Mettre à jour le statut de la demande après l'envoi du mail de rejet
                self.write({
                    'state': 'rejected',
                    'rejection_date': fields.Datetime.now(),
                    'rejection_mail_sent': True
                })
                
                return True
                
            except Exception as mail_error:
                _logger.error(
                    "Erreur spécifique d'envoi de mail de rejet: %s", 
                    str(mail_error),
                    exc_info=True
                )
                return False
                
        except Exception as e:
            _logger.error(
                "Erreur générale lors de l'envoi du mail de rejet pour la demande %s: %s", 
                self.reference, 
                str(e),
                exc_info=True
            )
            return False