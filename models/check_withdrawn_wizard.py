from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class CheckWithdrawnWizard(models.TransientModel):
    _name = 'check.withdrawn.wizard'
    _description = 'Assistant de retrait de chèque MA-PAA'

    mois_debut_prevelement = fields.Selection([
        ('janvier', 'Janvier'),
        ('fevrier', 'Février'),
        ('mars', 'Mars'),
        ('avril', 'Avril'),
        ('mai', 'Mai'),
        ('juin', 'Juin'),
        ('juillet', 'Juillet'),
        ('aout', 'Août'),
        ('septembre', 'Septembre'),
        ('octobre', 'Octobre'),
        ('novembre', 'Novembre'),
        ('decembre', 'Décembre'),
    ], string='Mois de Début de Prélèvement', required=True)

    create_date = fields.Datetime(string='Date Création',default=fields.Datetime.now,readonly=True)
    loan_id = fields.Many2one('loan.mutual', string='Demande de prêt')

        
    def confirm_withdrawn_check(self):
        self.ensure_one()
        if self.loan_id:
            # Mettre à jour l'enregistrement du prêt
            self.loan_id.write({
                'start_date_deduction': self.mois_debut_prevelement,
                'start_date_deduct': self.create_date,
                'state': 'check_withdrawn'
            })
            
            # Envoyer l'email de confirmation de retrait
            self.send_check_withdrawal_email()
            
        return {'type': 'ir.actions.act_window_close'}
    
    def send_check_withdrawal_email(self):
        """Envoie un email de confirmation de retrait de chèque"""
        self.ensure_one()
        
        if not self.loan_id:
            _logger.error("Impossible d'envoyer l'email: aucun prêt associé")
            return False
            
        try:
            _logger.info("Début de l'envoi du mail de confirmation de retrait pour la demande %s", self.loan_id.reference)
            
            template = self.env.ref('loan_mutual.check_withdrawal_email_template', raise_if_not_found=True)
            if not template:
                _logger.error("Template d'email non trouvé pour la demande %s", self.loan_id.reference)
                return False
                
            if not self.loan_id.email:
                _logger.error("Aucune adresse email fournie pour la demande %s", self.loan_id.reference)
                return False

            # Définir l'adresse email d'envoi
            company_email = self.env.company.email or 'noreply@paa.com'  # Email par défaut
            
            _logger.info("Informations d'envoi:")
            _logger.info("- Template ID: %s", template.id)
            _logger.info("- Application ID: %s", self.loan_id.id)
            _logger.info("- Email destinataire: %s", self.loan_id.email)
            _logger.info("- Email expéditeur: %s", company_email)

            try:
                mail_id = template.send_mail(
                    self.loan_id.id, 
                    force_send=True,
                    email_values={
                        'email_to': self.loan_id.email,
                        'email_from': company_email
                    }
                )
                
                _logger.info(
                    "Mail de confirmation de retrait envoyé avec succès pour la demande %s (ID mail: %s)", 
                    self.loan_id.reference, 
                    mail_id
                )
                return True
                
            except Exception as mail_error:
                _logger.error(
                    "Erreur d'envoi de mail de confirmation de retrait: %s", 
                    str(mail_error),
                    exc_info=True
                )
                return False
                
        except Exception as e:
            _logger.error(
                "Erreur générale lors de l'envoi du mail de confirmation de retrait pour la demande %s: %s", 
                self.loan_id.reference, 
                str(e),
                exc_info=True
            )
            return False