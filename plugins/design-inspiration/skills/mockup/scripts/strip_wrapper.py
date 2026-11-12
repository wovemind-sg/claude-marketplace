"""Strip the Artifact publish wrapper from a saved page, leaving the page alone.

The saved file is the served document: everything up to and including the
<body> open tag, and the closing </body></html>, were added by the publish.

Usage: python3 strip_wrapper.py <saved file> <output file>
"""
import re
import sys

page = open(sys.argv[1], encoding="utf-8").read()
page = re.sub(r"(?is)\A.*?<body[^>]*>\s*", "", page, count=1)
page = re.sub(r"(?is)</body>\s*</html>\s*\Z", "", page)
open(sys.argv[2], "w", encoding="utf-8").write(page)
