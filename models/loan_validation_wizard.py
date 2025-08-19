from odoo import models, fields, api
from odoo.exceptions import UserError

class LoanValidationWizard(models.TransientModel):
    _name = 'loan.validation.wizard'
    _description = 'Assistant de validation de prêt'

    loan_id = fields.Many2one('loan.application', string='Demande de prêt')
    campaign_name = fields.Char(string='Nom de la campagne', readonly=True)
    remaining_budget = fields.Integer(string='Budget restant', readonly=True)
    amount_requested = fields.Integer(string='Montant demandé', readonly=True)
    approved_amount = fields.Integer(string='Montant accordé', required=True)

    # Champs permettant d'envoyer mail 
    send_email = fields.Boolean(string="Envoyer un email de notification", default=True)

    @api.model
    def default_get(self, fields):
        res = super(LoanValidationWizard, self).default_get(fields)
        loan_id = self.env.context.get('active_id')
        if loan_id:
            loan = self.env['loan.application'].browse(loan_id)
            res.update({
                'loan_id': loan.id,
                'campaign_name': loan.campaign_id.name,
                'remaining_budget': loan.campaign_id.budget_restant,  # Utiliser budget_restant au lieu de total_budget
                'amount_requested': loan.amount_requested,
                'approved_amount': loan.amount_requested,
            })
        return res



    def validate_loan(self):
        """Méthode pour valider le prêt depuis le wizard"""
        self.ensure_one()
        loan_application = self.env['loan.application'].browse(self._context.get('active_id'))

        if not self.approved_amount:
            raise UserError('Veuillez saisir le montant accordé.')

        # Vérifié si le montant accordé dépasse le montant demandé         
        if self.approved_amount > self.amount_requested:
            raise UserError('Le montant accordé ne peut pas être supérieur au montant demandé.')
        
        
        # Calculer le nouveau budget restant
        new_remaining_budget = self.remaining_budget - self.approved_amount
        
        # Mettre à jour le budget restant de la campagne
        self.loan_id.campaign_id.write({
            'budget_restant': new_remaining_budget
        })
            
        # Mettre à jour la demande de prêt
        self.loan_id.write({
            'approved_amount': self.approved_amount,
            'state': 'validated'
        })


        
        # APRES VALIDATION D'UNE DEMANDE DE PRET FORCER LE RECALUL DANS LE MODEL COMITE DE VALIDATION POUR METTRE LE MONTANT TOTAL ACCORDE POUR LA CAMPAGNE A JOUR EN TEMPS REEL
        comite_validation = self.env['comite.validation'].search([('campaign_id', '=', self.loan_id.campaign_id.id)])

        comite_validation.action_refresh_demandes()

        # comite_validation._compute_total_montant_accorde()
        # comite_validation._compute_demandes_en_attente()



        # Envoyer l'email de notification si l'option est cochée
        if self.send_email:
            loan_application.send_validation_email()
        
        return {'type': 'ir.actions.act_window_close'}