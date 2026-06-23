# Copilot Instructions for This Repository

## Project scope

This repository is a Python sample for consuming LSEG Machine Readable News over WebSocket connections.

- `mrn_console_rtds.py` is the RTDS console example.
- `mrn_console_rto_v2.py` is the RTO version 2 authentication console example.
- `notebook/` contains notebook variants of the same workflows.

## Working rules

- Keep changes small and targeted. This repo is a sample application, not a framework.
- Preserve the existing separation between RTDS and RTO flows unless the task explicitly requires combining them.
- Prefer straightforward standard-library Python solutions unless the repository already depends on a package for the task.
- Match the existing script style in the file you are editing. Do not reformat unrelated code.

## Files to avoid editing

- Do not modify files under `mrn_python/`. This directory is a checked-in virtual environment and vendored dependency tree.
- Do not edit files under `mrn_python/Lib/site-packages/` to change application behavior.
- Only update dependency files such as `requirements.txt` or `requirements_notebook.txt` when the task actually requires a new dependency or a version change.

## Configuration and secrets

- Never hardcode credentials, tokens, hostnames, or customer-specific identifiers.
- For RTO version 2 configuration, follow the `.env` pattern shown in `.env.example`.
- If configuration changes are needed, update `.env.example` and `README.md` together when appropriate.

## Python and runtime expectations

- Target Python 3.10 compatibility unless the task explicitly requires something else.
- Keep console output compatible with the repository's current UTF-8 handling.
- MRN payload handling depends on base64 decoding and gzip/zlib decompression. Preserve that behavior and be careful around fragment assembly logic.

## Validation guidance

- For changes in Python scripts, prefer narrow validation such as `python -m py_compile <file>`.
- If documentation changes affect setup or execution, keep command examples consistent with `README.md`, `Dockerfile`, and the current entry scripts.

## Documentation expectations

- Keep README changes aligned with the actual file layout in this repo.
- Use the existing terminology from the project: RTDS, RTO, MRN, fragment assembly, and WebSocket API.
- When adding new instructions, prefer practical run steps over broad background material.