from io import BytesIO
from urllib.parse import quote

from server import TalentPlatformHandler, initialize_database


class WsgiSocket:
    def __init__(self, request_bytes):
        self.input = BytesIO(request_bytes)
        self.output = BytesIO()

    def makefile(self, mode, buffering=None):
        if "r" in mode:
            return self.input
        return self.output

    def sendall(self, data):
        self.output.write(data)


class WsgiServer:
    server_name = "pythonanywhere"
    server_port = 80


def build_request_bytes(environ):
    method = environ.get("REQUEST_METHOD", "GET")
    path = quote(environ.get("PATH_INFO", "/"), safe="/%")
    query = environ.get("QUERY_STRING", "")
    target = f"{path}?{query}" if query else path
    protocol = environ.get("SERVER_PROTOCOL", "HTTP/1.1")

    headers = [
        f"{method} {target} {protocol}",
        f"Host: {environ.get('HTTP_HOST', 'localhost')}",
    ]

    for key, value in environ.items():
        if not key.startswith("HTTP_"):
            continue
        header_name = key[5:].replace("_", "-").title()
        if header_name == "Host":
            continue
        headers.append(f"{header_name}: {value}")

    content_type = environ.get("CONTENT_TYPE")
    if content_type:
        headers.append(f"Content-Type: {content_type}")

    content_length = environ.get("CONTENT_LENGTH") or "0"
    body = environ["wsgi.input"].read(int(content_length or 0))
    headers.append(f"Content-Length: {len(body)}")

    return ("\r\n".join(headers) + "\r\n\r\n").encode("iso-8859-1") + body


def parse_response(response_bytes):
    head, _, body = response_bytes.partition(b"\r\n\r\n")
    lines = head.decode("iso-8859-1").split("\r\n")
    status_line = lines[0]
    status_parts = status_line.split(" ", 2)
    status = " ".join(status_parts[1:]) if len(status_parts) >= 3 else "500 Internal Server Error"
    headers = []
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers.append((name.strip(), value.strip()))
    return status, headers, body


def application(environ, start_response):
    initialize_database()
    request_socket = WsgiSocket(build_request_bytes(environ))
    TalentPlatformHandler(request_socket, ("127.0.0.1", 0), WsgiServer())
    status, headers, body = parse_response(request_socket.output.getvalue())
    start_response(status, headers)
    return [body]
