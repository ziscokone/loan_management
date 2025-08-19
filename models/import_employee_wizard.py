from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import xlrd

class EmployeeImportWizard(models.TransientModel):
    _name = 'employee.import.wizard'
    _description = 'Assistant d\'importation des employés'

    file = fields.Binary(string="Fichier Excel", required=True)
    filename = fields.Char(string="Nom du fichier")

    def import_employees(self):
        if not self.file:
            raise UserError("Veuillez sélectionner un fichier Excel.")
        
        try:
            # Lire le fichier Excel
            file_data = base64.b64decode(self.file)
            workbook = xlrd.open_workbook(file_contents=file_data)
            sheet = workbook.sheet_by_index(0)

            # Parcourir les lignes
            for row_idx in range(1, sheet.nrows):  # Ignorer la première ligne (entête)
                name = sheet.cell_value(row_idx, 0)
                job_title = sheet.cell_value(row_idx, 1)
                department = sheet.cell_value(row_idx, 2)
                email = sheet.cell_value(row_idx, 3)
                phone = sheet.cell_value(row_idx, 4)

                # Créer l'employé
                self.env['employee'].create({
                    'name': name,
                    'job_title': job_title,
                    'department': department,
                    'email': email,
                    'phone': phone,
                })
        except Exception as e:
            raise UserError(f"Erreur lors de l'importation : {str(e)}")
