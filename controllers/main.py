from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)

class LoanController(http.Controller):
    @http.route('/verif-matricule', type='http', auth='public', website=True)
    def loan_request_form(self, **kw):
        return request.render('loan_mutual.matricule_employee_verification')


    @http.route('/pret-mutuel', type='http', auth='public', website=True, methods=['POST'])
    def verify_employee(self, **post):
        matricule = post.get('matricule')
        Employee = request.env['paa.employee'].sudo()
        employee = Employee.search([('matricule', '=', matricule)], limit=1)
        
        if not employee:
            return request.render('loan_mutual.matricule_error', {
                'error': 'Matricule non trouvé'
            })

        campaign = request.env['mutual.campaign'].sudo().search([
            ('state', '=', 'open')
        ], limit=1)

        if not campaign:
            return request.render('loan_mutual.campaign_error', {
                'error': 'Désolé, il n\'y a pas de campagne ouverte actuellement.'
            })

        existing_application = request.env['loan.mutual'].sudo().search([
            ('employee_id', '=', employee.id),
            ('campaign_id', '=', campaign.id)
        ], limit=1)

        return request.render('loan_mutual.loan_application_form', {
            'employee': employee,
            'campaign': campaign,
            'existing_application': existing_application
        })


    # -------------------------------PREVIEW LES DONNEES SAISIE DANS LE FORMULAIRE
    @http.route('/demande-pret/preview', type='http', auth='public', website=True, methods=['POST'])
    def preview_loan(self, **post):
        """Afficher un aperçu de la demande avant la soumission finale"""
        _logger.info("Prévisualisation de la demande de prêt")
        _logger.info("Données reçues: %s", post)
        
        matricule = post.get('matricule')
        employee = request.env['paa.employee'].sudo().search([
            ('matricule', '=', matricule)
        ], limit=1)

        if not employee:
            return request.render('loan_mutual.loan_result', {
                'error': True,
                'message': 'Employé non trouvé'
            })


        # Vérification des prêts non soldés
        unsettled_loans = request.env['loan.mutual'].sudo().search([
            ('employee_id', '=', employee.id),
            ('is_on_sale', '=', False)
        ], limit=1)
        
        if unsettled_loans:
            # Préparation des informations détaillées sur le prêt non soldé
            campaign_name = unsettled_loans.campaign_id.name if unsettled_loans.campaign_id else 'N/A'
            remaining_amount = unsettled_loans.montant_restant if hasattr(unsettled_loans, 'montant_restant') else 'N/A'
            reference = unsettled_loans.reference if hasattr(unsettled_loans, 'reference') else 'N/A'
            
            # Si remaining_amount est un nombre (float ou int)
            if isinstance(remaining_amount, (float, int)):
                # Format avec séparateur de milliers (espace pour le format français)
                formatted_amount = "{:,.0f}".format(remaining_amount).replace(",", " ")
            else:
                formatted_amount = remaining_amount

            message = f"""
            <div style="margin-bottom: 10px;">Vous avez déjà un prêt non soldé. Veuillez solder votre prêt actuel avant de faire une nouvelle demande.</div>
            <div style="margin-bottom: 10px;"><strong>Détails du prêt non soldé:</strong></div>
            <p>Campagne: {campaign_name}</p>
            <p>- Référence: {reference}</p>
            <p>- Montant restant à payer: {formatted_amount} FCFA</p>
            """
            
            return request.render('loan_mutual.loan_result', {
                'error': True,
                'message': message
            })

        try:
            # Validation du montant
            try:
                amount = float(post.get('amount_requested', 0))
                if amount <= 0:
                    raise ValidationError('Le montant doit être supérieur à 0.')
            except ValueError:
                raise ValidationError('Montant invalide.')

            # Validation du motif
            motif_demande = post.get('motif_demande')
            if not motif_demande:
                raise ValidationError('Le motif de la demande est requis.')

            # Validation du TELEPHONE
            telephone = post.get('telephone')
            if not telephone:
                raise ValidationError('Le champs Téléphone est requis.')

            # Validation et traitement du fichier PDF
            files = request.httprequest.files
            if 'justificatif' not in files:
                raise ValidationError('La pièce d\'identité est requise.')

            justificatif = files['justificatif']
            
            # Vérification du type de fichier
            if not justificatif.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError('Le fichier doit être au format JPG, JPEG ou PNG.')

            # Vérification de la taille du fichier (5 Mo max)
            file_data = justificatif.read()
            if len(file_data) > 5 * 1024 * 1024:
                raise ValidationError('La taille du fichier ne doit pas dépasser 5 Mo.')

            # Encodage du fichier pour la transmission
            cotite_data = base64.b64encode(file_data).decode('utf-8')
            _logger.info("Fichier bien encodé: %s", cotite_data)

            # Stocker le fichier encodé pour le transmettre au formulaire suivant
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
                'telephone_2': post.get('telephone_2'),
                'email': post.get('email'),
                'type_pret': post.get('type_pret'),
                'campaign_id': int(post.get('campaign_id', 0)),
                'anciennete': employee.anciennete,
                'motif_demande': motif_demande,
                'justificatif': cotite_data,
                'form_data': post
            }

            return request.render('loan_mutual.loan_preview', preview_values)
            
        except ValidationError as e:
            return request.render('loan_mutual.loan_result', {
                'error': True,
                'message': str(e)
            })
        except Exception as e:
            _logger.error("Erreur lors de la prévisualisation: %s", str(e), exc_info=True)
            return request.render('loan_mutual.loan_result', {
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
            return request.render('loan_mutual.loan_result', {
                'error': True,
                'message': 'Employé non trouvé'
            })

        try:
            # --------------------------Vérification des prêts non soldés----------------
            unsettled_loans = request.env['loan.mutual'].sudo().search([
                ('employee_id', '=', employee.id),
                ('is_on_sale', '=', False)
            ], limit=1)
            
            if unsettled_loans:
                # Préparation des informations détaillées sur le prêt non soldé
                campaign_name = unsettled_loans.campaign_id.name if unsettled_loans.campaign_id else 'N/A'
                remaining_amount = unsettled_loans.montant_restant if hasattr(unsettled_loans, 'montant_restant') else 'N/A'
                reference = unsettled_loans.reference if hasattr(unsettled_loans, 'reference') else 'N/A'
                # approved_date = unsettled_loans.approval_date.strftime('%d/%m/%Y') if hasattr(unsettled_loans, 'approval_date') and unsettled_loans.approval_date else 'N/A'
                
                message = f"""Vous avez déjà un prêt non soldé. Veuillez solder votre prêt actuel avant de faire une nouvelle demande.
                
                Détails du prêt non soldé:

                - Campagne: {campaign_name}
                - Référence: {reference}
                - Montant restant à payer: {remaining_amount} FCFA

                """
                
                return request.render('loan_mutual.loan_result', {
                    'error': True,
                    'message': message
                })
# -------------------------Fin Vérification des prêts non soldés --------------------

            # Récupération des données du fichier depuis le champ caché
            cotite_data = None
            
            # Vérifier si les données encodées du fichier sont disponibles dans le post
            if post.get('justificatif_b64'):
                cotite_data = post.get('justificatif_b64')
                _logger.info("Fichier récupéré depuis le champ caché (encodé en base64)")
            else:
                # Fallback: vérifier si le fichier est encore disponible dans la requête
                files = request.httprequest.files
                _logger.info("Files dans la requête: %s", files)
                
                if 'justificatif' in files:
                    file = files['justificatif']
                    
                    # Vérification du type de fichier
                    if not file.filename.lower().endswith('.pdf'):
                        return request.render('loan_mutual.loan_result', {
                            'error': True,
                            'message': 'Le fichier doit être au format PDF'
                        })

                    # Lecture et encodage du fichier
                    file_data = file.read()
                    cotite_data = base64.b64encode(file_data).decode('utf-8')
                    _logger.info("Fichier récupéré depuis la requête HTTP")
            
            # Vérifier si on a bien récupéré le fichier
            if not cotite_data:
                _logger.error("Fichier justificatif manquant")
                return request.render('loan_mutual.loan_result', {
                    'error': True,
                    'message': 'Le fichier justificatif est requis'
                })

            amount = float(post.get('amount_requested', 0))
            campaign_id = int(post.get('campaign_id', 0))
            
            existing_application = request.env['loan.mutual'].sudo().search([
                ('employee_id', '=', employee.id),
                ('campaign_id', '=', campaign_id)
            ], limit=1)

            values = {
                'employee_id': employee.id,
                'modalite_remboursement': post.get('modalite_remboursement'),
                'telephone': post.get('telephone'),
                'telephone_2': post.get('telephone_2'),
                'email': post.get('email'),
                'type_pret': post.get('type_pret'),
                'amount_requested': amount,
                'campaign_id': campaign_id,
                'motif_demande': post.get('motif_demande'),
                'piece_identite': cotite_data,
                'state': 'pending'
            }
            
            _logger.info("Valeurs à enregistrer: %s", values)
            
            if existing_application:
                _logger.info("Mise à jour de la demande existante ID: %s", existing_application.id)
                existing_application.sudo().write(values)
                application = existing_application
            else:
                _logger.info("Création d'une nouvelle demande")
                application = request.env['loan.mutual'].sudo().create(values)
            
            _logger.info("Demande traitée avec succès, ID: %s", application.id)

            # Nettoyer la session après utilisation si nécessaire
            if 'justificatif_data' in request.session:
                del request.session['justificatif_data']

            # ENVOI DE MAIL
            with request.env.cr.savepoint():
                application = request.env['loan.mutual'].sudo().browse(application.id)
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
                'motif_demande': application.motif_demande,
                'reference': application.reference,
                'anciennete': employee.anciennete,
                'is_update': bool(existing_application),
                'email_sent': email_sent
            }

            # if not email_sent:
            #     template_values['warning_message'] = "Votre demande a été enregistrée mais l'envoi de l'email de confirmation a échoué."

            return request.render('loan_mutual.loan_result', template_values)
            
        except Exception as e:
            _logger.error("Erreur inattendue lors du traitement de la demande: %s", str(e), exc_info=True)
            request.env.cr.rollback()
            return request.render('loan_mutual.loan_result', {
                'error': True,
                'message': 'Une erreur est survenue lors du traitement de votre demande.'
            })