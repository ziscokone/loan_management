from odoo import models, fields
from datetime import date

class MaPaaConfig(models.Model):
    _name = 'mapaa.config'
    _description = 'Configuration de du module Prêt Mutuel'
    _rec_name = "date_reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']



    date_reference = fields.Date(string="Date de réference de l'ancienneté", required=True, default=lambda self: self.default_date_reference())

    # INFORMATIONS DES RESPONSABLE QUI DOIVENT FIGURER SUR LE TEMPLATE MAIL 
    responsable_1 = fields.Char(string="Responsable 1")
    contact_responsable_1 = fields.Char(string="Contact Responsable 1")

    responsable_2 = fields.Char(string="Responsable 2")
    contact_responsable_2 = fields.Char(string="Contact Responsable 2")

    responsable_3 = fields.Char(string="Responsable 3")
    contact_responsable_3 = fields.Char(string="Contact Responsable 3")

    responsable_4 = fields.Char(string="Responsable 4")
    contact_responsable_4 = fields.Char(string="Contact Responsable 4")
# ------------------------------------------------------------------------------------------------------------------------
    def default_date_reference(self):
        """
        Retourne le 31 octobre de l'année en cours
        """
        current_year = date.today().year
        return date(current_year, 10, 31)


    def update_anciennete_et_age(self):
        """
            Met à jour l'ancienneté et l'âge de tous les employés en fonction de la date de référence.
        """
        employees = self.env['paa.employee'].search([])  # Rechercher tous les employés
        count = 0  # Compteur du nombre d'employés mis à jour

        for emp in employees:
            if emp.date_embauche and emp.date_naissance and self.date_reference:
                # Calculer l'ancienneté en fonction de la date d'embauche
                delta_anciennete = self.date_reference - emp.date_embauche
                anciennete = delta_anciennete.days // 365  # Convertir la différence en années
                emp.anciennete = anciennete  # Mettre à jour le champ 'anciennete'

                # Calculer l'âge en fonction de la date de naissance
                delta_age = self.date_reference - emp.date_naissance
                age = delta_age.days // 365  # Convertir la différence en années
                emp.age = age  # Mettre à jour le champ 'age'

                count += 1  # Incrémenter le compteur

        # Envoyer un toast pour informer de la mise à jour
        message = f"{count} employés mis à jour avec succès (ancienneté et âge) !"
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {'title': "Mise à jour terminée", 'message': message, 'sticky': False, 'type': 'success'}
        )