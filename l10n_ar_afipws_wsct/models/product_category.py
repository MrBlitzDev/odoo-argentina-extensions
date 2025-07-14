from odoo import fields, models

class ProductCategory(models.Model):
    _inherit = "product.category"

    item_type_t = fields.Selection(
        string='Tipo de Item', 
        selection=[
            ('0', 'Item general'),
            ('97', 'Anticipo'),
            ('99', 'Descuento general')
        ])
    
    cod_tur = fields.Selection(
        string='Código de Turismo', 
        selection=[
            ('1', 'Servicio de hotelería - alojamiento sin desayuno'),
            ('2', 'Servicio de hotelería - alojamiento con desayuno'),
            ('5', 'Excedente')
        ])