# Security policy

## Scope

The starter targets a single user on a local Linux, macOS, or Windows
workstation. It must not be exposed to a LAN or the public internet.

The launcher binds the web service to `127.0.0.1`, creates a long random token,
and injects runtime guards that reject non-loopback connections. The server
also checks the client address, browser origin, upload size, engine extension,
artifact path, and token.

These controls do not make arbitrary engine code trustworthy. A derived
application must separately audit parsers, native libraries, model loaders,
archive handling, subprocesses, output formats, and licences.

## Reporting a vulnerability

Do not attach real confidential documents, tokens, or generated output to a
public issue. If a derived public repository enables private vulnerability
reporting, use that channel and include version, reproduction steps, impact,
and a minimal synthetic test file.
