from odoo import models, fields, api


class LoanMutualRejectWizard(models.TransientModel):
    _name = 'loan.mutual.reject.wizard'
    _description = 'Assistant de rejet de prêt mutuel'

    motif_rejet = fields.Text(string='Motif du rejet', required=True)
    loan_id = fields.Many2one('loan.mutual', string='Demande de prêt')



    def confirm_reject(self):
        self.ensure_one()
        if self.loan_id:
            self.loan_id.write({
                'rejection_reason': self.motif_rejet,
                'state': 'rejected',
                'is_rejection': True
            })

        return {'type': 'ir.actions.act_window_close'}