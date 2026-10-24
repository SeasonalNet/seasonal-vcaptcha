# seasonal-vcaptcha

Small Vosk-powered spoken digit CAPTCHA recognizer used by SeasonalPBX / FreePBX call flows.

This repository started as a preservation import from the legacy `FreePBX17` VM. It is now structured as a small SeasonalNet service with a daemon-backed CLI boundary: Asterisk still calls a command and receives digit-only stdout by default, while the daemon can keep the Vosk model warm for lower latency.

## Architecture

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

The CLI supports three modes:

- `auto`: try the daemon, then fall back to direct one-shot recognition
- `daemon`: require the local daemon
- `direct`: bypass the daemon and run recognition in the CLI process

The default stdout format is digit-only for Asterisk safety.

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── config.example.yaml
├── docs/
├── examples/
├── lib/seasonal_vcaptcha/
│   ├── audio.py
│   ├── cli.py
│   ├── client.py
│   ├── config.py
│   ├── daemon.py
│   ├── digits.py
│   ├── protocol.py
│   └── recognizer.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── run_digits.sh
├── tests/
└── vosk_digits.py
```

The `run_digits.sh` and `vosk_digits.py` files are compatibility wrappers. New integrations should prefer the installed console scripts.

## Dependencies

System packages:

```bash
sudo apt install python3 python3-venv sox
```

Python packages:

```bash
uv venv --python 3.15.1 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Development/test packages:

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

## Installation pattern

Example clean deployment path:

```bash
sudo install -d -o root -g root /opt/seasonal-vcaptcha
cd /opt/seasonal-vcaptcha
git clone https://git.seasonalnet.org/Seasonal_Currency/seasonal-vcaptcha.git .
uv venv --python 3.15.1 venv
uv pip install --python venv/bin/python -e .
```

Place the Vosk model outside Git, for example:

```text
/opt/seasonal-vcaptcha/models/model-small-en-us
```

Do not commit model files, virtual environments, generated audio, or logs.

## Docker deployment

The repository includes a hardened Compose service. Prepare the model and a
host socket directory that the FreePBX/Asterisk process can access:

```bash
cp config.example.yaml config.yaml
sudo install -d -o 10001 -g "$(getent group asterisk | cut -d: -f3)" -m 0770 /run/seasonal-vcaptcha
```

Set `MODEL_DIR` to the existing Vosk model directory and `ASTERISK_GID` to the
host Asterisk group ID. In `config.yaml`, set `api.unix_socket.group: null` so
the socket inherits the container process group. Then build and start the daemon:

```bash
MODEL_DIR=/opt/seasonal-vcaptcha/models/model-small-en-us \
ASTERISK_GID="$(getent group asterisk | cut -d: -f3)" \
docker compose up --build -d
```

The socket directory is bind-mounted at `/run/seasonal-vcaptcha`, so the host
FreePBX integration can use the same socket path. The model is mounted
read-only and remains outside the image and Git. The container runs as a
non-root numeric user with a read-only root filesystem, all capabilities
dropped, and no-new-privileges enabled.

After the Python CI job passes, pushes to `main` publish `latest` and a
commit-SHA tag. A `v*` tag publishes that version tag and its commit-SHA tag.
Images go to `ghcr.io/<owner>/seasonal-vcaptcha` on GitHub and
`registry.lan.seasonalnet.org/seasonalnet/seasonal-vcaptcha` on Forgejo.
Pull requests do not publish images.

## Configuration

Copy the example config and adjust paths:

```bash
sudo install -d /etc/seasonal-vcaptcha
sudo cp config.example.yaml /etc/seasonal-vcaptcha/config.yaml
```

Important defaults:

```yaml
api:
  unix_socket:
    enabled: true
    path: /run/seasonal-vcaptcha/seasonal-vcaptcha.sock
  tcp:
    enabled: false

cli:
  mode: auto
  format: digits

recognizer:
  engine: vosk
  vosk:
    model_path: /opt/seasonal-vcaptcha/models/model-small-en-us
```

`VOSK_MODEL` may override the configured model path for compatibility with the legacy deployment.

## CLI usage

Asterisk-safe default:

```bash
seasonal-vcaptcha-digits /path/to/input.wav
```

Example stdout:

```text
1234
```

JSON output for operators:

```bash
seasonal-vcaptcha-digits --format json /path/to/input.wav
```

Environment-style output:

```bash
seasonal-vcaptcha-digits --format env /path/to/input.wav
```

Force direct mode:

```bash
seasonal-vcaptcha-digits --mode direct /path/to/input.wav
```

Require daemon mode:

```bash
seasonal-vcaptcha-digits --mode daemon /path/to/input.wav
```

## Daemon usage

Run manually for testing:

```bash
seasonal-vcaptcha-daemon --config /etc/seasonal-vcaptcha/config.yaml
```

The daemon exposes a local API by default:

- `POST /v1/recognize`
- `GET /healthz`
- `GET /readyz`
- `GET /metrics` when enabled

Production integration should use the Unix socket, not a LAN-exposed TCP listener.

A starter systemd unit is provided at:

```text
examples/systemd/seasonal-vcaptcha.service
```

## Legacy source

The original working deployment lived on `FreePBX17` at:

```text
/opt/vosk-stt/
├── model-small-en-us/
├── run_digits.sh
├── venv/
└── vosk_digits.py
```

This repository tracks code only. It intentionally does not track the Vosk model directory or Python virtual environment.

## FreePBX / Asterisk integration

The exact dialplan call site should be confirmed from the live SeasonalPBX deployment. Useful search commands:

```bash
sudo grep -RIn \
  -e 'vosk' \
  -e 'run_digits' \
  -e 'vosk_digits' \
  -e 'vcaptcha' \
  -e 'captcha' \
  /etc/asterisk /var/lib/asterisk 2>/dev/null
```

Example integration notes are in:

```text
examples/asterisk/extensions_custom.conf.example
```

## Testing

```bash
pytest
```

The default tests do not require a Vosk model. Real audio/model integration testing should be done on SeasonalPBX before replacing the legacy call-flow hook.

## Non-goals

This repository does not preserve:

- FreePBX configuration
- CDR/CEL database history
- voicemail boxes
- TFTP/provisioning contents
- Vosk model files
- Python virtual environments
- full VM state
