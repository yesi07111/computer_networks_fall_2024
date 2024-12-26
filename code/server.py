import socket
from http import HTTPStatus
from utils import *

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

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                client_socket, client_address = server_socket.accept()
                with client_socket:
                    print(f"Connection from {client_address}")
                    request_data = client_socket.recv(4096).decode('utf-8')
                    if not request_data:
                        continue
                    
                    http_request = self.parse_http_request(request_data)
                    http_response = self.handle_request(http_request)
                    client_socket.sendall(http_response.build_response().encode('utf-8'))

    def parse_http_request(self, request_data: str) -> HttpRequest:
        lines = request_data.split("\r\n")
        if not lines:
            raise ValueError("Empty request data")
        
        request_line = lines[0].split(" ")
        if len(request_line) != 3:
            raise ValueError("Invalid request line format")
        
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
        return HttpRequest(method, uri, headers, body)

    def handle_request(self, request: HttpRequest) -> HttpResponse:
        try:
            # Validate HTTP method
            if request.method not in HTTP_METHODS:
                return self.generate_error_response(HTTPStatus.METHOD_NOT_ALLOWED)

            # Validate URI format (basic check)
            if not request.uri.startswith("/"):
                return self.generate_error_response(HTTPStatus.BAD_REQUEST)
            
            # Simple response for demonstration purposes
            body = f"<html><body><h1>Hello, World!</h1><p>You requested {request.uri}</p></body></html>"
            headers = {
                "Content-Type": "text/html",
                "Content-Length": str(len(body))
            }
            return HttpResponse("HTTP/1.1", "200", "OK", headers, body)

        except ValueError as e:
            # Invalid request data
            return self.generate_error_response(HTTPStatus.BAD_REQUEST)
        except Exception as e:
            # Generic error
            return self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR)

    def generate_error_response(self, status: HTTPStatus) -> HttpResponse:
        body = f"<html><body><h1>{status.phrase}</h1><p>{status.description}</p></body></html>"
        headers = {
            "Content-Type": "text/html",
            "Content-Length": str(len(body))
        }
        return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

if __name__ == "__main__":
    server = HttpServer(host='localhost', port=8080)
    server.start()

# import socket
# import ssl
# from http import HTTPStatus
# from utils import *

# HTTP_METHODS = [
#     'GET',
#     'HEAD',
#     'POST',
#     'PUT',
#     'DELETE',
#     'CONNECT',
#     'OPTIONS',
#     'TRACE',
#     'PATCH'
# ]

# class HttpServer:
#     def __init__(self, host: str = 'localhost', port: int = 8080, use_tls: bool = False, certfile: str = None, keyfile: str = None):
#         self.host = host
#         self.port = port
#         self.use_tls = use_tls
#         self.certfile = certfile
#         self.keyfile = keyfile

#         if self.use_tls and (not self.certfile or not self.keyfile):
#             raise ValueError("TLS enabled but certfile or keyfile is not provided.")

#     def start(self):
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
#             server_socket.bind((self.host, self.port))
#             server_socket.listen(5)

#             if self.use_tls:
#                 context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#                 context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
#                 server_socket = context.wrap_socket(server_socket, server_side=True)

#             protocol = "https" if self.use_tls else "http"
#             print(f"Server listening on {protocol}://{self.host}:{self.port}")

#             while True:
#                 client_socket, client_address = server_socket.accept()
#                 with client_socket:
#                     print(f"Connection from {client_address}")
#                     try:
#                         request_data = client_socket.recv(4096).decode('utf-8')
#                         if not request_data:
#                             continue

#                         http_request = self.parse_http_request(request_data)
#                         http_response = self.handle_request(http_request)
#                         client_socket.sendall(http_response.build_response().encode('utf-8'))
#                     except Exception as e:
#                         print(f"Error handling request: {e}")
#                         client_socket.sendall(self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR).build_response().encode('utf-8'))

#     def parse_http_request(self, request_data: str) -> HttpRequest:
#         lines = request_data.split("\r\n")
#         if not lines:
#             raise ValueError("Empty request data")

#         request_line = lines[0].split(" ")
#         if len(request_line) != 3:
#             raise ValueError("Invalid request line format")

#         method, uri, _ = request_line

#         headers = {}
#         index = 1
#         while index < len(lines) and lines[index] != "":
#             header_line = lines[index]
#             if ": " not in header_line:
#                 raise ValueError(f"Invalid header format: {header_line}")
#             key, value = header_line.split(": ", 1)
#             headers[key] = value
#             index += 1

#         body = "\r\n".join(lines[index + 1:])
#         return HttpRequest(method, uri, headers, body)

#     def handle_request(self, request: HttpRequest) -> HttpResponse:
#         try:
#             # Validate HTTP method
#             if request.method not in HTTP_METHODS:
#                 return self.generate_error_response(HTTPStatus.METHOD_NOT_ALLOWED)

#             # Validate URI format (basic check)
#             if not request.uri.startswith("/"):
#                 return self.generate_error_response(HTTPStatus.BAD_REQUEST)

#             # Simple response for demonstration purposes
#             body = f"<html><body><h1>Hello, World!</h1><p>You requested {request.uri}</p></body></html>"
#             headers = {
#                 "Content-Type": "text/html",
#                 "Content-Length": str(len(body))
#             }
#             return HttpResponse("HTTP/1.1", "200", "OK", headers, body)

#         except ValueError as e:
#             # Invalid request data
#             return self.generate_error_response(HTTPStatus.BAD_REQUEST)
#         except Exception as e:
#             # Generic error
#             return self.generate_error_response(HTTPStatus.INTERNAL_SERVER_ERROR)

#     def generate_error_response(self, status: HTTPStatus) -> HttpResponse:
#         body = f"<html><body><h1>{status.phrase}</h1><p>{status.description}</p></body></html>"
#         headers = {
#             "Content-Type": "text/html",
#             "Content-Length": str(len(body))
#         }
#         return HttpResponse("HTTP/1.1", str(status.value), status.phrase, headers, body)

# if __name__ == "__main__":
#     # Example usage with TLS enabled
#     server = HttpServer(host='localhost', port=8443, use_tls=True, certfile='server.crt', keyfile='server.key')
#     server.start()
