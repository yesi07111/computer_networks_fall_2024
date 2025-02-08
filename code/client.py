# client.py
import ipaddress
import socket
import ssl
import chardet
import zlib
import gzip
from datetime import datetime, timedelta, timezone
from utils import *
import base64
import hashlib
from io import BytesIO
import re
class HttpClient:
    def __init__(self, host: str, port: int = 80, use_tls: bool = True, max_redirects: int = 5, body_size_threshold: int = 1024 * 1024, auth: tuple = None, max_connections: int = 2):
        self.host: str = host
        self.port: int = port
        self.use_tls: bool = use_tls
        self.max_redirects: int = max_redirects
        self.body_size_threshold: int = body_size_threshold
        self.cache = {}  # Implementación de almacenamiento en caché
        self.auth = auth  # Tupla de autenticación (usuario, contraseña)
        self.outstanding_requests = []  # Lista de solicitudes pendientes
        self.max_connections = max_connections
        self.current_connections = 0

    def send_requests(self, http_requests: list[HttpRequest], use_pipeline: bool = False) -> list[HttpResponse]:
        # Validar el host
        if not self.is_valid_host(self.host):
            raise ValueError("Invalid host")

        responses = []
        sock = None

        try:
            if use_pipeline:
                # Establecer conexión una vez para el pipeline
                sock = self._establish_connection()
                

            for http_request in http_requests:
                redirects = 0
                while redirects < self.max_redirects:
                    # Añadir encabezado de autenticación si se proporciona
                    if self.auth:
                        user, password = self.auth
                        credentials = f"{user}:{password}"
                        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                        http_request.headers['Authorization'] = f"Basic {encoded_credentials}"

                    # Asegurar que el encabezado Host esté presente
                    if 'Host' not in http_request.headers:
                        http_request.headers['Host'] = self.host

                    # Verificar que no se envíen ambos Content-Length y Transfer-Encoding
                    if 'Transfer-Encoding' in http_request.headers and 'Content-Length' in http_request.headers:
                        del http_request.headers['Content-Length']

                    # Validar y establecer el encabezado Connection
                    if 'Connection' in http_request.headers:
                        if http_request.headers['Connection'].lower() not in ['keep-alive', 'close']:
                            http_request.headers['Connection'] = 'keep-alive'
                    else:
                        http_request.headers['Connection'] = 'keep-alive'

                    # Verificar el caché antes de enviar la solicitud
                    cache_key = (http_request.method, http_request.uri)
                    cached_response = self.cache.get(cache_key)
                    if cached_response:
                        response, expiry_time, etag = cached_response
                        if datetime.now(timezone.utc) < expiry_time:
                            # Usar respuesta en caché si es válida
                            responses.append(response)
                            break
                        else:
                            # Añadir encabezados condicionales para validación
                            if etag:
                                http_request.headers['If-None-Match'] = etag

                    if not use_pipeline:
                        # Establecer conexión para cada solicitud si no se usa pipeline
                        sock = self._establish_connection()

                    if http_request.body and len(http_request.body) > self.body_size_threshold:
                        http_request.headers['Expect'] = '100-continue'

                    request_data = http_request.build_request()
                    sock.sendall(request_data.encode('utf-8'))
                    print("Cliente ha enviado la peticion")

                    # Añadir la solicitud a la lista de pendientes
                    self.outstanding_requests.append(http_request)

                    response = self.receive_response(sock)

                    if response.status_code == '100':
                        if http_request.body:
                            sock.sendall(http_request.body.encode('utf-8'))
                        response = self.receive_response(sock)

                    if response.status_code.startswith('3') and 'Location' in response.headers:
                        new_location = response.headers['Location']
                        if response.status_code in ['301', '302', '307']:
                            self.host, self.port, http_request.uri = self.parse_url(new_location)
                            http_request.headers['Host'] = self.host
                        elif response.status_code == '303':
                            self.host, self.port, http_request.uri = self.parse_url(new_location)
                            http_request.method = 'GET'
                            http_request.body = None
                            http_request.headers['Host'] = self.host
                        redirects += 1
                        continue  # Intentar la nueva ubicación
                    else:
                        # Guardar en caché si la respuesta lo permite
                        cache_control = response.headers.get('Cache-Control', '')
                        if 'no-store' not in cache_control:
                            max_age = self.extract_max_age(cache_control)
                            etag = response.headers.get('ETag')
                            if max_age is not None:
                                expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
                                self.cache[cache_key] = (response, expires, etag)

                        # Verificar integridad del mensaje
                        if 'Content-MD5' in response.headers:
                            expected_md5 = response.headers['Content-MD5']
                            actual_md5 = hashlib.md5(response.body.encode('utf-8')).hexdigest()
                            if expected_md5 != actual_md5:
                                raise Exception('Message integrity check failed')

                        # Descomprimir el cuerpo si es necesario
                        if 'Content-Encoding' in response.headers:
                            response.body = self.decode_content_encoding(response.body, response.headers['Content-Encoding'])

                        responses.append(response)
                        break  # Salir del bucle de redirección

                # Cerrar la conexión si no es 'keep-alive' y no se usa pipeline, o si el servidor indica 'Connection: close'
                if (not use_pipeline and 'Connection' in response.headers and response.headers['Connection'].lower() != 'keep-alive') or ('Connection' in response.headers and response.headers['Connection'].lower() == 'close'):
                    sock.close()
                    self.current_connections -= 1

        finally:
            if sock is not None and use_pipeline:
                sock.close()
                self.current_connections -= 1

        return responses

    def _establish_connection(self):
        if self.current_connections >= self.max_connections:
            raise Exception('Too many connections')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        if self.use_tls:
            if self.host == 'localhost':
                # context.check_hostname = False
                # context.verify_mode = ssl.CERT_NONE
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                context.load_verify_locations('server.crt')
            else:
                context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=self.host)
        sock.connect((self.host, self.port))
        self.current_connections += 1
        return sock

    def is_valid_host(self, host: str) -> bool:
        if host == "localhost":
            return True
        
        # Validar si el host es un nombre de dominio válido
        domain_regex = re.compile(
            r'^(?:[a-zA-Z0-9]'  # Primera letra del dominio
            r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'  # Subdominios
            r'[a-zA-Z]{2,6}$'  # TLD
        )
        if domain_regex.match(host):
            return True

        # Validar si el host es una dirección IP válida
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return False

    def extract_max_age(self, cache_control: str) -> int:
        if 'max-age' in cache_control:
            try:
                parts = cache_control.split(',')
                for part in parts:
                    if 'max-age' in part:
                        return int(part.split('=')[1])
            except Exception:
                pass
        return None

    def parse_url(self, url: str) -> tuple[str, int, str]:
        if url.startswith('http://'):
            self.use_tls = False
            url = url[7:]
        elif url.startswith('https://'):
            self.use_tls = True
            url = url[8:]

        host, path = url.split('/', 1)
        path = '/' + path

        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        else:
            port = 443 if self.use_tls else 80

        return host, port, path

    def receive_response(self, sock: socket.socket) -> HttpResponse:
        response = b''
        while True:
            try:
                part = sock.recv(4096)
                print("part received: ", part)
                if not part:
                    break
                response += part
                print("part added to response")
            except socket.timeout:
                print("El tiempo de espera del socket se ha agotado")
                break
            except Exception as error:
                print(f"Some error occurred while receiving response: {error}")

        try:
            print(f"!!!!!Receiving response in client: {response}")
            encoding = chardet.detect(response)["encoding"]
            encoding = encoding if encoding else "utf-8"
            print(f"encoding: {encoding}")
            print(f"El mensaje que se recibe en el cliente mide: {len(response)}")
            decoded_response = response.decode(encoding)
            print("Decoded_response: ", decoded_response)
            parsed_response = self.parse_http_response(decoded_response)
            print("Parsed Response: ", parsed_response)
        except Exception as error:
            print(error)
            parsed_response = HttpResponse(
                "HTTP/1.1",
                "500",
                "CRITICAL ERROR",
                {},
                "This is a critical error on the client side.",
            )
        print(len(decoded_response))
        return parsed_response

    def parse_http_response(self, response_str: str) -> HttpResponse:
        lines = response_str.split('\r\n')

        status_line = lines[0]
        version, status_code, reason_phrase = status_line.split(' ', 2)

        headers = {}
        index = 1
        while lines[index] != '':
            header_line = lines[index]
            key, value = header_line.split(':', 1)  # Asegurar que no haya espacio antes del colon
            headers[key.strip()] = value.strip()  # Manejar OWS
            index += 1

            # Reemplazar obs-fold con espacios
            if '\r\n' in value:
                headers[key.strip()] = ' '.join(value.split())

        # Determinar la longitud del cuerpo del mensaje
        if 'Transfer-Encoding' in headers:
            if headers['Transfer-Encoding'].endswith('chunked'):
                body, trailers = self.decode_chunked_body(lines[index+1:])
                # Manejar trailers si es necesario
                for trailer in trailers:
                    if trailer[0] in headers:
                        headers[trailer[0]] += ', ' + trailer[1]
                    else:
                        headers[trailer[0]] = trailer[1]
            else:
                raise Exception('Unsupported Transfer-Encoding')
        elif 'Content-Length' in headers:
            try:
                content_length = int(headers['Content-Length'])
                body = '\r\n'.join(lines[index+1:index+1+content_length])
            except ValueError:
                raise Exception('Invalid Content-Length')
        else:
            body = '\r\n'.join(lines[index+1:])

        # Verificar si la respuesta es incompleta
        if not self.is_response_complete(headers, body):
            raise Exception('Incomplete response received')

        return HttpResponse(version, status_code, reason_phrase, headers, body)

    def decode_chunked_body(self, lines):
        body = ''
        trailers = []
        index = 0
        while index < len(lines):
            chunk_size_str = lines[index].strip()
            try:
                chunk_size = int(chunk_size_str.split(';')[0], 16)
            except ValueError:
                raise Exception('Invalid chunk size')
            if chunk_size == 0:
                index += 1
                break
            index += 1
            body += '\r\n'.join(lines[index:index+chunk_size])
            index += chunk_size + 1

        # Leer trailers
        while index < len(lines) and lines[index] != '':
            trailer_line = lines[index]
            if ':' in trailer_line:
                key, value = trailer_line.split(':', 1)
                trailers.append((key.strip(), value.strip()))
            index += 1

        return body, trailers

    def decode_content_encoding(self, body: str, encoding: str) -> str:
        if encoding == 'gzip':
            with gzip.GzipFile(fileobj=BytesIO(body.encode('utf-8'))) as f:
                return f.read().decode('utf-8')
        elif encoding == 'deflate':
            return zlib.decompress(body.encode('utf-8')).decode('utf-8')
        elif encoding == 'identity':
            return body
        else:
            raise Exception(f'Unsupported Content-Encoding: {encoding}')

    def is_response_complete(self, headers, body):
        print(headers)
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        print(len(body))
        if 'Transfer-Encoding' in headers and headers['Transfer-Encoding'].endswith('chunked'):
            return body.endswith('0\r\n\r\n')
        elif 'Content-Length' in headers:
            return (len(body) + 4 == int(headers['Content-Length']) # Add 4 because the newlines are omited
                    or len(body) == int(headers['Content-Length'])) # In case of redirect
        return True

if __name__ == '__main__':
    requests = [
        HttpRequest(
            method='GET',
            uri='/',
            headers={
                'Host': 'www.google.com',
                'User-Agent': 'CustomHttpClient/1.0'
            }
        ),
        HttpRequest(
            method='GET',
            uri='/search',
            headers={
                'Host': 'www.google.com',
                'User-Agent': 'CustomHttpClient/1.0'
            }
        )
    ]

    # Proporciona credenciales de autenticación
    client = HttpClient('www.google.com', 443, auth=('username', 'password'))
    responses = client.send_requests(requests, use_pipeline=True)

    for request, response in zip(requests, responses):
        print(request.build_request(), '\n\n\n\n')
        print(response)