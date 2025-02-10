import socket
import json
import chardet
import ssl  
from http import HTTPStatus
from utils import HttpRequest, HttpResponse

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
    def __init__(self, host: str = 'localhost', port: int = 8080, use_tls: bool = False, certfile: str = None, keyfile: str = None):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.certfile = certfile
        self.keyfile = keyfile
        self.data_store = {}  # In-memory data store for JSON objects

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            print(f"Server listening on {self.host}:{self.port}")

            if self.use_tls:
                # Crea un contexto SSL
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
                server_socket = context.wrap_socket(server_socket, server_side=True)

            while True:
                client_socket, client_address = server_socket.accept()
                with client_socket:
                    print(f"Connection from {client_address}")
                    request_data = self.receive_request(client_socket)
                    if not request_data:
                        continue
                    print("Is Request Data")
                    http_request = self.parse_http_request(request_data)
                    http_response = self.handle_request(http_request, request_data)
                    response = http_response.build_response().encode('utf-8')
                    print("Response a enviar: ", response)
                    client_socket.send(response)

    def receive_request(self, client_socket: socket.socket) -> str:
        request_data = b""
        client_socket.settimeout(30)  # Aumenta el tiempo de espera a 30 segundos
        while True:
            try:
                part = client_socket.recv(4096)
                if not part:
                    break
                request_data += part
                print("Received part: ", part)
                # Si se recibe una línea vacía, significa que la solicitud está completa
                if b'\r\n\r\n' in request_data:
                    break
            except socket.timeout:
                print("Socket timeout while receiving request")
                break
            except Exception as error:
                print(f"Error while receiving request: {error}")
                break

        if not request_data:
            print("No data received")
            return ""

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
            if request.method not in HTTP_METHODS:
                return self.generate_error_response(HTTPStatus.METHOD_NOT_ALLOWED)

            if not request.uri.startswith("/"):
                return self.generate_error_response(HTTPStatus.BAD_REQUEST)

            if request.uri == '/' and request.method == 'GET':
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
            return self.generate_error_response(HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR)
        
    def handle_get(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            body = json.dumps(self.data_store[key], indent=4)
            status = HTTPStatus.OK
        else:
            body = json.dumps({"error": "Not Found"})
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_head(self, request: HttpRequest) -> HttpResponse:
        response = self.handle_get(request)
        response.body = ""
        response.headers["Content-Length"] = "0"
        return response

    def handle_post(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        try:
            data = json.loads(request.body)
            self.data_store[key] = data
            body = json.dumps({"message": f"Data stored at {key}."})
            status = HTTPStatus.CREATED
        except json.JSONDecodeError:
            body = json.dumps({"error": "Invalid JSON"})
            status = HTTPStatus.BAD_REQUEST

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_put(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        try:
            data = json.loads(request.body)
            self.data_store[key] = data
            body = json.dumps({"message": f"Data at {key} updated."})
            status = HTTPStatus.OK
        except json.JSONDecodeError:
            body = json.dumps({"error": "Invalid JSON"})
            status = HTTPStatus.BAD_REQUEST

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_patch(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            try:
                updates = json.loads(request.body)
                self.data_store[key].update(updates)
                body = json.dumps({"message": f"Data at {key} patched."})
                status = HTTPStatus.OK
            except json.JSONDecodeError:
                body = json.dumps({"error": "Invalid JSON"})
                status = HTTPStatus.BAD_REQUEST
        else:
            body = json.dumps({"error": "Not Found"})
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_delete(self, request: HttpRequest) -> HttpResponse:
        key = request.uri.strip('/')
        if key in self.data_store:
            del self.data_store[key]
            body = json.dumps({"message": f"Data at {key} deleted."})
            status = HTTPStatus.OK
        else:
            body = json.dumps({"error": "Not Found"})
            status = HTTPStatus.NOT_FOUND

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

    def handle_connect(self, request: HttpRequest) -> HttpResponse:
        body = json.dumps({"message": "CONNECT method not supported in this context."})
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.NOT_IMPLEMENTED.value), HTTPStatus.NOT_IMPLEMENTED.phrase, headers, body)

    def handle_options(self, request: HttpRequest) -> HttpResponse:
        allowed_methods = ", ".join(method for method in HTTP_METHODS if method != "CONNECT")
        headers = {
            "Allow": allowed_methods,
            "Content-Length": "0",
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.NO_CONTENT.value), HTTPStatus.NO_CONTENT.phrase, headers, "")

    def handle_trace(self, request_data: str) -> HttpResponse:
        headers = {
            "Content-Type": "message/http",
            "Content-Length": str(len(request_data)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(HTTPStatus.OK.value), HTTPStatus.OK.phrase, headers, request_data)

    def generate_general_response(self):
        body = """
        <html>
        <head><style>body { font-family: Arial, sans-serif; }</style></head>
        <body>
            <h1>Welcome to the Server!</h1>
            <p>Here are the operations you can perform:</p>
            <ul>
                <li><strong>GET</strong>: Retrieve data from the server.
                    <br>Usage: Send a GET request to the server with the desired resource URI.
                    <br>Example: <code>GET /resource</code> retrieves the data stored at '/resource'.
                </li>
                <li><strong>HEAD</strong>: Retrieve headers for a resource without the body.
                    <br>Usage: Send a HEAD request to get the headers of a resource.
                    <br>Example: <code>HEAD /resource</code> returns the headers for the data at '/resource'.
                </li>
                <li><strong>POST</strong>: Create new data on the server.
                    <br>Usage: Send a POST request with a JSON body to create a new resource.
                    <br>Example: <code>POST /resource</code> with body <code>{"name": "example"}</code> stores the data.
                </li>
                <li><strong>PUT</strong>: Update existing data on the server.
                    <br>Usage: Send a PUT request with a JSON body to update a resource.
                    <br>Example: <code>PUT /resource</code> with body <code>{"name": "updated"}</code> updates the data.
                </li>
                <li><strong>PATCH</strong>: Partially update data on the server.
                    <br>Usage: Send a PATCH request with a JSON body to partially update a resource.
                    <br>Example: <code>PATCH /resource</code> with body <code>{"name": "partial"}</code> updates part of the data.
                </li>
                <li><strong>DELETE</strong>: Remove data from the server.
                    <br>Usage: Send a DELETE request to remove a resource.
                    <br>Example: <code>DELETE /resource</code> deletes the data stored at '/resource'.
                </li>
                <li><strong>OPTIONS</strong>: List supported HTTP methods.
                    <br>Usage: Send an OPTIONS request to discover the methods supported by the server.
                    <br>Example: <code>OPTIONS /</code> returns the allowed methods.
                </li>
                <li><strong>TRACE</strong>: Echo back the received request.
                    <br>Usage: Send a TRACE request to see what the server receives.
                    <br>Example: <code>TRACE /</code> returns the request as received by the server.
                </li>
            </ul>
        </body>
        </html>
        """
        headers = {
            "Content-Type": "text/html",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", "200", "OK", headers, body)

    def generate_error_response(self, status: HTTPStatus) -> HttpResponse:
        body = json.dumps({"error": status.phrase, "message": status.description})
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "keep-alive"
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

if __name__ == "__main__":
    server = HttpServer(host='localhost', port=8080, use_tls=True, certfile='localhost.pem', keyfile='localhost-key.pem')
    server.start()