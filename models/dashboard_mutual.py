from odoo import models, fields, api
from datetime import date


class DashboardMutual(models.TransientModel):  # TransientModel au lieu de Model
    _name = 'dashboard.mutual'
    _description = 'Dashboard de Demandes de Prêt Mutuel'

    # Champs de période avec valeurs par défaut (mois en cours)
    date_debut = fields.Date(string="Date de Début", default=lambda self: date.today().replace(day=1))
    date_fin = fields.Date(string="Date de Fin", default=lambda self: date.today())

    # Relation 
    direction_id = fields.Many2one('direction.employe',string='Direction')


    # Champs calculés
    total_demandes = fields.Integer(string="Nombre Total de Demandes", compute="_compute_total_demandes", store=True, default=0)
    pret_solde = fields.Integer(string="Nombre de Prêts Soldés", compute="_compute_total_demandes", store=True)
    pret_nom_solde = fields.Integer(string="Nombre de Prêts Non Soldés", compute="_compute_total_demandes", store=True)
    montant_total_pret_solde = fields.Integer(string="Montant Total des Prêts Soldés", compute="_compute_total_demandes", store=True)
    montant_total_pret_non_solde = fields.Integer(string="Montant Total des Prêts Non Soldés", compute="_compute_total_demandes", store=True)
    demandes_exceptionnelles = fields.Integer(string="Nombre de Demandes Exceptionnelles", compute="_compute_total_demandes", store=True)
 

# =============================================== COMPTAGE DES DEMANDES ===========================================
    # Méthodes de calcul : Compter le nombre total des demandes par campagne et période
    @api.depends('date_debut', 'date_fin', 'direction_id')
    def _compute_total_demandes(self):
        for record in self:
            # Vérifier que les dates sont définies
            if not record.date_debut or not record.date_fin:
                record.total_demandes = 0
                record.pret_solde = 0
                record.pret_nom_solde = 0
                record.montant_total_pret_solde = 0.0
                record.montant_total_pret_non_solde = 0.0
                continue
            
            # Filtre sur les dates 
            domain = [('create_date', '>=', record.date_debut),
                      ('create_date', '<=', record.date_fin)]


            # Appliquer le filtre de direction si une direction est sélectionnée
            if record.direction_id:
                domain.append(('direction', '=', record.direction_id.name)) 


            # Nombre total de demandes
            record.total_demandes = self.env['loan.mutual'].search_count(domain)

            # Prêts soldés
            pret_solde_records = self.env['loan.mutual'].search(domain + [('is_on_sale', '=', True)])
            record.pret_solde = len(pret_solde_records)
            record.montant_total_pret_solde = sum(pret_solde_records.mapped('approved_amount'))

            # Prêts non soldés
            pret_nom_solde_records = self.env['loan.mutual'].search(domain + [('is_on_sale', '!=', True)])
            record.pret_nom_solde = len(pret_nom_solde_records)
            record.montant_total_pret_non_solde = sum(pret_nom_solde_records.mapped('approved_amount'))


            # Filtrer et compter les demandes exceptionnelles
            demandes_exceptionnelles = self.env['loan.mutual'].search(domain + [('demande_exceptionnelle', '=', True)])
            record.demandes_exceptionnelles = len(demandes_exceptionnelles)


# -------------------------------------- AFFICHER LE TOP 10 DEMANDEURS ---------------------------------------------------------
