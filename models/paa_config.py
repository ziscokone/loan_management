from odoo import models, fields
from datetime import date
from dateutil.relativedelta import relativedelta


class PaaConfig(models.Model):
    _name = 'paa.config'
    _description = 'Configuration de du module Prêt Scolaire'
    _rec_name = "date_reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']


    date_reference = fields.Date(string="Date de réference de l'ancienneté", tracking=True, required=True, default=lambda self: self.default_date_reference())

    # INFORMATIONS DES RESPONSABLE QUI DOIVENT FIGURER SUR LE TEMPLATE MAIL 
    responsable_1 = fields.Char(string="Responsable 1", tracking=True,)
    contact_responsable_1 = fields.Integer(string="Contact Responsable 1", tracking=True,)

    responsable_2 = fields.Char(string="Responsable 2", tracking=True,)
    contact_responsable_2 = fields.Integer(string="Contact Responsable 2", tracking=True,)

    responsable_3 = fields.Char(string="Responsable 3", tracking=True,)
    contact_responsable_3 = fields.Integer(string="Contact Responsable 3", tracking=True,)


# ------------------------------------------------------------------------------------------------------------------------
    def default_date_reference(self):
        """
        Retourne le 31 octobre de l'année en cours
        """
        current_year = date.today().year
        return date(current_year, 10, 31)



    def update_anciennete_et_age(self):
        """
        Met à jour l'ancienneté (en années et en texte) et l'âge de tous les employés en fonction de la date de référence.
        """
        employees = self.env['paa.employee'].search([])  # Rechercher tous les employés
        count = 0  # Compteur du nombre d'employés mis à jour

        for emp in employees:
            if emp.date_embauche and emp.date_naissance and self.date_reference:
                # Calcul de l'ancienneté
                delta_anciennete = relativedelta(self.date_reference, emp.date_embauche)
                years = delta_anciennete.years
                months = delta_anciennete.months

                # Mise à jour du champ anciennete (en années, Integer)
                emp.anciennete_paa = years

                # Construction de la chaîne pour anciennete_employe (Char)
                anciennete_str = ""
                if years > 0:
                    anciennete_str += f"{years} an{'s' if years > 1 else ''}"
                if months > 0:
                    if years > 0:
                        anciennete_str += " et "
                    anciennete_str += f"{months} mois"
                if not anciennete_str:
                    anciennete_str = "Moins d'un mois"

                emp.anciennete_employe_paa = anciennete_str

                # Calcul de l'âge
                delta_age = relativedelta(self.date_reference, emp.date_naissance)
                emp.age = delta_age.years

                count += 1  # Incrémenter le compteur

        # Envoyer un toast pour informer de la mise à jour
        message = f"{count} employés mis à jour avec succès (ancienneté et âge) !"
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {'title': "Mise à jour terminée", 'message': message, 'sticky': False, 'type': 'success'}
        )

