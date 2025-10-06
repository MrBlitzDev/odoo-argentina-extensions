import xml.etree.ElementTree as ET

class Item:
    def __init__(self, tipo, codigoTurismo, codigo, descripcion, codigoAlicuotaIVA, importeIVA, importeItem):
        self.tipo = tipo
        self.codigoTurismo = codigoTurismo
        self.codigo = codigo
        self.descripcion = descripcion
        self.codigoAlicuotaIVA = codigoAlicuotaIVA
        self.importeIVA = float(importeIVA)
        self.importeItem = float(importeItem)

class SubtotalIVA:
    def __init__(self, codigo, importe):
        self.codigo = codigo
        self.importe = float(importe)
        
class ComprobanteAsociado:
    def __init__(self, codigoTipoComprobante, numeroPuntoVenta, numeroComprobante):
        self.codigoTipoComprobante = codigoTipoComprobante
        self.numeroPuntoVenta = numeroPuntoVenta
        self.numeroComprobante = numeroComprobante

class ComprobanteRequest:
    def __init__(self):
        self.codigoTipoComprobante = ""
        self.numeroPuntoVenta = ""
        self.numeroComprobante = ""
        self.fechaEmision = ""
        self.codigoTipoAutorizacion = ""
        self.codigoTipoDocumento = ""
        self.numeroDocumento = ""
        self.idImpositivo = ""
        self.codigoPais = ""
        self.domicilioReceptor = ""
        self.codigoRelacionEmisorReceptor = ""
        self.importeGravado = 0.0
        self.importeNoGravado = 0.0
        self.importeExento = 0.0
        self.importeReintegro = 0.0
        self.importeTotal = 0.0
        self.codigoMoneda = ""
        self.cotizacionMoneda = 0.0
        self.observaciones = ""
        self.items = []
        self.subtotales_iva = []
        self.comprobantes_asociados = []

class AuthRequest:
    def __init__(self, token, sign, cuitRepresentada):
        self.token = token
        self.sign = sign
        self.cuitRepresentada = cuitRepresentada

class AutorizarComprobanteRequest:
    def __init__(self, auth: AuthRequest, comprobante: ComprobanteRequest):
        self.auth = auth
        self.comprobante = comprobante


def parse_autorizar_comprobante(xml_string: str) -> AutorizarComprobanteRequest:
    ns = {"soap": "http://schemas.xmlsoap.org/soap/envelope/",
          "ser": "http://ar.gob.afip.wsct/CTService/"}
    
    root = ET.fromstring(xml_string)
    req = root.find(".//ser:autorizarComprobanteRequest", ns)

    # --- authRequest ---
    auth_node = req.find("authRequest", ns)
    auth = AuthRequest(
        token=auth_node.findtext("token"),
        sign=auth_node.findtext("sign"),
        cuitRepresentada=auth_node.findtext("cuitRepresentada"),
    )

    # --- comprobanteRequest ---
    comp_node = req.find("comprobanteRequest", ns)
    comp = ComprobanteRequest(
        codigoTipoComprobante=comp_node.findtext("codigoTipoComprobante"),
        numeroPuntoVenta=comp_node.findtext("numeroPuntoVenta"),
        numeroComprobante=comp_node.findtext("numeroComprobante"),
        fechaEmision=comp_node.findtext("fechaEmision"),
        codigoTipoAutorizacion=comp_node.findtext("codigoTipoAutorizacion"),
        codigoTipoDocumento=comp_node.findtext("codigoTipoDocumento"),
        numeroDocumento=comp_node.findtext("numeroDocumento"),
        idImpositivo=comp_node.findtext("idImpositivo"),
        codigoPais=comp_node.findtext("codigoPais"),
        domicilioReceptor=comp_node.findtext("domicilioReceptor"),
        codigoRelacionEmisorReceptor=comp_node.findtext("codigoRelacionEmisorReceptor"),
        importeGravado=float(comp_node.findtext("importeGravado")),
        importeNoGravado=float(comp_node.findtext("importeNoGravado")),
        importeExento=float(comp_node.findtext("importeExento")),
        importeReintegro=float(comp_node.findtext("importeReintegro")),
        importeTotal=float(comp_node.findtext("importeTotal")),
        codigoMoneda=comp_node.findtext("codigoMoneda"),
        cotizacionMoneda=float(comp_node.findtext("cotizacionMoneda")),
        observaciones=comp_node.findtext("observaciones"),
    )

    # --- Items ---
    for item_node in comp_node.findall(".//item", ns):
        item = Item(
            tipo=item_node.findtext("tipo"),
            codigoTurismo=item_node.findtext("codigoTurismo"),
            codigo=item_node.findtext("codigo"),
            descripcion=item_node.findtext("descripcion"),
            codigoAlicuotaIVA=item_node.findtext("codigoAlicuotaIVA"),
            importeIVA=float(item_node.findtext("importeIVA")),
            importeItem=float(item_node.findtext("importeItem")),
        )
        comp.items.append(item)

    # --- Subtotales IVA ---
    for iva_node in comp_node.findall(".//subtotalIVA", ns):
        sub = SubtotalIVA(
            codigo=iva_node.findtext("codigo"),
            importe=float(iva_node.findtext("importe")),
        )
        comp.subtotales_iva.append(sub)
    
    # --- Comprobantes Asociados ---
    for ca_node in comp_node.findall(".//comprobanteAsociado", ns):
        ca = ComprobanteAsociado(
            codigoTipoComprobante=ca_node.findtext("codigoTipoComprobante"),
            numeroPuntoVenta=ca_node.findtext("numeroPuntoVenta"),
            numeroComprobante=ca_node.findtext("numeroComprobante"),
        )
        comp.comprobantes_asociados.append(ca)

    return AutorizarComprobanteRequest(auth=auth, comprobante=comp)

class ComprobanteResponse:
    def __init__(self):
        self.cuit: str = ""
        self.codigoTipoComprobante: str = ""
        self.numeroPuntoVenta: str = ""
        self.numeroComprobante: str = ""
        self.fechaEmision: str = ""
        self.tipo_autorizacion: str = ""       # "CAE" o "CAI"
        self.codigo_autorizacion: str = ""     # valor del CAE/CAI
        self.fechaVencimiento: str = ""        # fecha de vencimiento del CAE/CAI
        self.resultado: str = ""


def parse_afip_response(xml_string: str) -> ComprobanteResponse:
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "wsct": "http://ar.gob.afip.wsct/CTService/"
    }

    root = ET.fromstring(xml_string)
    comp_resp_node = root.find(
        ".//wsct:autorizarComprobanteResponse/wsct:autorizarComprobanteReturn/comprobanteResponse",
        ns
    )
    resultado_node = root.find(
        ".//wsct:autorizarComprobanteResponse/wsct:autorizarComprobanteReturn/resultado",
        ns
    )

    comp = ComprobanteResponse()
    if comp_resp_node is not None:
        comp.cuit = comp_resp_node.findtext("cuit", "")
        comp.codigoTipoComprobante = comp_resp_node.findtext("codigoTipoComprobante", "")
        comp.numeroPuntoVenta = comp_resp_node.findtext("numeroPuntoVenta", "")
        comp.numeroComprobante = comp_resp_node.findtext("numeroComprobante", "")
        comp.fechaEmision = comp_resp_node.findtext("fechaEmision", "")

        # Detectar si viene CAE o CAI
        if comp_resp_node.find("CAE") is not None:
            comp.tipo_autorizacion = "CAE"
            comp.codigo_autorizacion = comp_resp_node.findtext("CAE", "")
            comp.fechaVencimiento = comp_resp_node.findtext("fechaVencimientoCAE", "")
        elif comp_resp_node.find("CAI") is not None:
            comp.tipo_autorizacion = "CAI"
            comp.codigo_autorizacion = comp_resp_node.findtext("CAI", "")
            comp.fechaVencimiento = comp_resp_node.findtext("fechaVencimientoCAI", "")
        else:
            comp.tipo_autorizacion = ""
            comp.codigo_autorizacion = ""
            comp.fechaVencimiento = ""

    if resultado_node is not None:
        comp.resultado = resultado_node.text or ""

    return comp

def format_fixed_decimal(value: float, int_digits: int = 12, dec_digits: int = 6) -> str:
    # separo parte entera y decimal
    entero, decimal = f"{value:.{dec_digits}f}".split(".")
    
    # relleno la parte entera con ceros a la izquierda
    entero = entero.zfill(int_digits)
    
    # concateno entero + decimal
    return entero + decimal
