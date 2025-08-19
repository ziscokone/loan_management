from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

class LoanController(http.Controller):
    @http.route('/matricule', type='http', auth='public', website=True)
    def loan_request_form(self, **kw):
        return request.render('loan_management.matricule_employee_verification')

    @http.route('/demande-pret', type='http', auth='public', website=True, methods=['POST'])
    def verify_employee(self, **post):
        matricule = post.get('matricule')
        Employee = request.env['paa.employee'].sudo()
        employee = Employee.search([('matricule', '=', matricule)], limit=1)
        
        if not employee:
            return request.render('loan_management.matricule_error', {
                'error': 'Matricule non trouvé'
            })

        campaign = request.env['loan.campaign'].sudo().search([
            ('state', '=', 'open')
        ], limit=1)

        if not campaign:
            return request.render('loan_management.campaign_error', {
                'error': 'Désolé, il n\'y a pas de campagne ouverte actuellement.'
            })

        existing_application = request.env['loan.application'].sudo().search([
            ('employee_id', '=', employee.id),
            ('campaign_id', '=', campaign.id)
        ], limit=1)

        # Récupérer les informations des responsables depuis la campagne
        responsables_data = {
            'responsable_1': campaign.responsable_1 or '',
            'contact_responsable_1': campaign.contact_responsable_1 or 0,
            'responsable_2': campaign.responsable_2 or '',
            'contact_responsable_2': campaign.contact_responsable_2 or 0,
            'responsable_3': campaign.responsable_3 or '',
            'contact_responsable_3': campaign.contact_responsable_3 or 0,
        }

        return request.render('loan_management.loan_application_form', {
            'employee': employee,
            'campaign': campaign,
            'existing_application': existing_application,
            'responsables_data': responsables_data
        })


    # -------------------------------PREVIEW LES DONNEES SAISIE DANS LE FORMULAIRE
    @http.route('/demande-pret/preview', type='http', auth='public', website=True, methods=['POST'])
    def preview_loan(self, **post):
        """Afficher un aperçu de la demande avant la soumission finale"""
        _logger.info("Prévisualisation de la demande de prêt")
        _logger.info("Données reçues: %s", post)
        
        matricule = post.get('matricule')
        employee = request.env['paa.employee'].sudo().search([('matricule', '=', matricule)], limit=1)

        if not employee:
            return request.render('loan_management.loan_result', {
                'error': True,
                'message': 'Employé non trouvé'
            })

        try:
            # Validation du montant de la demande
            amount = float(post.get('amount_requested', 0))
            if amount <= 0:
                raise ValidationError('Le montant doit être supérieur à 0.')
            
            # Validation de l'email
            email = post.get('email', '')
            if not email or '@' not in email:
                raise ValidationError('Adresse email invalide.')
            
            # Validation du téléphone
            telephone = post.get('telephone', '')
            if not telephone or len(telephone)<10:
                raise ValidationError('Numéro de téléphone invalide.')
                

            # Récupérer les données des responsables
            campaign_id = int(post.get('campaign_id', 0))
            campaign = request.env['loan.campaign'].sudo().browse(campaign_id)
            
            preview_values = {
                'matricule': employee.matricule,
                'nom': employee.name,
                'prenoms': employee.prenoms,
                'sexe': employee.sexe,
                'direction': employee.direction.name if employee.direction else '',
                'typecategorie': employee.typecat,
                'amount_requested': amount,
                'modalite_remboursement': post.get('modalite_remboursement'),
                'telephone': post.get('telephone'),
                'email': post.get('email'),
                'campaign_id': campaign_id,
                'anciennete': employee.anciennete,
                'responsable_1': campaign.responsable_1 or '',
                'contact_responsable_1': campaign.contact_responsable_1 or 0,
                'responsable_2': campaign.responsable_2 or '',
                'contact_responsable_2': campaign.contact_responsable_2 or 0,
                'responsable_3': campaign.responsable_3 or '',
                'contact_responsable_3': campaign.contact_responsable_3 or 0,
                'form_data': post  # Pour pouvoir renvoyer les données au formulaire si modification
            }

            return request.render('loan_management.loan_preview', preview_values)
            
        except ValidationError as e:
            return request.render('loan_management.loan_result', {
                'error': True,
                'message': str(e)
            })
        except Exception as e:
            _logger.error("Erreur lors de la prévisualisation: %s", str(e), exc_info=True)
            return request.render('loan_management.loan_result', {
                'error': True,
                'message': 'Une erreur est survenue lors de la prévisualisation.'
            })


    # ----------------------------------------TRAITER LES DONNEES DU FORM ET AJOUTER  A LA BD
    @http.route('/demande-pret/submit', type='http', auth='public', website=True, methods=['POST'])
    def submit_loan(self, **post):
        """Handle loan application submission"""
        _logger.info("Début du traitement de la demande de prêt")
        _logger.info("Données reçues: %s", post)
        
        matricule = post.get('matricule')
        employee = request.env['paa.employee'].sudo().search([
            ('matricule', '=', matricule)
        ], limit=1)

        if not employee:
            return request.render('loan_management.loan_result', {
                'error': True,
                'message': 'Employé non trouvé'
            })

        try:
            amount = float(post.get('amount_requested', 0))
            campaign_id = int(post.get('campaign_id', 0))
            
            # Récupérer les informations des responsables depuis la campagne
            campaign = request.env['loan.campaign'].sudo().browse(campaign_id)
            
            existing_application = request.env['loan.application'].sudo().search([
                ('employee_id', '=', employee.id),
                ('campaign_id', '=', campaign_id)
            ], limit=1)

            values = {
                'employee_id': employee.id,
                'modalite_remboursement': post.get('modalite_remboursement'),
                'telephone': post.get('telephone'),
                'email': post.get('email'),
                'amount_requested': amount,
                'campaign_id': campaign_id,
                'state': 'pending',
                # Ajouter les champs des responsables depuis la campagne
                'responsable_1': campaign.responsable_1 or '',
                'contact_responsable_1': campaign.contact_responsable_1 or 0,
                'responsable_2': campaign.responsable_2 or '',
                'contact_responsable_2': campaign.contact_responsable_2 or 0,
                'responsable_3': campaign.responsable_3 or '',
                'contact_responsable_3': campaign.contact_responsable_3 or 0,
            }
            
            if existing_application:
                _logger.info("Mise à jour de la demande existante ID: %s", existing_application.id)
                existing_application.sudo().write(values)
                application = existing_application
            else:
                _logger.info("Création d'une nouvelle demande")
                application = request.env['loan.application'].sudo().create(values)
            
            _logger.info("Demande traitée avec succès, ID: %s", application.id)


            # ENVOIE DE MAIL 
            with request.env.cr.savepoint():
                # Récupérer l'application avec un nouveau curseur
                application = request.env['loan.application'].sudo().browse(application.id)
                email_sent = application.send_confirmation_email()

            template_values = {
                'success': True,
                'matricule': employee.matricule,
                'nom': employee.name,
                'prenoms': employee.prenoms,
                'sexe': employee.sexe,
                'direction': employee.direction.name if employee.direction else '',
                'typecategorie': employee.typecat,
                'amount_requested': application.amount_requested,
                'modalite_remboursement': application.modalite_remboursement,
                'reference': application.reference,
                'mensualite': application.mensualite,
                'anciennete': employee.anciennete,
                'is_update': bool(existing_application),
                'email_sent': email_sent,
                # Inclure les responsables dans les valeurs du template
                'responsable_1': application.responsable_1,
                'contact_responsable_1': application.contact_responsable_1,
                'responsable_2': application.responsable_2,
                'contact_responsable_2': application.contact_responsable_2,
                'responsable_3': application.responsable_3,
                'contact_responsable_3': application.contact_responsable_3
            }

            if not email_sent:
                template_values['warning_message'] = "Votre demande a été enregistrée mais l'envoi de l'email de confirmation a échoué."

            return request.render('loan_management.loan_result', template_values)
            
        except Exception as e:
            _logger.error("Erreur inattendue lors du traitement de la demande: %s", str(e), exc_info=True)
            request.env.cr.rollback()
            return request.render('loan_management.loan_result', {
                'error': True,
                'message': 'Une erreur est survenue lors du traitement de votre demande.'
            })