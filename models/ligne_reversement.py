from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Ligneversement(models.Model):
    _name = 'ligne.versement'
    _description = 'Ligne de reversement du PAA 0025'

    reversement_id = fields.Many2one( 'reversement',string='Prélèvement', required=True)
    employee_id = fields.Many2one('paa.employee', string='Matricule', required=True)
    campagne = fields.Many2one('loan.campaign',string='Campagne',related='reversement_id.campagne_id',store=True)
    montant_paye = fields.Integer(string='Montant Payé',required=True)
    loan_application_id = fields.Many2one('loan.application',string='Demande de Prêt',required=True)
    is_existing = fields.Boolean(string="Ancien Paiement", default=False, invisible =True)
  
    email = fields.Char(string='Email', compute='_compute_email', store=True)
# --------------------------------------------- CHAMPS RELATION -----------------------------------------------

    nom = fields.Char(string='Nom', size=50, tracking=True, related="employee_id.name", store=True, readonly=True, invisible=True)
    prenoms = fields.Char(string='Prénoms', tracking=True, related="employee_id.prenoms", store=True, readonly=True, invisible=True)
    nom_complet = fields.Char(string="NOM & PRENOMS", compute="_compute_nom_complet", store=True, readonly=True)


    @api.depends('nom', 'prenoms')
    def _compute_nom_complet(self):
        for record in self:
            noms = filter(None, [record.nom, record.prenoms])  # Évite les valeurs None
            record.nom_complet = " ".join(noms)

# ----------------------------------------- METHODES ----------------------------------------------------

    @api.model
    def create(self, vals):
        """
        Identifier si un paiement est un nouveau ou ancien lors de la création
        """
        record = super(Ligneversement, self).create(vals)
        record.is_existing = True  # Marque comme ancien paiement après création
        return record


    @api.depends('loan_application_id')
    def _compute_email(self):
        for record in self:
            # Récupérer directement l'email depuis la demande de prêt
            if record.loan_application_id and record.loan_application_id.email:
                record.email = record.loan_application_id.email
            else:
                record.email = False



    @api.constrains('montant_paye')
    def _check_montant_paye(self):
        for record in self:
            if record.montant_paye < 0:
                raise ValidationError("Le montant payé doit être strictement positif.")



    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """ Remplit automatiquement la demande de prêt en fonction de l'employé sélectionné """
        if self.employee_id:
            demande = self.env['loan.application'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validated')
            ], limit=1)
            if demande:
                self.loan_application_id = demande.id
            else:
                self.loan_application_id = False
                return {
                    'warning': {
                        'title': "Aucune demande trouvée",
                        'message': f"L'employé {self.employee_id.name} n'a pas de prêt validé en cours."
                    }
                }