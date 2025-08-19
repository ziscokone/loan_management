from odoo import models, fields, api
import xlrd
import base64
from datetime import datetime
from odoo.exceptions import UserError

class EmployeeImport(models.TransientModel):
    _name = 'paa.employee.import'
    _description = 'Import des employés depuis Excel'

    file = fields.Binary(string='Fichier Excel', required=True)
    filename = fields.Char(string='Nom du fichier')

    def import_employee_data(self):
        try:
            # Décoder le fichier
            excel_data = base64.b64decode(self.file)
            book = xlrd.open_workbook(file_contents=excel_data)
            sheet = book.sheet_by_index(0)

            # Définir les correspondances entre les colonnes Excel et les champs Odoo
            field_mapping = {
                'matricule': 0,  # Colonne A
                'nom': 1,        # Colonne B
                'prenoms': 2,    # Colonne C
                'date_naissance': 3,
                'date_embauche': 4,
                'date_prise_service': 5,
                'intitule_poste': 6,
                'fonction': 7,
                'categorie': 8,
                'categorie_actuelle': 9,
                'sexe': 10,
                'direct': 11,
                'departement': 12,
                'service': 13,
                'site_localite': 14,
                'typecat': 15
            }

            # Parcourir les lignes du fichier Excel
            for row_index in range(1, sheet.nrows):  # Commencer à 1 pour ignorer l'en-tête
                row_data = {}
                
                for field, col_index in field_mapping.items():
                    value = sheet.cell(row_index, col_index).value

                    # Conversion des dates
                    if field in ['date_naissance', 'date_embauche', 'date_prise_service']:
                        if isinstance(value, float):  # Excel stocke les dates comme des nombres
                            try:
                                value = xlrd.xldate.xldate_as_datetime(value, book.datemode)
                                value = value.strftime('%Y-%m-%d')
                            except xlrd.XLDateError:
                                value = False
                        else:
                            value = False

                    # Conversion du sexe
                    if field == 'sexe':
                        value = 'M' if value.upper() in ['M', 'MASCULIN'] else 'F' if value.upper() in ['F', 'FEMININ'] else False

                    row_data[field] = value

                # Calculer l'année de naissance et l'année d'embauche
                if row_data.get('date_naissance'):
                    row_data['annee_naissance'] = int(row_data['date_naissance'][:4])
                if row_data.get('date_embauche'):
                    row_data['annee_embauche'] = int(row_data['date_embauche'][:4])

                # Créer ou mettre à jour l'employé
                existing_employee = self.env['paa.employee'].search([('matricule', '=', row_data['matricule'])])
                if existing_employee:
                    existing_employee.write(row_data)
                else:
                    self.env['paa.employee'].create(row_data)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Succès',
                    'message': 'Importation réussie des employés',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(f"Erreur lors de l'importation: {str(e)}")