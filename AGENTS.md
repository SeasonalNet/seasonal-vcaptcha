# AGENTS.md

## Project purpose

This repository maintains the Vosk-powered spoken digit CAPTCHA used by SeasonalPBX / FreePBX call flows.

The initial source came from the legacy `FreePBX17` VM under:

```text
/opt/vosk-stt
```

The modern shape is daemon-backed but CLI-fronted: Asterisk calls a stable command, the command formats dialplan-safe stdout, and the daemon may keep Vosk warm behind a local Unix socket.

## Operating rules

- Preserve Asterisk/FreePBX compatibility.
- Keep default CLI stdout digit-only or empty.
- Send diagnostics to stderr or structured non-default formats, not default stdout.
- Keep the daemon local-only by default.
- Prefer Unix sockets over TCP for production integration.
- Keep direct CLI recognition available as an emergency fallback.
- Do not commit Vosk model files.
- Do not commit Python virtual environments.
- Do not commit generated audio files, converted WAV files, runtime sockets, or logs.
- Keep deployment paths explicit in documentation.
- Prefer small, boring changes over large rewrites.
- Use `docs:` for documentation-only commits.
- Use `feat:` for new behavior.
- Use `fix:` for behavior corrections.
- Use `refactor:` for internal restructuring without intended behavior changes.

## Expected repository contents

```text
.
├── AGENTS.md
├── README.md
├── config.example.yaml
├── docs/
├── examples/
├── lib/seasonal_vcaptcha/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── run_digits.sh
├── tests/
└── vosk_digits.py
```

## Runtime expectations

The recognizer should:

- accept a WAV file path as input
- recognize spoken digits only
- map `zero` and `oh` to `0`
- return recognized digits on default CLI stdout
- avoid unrelated stdout noise that could break dialplan parsing
- support daemon-backed recognition and direct one-shot recognition
- clean up converted temporary WAV files

## Configuration expectations

The primary config file is `config.yaml`, based on `config.example.yaml`.

Top-level sections should remain stable unless there is a strong reason to change them:

- `service`
- `api`
- `recognizer`
- `audio`
- `cli`
- `recognition`
- `logging`
- `metrics`

Do not rename `recognizer` to `tts`; this project performs speech-to-text.

## Deployment expectations

The legacy deployment used:

```text
/opt/vosk-stt
```

The clean deployment target is:

```text
/opt/seasonal-vcaptcha
```

If deployment paths change, update the README, `config.example.yaml`, and any FreePBX/Asterisk examples in the same change.

## Testing expectations

Before replacing the legacy implementation, test against real or representative recorded CAPTCHA audio.

At minimum, verify:

- digit word normalization
- `oh` to `0`
- `zero` to `0`
- digit-only stdout in default CLI mode
- failure behavior when the input file is missing
- behavior when `sox` conversion is required
- daemon unavailable behavior in `auto` and `daemon` modes

Run:

```bash
pytest
```

## Safety notes

The Vosk model and virtual environment are deployment artifacts, not source code.

The FreePBX rebuild must not depend on copying the old VM wholesale. This repository should be enough to restore the CAPTCHA code once the new VM has Python, `sox`, the Vosk package, the model files, and the proper dialplan hook.
