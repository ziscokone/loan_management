from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class PaaEmployee(models.Model):
    _name = 'paa.employee'
    _description = 'La liste des employées du Port Autonome d\'Abidjan.'
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

    anciennete_employe = fields.Integer(string='Ancienneté au 31/10',store=True,help="Ancienneté calculée au 31 octobre de l'année en cours")

    # Relation avec le modèle DirectionEmploye
    direction = fields.Many2one('direction.employe', string="Direction")
    nom_direction = fields.Char(string="Nom de la Direction", related='direction.name', readonly=True)

    # Relation avec le model Demande Prêt Mutuel
    loan_history_ids = fields.One2many('loan.mutual', 'employee_id', string="Historique des prêts")






