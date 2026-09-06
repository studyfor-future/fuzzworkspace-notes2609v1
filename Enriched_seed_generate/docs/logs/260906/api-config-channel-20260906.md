# API configuration channel change - 2026-09-06

## Scope

Added a shared `config.py` credential channel without removing the existing environment-variable or legacy `SummIssue_improved_final.py` channels.

## Credential precedence

1. `OPENAI_API_KEY` and `OPENAI_BASE_URL` environment variables.
2. `API_KEY` and `BASE_URL` from `config.py`.
3. Legacy `SummIssue_improved_final.py` fallback in both generator scripts.

`SummIssue.py` now uses environment variables first and `config.py` second. Its former inline credential literals were removed and migrated to `config.py`. Leading and trailing whitespace was stripped during migration.

## Modified files

- `config.py` (new)
- `SummIssue.py`
- `Generate.py`
- `Generate copy.py`

## Validation command

```powershell
conda run -n ICSTsys01-py39 python -m py_compile config.py SummIssue.py Generate.py
conda run -n ICSTsys01-py39 python -m py_compile "Generate copy.py"
```

## Security note

`config.py` contains a credential and must not be committed or shared. Rotate any key that has previously appeared in source code or logs.
