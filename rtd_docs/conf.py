# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import platform
from pathlib import Path
if list(map(int, platform.python_version_tuple()[:2])) < [3, 11]:
    import tomli as tomllib
else:
    import tomllib

pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
with pyproject_path.open("rb") as f:
    pyproject = tomllib.load(f)

release = pyproject["project"]["version"]
project = f'hec-python-library {release}'
copyright = 'None'
author = 'CEIWR-HEC-WM'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx_design"
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]

# -- Generate a base parameter table -----------------------------------------

def generate_base_parameter_table():

    base_parameters_path = Path(__file__).parent.parent / "hec" / "resources" / "base_parameters.tsv"
    with base_parameters_path.open("rb") as f:
        text = f.read().decode("utf-8")
    lines = [line for line in text.strip().split("\n") if not line.startswith("#")]
    base_param_info = list(map(lambda s: s.split("\t")[:5], lines))
    base_param_info.insert(0, ["Base Parameter Name", "Long Name", "Description", "Default English Unit", "Default SI Unit"])
    widths = 5 * [0]
    for i in range(len(base_param_info)):
        if i > 0:
            for j in 0, 3, 4:
                base_param_info[i][j] = f"``{base_param_info[i][j]}``"
        for j in range(5):
            widths[j] = max(widths[j], len(base_param_info[i][j])+2)
    separator = "+"
    for i in range(5):
        separator += f"{widths[i] * '-'}+"

    with open("base_parameter_table.rst", "wb") as f:
        f.write(f"{separator}\n".encode("utf-8"))
        for i in range(len(base_param_info)):
            f.write("| ".encode("utf-8"))
            for j in range(5):
                f.write(f"{base_param_info[i][j].ljust(widths[j]-1)}| ".encode("utf-8"))
            if i == 0:
                f.write(f"\n{separator.replace('-', '-')}\n".encode("utf-8"))
            else:
                f.write(f"\n{separator}\n".encode("utf-8"))

# generate_base_parameter_table()

