from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class PaaEmployee(models.Model):
    _name = 'paa.employee'
    _description = 'La liste des employées du Port Autonome d\'Abidjan 002'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "matricule"

    
    # CHAMPS DE LA BD 
    name = fields.Char(string='Nom', required=True)
    prenoms = fields.Char(string='Prénoms')
    date_naissance = fields.Date(string='Date de Naissance')
    annee_naissance = fields.Integer(string='Année de Naissance')
    annee_en_cours = fields.Integer(string='Année en Cours')
    age = fields.Integer(string='Age')
    date_embauche = fields.Date(string='Date d\'Embauche')
    date_prise_service = fields.Date(string='Date de Prise de Service')
    annee_embauche = fields.Integer(string='Année d\'Embauche')
    anciennete = fields.Integer(string='Ancienneté')
    fonction = fields.Char(string='Fonction')
    categorie_actuelle = fields.Char(string='Catégorie Actuelle')
    sexe = fields.Selection([('Masculin', 'Masculin'),('Feminin', 'Feminin')], string='Sexe')
    services = fields.Char(string='Services')
    sites = fields.Char(string='Sites')
    typecat = fields.Char(string='Catégorie')
    matricule = fields.Char(string='Matricule')


    # Relation : Anciennes demande de prêt 
    loan_history_ids = fields.One2many('loan.application', 'employee_id', string="Historique des prêts")

    anciennete_employe = fields.Integer(string='Ancienneté au 31/10',store=True,help="Ancienneté calculée au 31 octobre de l'année en cours")

    # Relation avec le modèle DirectionEmploye
    direction = fields.Many2one('direction.employe', string="Direction")
    nom_direction = fields.Char(string="Nom de la Direction", related='direction.name', readonly=True)



# Champ pour afficher l'ancienneté en texte (années et mois)
    anciennete_employe_paa = fields.Char(
        string="Ancienneté",
        compute="_compute_anciennete_employe",
        store=True,
        help="Ancienneté calculée en années et mois à partir de la date d'embauche"
    )

    # Champ pour stocker uniquement les années (si nécessaire ailleurs)
    anciennete_paa = fields.Integer(
        string="Ancienneté (années)",
        compute="_compute_anciennete_employe",
        store=True,
        help="Ancienneté calculée en années"
    )


    @api.depends('date_embauche')
    def _compute_anciennete_employe(self):
        """Calcule l'ancienneté en années et mois à partir de la date d'embauche."""
        for record in self:
            if record.date_embauche:
                # Date actuelle ou date fixe (31/10 de l'année en cours)
                today = datetime.today().date()
                # Si vous voulez fixer au 31/10 :
                # today = datetime(today.year, 10, 31).date()
                
                # Calcul de la différence avec relativedelta
                delta = relativedelta(today, record.date_embauche)
                
                # Formatage du champ texte (anciennete_employe)
                years = delta.years
                months = delta.months
                anciennete_str = ""
                if years > 0:
                    anciennete_str += f"{years} an{'s' if years > 1 else ''}"
                if months > 0:
                    if years > 0:
                        anciennete_str += " et "
                    anciennete_str += f"{months} mois"
                if not anciennete_str:
                    anciennete_str = "Moins d'un mois"
                
                record.anciennete_employe_paa = anciennete_str
                
                # Calcul pour le champ entier (anciennete)
                record.anciennete_paa = years
            else:
                record.anciennete_employe_paa = "Non défini"
                record.anciennete_paa = 0