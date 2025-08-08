from odoo import _, models
from odoo.addons.l10n_ar_afipws_wsct.afip_utils import get_invoice_number_from_response

class AccountMove(models.Model):
    _inherit = "account.move"

    def _set_next_sequence(self):
        if self.journal_id.afip_ws != 'wsct':
            return super()._set_next_sequence()
        
        if self.afip_auth_code and self.journal_id.afip_ws and self.afip_xml_response:
            invoice_number = get_invoice_number_from_response(self.afip_xml_response)
            if invoice_number:
                last_sequence = self._get_formatted_sequence(invoice_number)
                format, format_values = self._get_sequence_format_param(last_sequence)
                format_values['year'] = self[self._sequence_date_field].year % (10 ** format_values['year_length'])
                format_values['month'] = self[self._sequence_date_field].month
                format_values['seq'] = invoice_number

                self[self._sequence_field] = format.format(**format_values)
                return
        super()._set_next_sequence()
