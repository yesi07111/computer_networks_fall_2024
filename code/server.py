import socket
import json
import chardet
from http import HTTPStatus
from utils import HttpRequest, HttpResponse
import traceback

HTTP_METHODS = [
    'GET',
    'HEAD',
    'POST',
    'PUT',
    'DELETE',
    'CONNECT',
    'OPTIONS',
    'TRACE',
    'PATCH'
]

class HttpServer:
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.data_store = {}  # In-memory data store for JSON objects

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                client_socket, client_address = server_socket.accept()
                with client_socket:
                    print(f"Connection from {client_address}")
                    request_data = self.receive_request(client_socket)
                    print("El servidor recibio los datos del cliente")
                    if not request_data:
                        continue
                    
                    try:
                        http_request = self.parse_http_request(request_data)
                        print("Request parsed successfully")
                        print("Handling Request...")
                        http_response = self.handle_request(http_request, request_data)
                        print("Response in try after handle_request: ", http_response)
                    except Exception as e:
                        print("Error processing request:", e)
                        traceback.print_exc()
                        http_response = self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR)

                    xxx = http_response.build_response().encode('utf-8')
                    
                    print(f"El mensaje que se envia mide: {len(xxx)}")
                    client_socket.sendall(xxx)

    def receive_request(self, client_socket: socket.socket) -> str:
        request_data = b""
        while True:
            try:
                part = client_socket.recv(4096)
                if not part:
                    break
                request_data += part
            except socket.timeout:
                break

        encoding = chardet.detect(request_data)["encoding"]
        encoding = encoding if encoding else "utf-8"

        try:
            return request_data.decode(encoding)
        except UnicodeDecodeError:
            print("Failed to decode request data")
            return ""

    def parse_http_request(self, request_data: str) -> HttpRequest:
        print("request_data: ", request_data)
        lines = request_data.split("\r\n")
        print("Request lines: ", lines)
        print("Request first line has to split in 3: METHOD URI HTTP/VERSIONL: ", lines[0].split(" "))
        if not lines or len(lines[0].split(" ")) < 3:
            raise ValueError("Invalid request line format")
        
        request_line = lines[0].split(" ")
        method, uri, _ = request_line

        headers = {}
        index = 1
        while index < len(lines) and lines[index] != "":
            header_line = lines[index]
            if ": " not in header_line:
                raise ValueError(f"Invalid header format: {header_line}")
            key, value = header_line.split(": ", 1)
            headers[key] = value
            index += 1

        body = "\r\n".join(lines[index+1:])
        print(f"parse_http_request return an HttpRequest with method: {method}, uri: {uri}, headers: {headers} and body: {body}")
        return HttpRequest(method, uri, headers, body)
    
    def handle_request(self, request: HttpRequest, request_data: str) -> HttpResponse:
        try:
            print(f"request.method: {request.method}. Is in HTTP_METHODS: {request.method in HTTP_METHODS}")
            if request.method not in HTTP_METHODS:
                return self.generate_error_response(HTTPStatus.METHOD_NOT_ALLOWED)

            print(f"request.uri.starstswith(/): {request.uri.startswith('/')}")
            if not request.uri.startswith("/"):
                return self.generate_error_response(HTTPStatus.BAD_REQUEST)

            if request.uri == '/':
                print("Returning General Response...")
                return self.generate_general_response()

            if request.method == 'GET':
                return self.handle_get(request)
            elif request.method == 'HEAD':
                return self.handle_head(request)
            elif request.method == 'POST':
                return self.handle_post(request)
            elif request.method == 'PUT':
                return self.handle_put(request)
            elif request.method == 'PATCH':
                return self.handle_patch(request)
            elif request.method == 'DELETE':
                return self.handle_delete(request)
            elif request.method == 'CONNECT':
                return self.handle_connect(request)
            elif request.method == 'OPTIONS':
                return self.handle_options(request)
            elif request.method == 'TRACE':
                return self.handle_trace(request_data)

            return self.generate_error_response(HTTPStatus.NOT_IMPLEMENTED)

        except ValueError as e:
            print("ValueError:", e)
            return self.generate_error_response(HTTPStatus.BAD_REQUEST)
        except Exception as e:
            print("Exception:", e)
            traceback.print_exc()
            return self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR)


    def handle_get(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            body = f"""
            <html>
            <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
            <body>
                <h1>GET Request</h1>
                <p>Data for <strong>{key}</strong>:</p>
                <pre>{json.dumps(self.data_store[key], indent=4)}</pre>
            </body>
            </html>
            """
            status = HTTPStatus.OK
        else:
            body = """
            <html>
            <head><style>body { font-family: Arial, sans-serif; }</style></head>
            <body>
                <h1>GET Request</h1>
                <p><strong>Not Found</strong></p>
            </body>
            </html>
            """
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_head(self, request: HttpRequest) -> HttpResponse:
        response = self.handle_get(request)
        response.body = ""
        return response

    def handle_post(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        try:
            data = json.loads(request.body)
            self.data_store[key] = data
            body = f"""
            <html>
            <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
            <body>
                <h1>POST Request</h1>
                <p>Data stored at <strong>{key}</strong> successfully.</p>
            </body>
            </html>
            """
            status = HTTPStatus.CREATED
        except json.JSONDecodeError:
            body = """
            <html>
            <head><style>body { font-family: Arial, sans-serif; }</style></head>
            <body>
                <h1>POST Request</h1>
                <p><strong>Invalid JSON</strong></p>
            </body>
            </html>
            """
            status = HTTPStatus.BAD_REQUEST

        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_put(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        try:
            data = json.loads(request.body)
            self.data_store[key] = data
            body = f"""
            <html>
            <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
            <body>
                <h1>PUT Request</h1>
                <p>Data at <strong>{key}</strong> updated successfully.</p>
            </body>
            </html>
            """
            status = HTTPStatus.OK
        except json.JSONDecodeError:
            body = """
            <html>
            <head><style>body { font-family: Arial, sans-serif; }</style></head>
            <body>
                <h1>PUT Request</h1>
                <p><strong>Invalid JSON</strong></p>
            </body>
            </html>
            """
            status = HTTPStatus.BAD_REQUEST

        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_patch(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            try:
                updates = json.loads(request.body)
                self.data_store[key].update(updates)
                body = f"""
                <html>
                <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
                <body>
                    <h1>PATCH Request</h1>
                    <p>Data at <strong>{key}</strong> patched successfully.</p>
                </body>
                </html>
                """
                status = HTTPStatus.OK
            except json.JSONDecodeError:
                body = """
                <html>
                <head><style>body { font-family: Arial, sans-serif; }</style></head>
                <body>
                    <h1>PATCH Request</h1>
                    <p><strong>Invalid JSON</strong></p>
                </body>
                </html>
                """
                status = HTTPStatus.BAD_REQUEST
        else:
            body = """
            <html>
            <head><style>body { font-family: Arial, sans-serif; }</style></head>
            <body>
                <h1>PATCH Request</h1>
                <p><strong>Not Found</strong></p>
            </body>
            </html>
            """
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_delete(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            del self.data_store[key]
            body = f"""
            <html>
            <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
            <body>
                <h1>DELETE Request</h1>
                <p>Data at <strong>{key}</strong> deleted successfully.</p>
            </body>
            </html>
            """
            status = HTTPStatus.OK
        else:
            body = """
            <html>
            <head><style>body { font-family: Arial, sans-serif; }</style></head>
            <body>
                <h1>DELETE Request</h1>
                <p><strong>Not Found</strong></p>
            </body>
            </html>
            """
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_connect(self, request: HttpRequest) -> HttpResponse:
        body = """
        <html>
        <head><style>body { font-family: Arial, sans-serif; }</style></head>
        <body>
            <h1>CONNECT Request</h1>
            <p><strong>CONNECT method not supported in this context.</strong></p>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.NOT_IMPLEMENTED.value), HTTPStatus.NOT_IMPLEMENTED.phrase, headers, body)

    def handle_options(self, request: HttpRequest) -> HttpResponse:
        allowed_methods = ", ".join(HTTP_METHODS)
        body = f"""
        <html>
        <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
        <body>
            <h1>OPTIONS Request</h1>
            <p>Allowed methods: <strong>{allowed_methods}</strong></p>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.NO_CONTENT.value), HTTPStatus.NO_CONTENT.phrase, headers, body)

    def handle_trace(self, request_data: str) -> HttpResponse:
        body = f"""
        <html>
        <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
        <body>
            <h1>TRACE Request</h1>
            <pre>{request_data}</pre>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.OK.value), HTTPStatus.OK.phrase, headers, body)

    def generate_general_response(self) -> HttpResponse:
        body = """
        <html>
        <head><style>body { font-family: Arial, sans-serif; }</style></head>
        <body>
            <h1>Welcome to the Server!</h1>
            <p>Here are the operations you can perform:</p>
            <ul>
                <li><strong>GET</strong>: Retrieve data from the server.</li>
                <li><strong>POST</strong>: Create new data on the server.</li>
                <li><strong>PUT</strong>: Update existing data on the server.</li>
                <li><strong>PATCH</strong>: Partially update data on the server.</li>
                <li><strong>DELETE</strong>: Remove data from the server.</li>
                <li><strong>OPTIONS</strong>: List supported HTTP methods.</li>
                <li><strong>TRACE</strong>: Echo back the received request.</li>
            </ul>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        print("General Response:", HttpResponse("HTTP/1.1", "200", "OK", headers, body))
        return HttpResponse("HTTP/1.1", "200", "OK", headers, body)

    def generate_error_response(self, status: HTTPStatus) -> HttpResponse:
        body = f"""
        <html>
        <head><style>body {{ font-family: Arial, sans-serif; }}</style></head>
        <body>
            <h1>Error {status.value}</h1>
            <p>{status.phrase}: {status.description}</p>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Encoding-Type": "utf-8"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

if __name__ == "__main__":
    server = HttpServer(host='localhost', port=8080)
    server.start()