from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    codigo_relacion = fields.Selection(
        string='Código de Relación', 
        selection=[
            ('1', 'Alojamiento Directo a Turista No Residente'),
            ('2', 'Alojamiento a Agencia de Viaje Residente'),
            ('3', 'Alojamiento a Agencia de Viaje No Residente')
        ])