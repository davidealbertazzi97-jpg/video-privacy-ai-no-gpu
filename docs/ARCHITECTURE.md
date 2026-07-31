# Architecture

```text
browser on 127.0.0.1
        |
        | token + same-origin request
        v
 FastAPI boundary ──> SQLite job metadata
        |
        | bounded private work copy
        v
 one local worker ──> registered engine ──> durable result artifacts
        |
        └── work copy removed after success or failure
```

The launcher is the security root. It creates a private token, chooses an
available loopback port, removes inherited Python injection paths, enables the
runtime network guard, and starts a fixed Uvicorn command without a shell.

The HTTP boundary accepts only loopback clients. API calls require the token;
state-changing browser calls must also come from the exact loopback origin.
Uploaded names are reduced to a safe basename and accepted only when a
registered engine declares their extension.

Jobs are serialized deliberately. This gives predictable CPU and memory use on
consumer hardware. SQLite retains status and small non-sensitive summaries.
Source documents live only in the private work directory and are removed in a
`finally` path. Result files are durable and visible to the user.

The Python network guard is cross-platform. The small `LD_PRELOAD` guard adds a
second layer on Linux and also covers many native libraries. Neither can defend
against malicious code deliberately disabling the guard, so engines remain
trusted code and must be reviewed.
