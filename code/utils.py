# utils.py
from typing import Dict, Optional

class HttpRequest:
    def __init__(self, method: str, uri: str, headers: Optional[Dict[str, str]] = None, body: Optional[str] = None):
        self.method: str = method
        self.uri: str = uri
        self.headers: Dict[str, str] = headers if headers is not None else {}
        self.body: Optional[str] = body

    def buildHeaders(self) -> str:
        """
        Construye los encabezados HTTP en un formato adecuado.
        """
        headers = ''
        for key, value in self.headers.items():
            # Eliminar espacios en blanco insignificantes
            key = key.strip()
            value = build_header_list([value])  # Usar build_header_list para construir el valor del encabezado
            headers += f'{key}: {value}\r\n'
        return headers

    def build_request(self) -> str:
        request_line = f'{self.method} {self.uri} HTTP/1.1\r\n'
        headers = self.buildHeaders()  # Usar el método buildHeaders para construir los encabezados
        blank_line = '\r\n'
        body = self.body if self.body else ''
        return request_line + headers + blank_line + body

    def __str__(self) -> str:
        request_str = f'Method: {self.method}\nURI: {self.uri}\nHeaders:\n'
        for key, value in self.headers.items():
            request_str += f' {key}: {value}\n'
        request_str += f'Body:\n' + self.body if self.body else 'No Body'
        return request_str

class HttpResponse:
    def __init__(self, version: str, status_code: str, reason_phrase: str, headers: Dict[str, str], body: str):
        self.version: str = version
        self.status_code: str = status_code
        self.reason_phrase: str = reason_phrase
        self.headers: Dict[str, str] = headers
        self.body: str = body

    def build_response(self) -> str:
        response_line = f"{self.version} {self.status_code} {self.reason_phrase}\r\n"

        headers = ""
        for key, value in self.headers.items():
            headers += f"{key}: {value}\r\n"

        blank_line = "\r\n"

        return response_line + headers + blank_line + self.body

    def __str__(self) -> str:
        response_str = f'HTTP Version: {self.version}\nStatus Code: {self.status_code}\nReason Phrase: {self.reason_phrase}\nHeaders:\n'
        for key, value in self.headers.items():
            response_str += f' {key}: {value}\n'
        response_str += f'Body:\n' + self.body if self.body else 'No Body'
        return response_str

def build_header_list(elements: list) -> str:
    """
    Construye una lista de encabezados HTTP que cumpla con las reglas de ABNF para listas.
    """
    if not elements:
        return ''
    return ', '.join(str(element).strip() for element in elements if element)

# Ejemplo de uso de build_header_list
# headers['Accept'] = build_header_list(['text/html', 'application/json'])