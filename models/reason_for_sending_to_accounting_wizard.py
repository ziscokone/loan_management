from odoo import models, fields, api


class SendindToAccountingWizard(models.TransientModel):
    _name = 'sending.to.accounting.wizard'
    _description = 'Assistant d\'envoie de demande à la comptabilité par la Secrétaire Exécutive'

    motif_envoie_comptabilite = fields.Text(string="Motif d'envoie à la comptabilité", required=True)
    loan_id = fields.Many2one('loan.mutual', string='Demande de prêt', invisible=True)


    def confirm_sending_to_accounting(self):
        self.ensure_one()
        if self.loan_id:
            self.loan_id.write({
                'reason_for_sending_to_accounting': self.motif_envoie_comptabilite,
                'state': 'approved'
            })

        return {'type': 'ir.actions.act_window_close'}