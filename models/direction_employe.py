from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DirectionEmploye(models.Model):
    _name = 'direction.employe'
    _description = 'Liste des directions du Port Autonome d\'Abidjan.'
    _rec_name = "name"
    # Contrainte SQL pour rendre les noms des directions UNIQUE dans la BD
    _sql_constraints = [('unique_direction_name', 'unique(name)', "Cette direction existe déjà !")]

    # Champs de base
    name = fields.Char(string="Nom de la Direction", required=True)
    date_creation = fields.Date(string="Date création", default=lambda self: fields.Date.today(), readonly=True)


