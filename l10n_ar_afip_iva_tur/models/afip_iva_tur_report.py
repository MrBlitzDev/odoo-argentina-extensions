# l10n_ar_afip_iva_tur/models/afip_iva_tur_report.py

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import datetime
import io
import base64
import logging

_logger = logging.getLogger(__name__)

class AfipIvaTurReport(models.Model):
    _name = 'afip.iva.tur.report'
    _description = 'AFIP IVA Turismo Report'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Hereda para el chatter
    _order = 'date_from desc'

    name = fields.Char(
        string='Nombre del Reporte',
        compute='_compute_name',
        store=True,
        help="Nombre generado automáticamente para el reporte (ej. IVA TUR 2025/06)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
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
    
    date_payment = fields.Date(
        string='Fecha de Pago (Exportable)',
        required=True,
        default=lambda self: datetime.date.today() + datetime.timedelta(days=1), 
        help="Fecha que se utilizará como 'Fecha de Pago' en el archivo exportable de AFIP IVA Turismo."
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('presented', 'Presentado'),
    ], string='Estado', default='draft', readonly=True, copy=False,
        help="Estado del reporte: Borrador (se pueden editar los datos), Generado (listo para presentar), Presentado (reporte enviado a AFIP)."
    )
    invoice_ids = fields.Many2many(
        'account.move',
        string='Comprobantes Incluidos',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
        help="Listado de comprobantes Tipo T incluidos en este reporte. Se completará automáticamente al generar el borrador."
    )
    exported_file = fields.Binary(
        string='Archivo TXT Exportado',
        readonly=True,
        attachment=True,
        help="Archivo TXT generado para la presentación en AFIP."
    )
    exported_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
    )
    presentation_date = fields.Date(
        string='Fecha de Presentación',
        readonly=True,
        help="Fecha en que el reporte fue marcado como presentado."
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.name = _("IVA TUR %s/%s") % (rec.date_from.year, str(rec.date_from.month).zfill(2))
            else:
                rec.name = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("La 'Fecha Desde' no puede ser posterior a la 'Fecha Hasta'."))

    def action_clear_invoices(self):
        """ Acción para eliminar todos los comprobantes de la lista si el reporte está en borrador. """
        self.ensure_one()
        if self.state == 'presented':
            raise UserError(_("No puede limpiar los comprobantes de un reporte ya presentado. Cree uno nuevo si necesita corregir."))
        if self.state == 'draft':
            self.invoice_ids = [(5, 0, 0)] # Comando (5, 0, 0) vacía completamente el many2many
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Comprobantes Borrados'),
                    'message': _('Todos los comprobantes han sido eliminados del reporte borrador.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        else:
            pass
    
    # --- CAMBIO CLAVE AQUÍ: Renombramos action_generate_draft a action_update_invoices ---
    def action_update_invoices(self):
        """ Acción para actualizar la lista de comprobantes del reporte, añadiendo los no duplicados. """
        self.ensure_one()
        afip_iva_tur_doc_codes = ['195', '196', '197', '362']

        doc_type_ids = self.env['l10n_latam.document.type'].search([
            ('code', 'in', afip_iva_tur_doc_codes),
            ('l10n_ar_letter', '=', 'T'),
        ]).ids

        if not doc_type_ids:
            self.invoice_ids = [(5, 0, 0)]
            self.state = 'draft'
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("No se encontraron tipos de documento AFIP configurados para 'IVA Turismo' (códigos: %s, letra 'T')." % afip_iva_tur_doc_codes),
                }
            }

        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('l10n_latam_document_type_id', 'in', doc_type_ids),
        ]

        # Facturas candidatas que Odoo encuentra para este período y criterios (invoices que *podrían* ir en este reporte)
        invoices_found_in_period = self.env['account.move'].search(domain)
        
        # --- Lógica MEJORADA para identificar y reportar *solo* las duplicadas conflictivas ---
        # 1. Obtener todas las facturas que *ya están* en *otros* reportes (excluyendo el reporte actual)
        all_invoices_in_other_reports_excluding_self = self.env['afip.iva.tur.report'].search([
            ('id', '!=', self.id), # Excluir el reporte que estamos generando/editando
        ]).mapped('invoice_ids') # Esto da un recordset de todas las facturas ya usadas en otros reportes

        # 2. Encontrar la intersección: cuáles de las 'invoices_found_in_period' (candidatas para ESTE reporte)
        #    ya se encuentran en 'all_invoices_in_other_reports_excluding_self'.
        #    Esto nos da las facturas que *realmente causan el conflicto*.
        
        conflicting_invoices = invoices_found_in_period & all_invoices_in_other_reports_excluding_self

        if conflicting_invoices:
            duplicate_messages = []
            for inv_conflict in conflicting_invoices:
                # Para cada factura en conflicto, encontrar los reportes específicos donde ya está
                reports_containing_this_invoice = self.env['afip.iva.tur.report'].search([
                    ('id', '!=', self.id), # Excluir el reporte actual
                    ('invoice_ids', 'in', inv_conflict.id) # Buscar reportes que contengan esta factura
                ])
                report_info = ", ".join([f"{r.name} (ID: {r.id})" for r in reports_containing_this_invoice])
                duplicate_messages.append(
                    _("La factura %s ya está incluida en el reporte(s): %s") % (inv_conflict.name, report_info)
                )
            
            raise UserError(_(
                "No se pueden agregar los siguientes comprobantes por estar ya incluidos en otros reportes de IVA Turismo:\n\n%s"
            ) % "\n".join(duplicate_messages))
        # --- FIN Lógica MEJORADA ---

        # Si no hay conflictos, asignamos todas las facturas encontradas en el período a este reporte
        self.invoice_ids = [(6, 0, invoices_found_in_period.ids)]
        self.state = 'generated' # Si se actualizaron los comprobantes, el reporte pasa a generado
        
        if not invoices_found_in_period:
            self.state = 'draft' # Si no se encontraron facturas, queda en borrador
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("No se encontraron comprobantes Tipo T para el período seleccionado."),
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'afip.iva.tur.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': self.env.context,
            'flags': {'action_buttons': True, 'reload': True},
        }
    # --- FIN CAMBIO CLAVE: Renombramos action_generate_draft a action_update_invoices ---

    def action_generate_file(self):
        """ Acción para generar el archivo TXT a partir de los comprobantes ya cargados. """
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(_("No hay comprobantes asociados a este reporte para generar el archivo."))
        
        output = io.StringIO()
        
        # --- REGISTRO TIPO 1: CABECERA DEL ARCHIVO ---
        cuit_informante = self.company_id.vat.replace('-', '').strip()
        fecha_generacion = datetime.date.today().strftime('%Y%m%d')
        cantidad_registros_tipo2 = len(self.invoice_ids)
        
        line1 = (
            "01" +
            str(cuit_informante).ljust(11, ' ') +
            fecha_generacion +
            str(cantidad_registros_tipo2).zfill(10) # Borrar, aca van los valores fijos
            # Agregar valores de secuencia y presentacion sin movimiento
        )
        output.write(line1 + '\r\n')

        # --- GENERACION DE OTROS TIPOS DE REGISTRO POR CADA FACTURA ---
        ident_agente = self.company_id.afip_iva_tur_agent_identification or 'C'
        fecha_pago = self.date_payment.strftime('%Y%m%d')

        for inv in self.invoice_ids:
            # Extraer Punto de Venta y Número de Comprobante del document_number
            parts = (inv.l10n_latam_document_number or '').split('-')
            punto_venta = ""
            numero_comprobante_seq = ""
            if len(parts) == 2:
                punto_venta = str(parts[0]).zfill(5)
                numero_comprobante_seq = str(parts[1]).zfill(8)
            else:
                _logger.warning(f"Factura {inv.name}: Formato de document_number ({inv.l10n_latam_document_number}) no es el esperado (PV-Número). Asumiendo 0 para PV y número completo para Nro. Comprobante.")
                punto_venta = "00000"
                numero_comprobante_seq = str(inv.l10n_latam_document_number or '')[-8:].zfill(8)


            # --- REGISTRO TIPO 2: COMPROBANTE DE VENTA ---
            tipo_comprobante_afip = str(inv.l10n_latam_document_type_id.code or '000').zfill(3)
            if len(tipo_comprobante_afip) > 3:
                _logger.warning(f"Factura {inv.name}: Código AFIP de tipo de comprobante ({tipo_comprobante_afip}) excede 3 dígitos. Se truncará.")
                tipo_comprobante_afip = tipo_comprobante_afip[-3:]

            fecha_emision = inv.invoice_date.strftime('%Y%m%d') if inv.invoice_date else '00000000'

            tipo_doc_turista = str(inv.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code or '').zfill(2)

            nro_doc_turista = str(inv.partner_id.vat or '').replace('-', '').strip().zfill(11)

            importe_total_comprobante = str(int(round(inv.amount_total * 100))).zfill(15)
            if len(importe_total_comprobante) > 15:
                _logger.error(f"Factura {inv.name}: Importe total ({inv.amount_total}) convertido a {importe_total_comprobante} excede 15 dígitos. ¡Formato AFIP inválido!")

            tipo_operacion = 'A' # Default
            for line in inv.invoice_line_ids:
                if line.product_id and line.product_id.categ_id and hasattr(line.product_id.categ_id, 'item_type_t') and line.product_id.categ_id.item_type_t:
                    tipo_operacion = line.product_id.categ_id.item_type_t
                    break

            cant_noches = 0
            for line in inv.invoice_line_ids:
                if line.product_id and line.product_id.categ_id and hasattr(line.product_id.categ_id, 'cod_tur') and isinstance(line.product_id.categ_id.cod_tur, (int, float)):
                    cant_noches += int(line.product_id.categ_id.cod_tur * line.quantity)
                else:
                    _logger.warning(f"Factura {inv.name}: No se pudo obtener la cantidad de noches de la línea {line.name} (campo 'cod_tur' no numérico o ausente). Se usará 0 para esta línea.")
            cant_noches = str(cant_noches).zfill(5)
            if len(cant_noches) > 5:
                _logger.error(f"Factura {inv.name}: Cantidad de noches ({cant_noches}) excede 5 dígitos. ¡Revise el formato AFIP!")
                cant_noches = '99999'

            moneda_afip_code = str(inv.currency_id.l10n_ar_afip_code or 'PES').ljust(3, ' ')

            tipo_cambio = 'V' if inv.currency_id != inv.company_id.currency_id else 'F'
            monto_tipo_cambio = 0.0
            if inv.currency_id != inv.company_id.currency_id:
                if hasattr(inv, 'l10n_ar_currency_rate') and inv.l10n_ar_currency_rate:
                    monto_tipo_cambio = inv.l10n_ar_currency_rate
                else:
                    try:
                        from_currency = inv.currency_id
                        to_currency = inv.company_id.currency_id
                        monto_tipo_cambio = inv.amount_total_company_signed / inv.amount_total if inv.amount_total != 0 else 0.0
                        _logger.warning(f"Factura {inv.name}: Usando cálculo aproximado para tasa de cambio. Considere campo `l10n_ar_currency_rate`.")
                    except Exception as e:
                        _logger.error(f"Factura {inv.name}: Error al calcular monto tipo de cambio: {e}. Se usará 0.")
            monto_tipo_cambio = str(int(round(monto_tipo_cambio * 10000))).zfill(10)
            if len(monto_tipo_cambio) > 10:
                 _logger.error(f"Factura {inv.name}: Monto tipo de cambio ({monto_tipo_cambio}) excede 10 dígitos. ¡Revise formato!")


            cae_cai = str(inv.afip_auth_code or '').ljust(14, ' ')
            if len(cae_cai) > 14:
                _logger.warning(f"Factura {inv.name}: CAE/CAI ({cae_cai}) excede 14 digitos. Se truncará.")
                cae_cai = cae_cai[:14]

            fecha_vto_cae = inv.afip_auth_code_due.strftime('%Y%m%d') if inv.afip_auth_code_due else '00000000'

            importe_neto_gravado = str(int(round(inv.amount_untaxed * 100))).zfill(15)
            importe_impuesto_liquidado = str(int(round(inv.amount_tax * 100))).zfill(15)

            line2 = (
                "02" +
                tipo_comprobante_afip +
                punto_venta +
                numero_comprobante_seq +
                fecha_emision +
                tipo_doc_turista +
                nro_doc_turista +
                importe_total_comprobante +
                tipo_operacion +
                cant_noches +
                moneda_afip_code +
                tipo_cambio +
                monto_tipo_cambio +
                cae_cai +
                fecha_vto_cae +
                importe_neto_gravado +
                importe_impuesto_liquidado
            )
            output.write(line2 + '\r\n')

            # --- REGISTRO TIPO 3: TOTALES DEL COMPROBANTE DE VENTA (Base IVA) ---
            total_gravado_alicuota = str(int(round(inv.amount_untaxed * 100))).zfill(15)
            total_iva_alicuota = str(int(round(inv.amount_tax * 100))).zfill(15)
            
            line3 = (
                "03" +
                "000" + # Tipo de Concepto (1) + Tipo de Impuesto (1) + Código de Impuesto (2) -> placeholder
                "0000" + # Alícuota (4) -> placeholder
                total_gravado_alicuota +
                total_iva_alicuota
            )
            output.write(line3 + '\r\n')


            # --- REGISTRO TIPO 4: DATOS DEL TURISTA EXTRANJERO ---
            full_name = str(inv.partner_id.name or '').strip()
            apellido_turista = ''
            nombre_turista = ''
            name_parts = full_name.rsplit(' ', 1) # Divide por el último espacio
            if len(name_parts) > 1:
                apellido_turista = name_parts[1]
                nombre_turista = name_parts[0]
            else: # Si no hay espacio o es una sola palabra, asumimos todo como nombre
                nombre_turista = full_name
            
            apellido_turista = apellido_turista.ljust(30, ' ')[:30]
            nombre_turista = nombre_turista.ljust(30, ' ')[:30]

            nacionalidad_afip_code = str(inv.partner_id.country_id.l10n_ar_afip_code or '000').zfill(3)
            
            sexo_turista = 'M' # Valor por defecto si no existe el campo o es nulo
            if hasattr(inv.partner_id, 'gender') and inv.partner_id.gender:
                sexo_turista = str(inv.partner_id.gender)
            sexo_turista = sexo_turista.upper()

            fecha_nacimiento = '00000000' # Valor por defecto si no existe el campo o es nulo
            if hasattr(inv.partner_id, 'birthdate') and inv.partner_id.birthdate:
                try:
                    fecha_nacimiento = inv.partner_id.birthdate.strftime('%Y%m%d')
                except Exception as e:
                    _logger.warning(f"Factura {inv.name}: Error al formatear fecha de nacimiento {inv.partner_id.birthdate}: {e}. Se usará '00000000'.")

            line4 = (
                "04" +
                tipo_doc_turista +
                nro_doc_turista +
                apellido_turista +
                nombre_turista +
                nacionalidad_afip_code +
                sexo_turista +
                fecha_nacimiento
            )
            output.write(line4 + '\r\n')


            # --- REGISTRO TIPO 5: IMPUESTOS Y PERCEPCIONES DEL COMPROBANTE ---
            line5 = (
                "05" +
                str(cuit_informante).ljust(11, ' ') +
                tipo_comprobante_afip +
                punto_venta +
                numero_comprobante_seq +
                cae_cai +
                fecha_vto_cae +
                importe_total_comprobante
            )
            output.write(line5 + '\r\n')


            # --- REGISTRO TIPO 7: CONCEPTOS DE DETALLE DEL COMPROBANTE ---
            for line_inv in inv.invoice_line_ids:
                codigo_item = str(line_inv.product_id.categ_id.cod_tur or '').ljust(5, ' ')[:5]
                descripcion_item = str(line_inv.name or line_inv.product_id.name or '').ljust(40, ' ')[:40]
                cantidad_item = str(int(round(line_inv.quantity * 1000))).zfill(10)
                precio_unitario_item = str(int(round(line_inv.price_unit * 100))).zfill(15)
                importe_total_item = str(int(round(line_inv.price_subtotal * 100))).zfill(15)
                tipo_operacion_item = str(line_inv.product_id.categ_id.item_type_t or 'A')

                line7 = (
                    "07" +
                    codigo_item +
                    descripcion_item +
                    cantidad_item +
                    precio_unitario_item +
                    importe_total_item +
                    tipo_operacion_item
                )
                output.write(line7 + '\r\n')


            # --- REGISTRO TIPO 8: MEDIOS DE PAGO ---
            codigo_medio_pago = "01" # Default "01" para Efectivo
            importe_medio_pago = str(int(round(inv.amount_total * 100))).zfill(15)

            line8 = (
                "08" +
                codigo_medio_pago +
                importe_medio_pago
            )
            output.write(line8 + '\r\n')
        
        content = output.getvalue()
        
        def _get_export_filename_report(record):
            cuit_informante_clean = record.company_id.vat.replace('-', '').strip() # CUIT sin guiones/puntos
            # Asegurar que el CUIT tiene 11 dígitos, rellenar si es necesario, o truncar
            cuit_informante_padded = cuit_informante_clean.ljust(11, '0')[:11] # Rellenar con 0 y truncar a 11

            fecha_generacion_hoy = datetime.date.today()
            periodo = fecha_generacion_hoy.strftime('%Y%m') # AAAAMM

            # Asumimos '0000' para la primera remesa.
            # Si necesitas un manejo de remesas, esto implicaría un campo en afip.iva.tur.report
            # para almacenar la última remesa del período.
            numero_remesa = '0001' # Por defecto la primera remesa

            # Formato: F + COD_REGIMEN + CUIT_INFORMATE + PERIODO_AAAAMM + NRO_REMESA + .TXT
            # COD_REGIMEN = 8089 para IVA Turismo
            return f"F8089.{cuit_informante_padded}.{periodo}.{numero_remesa}.TXT"

        filename = _get_export_filename_report(self)

        encoded_content = base64.b64encode(content.encode('utf-8'))

        self.write({
            'exported_file': encoded_content,
            'exported_filename': filename,
        })
        self.state = 'generated'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True}, # Asegura que los botones se refresquen
        }

    def action_mark_as_presented(self):
        """ Acción para marcar el reporte como presentado. """
        self.ensure_one()
        if self.state == 'draft':
            raise UserError(_("No puede marcar un borrador de reporte como presentado. Genere el borrador primero."))
        self.write({
            'state': 'presented',
            'presentation_date': fields.Date.today(),
        })
        # --- CAMBIO CLAVE: Refrescar la vista después de la acción ---
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True},
        }
        # --- FIN CAMBIO CLAVE ---

    def action_set_to_draft(self):
        """ Acción para volver el reporte a estado borrador. """
        self.ensure_one()
        if self.state == 'presented':
            raise UserError(_("No puede volver un reporte presentado a borrador. Cree uno nuevo si necesita corregir."))
        self.write({
            'state': 'draft',
            'exported_file': False,
            'exported_filename': False,
            'presentation_date': False,
            'invoice_ids': [(5, 0, 0)],
        })
        # --- CAMBIO CLAVE: Refrescar la vista después de la acción ---
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True},
        }
        # --- FIN CAMBIO CLAVE ---