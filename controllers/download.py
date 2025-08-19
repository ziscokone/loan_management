from odoo import http
from odoo.http import request
import json

class LoanApplicationController(http.Controller):
    
    @http.route(['/demande-pret/download/<string:reference>'], type='http', auth="user", website=True)
    def download_loan_recap(self, reference, **kw):
        try:
            loan_application = request.env['loan.application'].sudo().search([
                ('reference', '=', reference)
            ], limit=1)

            if not loan_application:
                return request.redirect('/404')

            # Vérification que l'utilisateur actuel est bien le propriétaire de la demande
            if request.env.user.employee_id != loan_application.employee_id:
                return request.redirect('/404')

            # Génération du PDF
            pdf_content = request.env.ref('loan_management.action_report_loan_application')._render_qweb_pdf(loan_application.ids)[0]

            # Configuration de la réponse HTTP
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename=Recap_Pret_{reference}.pdf')
            ]
            
            return request.make_response(pdf_content, headers=pdfhttpheaders)
            
        except Exception as e:
            return request.redirect('/404')