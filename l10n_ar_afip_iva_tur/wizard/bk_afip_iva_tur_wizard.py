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
    _description = 'AFIP IVA Turismo Exportable Wizard'

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
    # Nuevo campo para la fecha de pago
    date_payment = fields.Date(
        string='Fecha de Pago (Exportable)',
        required=True,
        help="Fecha que se utilizará como 'Fecha de Pago' en el archivo exportable de AFIP IVA Turismo."
    )

    exported_file = fields.Binary(
        string='Archivo Exportado',
        readonly=True,
        attachment=False,
    )
    exported_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
    )

    def action_generate_iva_tur_file(self):
        """ Genera el archivo de texto para AFIP IVA Turismo """
        self.ensure_one()
        content = self._generate_file_content()

        if not content:
            raise UserError(_("No se encontraron comprobantes Tipo T para el período seleccionado o la lógica de extracción no encontró datos."))

        filename = self._get_export_filename()
        encoded_content = base64.b64encode(content.encode('utf-8'))

        self.write({
            'exported_file': encoded_content,
            'exported_filename': filename,
        })

        # --- CAMBIO CLAVE AQUÍ: Retorna una acción para descargar el archivo ---
        # Usamos '_blank' para intentar abrirlo en una nueva pestaña.
        # Si el navegador lo reconoce como descarga, la pestaña se cerrará sola o quedará en blanco.
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/exported_file/%s' % (self._name, self.id, self.exported_filename),
            'target': '_blank', # <-- ¡CAMBIO AQUÍ! Abre en una nueva pestaña/ventana
        }
        # --- FIN DEL CAMBIO CLAVE ---

    def _generate_file_content(self):
        """
        Método central para obtener los datos y formatearlos.
        """
        afip_iva_tur_doc_codes = ['195', '196', '197', '362']

        try:
            doc_type_model = self.env['l10n_latam.document.type']
            doc_type_ids = doc_type_model.search([
                ('code', 'in', afip_iva_tur_doc_codes)
            ]).ids
        except KeyError:
            _logger.error(f"Error: El modelo 'l10n_latam.document.type' no fue encontrado.")
            return ""

        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('l10n_latam_document_type_id', 'in', doc_type_ids),
        ]

        invoices = self.env['account.move'].search(domain)

        if not invoices:
            return ""

        output = io.StringIO()

        for inv in invoices:
            # 1. CUIT del Emisor
            cuit_emisor = inv.company_id.vat.replace('-', '').strip().ljust(13, ' ')
            if not cuit_emisor.strip():
                _logger.warning(f"Factura {inv.name}: CUIT de la compañía no encontrado para el exportable IVA TUR. Se usará un valor vacío.")
                cuit_emisor = ''.ljust(13, ' ')

            # 2. Número de comprobante de venta (10 dígitos)
            comprobante_numero = str(inv.document_number or '').zfill(10)
            if len(comprobante_numero) > 10:
                _logger.warning(f"Factura {inv.name}: Número de comprobante ({comprobante_numero}) excede 10 dígitos. Se truncará.")
                comprobante_numero = comprobante_numero[-10:]

            # 3. Número de documento de identificación del turista extranjero (10 dígitos)
            doc_turista = inv.partner_id.vat or ''
            doc_turista = doc_turista.replace('-', '').strip().zfill(10)
            if not doc_turista.strip():
                _logger.warning(f"Factura {inv.name}: VAT del turista no encontrado para el exportable IVA TUR. Se usará un valor vacío.")
                doc_turista = ''.zfill(10)

            # 4. Fecha de emisión del comprobante (YYYYMMDD)
            fecha_emision = inv.invoice_date.strftime('%Y%m%d') if inv.invoice_date else '00000000'
            if not fecha_emision or fecha_emision == '00000000':
                _logger.warning(f"Factura {inv.name}: Fecha de emisión no válida. Se usará '00000000'.")
                fecha_emision = '00000000'

            # 5. Importe del comprobante (15 dígitos, con 2 decimales)
            importe_comprobante = int(round(inv.amount_total * 100))
            importe_comprobante = str(importe_comprobante).zfill(15)
            if len(importe_comprobante) > 15:
                _logger.error(f"Factura {inv.name}: Importe {inv.amount_total} convertido a {importe_comprobante} excede 15 dígitos. ¡Revise el formato AFIP!")

            # 6. Tipo de operación (A=Alojamiento, S=Servicio de transporte, C=Combinado)
            tipo_operacion = 'A'
            for line in inv.invoice_line_ids:
                if line.product_id and line.product_id.categ_id and hasattr(line.product_id.categ_id, 'item_type_t') and line.product_id.categ_id.item_type_t:
                    tipo_operacion = line.product_id.categ_id.item_type_t
                    break

            # 7. Cantidad de Noches (5 dígitos)
            cant_noches = 0
            for line in inv.invoice_line_ids:
                if line.product_id and line.product_id.categ_id and hasattr(line.product_id.categ_id, 'cod_tur') and isinstance(line.product_id.categ_id.cod_tur, (int, float)):
                    cant_noches += line.product_id.categ_id.cod_tur * line.quantity
                else:
                    _logger.warning(f"Factura {inv.name}: No se pudo obtener la cantidad de noches de la línea {line.name} (campo 'cod_tur' no numérico o ausente). Se usará 0 para esta línea.")

            cant_noches = str(int(cant_noches)).zfill(5)
            if len(cant_noches) > 5:
                _logger.error(f"Factura {inv.name}: Cantidad de noches ({cant_noches}) excede 5 dígitos. ¡Revise el formato AFIP!")
                cant_noches = '99999'

            # 8. Tipo de Cambio (F=Fijo, V=Variable)
            tipo_cambio = 'V' if inv.currency_id != inv.company_id.currency_id else 'F'
            
            # 9. Monto Tipo de Cambio (10 dígitos, con 4 decimales)
            monto_tipo_cambio = 0.0
            if inv.currency_id != inv.company_id.currency_id:
                if hasattr(inv, 'l10n_ar_currency_rate') and inv.l10n_ar_currency_rate:
                    monto_tipo_cambio = inv.l10n_ar_currency_rate
                else:
                    try:
                        from_currency = inv.currency_id
                        to_currency = inv.company_id.currency_id
                        amount_in_company_currency = from_currency._convert(
                            1.0, to_currency, inv.company_id, inv.invoice_date
                        )
                        if amount_in_company_currency != 0:
                            monto_tipo_cambio = 1.0 / amount_in_company_currency
                        else:
                            _logger.warning(f"Factura {inv.name}: No se pudo calcular el monto del tipo de cambio (división por cero). Se usará 0.")
                    except Exception as e:
                        _logger.error(f"Factura {inv.name}: Error al calcular monto tipo de cambio: {e}. Se usará 0.")
                        monto_tipo_cambio = 0.0

            monto_tipo_cambio = int(round(monto_tipo_cambio * 10000))
            monto_tipo_cambio = str(monto_tipo_cambio).zfill(10)
            if len(monto_tipo_cambio) > 10:
                _logger.error(f"Factura {inv.name}: Monto tipo de cambio ({monto_tipo_cambio}) excede 10 dígitos. ¡Revise el formato AFIP!")

            # 10. Fecha de Pago (YYYYMMDD) - Del nuevo campo del wizard
            fecha_pago = self.date_payment.strftime('%Y%m%d') if self.date_payment else '00000000'
            if not fecha_pago or fecha_pago == '00000000':
                _logger.warning(f"Factura {inv.name}: Fecha de pago no válida desde el wizard. Se usará '00000000'.")
                fecha_pago = '00000000'

            # 11. Identificación del Agente de Recaudación (C=Compañía, O=Otro)
            ident_agente = inv.company_id.afip_iva_tur_agent_identification or 'C'

            # Construir la línea del registro
            line = (
                cuit_emisor +
                comprobante_numero +
                doc_turista +
                fecha_emision +
                importe_comprobante +
                tipo_operacion +
                cant_noches +
                tipo_cambio +
                monto_tipo_cambio +
                fecha_pago +
                ident_agente
            )
            output.write(line + '\r\n')

        return output.getvalue()

    def _get_export_filename(self):
        """ Genera el nombre del archivo de salida según el período """
        date_from_str = self.date_from.strftime('%Y%m%d')
        date_to_str = self.date_to.strftime('%Y%m%d')
        return f"IVA_TUR_{date_from_str}_{date_to_str}.txt"