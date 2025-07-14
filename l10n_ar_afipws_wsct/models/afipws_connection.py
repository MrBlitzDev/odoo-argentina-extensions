from odoo import fields, models

class AfipwsConnection(models.Model):
    _inherit = "afipws.connection"

    afip_ws = fields.Selection(
        selection_add=[
            ("wsct", "Comprobantes de Turismo - Web Service"),
        ],
        ondelete={
            "wsct": "set default",
        },
    )

    def _get_ws(self, afip_ws):
        ws = super()._get_ws(afip_ws)
        if afip_ws == "wsct":
            from pyafipws.wsct import WSCT

            ws = WSCT()
        return ws

    def get_afip_ws_url(self, afip_ws, environment_type):
        afip_ws_url = super().get_afip_ws_url(afip_ws, environment_type)
        if afip_ws == "wsct":
            if environment_type == "production":
                afip_ws_url = "https://serviciosjava.afip.gob.ar/wsct/CTService?wsdl"
            else:
                afip_ws_url = "https://fwshomo.afip.gov.ar/wsct/CTService?wsdl"
        return afip_ws_url