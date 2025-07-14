from odoo import models, _

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_journal_letter(self, counterpart_partner=False):
        if self.afip_ws == 'wsct':
            letters = ['T']
        else:
            letters = super()._get_journal_letter(counterpart_partner)
        
        return letters
    
    def _get_codes_per_journal_type(self, afip_pos_system):
        if self.afip_ws == 'wsct':
            codes = ['195', '196', '197']
            return [('code', 'in', codes)]
        codes = super()._get_codes_per_journal_type(afip_pos_system)
        return codes
    
    def _get_l10n_ar_afip_pos_types_selection(self):
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.insert(0, ("WSCT", _("Comprobantes de Turismo - Web Service")))
        return res
    
    def _get_afip_ws(self):
        res = super()._get_afip_ws()
        res.insert(0, ("wsct", _("Turismo - with detail - RG3971 (WSCT)")))
        return res
    
    def _get_type_mapping(self):
        res = super()._get_type_mapping()
        res["WSCT"] = "wsct"
        return res