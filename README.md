# pyleary

Minimal Python package for listing and downloading files from a GitHub repo via
the GitHub API (no git required).

## Install

```bash
python -m pip install -e .
```

## Usage

```python
from pyleary import fetch

# list repo root
items = fetch("owner/repo", token="YOUR_TOKEN")

# download selected items to current directory
fetch("owner/repo", selections=["AGENTS.MD", "plans"], token="YOUR_TOKEN")
```

## Notes

- For private repos, provide a token via `token=` or `GITHUB_TOKEN` / `GH_TOKEN`.
- Downloads default to current directory. Use `dest="./path"` to change it.
- Existing files are not overwritten unless `on_exists="overwrite"`.
