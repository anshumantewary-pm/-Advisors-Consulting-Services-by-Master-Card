# Security

Cardwise is a calculation library: it makes no network calls, stores nothing and runs entirely on your machine or in your browser.

## Reporting a vulnerability

Please report security issues privately through GitHub's **Security → Report a vulnerability** on this repository rather than in a public issue. Include the version (`cardwise --version`), what you ran and what happened. You should get a reply within a week.

## Handling client data

- The web workbench runs in the browser via Pyodide; files you load are not uploaded anywhere.
- The CLI reads only the files you pass it and writes only where you ask (`--report`, `--memo`).
- Do not commit client data to this repository. The files in `examples/` are synthetic.
