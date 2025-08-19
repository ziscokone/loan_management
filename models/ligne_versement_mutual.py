from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Ligneversement(models.Model):
    _name = 'ligne.versement'
    _description = 'Ligne de reversement du Prêt Mutuel'

    reversement_id = fields.Many2one(
        'mutual.reversement', 
        string='Prélèvement', 
        required=True
    )
    
    employee_id = fields.Many2one(
        'paa.employee', 
        string='Matricule', 
        required=True
    )

    montant_paye = fields.Integer(
        string='Montant Payé', 
        required=True
    )

    loan_mutual_id = fields.Many2one(
        'loan.mutual', 
        string='Demande de Prêt', 
        required=True
    )

    is_existing = fields.Boolean(string="Ancien Paiement", default=False, invisible =True)
  
# -------------------------------------------------------------------------------------------------------------------

    @api.model
    def create(self, vals):
        """
        Identifier si un paiement est un nouveau ou ancien lors de la création
        """
        record = super(Ligneversement, self).create(vals)
        record.is_existing = True  # Marque comme ancien paiement après création
        return record



    @api.constrains('montant_paye')
    def _check_montant_paye(self):
        for record in self:
            if record.montant_paye < 0:
                raise ValidationError("Le montant payé doit être strictement positif.")



    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """ Remplit automatiquement la demande de prêt en fonction de l'employé sélectionné """
        if self.employee_id:
            demande = self.env['loan.mutual'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'check_delivery')
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