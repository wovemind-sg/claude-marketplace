"""Serve a directory on localhost with a UTF-8 charset for .html files.

Usage: python3 serve.py <directory> <port>
"""
import functools
import http.server
import sys

if len(sys.argv) != 3 or not sys.argv[2].isdigit():
    sys.exit("usage: python3 serve.py <directory> <port>")
directory, port = sys.argv[1], int(sys.argv[2])
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
http.server.SimpleHTTPRequestHandler.extensions_map[".html"] = "text/html; charset=utf-8"
try:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
except OSError:
    sys.exit(f"port {port} is already in use, pick another")
server.serve_forever()
