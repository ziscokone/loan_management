from odoo import models, fields, api


class CheckCancelWizard(models.TransientModel):
    _name = 'check.cancel.wizard'
    _description = 'Assistant d\' annulation de chèque MAPAA'

    motif_rejet = fields.Text(string='Motif du rejet', required=True)
    loan_id = fields.Many2one('loan.mutual', string='Demande de prêt')


    def confirm_cancel_check(self):
        self.ensure_one()
        if self.loan_id:

            # Restaurer le budget avant de modifier l'état
            self.loan_id.restore_campaign_budget()

            self.loan_id.write({
                'reason_for_check_rejection': self.motif_rejet,
                'state': 'check_cancel'
            })

        return {'type': 'ir.actions.act_window_close'}