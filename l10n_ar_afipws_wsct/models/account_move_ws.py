from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def wsct_request_autorization(self, ws):
        ws.CAESolicitar()

    def wsct_map_invoice_info(self):
        invoice_info = self.base_map_invoice_info()
        invoice_info["imp_reintegro"] = None
        return invoice_info
    
    def wsct_pyafipws_create_invoice(self, ws, invoice_info):
        ws.CrearFactura(
            invoice_info["tipo_doc"],
            invoice_info["nro_doc"],
            invoice_info["doc_afip_code"],
            invoice_info["pos_number"],
            invoice_info["cbte_nro"],
            invoice_info["imp_total"],
            invoice_info["imp_tot_conc"],
            invoice_info["imp_neto"],
            invoice_info["imp_subtotal"],
            invoice_info["imp_trib"],
            invoice_info["imp_op_ex"],
            invoice_info["imp_reintegro"],
            invoice_info["fecha_cbte"],
            invoice_info["id_impositivo"],
            invoice_info["cod_pais"],
            invoice_info["domicilio"],
            invoice_info["cod_relacion"],
            invoice_info["moneda_id"],
            invoice_info["moneda_ctz"],
            invoice_info["observaciones"],
            invoice_info["cancela_misma_moneda_ext"],
        )