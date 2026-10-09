# Ghidra AI Analyzer

Task-directed reverse engineering inside Ghidra using OpenAI or free OpenRouter
models. Enter a task such as **Find the flag starting with flag{ and explain
the input check**, then analyze a function, selection, or bounded program batch.

The Python script sends decompiled code, called-function names and referenced
data previews to the model. It returns structured explanations, evidence,
uncertainty and candidate flags. Optionally apply comments and generated-name
renames through Ghidra transactions.

## Requirements

- Python 3.10+ and Ghidra with PyGhidra support.
- A JDK supported by your Ghidra version (Ghidra 12.1.2 requires Java 21).
- An API key for OpenRouter or OpenAI.
- Sample binary tests require Linux x86-64 (including WSL) and GNU binutils
  (`as`, `ld`, `nm`). Sample assembly files are only test fixtures.

Setup, launching and testing use Python scripts; no shell scripts are required.
Run the analyzer inside Ghidra/PyGhidra, not ordinary Python.
GUI setup is designed for Linux, Windows and macOS; only the WSL Snap runtime
has been integration-tested here.

## Quick start: WSL with Ghidra Snap

Clone this repository and change into its folder. Snap is detected automatically:

```bash
python3 ghidra_ai.py install
python3 ghidra_ai.py launch --provider openrouter
```

The launcher asks for your key with hidden input. In CodeBrowser, import a binary
and finish auto-analysis, then open **Window → Script Manager** and run
**OpenAIAnalyze.py**. Add the directory printed by install through **Manage
Script Directories** if needed. Start with **Report only**.

## Standard Ghidra installation

```bash
python -m venv .venv
# Activate .venv using the command appropriate to your terminal.
python -m pip install -r requirements.txt
python ghidra_ai.py install --ghidra /path/to/ghidra
python ghidra_ai.py launch --ghidra /path/to/ghidra --provider openrouter
```

On Windows, use a quoted Windows path for --ghidra. On macOS, select the
distribution directory containing Ghidra/application.properties.
Supply --java-home /path/to/jdk if needed. Use --python /path/to/python for
an alternative environment containing PyGhidra. GHIDRA_INSTALL_DIR can replace
--ghidra. See `python ghidra_ai.py --help` for all options.

## Providers and keys

OpenRouter is the CLI default. Only openrouter/free and model IDs ending in
:free are accepted; paid OpenRouter IDs are rejected before API requests.
Free models have usage limits, varying availability and varying quality.
The free router can select different models. We require structured-output
support and validate output locally before applying it.

```bash
python ghidra_ai.py launch --provider openrouter --model openrouter/free
python ghidra_ai.py launch --provider openai --model gpt-4.1-mini
```

Keys can come from OPENROUTER_API_KEY or OPENAI_API_KEY in the process
environment. AI_PROVIDER, OPENROUTER_MODEL and OPENAI_MODEL configure direct
Ghidra launches. .env.example documents settings; .env is not auto-loaded.
Keys are never placed in command arguments, source files or reports. Revoke
exposed keys and enter replacements privately.

Analysis sends selected code, names, signatures and data previews to the
provider. Retention policies vary. OpenAI uses store: false, which does not
guarantee zero retention. Keep private binaries/reports out of GitHub.
Existing comments are preserved. Automatic renames only affect DEFAULT symbols
with estimated confidence of at least 0.8. Use Ghidra Undo to revert annotations.

## Test the workflow

Offline unit tests need neither Ghidra nor an API key:

```bash
python -m unittest discover -s tests -v
```

Real Ghidra tests on Linux x86-64:

```bash
python3 ghidra_ai.py test --flag
python3 ghidra_ai.py test --flag --live --provider openrouter
```

The first command mocks only the API. It builds our owned ELF fixture,
imports it into real Ghidra, extracts XOR-encoded data, adds annotations and
checks the recovered candidate against the binary. The live command asks a
model to recover the flag and fails if no candidate is accepted. It prompts
for your key privately. Only our known fixture is executed.
Use --ghidra for standard installations and --work-dir to select output storage.

## GitHub upload

Upload this source folder, or run `python package_source.py` to build a source
ZIP. Environments, caches, logs, reports and generated projects are excluded.
Never upload keys, proprietary binaries or generated private reports.
The MIT license covers this project's code; dependencies/providers have their
own licenses and terms.

Official references:
- [Ghidra](https://github.com/NationalSecurityAgency/ghidra)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

