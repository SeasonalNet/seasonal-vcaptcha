# AGENTS.md

## Project purpose

This repository preserves and maintains the Vosk-powered spoken digit CAPTCHA used by SeasonalPBX / FreePBX call flows.

The initial source comes from the legacy `FreePBX17` VM under:

```text
/opt/vosk-stt
```

## Operating rules

- Keep the known-working legacy behavior intact unless a change is intentionally tested.
- Do not commit Vosk model files.
- Do not commit Python virtual environments.
- Do not commit generated audio files, converted WAV files, or logs.
- Keep deployment paths explicit in documentation.
- Preserve compatibility with Asterisk/FreePBX call flows.
- Prefer small, boring changes over large rewrites.
- Use `docs:` for documentation-only commits.
- Use `feat:` for new behavior.
- Use `fix:` for behavior corrections.
- Use `refactor:` for internal restructuring without intended behavior changes.

## Expected repository contents

Minimal initial layout:

```text
.
├── AGENTS.md
├── README.md
├── .gitignore
├── requirements.txt
├── run_digits.sh
└── vosk_digits.py
```

## Runtime expectations

The recognizer should:

- accept a WAV file path as input
- recognize spoken digits only
- map `zero` and `oh` to `0`
- return recognized digits on stdout
- avoid unrelated stdout noise that could break dialplan parsing

## Deployment expectations

The legacy deployment used:

```text
/opt/vosk-stt
```

A future clean deployment may use:

```text
/opt/seasonal-vcaptcha
```

If deployment paths change, update the README and any FreePBX/Asterisk dialplan examples in the same change.

## Testing expectations

Before replacing the legacy implementation, test against real or representative recorded CAPTCHA audio.

At minimum, verify:

- digit word normalization
- `oh` to `0`
- `zero` to `0`
- digit-only stdout
- failure behavior when the input file is missing
- behavior when `sox` conversion is required

## Safety notes

The Vosk model and virtual environment are deployment artifacts, not source code.

The FreePBX rebuild must not depend on copying the old VM wholesale. This repository should be enough to restore the CAPTCHA code once the new VM has Python, `sox`, the Vosk package, the model files, and the proper dialplan hook.
