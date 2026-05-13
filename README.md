# seasonal-vcaptcha

Small Vosk-powered spoken digit recognizer used by SeasonalPBX / FreePBX call flows.

This repository exists to preserve the working legacy CAPTCHA code from `FreePBX17` before the PBX is rebuilt as a cleaner `SeasonalPBX` VM.

## Legacy source

The original working deployment lived on `FreePBX17` at:

```text
/opt/vosk-stt/
├── model-small-en-us/
├── run_digits.sh
├── venv/
└── vosk_digits.py
```

This repository tracks the code only. It intentionally does not track the Vosk model directory or Python virtual environment.

## Tracked files

Expected initial repository layout:

```text
.
├── AGENTS.md
├── README.md
├── .gitignore
├── requirements.txt
├── run_digits.sh
└── vosk_digits.py
```

## Runtime behavior

The recognizer:

- accepts a WAV file path as its first argument
- converts nonconforming audio to mono 16-bit WAV using `sox`
- loads a Vosk English model
- constrains recognition to digit words and digit characters
- maps `zero` and `oh` to `0`
- prints only the recognized digits to stdout

Example output:

```text
1234
```

## Dependencies

System packages:

```bash
sudo apt install python3 python3-venv sox
```

Python package:

```bash
pip install -r requirements.txt
```

Initial `requirements.txt`:

```text
vosk
```

## Model path

The legacy wrapper script expects the model at:

```text
/opt/vosk-stt/model-small-en-us
```

The Python script also supports overriding this with:

```bash
export VOSK_MODEL=/path/to/model
```

Do not commit model files to this repository.

## Legacy usage

From the deployed directory:

```bash
./run_digits.sh /path/to/input.wav
```

Or directly:

```bash
VOSK_MODEL=/opt/vosk-stt/model-small-en-us python3 ./vosk_digits.py /path/to/input.wav
```

## FreePBX / Asterisk integration

The exact dialplan call site should be documented after discovery from the old `FreePBX17` VM.

Useful search commands:

```bash
sudo grep -RIn \
  -e 'vosk' \
  -e 'run_digits' \
  -e 'vosk_digits' \
  -e 'captcha' \
  /etc/asterisk /var/lib/asterisk 2>/dev/null
```

```bash
sudo grep -RIn \
  -e 'AGI' \
  -e 'System' \
  -e 'TrySystem' \
  -e 'SHELL' \
  /etc/asterisk/extensions_custom.conf \
  /etc/asterisk/extensions_override_freepbx.conf \
  /etc/asterisk/*.conf 2>/dev/null
```

## Rebuild notes

During the `FreePBX17` to `SeasonalPBX` rebuild, this repository is the source of truth for restoring the CAPTCHA code.

Expected restore pattern:

```bash
cd /opt
git clone https://git.seasonalnet.org/Seasonal_Currency/seasonal-vcaptcha.git
cd seasonal-vcaptcha
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

Then ensure the Vosk model exists and the FreePBX/Asterisk dialplan calls the wrapper script.

## Non-goals

This repository does not preserve:

- FreePBX configuration
- CDR/CEL database history
- voicemail boxes
- TFTP/provisioning contents
- Vosk model files
- Python virtual environments
- full VM state

Those are handled separately during the PBX migration.
