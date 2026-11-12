"""Strip the Artifact publish wrapper from a saved page, leaving the page alone.

The saved file is the served document: everything up to and including the
<body> open tag, and the closing </body></html>, were added by the publish.
A file without that wrapper is rejected (write the inline HTML directly instead).

Usage: python3 strip_wrapper.py <saved file> <output file>
       python3 strip_wrapper.py --selftest
"""
import re
import sys

HEAD = re.compile(r"(?is)\A.*?<body[^>]*>\s*")
TAIL = re.compile(r"(?is)</body>\s*</html>\s*\Z")


def strip_wrapper(text):
    head, tail = HEAD.search(text), TAIL.search(text)
    if not head or not tail or tail.start() < head.end():
        raise ValueError("no Artifact wrapper found (need a <body> open tag and a closing </body></html>)")
    return text[head.end():tail.start()]


def selftest():
    page = '<div class="a">héllo — ©</div>\n<p>x</p>'
    wrapped = f'<!doctype html><html><head><meta charset="utf-8"></head>\n<body class="b">\n{page}\n</body>\n</html>\n'
    assert strip_wrapper(wrapped) == page + "\n", strip_wrapper(wrapped)
    for bad in (page, "<html><body>" + page, page + "</body></html>"):
        try:
            strip_wrapper(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted unwrapped input: {bad!r}")
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit("usage: python3 strip_wrapper.py <saved file> <output file>")
    try:
        out = strip_wrapper(open(sys.argv[1], encoding="utf-8").read())
    except ValueError as e:
        sys.exit(f"strip_wrapper: {e}")
    open(sys.argv[2], "w", encoding="utf-8").write(out)
