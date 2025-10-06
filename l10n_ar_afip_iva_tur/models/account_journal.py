from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = "account.journal"
    
    # Lo agrego acá y no en el módulo wsct porque este campo no es suficiente para enviar a ARCA
    # Es solamente para enviar en el reporte

    l10n_ar_afip_wsct_payment_type = fields.Selection(
        [
            ('1', 'Tarjeta de crédito'),
            ('2', 'Tarjeta de débito'),
            ('3', 'Transferencia Bancaria'),
        ],
        string="Forma de pago",
    )
