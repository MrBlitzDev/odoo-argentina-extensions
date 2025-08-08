from pysimplesoap.client import SimpleXMLElement

def _get_response_info(xml_response):
    return SimpleXMLElement(xml_response)


def get_invoice_number_from_response(xml_response):
    if not xml_response:
        return False
    try:
        xml = _get_response_info(xml_response)
        return int(xml('numeroComprobante'))         
    except:
        return False
