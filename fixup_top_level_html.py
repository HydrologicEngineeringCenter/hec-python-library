html_filename = "docs/hec.html"
with open(html_filename, "rb") as f:
    data = f.read()
data = data.decode("utf-8")
data = data.replace('href="parameter.html#', 'href=hec/parameter.html#')
data = data.encode("utf-8")
with open(html_filename, "wb") as f:
    f.write(data)
