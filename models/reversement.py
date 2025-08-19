from odoo import models, fields, api
import base64
import xlrd
import logging
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)



class Reversement(models.Model):
    _name = 'reversement'
    _description = 'Reversement du PAA 002'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "mois"


    date = fields.Date(
        string='Date', 
        required=True, 
        default=fields.Datetime.now,
        tracking=True
    )
    campagne_id = fields.Many2one(
        'loan.campaign', 
        string='Campagne', 
        required=True,
        domain="[('state', '=', 'suivie')]", 
        tracking=True
    )
    fichier_excel = fields.Binary(string='Fichier Excel')
    nom_fichier = fields.Char(string='Nom du fichier')
    ligne_ids = fields.One2many(
        'ligne.versement', 
        'reversement_id', 
        string='Lignes de Prélèvement'
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé')
    ], string='État', default='draft', tracking=True)

    total_montant = fields.Integer(
        string='Montant Total', 
        compute='_compute_total_montant', 
        store=True
    )

    mois = fields.Selection([
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
    ], string='Mois', required=True)
    
# -------------------------------------METHODES ---------------------------------------------
    @api.depends('ligne_ids.montant_paye')
    def _compute_total_montant(self):
        for record in self:
            record.total_montant = sum(record.ligne_ids.mapped('montant_paye'))


    def _clean_matricule(self, matricule):
        """Nettoie le matricule en vérifiant le préfixe I00"""
        try:
            if isinstance(matricule, float):
                matricule = str(int(matricule))
            else:
                matricule = str(matricule).strip()

            if not matricule.upper().startswith('I00'):
                return False, f"Le matricule {matricule} ne commence pas par I00"

            matricule_clean = matricule[3:]
            return True, matricule_clean

        except Exception as e:
            return False, f"Erreur de format pour le matricule {matricule}: {str(e)}"



    # QUAND LA CAMPAGNE EN ETAT 'SUIVIE' EST SELECTIONNER AVEC LE FICHIER EXCEL CONTENANT LES DONNEES : on commence le porces a afficher les lignes 
    @api.onchange('fichier_excel', 'campagne_id')
    def _onchange_fichier_excel(self):
        if not self.fichier_excel or not self.campagne_id:
            return

        _logger.info(f"Début du traitement - Campagne ID: {self.campagne_id.id}, State: {self.campagne_id.state}")

        if self.campagne_id.state != 'suivie':
            return {
                'warning': {
                    'title': 'Erreur',
                    'message': 'La campagne sélectionnée n\'est pas en statut "suivi"'
                }
            }

        try:
            excel_data = base64.b64decode(self.fichier_excel)
            wb = xlrd.open_workbook(file_contents=excel_data)
            sheet = wb.sheet_by_index(0)

            # Vérification des nouveaux en-têtes
            headers = [str(cell.value).strip().upper() for cell in sheet.row(0)]
            expected_headers = ['MATRICULE', 'NOM', 'PRENOMS', 'MENSUALITE']
            
            if headers != expected_headers:
                return {
                    'warning': {
                        'title': 'Format incorrect',
                        'message': f'Les en-têtes attendus sont : {", ".join(expected_headers)}'
                    }
                }

            _logger.info(f"En-têtes trouvés: {headers}")

            self.ligne_ids = [(5, 0, 0)]
            lignes_valides = []
            lignes_erreur = []

            # Recherche des demandes validées
            demandes_validees = self.env['loan.application'].search([
                ('campaign_id', '=', self.campagne_id.id),
                ('state', '=', 'validated')
            ])
            
            _logger.info(f"Nombre de demandes validées trouvées: {len(demandes_validees)}")
            demandes_par_matricule = {d.employee_id.matricule: d for d in demandes_validees}

            # Lecture des lignes
            for row_idx in range(1, sheet.nrows):
                try:
                    row = sheet.row_values(row_idx)
                    matricule_original = str(row[0]).strip()
                    is_valid, matricule = self._clean_matricule(matricule_original)
                    
                    if not is_valid:
                        lignes_erreur.append(f"Ligne {row_idx + 1}: Matricule invalide - {matricule_original}")
                        continue

                    try:
                        montant = float(row[3])  # MENSUALITE est maintenant à l'index 3
                    except ValueError:
                        lignes_erreur.append(f"Ligne {row_idx + 1}: Montant invalide - {row[3]}")
                        continue

                    demande = demandes_par_matricule.get(matricule)
                    
                    if demande:
                        vals = {
                            'employee_id': demande.employee_id.id,
                            'montant_paye': montant,
                            'loan_application_id': demande.id
                        }
                        lignes_valides.append((0, 0, vals))
                    else:
                        lignes_erreur.append(
                            f"Ligne {row_idx + 1}: Matricule {matricule_original} - Aucune demande validée trouvée"
                        )

                except Exception as e:
                    _logger.error(f"Erreur sur la ligne {row_idx + 1}: {str(e)}")
                    lignes_erreur.append(f"Ligne {row_idx + 1}: Erreur - {str(e)}")

            if lignes_valides:
                self.ligne_ids = lignes_valides
                _logger.info(f"Nombre total de lignes valides créées: {len(lignes_valides)}")

            if lignes_erreur:
                return {
                    'warning': {
                        'title': 'Certaines lignes n\'ont pas été importées',
                        'message': '\n'.join(lignes_erreur)
                    }
                }

        except Exception as e:
            _logger.error(f"Erreur générale: {str(e)}")
            return {
                'warning': {
                    'title': 'Erreur',
                    'message': f'Erreur lors de la lecture du fichier: {str(e)}'
                }
            }


# ACTION DE VALIDATION D'UN VERSEMENT 
    def action_validate(self):
        """Valider le reversement et envoyer les notifications."""
        for record in self:
            if not record.ligne_ids:
                raise UserError("Impossible de valider un versement sans lignes.")
            
            # Validation du reversement
            record.write({
                'state': 'validated'
            })

            # Récupération du template
            template = self.env.ref('loan_management.versement_notification_email_template', raise_if_not_found=False)
            if not template:
                _logger.error("Template d'email de notification de versement non trouvé")
            else:
                # Envoi des emails pour chaque ligne
                for ligne in record.ligne_ids:
                    # Vérification de l'email dans la demande de prêt
                    if not ligne.loan_application_id.email:
                        _logger.warning(
                            "Email manquant dans la demande de prêt pour l'employé %s %s", 
                            ligne.loan_application_id.nom,
                            ligne.loan_application_id.prenoms
                        )
                        continue

                    try:
                        # Envoi de l'email
                        # template.send_mail(
                        #     ligne.id,
                        #     force_send=True,
                        #     email_values={
                        #         'email_to': ligne.loan_application_id.email,
                        #         'author_id': self.env.user.partner_id.id
                        #     }
                        # )
                        _logger.info(
                            "Email de notification envoyé à %s pour le versement de %s FCFA",
                            ligne.loan_application_id.email,
                            ligne.montant_paye
                        )
                    except Exception as e:
                        _logger.error(
                            "Erreur lors de l'envoi de l'email à %s: %s",
                            ligne.loan_application_id.email,
                            str(e)
                        )

            # Log de la validation
            _logger.info(
                'Reversement %s validé avec %s lignes pour un montant total de %s',
                record.mois,
                len(record.ligne_ids),
                record.total_montant
            )

            # Message toast de confirmation
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Succès',
                    'message': f'Le prélèvement du mois de {record.mois} a été validé avec succès.',
                    # 'message': f'Le reversement du mois de {record.mois} a été validé et les notifications ont été envoyées !',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }