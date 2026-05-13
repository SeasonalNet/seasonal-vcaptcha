# Architecture

Seasonal VCaptcha is daemon-backed but keeps a CLI boundary for Asterisk.

```text
Asterisk / FreePBX
        │
        ▼
seasonal-vcaptcha-digits /path/to.wav
        │
        ▼
local Unix-socket API daemon
        │
        ▼
warm Vosk recognizer
```

Asterisk should continue to call the CLI. The CLI formats stdout for the
dialplan and may use the daemon, direct recognition, or automatic daemon with
direct fallback mode.

## CLI contract

Default stdout is digits only:

```text
1234
```

Diagnostics go to stderr. Alternative stdout formats are available for operators:

```bash
seasonal-vcaptcha-digits --format json /path/to.wav
seasonal-vcaptcha-digits --format env /path/to.wav
```

## Daemon API

The daemon listens on a Unix socket by default:

```text
/run/seasonal-vcaptcha/seasonal-vcaptcha.sock
```

Endpoints:

- `POST /v1/recognize`
- `GET /healthz`
- `GET /readyz`
- `GET /metrics` when metrics are enabled

The API is local-only by design. TCP exists only as an explicit development or
operator override.
