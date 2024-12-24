import socket
import ssl

from utils import *

class HttpClient:
    def __init__(self, host: str, port: int = 80, use_tls: bool = True, max_redirects: int = 5):
        self.host: str = host
        self.port: int = port
        self.use_tls: bool = use_tls
        self.max_redirects: int = max_redirects

    def send_request(self, http_request: HttpRequest) -> HttpResponse:
        redirects = 0
        while redirects < self.max_redirects:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                if self.use_tls:
                    context = ssl.create_default_context()
                    with context.wrap_socket(sock, server_hostname=self.host) as tls_sock:
                        tls_sock.connect((self.host, self.port))
                        request_data = http_request.build_request()
                        tls_sock.sendall(request_data.encode('utf-8'))
                        response = self.receive_response(tls_sock)
                else:
                    sock.connect((self.host, self.port))
                    request_data = http_request.build_request()
                    sock.sendall(request_data.encode('utf-8'))
                    response = self.receive_response(sock)

            if response.status_code.startswith('3') and 'Location' in response.headers:
                new_location = response.headers['Location']
                self.host, self.port, http_request.uri = self.parse_url(new_location)
                request.headers['Host'] = self.host
                redirects += 1
            else:
                return response

        raise Exception('Too many redirects')

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
                if not part:
                    break
                response += part
            except socket.timeout:
                break
        
        parsed_response = self.parse_http_response(response.decode('utf-8'))

        return parsed_response
    
    def parse_http_response(self, response_str: str) -> HttpResponse:
        lines = response_str.split('\r\n')
        
        status_line = lines[0]
        version, status_code, reason_phrase = status_line.split(' ', 2)
        
        headers = {}
        index = 1
        while lines[index] != '':
            header_line = lines[index]
            key, value = header_line.split(': ', 1)
            headers[key] = value
            index += 1
        
        body = '\r\n'.join(lines[index+1:])
        
        return HttpResponse(version, status_code, reason_phrase, headers, body)

if __name__ == '__main__':
    request = HttpRequest(
        method='GET',
        uri='/',
        headers={
            'Host': 'google.com',
            'User-Agent': 'CustomHttpClient/1.0'
        }
    )

    client = HttpClient('google.com', 443)
    response = client.send_request(request)

    print(request.build_request(), '\n\n\n\n')
    print(response)