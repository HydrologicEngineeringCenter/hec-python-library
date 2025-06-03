html_filename = "docs/hec.html"
with open(html_filename, "rb") as f:
    data = f.read()
for module in (
    "const",
    "datastore",
    "duration",
    "hectime",
    "interval",
    "location",
    "parameter",
    "quality",
    "timeseries",
    "timespan",
    "unit",
):
    old = f'href="{module}.html#'.encode("utf-8")
    new = f'href="hec/{module}.html#'.encode("utf-8")
    data = data.replace(old, new)
    old = f'href="./{module}.html#'.encode("utf-8")
    new = f'href="./hec/{module}.html#'.encode("utf-8")
    data = data.replace(old, new)
with open(html_filename, "wb") as f:
    f.write(data)
