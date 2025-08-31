# l10n_ar_afip_iva_tur/wizard/afip_iva_tur_wizard.py

from odoo import fields, models, _, tools
from odoo.exceptions import UserError
import base64
import io
import datetime
import logging

_logger = logging.getLogger(__name__)

class AfipIvaTurWizard(models.TransientModel):
    _name = 'afip.iva.tur.wizard'
    _description = 'AFIP IVA Turismo Exportable Wizard - Generador de Reporte'

    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: datetime.date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: datetime.date.today()
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    # Ya no necesitamos date_payment o los campos de archivo aquí, porque el reporte persistente los tendrá.
    # exported_file = fields.Binary(...)
    # exported_filename = fields.Char(...)

    def action_create_iva_tur_report(self):
        """ Crea un nuevo registro de afip.iva.tur.report y lo abre. """
        self.ensure_one()
        report_record = self.env['afip.iva.tur.report'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            # No hay fecha de pago aquí, se la ponemos cuando se genera el archivo desde el reporte
            'state': 'draft', # Siempre inicia como borrador
        })

        # Retorna una acción para abrir la vista de formulario del nuevo reporte creado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'afip.iva.tur.report',
            'view_mode': 'form',
            'res_id': report_record.id,
            'target': 'current', # Abre en la ventana principal de Odoo
            'context': self.env.context,
        }

    # Eliminamos el método _generate_file_content y _get_export_filename de aquí,
    # ya que la lógica de generación de archivo se moverá a afip.iva.tur.report
    # o a un método compartido.
    # def _generate_file_content(self):
    #     pass
    # def _get_export_filename(self):
    #     pass