"""Serve a directory on localhost with a UTF-8 charset for .html files.

Usage: python3 serve.py <directory> <port>
"""
import functools
import http.server
import sys

directory, port = sys.argv[1], int(sys.argv[2])
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
http.server.SimpleHTTPRequestHandler.extensions_map[".html"] = "text/html; charset=utf-8"
http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
