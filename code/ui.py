from http import HTTPStatus
import socket
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from threading import Thread

import chardet
from client import HttpClient
from utils import HttpResponse, HttpRequest
from server import HttpServer
import os
import tempfile
import webbrowser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import base64

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

HTTP_HEADERS = {
    'Accept': ['text/html', 'application/json', 'application/xml'],
    'Accept-Language': ['en-US', 'es-ES', 'fr-FR'],
    'User-Agent': ['Mozilla/5.0', 'CustomHttpClient/1.0'],
    'Content-Type': ['application/json', 'application/x-www-form-urlencoded'],
    'Authorization': ['Bearer token', 'Basic auth'],
    'Cache-Control': ['no-cache', 'no-store'],
    'Connection': ['keep-alive', 'close'],
    'Cookie': ['sessionId=abc123', 'userId=xyz789'],
    'Host': ['localhost', 'www.example.com'],
    'Referer': ['http://localhost', 'http://www.example.com']
}

DEFAULT_HEADERS = {
    'Host': '',
    'User-Agent': 'CustomHttpClient/1.0'
}

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HTTP Client-Server Interface")
        self.root.geometry("1200x1000")
        self.current_response_index = 0
        self.responses = []
        self.create_widgets()
    
    def create_widgets(self):
        # Main Frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Client Section
        client_frame = ttk.LabelFrame(main_frame, text="HTTP Client", padding=(10, 10))
        client_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(client_frame, text="Host:").grid(row=0, column=0, sticky="w")
        self.client_host = ttk.Entry(client_frame)
        self.client_host.grid(row=0, column=1, sticky="ew", padx=5)
        self.client_host.insert(0, "www.google.com")

        ttk.Label(client_frame, text="Port:").grid(row=1, column=0, sticky="w")
        self.client_port = ttk.Entry(client_frame)
        self.client_port.grid(row=1, column=1, sticky="ew", padx=5)
        self.client_port.insert(0, "443")

        ttk.Label(client_frame, text="Method:").grid(row=2, column=0, sticky="w")
        self.method_var = tk.StringVar(value="GET")
        self.method_dropdown = ttk.Combobox(client_frame, textvariable=self.method_var, values=HTTP_METHODS)
        self.method_dropdown.grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Label(client_frame, text="URI:").grid(row=3, column=0, sticky="w")
        self.client_uri = ttk.Entry(client_frame)
        self.client_uri.grid(row=3, column=1, sticky="ew", padx=5)
        self.client_uri.insert(0, "/")

        self.use_tls = tk.BooleanVar(value=True)
        ttk.Checkbutton(client_frame, text="Use TLS", variable=self.use_tls).grid(row=4, column=0, columnspan=2, sticky="w")

        ttk.Label(client_frame, text="Body Size Threshold (bytes):").grid(row=5, column=0, sticky="w")
        self.body_size_threshold = ttk.Entry(client_frame)
        self.body_size_threshold.grid(row=5, column=1, sticky="ew", padx=5)
        self.body_size_threshold.insert(0, "1048576")  # Default 1 MB

        # Custom Body Section
        custom_body_frame = ttk.Frame(client_frame)
        custom_body_frame.grid(row=0, column=2, rowspan=6, sticky="nsew", padx=5, pady=5)

        self.custom_body_label = ttk.Label(custom_body_frame, text="Custom\nBody:")
        self.custom_body_label.pack(anchor="w")

        self.custom_body = tk.Text(custom_body_frame, height=8, width=40, wrap="word")
        self.custom_body.pack(fill="both", expand=True)

        ttk.Label(client_frame, text="Headers Examples:").grid(row=6, column=0, sticky="nw")
        self.headers_listbox = tk.Listbox(client_frame, selectmode="multiple", height=6)
        for header in HTTP_HEADERS.keys():
            self.headers_listbox.insert(tk.END, header)
        self.headers_listbox.grid(row=6, column=1, sticky="ew", pady=5)
        self.headers_listbox.bind('<<ListboxSelect>>', self.update_header_values)

        self.header_values_label = ttk.Label(client_frame, text="Header Values Example:")
        self.header_values_label.grid(row=7, column=0, sticky="nw")
        self.header_values_listbox = tk.Listbox(client_frame, selectmode="multiple", height=6)
        self.header_values_listbox.grid(row=7, column=1, sticky="ew", pady=5)
        self.header_values_listbox.bind('<Button-1>', lambda e: 'break')  # Make listbox read-only

        self.custom_headers_label = ttk.Label(client_frame, text="Custom\nHeaders:")
        self.custom_headers_label.grid(row=8, column=0, sticky="nw")
        
        self.custom_headers = tk.Text(client_frame, height=5, width=40, wrap="word")
        self.custom_headers.grid(row=8, column=1, sticky="ew", pady=5)
        self.set_default_headers()

        self.use_pipeline = tk.BooleanVar(value=False)
        ttk.Checkbutton(client_frame, text="Use Pipeline", variable=self.use_pipeline).grid(row=9, column=0, columnspan=2, sticky="w")

        ttk.Button(client_frame, text="Send Request", command=self.start_send_request_thread).grid(row=10, column=0, columnspan=2, pady=5)

        # Response Display
        self.response_display = tk.Text(client_frame, height=10, wrap="word", state='disabled')
        self.response_display.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=5)

        # Navigation Buttons
        self.prev_button = ttk.Button(client_frame, text="Atras", command=self.show_previous_response)
        self.next_button = ttk.Button(client_frame, text="Siguiente", command=self.show_next_response)
        self.prev_button.grid(row=12, column=0, sticky="ew", padx=5)
        self.next_button.grid(row=12, column=1, sticky="ew", padx=5)

        ttk.Button(client_frame, text="View Response Html", command=self.view_response).grid(row=13, column=0, columnspan=2, pady=5)

        # Server Section
        server_frame = ttk.LabelFrame(main_frame, text="HTTP Server", padding=(10, 10))
        server_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        ttk.Label(server_frame, text="Host:").grid(row=0, column=0, sticky="w")
        self.server_host = ttk.Entry(server_frame)
        self.server_host.grid(row=0, column=1, sticky="ew", padx=5)
        self.server_host.insert(0, "localhost")

        ttk.Label(server_frame, text="Port:").grid(row=1, column=0, sticky="w")
        self.server_port = ttk.Entry(server_frame)
        self.server_port.grid(row=1, column=1, sticky="ew", padx=5)
        self.server_port.insert(0, "8080")

        ttk.Button(server_frame, text="Start Server", command=self.start_server).grid(row=2, column=0, columnspan=2, pady=5)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        client_frame.columnconfigure(1, weight=1)
        server_frame.columnconfigure(1, weight=1)

    def set_default_headers(self):
        host = self.client_host.get()
        default_headers_text = f"Host: {host}\nUser-Agent: {DEFAULT_HEADERS['User-Agent']}"
        self.custom_headers.insert("1.0", default_headers_text)

    def update_header_values(self, event):
        selected_indices = self.headers_listbox.curselection()
        self.header_values_listbox.delete(0, tk.END)
        for i in selected_indices:
            header = self.headers_listbox.get(i)
            for value in HTTP_HEADERS[header]:
                self.header_values_listbox.insert(tk.END, f"{header}: {value}")

    def start_send_request_thread(self):
        print("Starting request thread...")
        self.root.after(0, lambda: messagebox.showinfo("Info", "Sending request..."))
        thread = Thread(target=self.send_request)
        thread.start()

    def display_current_response(self):
        print("Displaying current response...")
        if self.responses:
            self.response_display.config(state='normal')
            self.response_display.delete("1.0", tk.END)
            self.response_display.insert(tk.END, str(self.responses[self.current_response_index]))
            self.response_display.config(state='disabled')
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        print("Updating navigation buttons...")
        if len(self.responses) > 1:
            if self.current_response_index > 0:
                self.prev_button.grid()
            else:
                self.prev_button.grid_forget()

            if self.current_response_index < len(self.responses) - 1:
                self.next_button.grid()
            else:
                self.next_button.grid_forget()
        else:
            self.prev_button.grid_forget()
            self.next_button.grid_forget()

    def show_previous_response(self):
        print("Showing previous response...")
        if self.current_response_index > 0:
            self.current_response_index -= 1
            self.display_current_response()

    def show_next_response(self):
        print("Showing next response...")
        if self.current_response_index < len(self.responses) - 1:
            self.current_response_index += 1
            self.display_current_response()

    def handle_response_codes(self, responses, requests):
        print("Handling response codes in ui...")
        for i, (response, request) in enumerate(zip(responses, requests)):
            print(f"response: {response} \nrequest: {request}")
            if response.status_code.startswith('2'):
                self.display_2xx_info(response, request, i)
            elif response.status_code.startswith('3'):
                self.handle_3xx_info(response, request, i)
            elif response.status_code.startswith('4'):
                self.handle_4xx_info(response, request, i)
            elif response.status_code.startswith('5'):
                self.handle_5xx_info(response, request, i)

    def display_2xx_info(self, response, request, index):
        info_message = {
            '200': "Request was successful.",
            '201': "Resource created successfully.",
            '202': "Request accepted for processing, but not completed.",
            '203': "Non-authoritative information received.",
            '204': "No content to display.",
            '205': "Reset content.",
            '206': "Partial content received.",
            '207': "Multi-status response received."
        }.get(response.status_code, "Successful response received.")
        messagebox.showinfo(f"2xx Response for Request {index+1}", f"URL: {request.uri}\n{info_message}")

    def handle_3xx_info(self, response, request, index):
        if response.status_code == '304':
            messagebox.showinfo(f"304 Not Modified for Request {index+1}", f"URL: {request.uri}\nResource not modified. Using cached version.")
        elif response.status_code == '305':
            if messagebox.askyesno(f"305 Use Proxy for Request {index+1}", f"URL: {request.uri}\nUse proxy specified in the response?"):
                proxy_host, proxy_port, _ = self.parse_url(response.headers['Location'])
                self.use_proxy(request, proxy_host, proxy_port)
        elif response.status_code == '306':
            messagebox.showinfo(f"306 Switch Proxy for Request {index+1}", f"URL: {request.uri}\nSwitch proxy. This code is deprecated.")

    def handle_4xx_info(self, response, request, index):
        error_message = {
            '400': "Bad Request: The request contains syntax errors and should not be repeated.",
            '401': "Unauthorized: Authentication is required. Would you like to provide credentials?",
            '402': "Payment Required: This code is reserved for future use.",
            '403': "Forbidden: The request was legal, but the server refuses to respond.",
            '404': "Not Found: The requested resource could not be found.",
            '405': "Method Not Allowed: The request method is not supported for the requested resource.",
            '406': "Not Acceptable: The server cannot return data in any of the formats accepted by the client.",
            '407': "Proxy Authentication Required: Authentication with the proxy is required.",
            '408': "Request Timeout: The client failed to continue the request.",
            '409': "Conflict: The request could not be processed due to a conflict with the current state of the resource.",
            '410': "Gone: The requested resource is no longer available and will not be available again.",
            '411': "Length Required: The request did not specify the length of its content, which is required by the requested resource.",
            '412': "Precondition Failed: The server does not meet one of the preconditions that the requester put on the request.",
            '413': "Payload Too Large: The request is larger than the server is willing or able to process.",
            '414': "URI Too Long: The URI provided was too long for the server to process.",
            '415': "Unsupported Media Type: The request entity has a media type which the server or resource does not support.",
            '416': "Range Not Satisfiable: The client has asked for a portion of the file, but the server cannot supply that portion.",
            '417': "Expectation Failed: The server cannot meet the requirements of the Expect request-header field.",
            '421': "Misdirected Request: The request was directed at a server that is not able to produce a response.",
            '422': "Unprocessable Entity: The request was well-formed but was unable to be followed due to semantic errors.",
            '423': "Locked: The resource that is being accessed is locked.",
            '424': "Failed Dependency: The request failed due to failure of a previous request.",
            '425': "Too Early: The server is unwilling to risk processing a request that might be replayed.",
            '426': "Upgrade Required: The client should switch to a different protocol such as TLS/1.0.",
            '449': "Retry With: The request should be retried after doing the appropriate action."
        }.get(response.status_code, "Client error occurred.")

        if response.status_code == '401':
            if messagebox.askyesno(f"401 Unauthorized for Request {index+1}", f"URL: {request.uri}\n{error_message}"):
                username = simpledialog.askstring("Username", "Enter your username:")
                password = simpledialog.askstring("Password", "Enter your password:", show='*')
                if username and password:
                    self.custom_headers.insert(tk.END, f"\nAuthorization: Basic {username}:{password}")
                    self.start_send_request_thread()
        elif response.status_code == '411':
            if messagebox.askyesno(f"411 Length Required for Request {index+1}", f"URL: {request.uri}\n{error_message}"):
                length = simpledialog.askinteger("Content Length", "Enter the content length:")
                if length:
                    self.custom_headers.insert(tk.END, f"\nContent-Length: {length}")
                    self.start_send_request_thread()
        elif response.status_code == '426':
            if messagebox.askyesno(f"426 Upgrade Required for Request {index+1}", f"URL: {request.uri}\n{error_message}"):
                self.use_tls.set(True)
                self.start_send_request_thread()
        else:
            messagebox.showinfo(f"{response.status_code} Error for Request {index+1}", f"URL: {request.uri}\n{error_message}")

    def handle_5xx_info(self, response, request, index):
        error_message = {
            '500': "Internal Server Error: The server encountered an unexpected condition.",
            '501': "Not Implemented: The server does not support the functionality required to fulfill the request.",
            '502': "Bad Gateway: The server received an invalid response from the upstream server.",
            '503': "Service Unavailable: The server is currently unable to handle the request due to temporary overloading or maintenance.",
            '504': "Gateway Timeout: The server did not receive a timely response from the upstream server.",
            '505': "HTTP Version Not Supported: The server does not support the HTTP protocol version used in the request.",
            '506': "Variant Also Negotiates: Transparent content negotiation for the request results in a circular reference.",
            '507': "Insufficient Storage: The server is unable to store the representation needed to complete the request.",
            '509': "Bandwidth Limit Exceeded: The server has exceeded the bandwidth specified by the server administrator.",
            '510': "Not Extended: Further extensions to the request are required for the server to fulfill it."
        }.get(response.status_code, "Server error occurred.")

        if response.status_code == '503':
            if messagebox.askyesno(f"503 Service Unavailable for Request {index+1}", f"URL: {request.uri}\n{error_message} Would you like to retry?"):
                self.start_send_request_thread()
        else:
            messagebox.showinfo(f"{response.status_code} Error for Request {index+1}", f"URL: {request.uri}\n{error_message}")

    def use_proxy(self, http_request: HttpRequest, proxy_host: str, proxy_port: int):
        print("Using proxy...")
        # Connect to the proxy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((proxy_host, proxy_port))

        # Modify the request line to include the full URL
        full_url = f"http://{self.client_host.get()}{http_request.uri}"
        request_line = f"{http_request.method} {full_url} HTTP/1.1\r\n"
        http_request.headers['Host'] = self.client_host.get()

        # Rebuild the request with the modified request line
        headers = ''
        for key, value in http_request.headers.items():
            headers += f'{key}: {value}\r\n'
        
        blank_line = '\r\n'
        body = http_request.body if http_request.body else ''
        
        request_data = request_line + headers + blank_line + body
        sock.sendall(request_data.encode('utf-8'))

        # Receive the response from the proxy
        response = self.receive_response(sock)
        sock.close()
        self.display_response(response)

    def view_response(self):
        print("Viewing response...")
        if self.responses and self.responses[self.current_response_index].body:
            # Parse the HTML to find image URLs
            soup = BeautifulSoup(self.responses[self.current_response_index].body, 'html.parser')
            images = soup.find_all('img')

            # Create a temporary directory to store images
            temp_dir = tempfile.mkdtemp()

            # Download images and update their src attributes
            for img in images:
                img_url = img.get('src')
                if img_url:
                    try:
                        if img_url.startswith('data:image/'):
                            # Handle base64 encoded images
                            header, encoded = img_url.split(',', 1)
                            img_data = base64.b64decode(encoded)
                            img_extension = header.split('/')[1].split(';')[0]
                            img_name = f"image_{images.index(img)}.{img_extension}"
                        else:
                            # Convert relative URLs to absolute URLs
                            img_url = urljoin(f"https://{self.client_host.get()}", img_url)
                            img_data = requests.get(img_url).content
                            img_name = os.path.basename(img_url)

                        img_path = os.path.join(temp_dir, img_name)

                        with open(img_path, 'wb') as img_file:
                            img_file.write(img_data)

                        # Update the src attribute to point to the local file
                        img['src'] = f"file://{img_path}"
                    except Exception as e:
                        print(f"Failed to process image {img_url}: {e}")

            # Save the modified HTML to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                temp_file.write(soup.prettify().encode('utf-8'))
                temp_file_path = temp_file.name

            # Open the modified HTML in the default web browser
            webbrowser.open(f"file://{os.path.abspath(temp_file_path)}")
        else:
            self.root.after(0, lambda: messagebox.showinfo("Info", "No response body to display"))

    def start_server(self):
        print("Starting server...")
        host = self.server_host.get()
        port = int(self.server_port.get())

        def run_server():
            server = HttpServer(host, port, self.use_tls.get(), certfile='server.crt', keyfile='server.key')
            server.start()

        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        self.root.after(0, lambda: messagebox.showinfo("Server", f"Server started on {host}:{port}"))

    def parse_url(self, url: str) -> tuple[str, int, str]:
        print(f"Parsing URL: {url}")
        if url.startswith('http://'):
            url = url[7:]
        elif url.startswith('https://'):
            url = url[8:]

        host, path = url.split('/', 1)
        path = '/' + path

        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        else:
            port = 443 if self.use_tls.get() else 80

        return host, port, path

    # In ui.py, update the send_request method to correctly handle the response
    def send_request(self):
        print("Preparing to send request...")
        host = self.client_host.get()
        port = int(self.client_port.get())
        method = self.method_var.get()
        uri = self.client_uri.get()
        use_tls = self.use_tls.get()
        body_size_threshold = int(self.body_size_threshold.get())
        use_pipeline = self.use_pipeline.get()
        body: str = self.custom_body.get("1.0", tk.END).strip()

        if not body:
            body = None

        print(f"Host: {host}, Port: {port}, Method: {method}, URI: {uri}, Use TLS: {use_tls}, Pipeline: {use_pipeline}")

        if not HttpClient.is_valid_host(self, host):
            self.root.after(0, lambda: messagebox.showerror("Error", "Invalid host"))
            return

        headers = {}
        custom_headers_text = self.custom_headers.get("1.0", tk.END).strip()
        if custom_headers_text:
            custom_headers = dict(line.split(": ", 1) for line in custom_headers_text.splitlines() if ": " in line)
            headers.update(custom_headers)
        if 'Host' not in headers:
            headers['Host'] = host

        # Create multiple requests for demonstration
        requests = [
            HttpRequest(method=method, uri=uri, headers=headers, body=body)
        ]

        client = HttpClient(host, port, use_tls, body_size_threshold=body_size_threshold)

        try:
            print(f"Self.responses before sending requests: {self.responses}")
            print("Sending requests...")
            new_responses = client.send_requests(requests, use_pipeline=use_pipeline)
            print("Requests sent successfully.")
            self.responses = new_responses + self.responses  # Add new responses to the front
            print("Response: ", new_responses)
            self.current_response_index = 0
            print(f"Self.responses after sending requests: {self.responses}")
            self.root.after(0, self.display_current_response)
            self.root.after(0, self.handle_response_codes, new_responses, requests)
        except Exception as e:
            print(f"Error sending request: {e}")
            self.root.after(0, lambda e=e: messagebox.showerror("Error", str(e)))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()