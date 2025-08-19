from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ComiteValidation(models.Model):
    _name = 'comite.validation'
    _description = 'Comité de Validation des Demandes de Prêt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_validation desc"


    # Champs de base
    name = fields.Char(string="Nom du Comité", required=True, tracking=True)
    campaign_id = fields.Many2one('loan.campaign', string="Campagne de Prêt", required=True, tracking=True)
    date_validation = fields.Date(string="Date création", default=lambda self: fields.Date.today(), readonly=True)

    # Champs calculés
    total_demandes = fields.Integer(string="Nombre Total de Demandes", compute="_compute_total_demandes", store=True, default=0)
    montant_total = fields.Integer(string="Montant Total des Demandes", compute="_compute_montant_total", store=True)
    demandes_en_attente = fields.Many2many('loan.application', string="Demandes en Attente", compute="_compute_demandes_en_attente", store=True)

    # Champs pour afficher le budget prévisionnel de la campagne 
    budget_previsionnel = fields.Integer(string="Budget Prévisionnel", compute="_compute_budget_previsionnel", store=True)

    # Nouveau champ pour le montant total accordé
    total_montant_accorde = fields.Integer(string="Total Montant Accordé", compute="_compute_total_montant_accorde",  store=True)

    direction_filter = fields.Many2one('direction.employe', string='Filtrer par Direction')

    montant_direction = fields.Integer(
        string="Montant Total par Direction", 
        compute="_compute_montant_direction",
        store=True
    )

#  ------------------------------------------- METHODES -----------------------------------
  
    # Focntion calculée qui renvoie le montant total par direction
    @api.depends('campaign_id', 'direction_filter')
    def _compute_montant_direction(self):
        for comite in self:
            domain = [
                ('campaign_id', '=', comite.campaign_id.id)
            ]
            
            # Ajouter le filtre par direction si une direction est sélectionnée
            if comite.direction_filter:
                domain.append(('direction', '=', comite.direction_filter.name))
            
            # Rechercher les demandes qui correspondent aux critères
            demandes = self.env['loan.application'].search(domain)
            comite.montant_direction = sum(demandes.mapped('amount_requested'))



  # Contrainte pour vérifier l'unicité de la campagne
    @api.constrains('campaign_id')
    def _check_unique_campaign(self):
        for record in self:
            existing_comite = self.search([('campaign_id', '=', record.campaign_id.id), ('id', '!=', record.id)])
            if existing_comite:
                raise ValidationError("Un comité est déjà associé à cette campagne. Veuillez choisir une autre campagne.")


# ---------------------------------------------------------------------------------------
    # Méthodes de calcul : Compter le nombre total des demandes par campagne
    @api.depends('campaign_id', 'direction_filter')
    def _compute_total_demandes(self):
        for comite in self:
            domain = [('campaign_id', '=', comite.campaign_id.id)]
            
            # Si une direction est sélectionnée, filtrer les demandes par direction
            if comite.direction_filter:
                domain.append(('direction', '=', comite.direction_filter.name))
            
            comite.total_demandes = self.env['loan.application'].search_count(domain)
# ---------------------------------------------------------------------------------------


    # Retourne le montant total demandé par campagne
    @api.depends('campaign_id')
    def _compute_montant_total(self):
        for comite in self:
            demandes = self.env['loan.application'].search([('campaign_id', '=', comite.campaign_id.id)])
            comite.montant_total = sum(demandes.mapped('amount_requested'))


    # Retourne le montant total accordé pour la campagne en cours .
    @api.depends('campaign_id', 'direction_filter')
    def _compute_total_montant_accorde(self):
        for comite in self:
            # Construire le domaine de base avec la campagne
            domain = [
                ('campaign_id', '=', comite.campaign_id.id),
                ('state', '=', 'validated')
            ]
            
            # Ajouter le filtre par direction si une direction est sélectionnée
            if comite.direction_filter:
                domain.append(('direction', '=', comite.direction_filter.name))
                
            # Rechercher les demandes qui correspondent aux critères
            demandes = self.env['loan.application'].search(domain)
            
            # Calculer la somme des montants approuvés
            total = sum(demande.approved_amount for demande in demandes if demande.approved_amount)
            comite.total_montant_accorde = total
        self._compute_demandes_en_attente()
    

    @api.onchange('campaign_id', 'direction_filter')
    def _onchange_campaign_or_direction(self):
        """Mettre à jour le montant accordé en temps réel dans l'interface."""
        self._compute_total_montant_accorde()



    # ----------------------------- Méthode pour retourner la liste des demandes en entente par Direction et Campagne
    @api.depends('campaign_id', 'direction_filter')
    def _compute_demandes_en_attente(self):
        """
        Calcule les demandes en attente pour chaque comité en fonction de la campagne et du filtre de direction.
        Si une direction est sélectionnée mais qu'aucune demande ne correspond, retourne une liste vide.
        """
        for comite in self:
            if comite.campaign_id:
                # Construire le domaine de base
                domain = [
                    ('campaign_id', '=', comite.campaign_id.id),
                    ('state', '=', 'pending')
                ]
                # Ajouter le filtre par direction si une direction est sélectionnée
                if comite.direction_filter:
                    domain.append(('direction', '=', comite.direction_filter.name))

                    # Vérifier s'il y a des demandes correspondant à la direction
                    demandes = self.env['loan.application'].search(domain)
                    if not demandes:
                        # Si aucune demande ne correspond, retourner une liste vide
                        comite.demandes_en_attente = False
                    else:
                        # Sinon, retourner les demandes correspondantes
                        comite.demandes_en_attente = demandes
                else:
                    # Si aucune direction n'est sélectionnée, retourner toutes les demandes de la campagne
                    demandes = self.env['loan.application'].search(domain)
                    comite.demandes_en_attente = demandes
            else:
                # Si aucune campagne n'est sélectionnée, ne pas afficher de demandes
                comite.demandes_en_attente = False


    # Méthode d'action pour rafraîchir la liste
    def action_refresh_demandes(self):
        self.ensure_one()
        self._compute_demandes_en_attente()
        self._compute_total_montant_accorde()
        return True
# -------------------------------------------Fin Recherche des demandes par Direction et Campagne 



    # Méthode pour obtenir la liste des directions disponibles
    @api.model
    def get_available_directions(self):
        """Retourne la liste des directions qui ont des demandes en attente"""
        demandes = self.env['loan.application'].search([('state', '=', 'pending')])
        directions = demandes.mapped('direction')
        return list(set(directions))  # Elimine les doublons


    # Calcul : Récupère le budget prévisionnel de la campagne 
    @api.depends('campaign_id')
    def _compute_budget_previsionnel(self):
        for record in self:
            record.budget_previsionnel = record.campaign_id.total_budget if record.campaign_id else 0.0


    # Actions pour valider et rejeter
    def action_valider_demandes(self):
        """Valider toutes les demandes en attente associées."""
        for comite in self:
            demandes = self.env['loan.application'].search([('campaign_id', '=', comite.campaign_id.id), ('state', '=', 'pending')])
            demandes.write({'state': 'validated'})


    # Action de rejet 
    def action_rejeter_demandes(self):
        """Rejeter toutes les demandes en attente associées."""
        for comite in self:
            demandes = self.env['loan.application'].search([('campaign_id', '=', comite.campaign_id.id), ('state', '=', 'pending')])
            demandes.write({'state': 'rejected'})