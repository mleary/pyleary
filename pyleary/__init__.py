from __future__ import annotations

import os
from pathlib import Path

import requests

__all__ = ["fetch", "GitHubError"]

DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
ON_EXISTS_OPTIONS = {"error", "skip", "overwrite"}


class GitHubError(RuntimeError):
    pass


def fetch(
    repo: str,
    selections: list[str] | str | None = None,
    dest: str | Path = ".",
    token: str | None = None,
    path: str = "",
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    on_exists: str = "error",
    max_bytes: int | None = DEFAULT_MAX_BYTES,
):
    """
    List repo contents or download selected paths.

    - repo: "owner/name"
    - selections: None to list; otherwise list of repo paths to download.
    - dest: destination directory when downloading.
    - token: GitHub token (or set GITHUB_TOKEN / GH_TOKEN).
    - path: subdirectory to list when selections is None.
    - timeout: request timeout (seconds or (connect, read)).
    - on_exists: "error", "skip", or "overwrite" when files exist locally.
    - max_bytes: refuse downloads larger than this limit (None to disable).

    Returns a list of items when listing, or a list of downloaded file paths when downloading.
    """
    owner, name = _parse_repo(repo)
    token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if on_exists not in ON_EXISTS_OPTIONS:
        raise ValueError(f"on_exists must be one of {sorted(ON_EXISTS_OPTIONS)}.")

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    def api_url(api_path: str) -> str:
        api_path = api_path.strip("/")
        if api_path:
            return f"https://api.github.com/repos/{owner}/{name}/contents/{api_path}"
        return f"https://api.github.com/repos/{owner}/{name}/contents"

    def raise_for_status(response: requests.Response, action: str) -> None:
        if response.status_code in {401, 403, 404}:
            raise GitHubError(
                f"{action} failed (HTTP {response.status_code}). "
                "Provide a token for private repos."
            )
        if not response.ok:
            raise GitHubError(f"{action} failed (HTTP {response.status_code}).")

    def get_raw(api_path: str):
        response = session.get(api_url(api_path), timeout=timeout)
        raise_for_status(response, f"Fetching {api_path or '/'}")
        return response.json()

    def download_file(repo_path: str, target: Path, expected_size: int | None) -> bool:
        if target.exists():
            if on_exists == "skip":
                return False
            if on_exists == "error":
                raise GitHubError(f"Refusing to overwrite existing file: {target}")
        if max_bytes is not None and expected_size is not None and expected_size > max_bytes:
            raise GitHubError(
                f"{repo_path} size {expected_size} exceeds max_bytes={max_bytes}"
            )
        response = session.get(
            api_url(repo_path),
            headers={"Accept": "application/vnd.github.raw"},
            stream=True,
            timeout=timeout,
        )
        raise_for_status(response, f"Downloading {repo_path}")
        if max_bytes is not None:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise GitHubError(
                            f"{repo_path} content-length exceeds max_bytes={max_bytes}"
                        )
                except ValueError:
                    pass
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            written = 0
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    written += len(chunk)
                    if max_bytes is not None and written > max_bytes:
                        handle.close()
                        try:
                            target.unlink()
                        except FileNotFoundError:
                            pass
                        raise GitHubError(
                            f"{repo_path} exceeded max_bytes={max_bytes} during download"
                        )
                    handle.write(chunk)
        return True

    def ensure_safe_path(repo_path: str) -> str:
        repo_path = repo_path.strip("/")
        if not repo_path:
            raise ValueError("Repo path cannot be empty.")
        if ".." in Path(repo_path).parts:
            raise ValueError("Repo path cannot contain '..'.")
        return repo_path

    if selections is None:
        data = get_raw(path)
        if isinstance(data, dict):
            data = [data]
        return [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "type": item.get("type"),
            }
            for item in data
        ]

    if isinstance(selections, str):
        selections = [selections]

    dest_root = Path(dest).expanduser()
    downloaded: list[str] = []

    def walk_download(repo_path: str) -> None:
        repo_path = ensure_safe_path(repo_path)
        data = get_raw(repo_path)
        if isinstance(data, dict):
            item_type = data.get("type")
            if item_type == "file":
                target = dest_root / repo_path
                if download_file(repo_path, target, data.get("size")):
                    downloaded.append(str(target))
                return
            if item_type == "dir":
                for child in get_raw(repo_path):
                    walk_download(str(child.get("path", "")))
                return
            raise GitHubError(
                f"Unsupported item type '{item_type}' at {repo_path}"
            )

        for item in data:
            item_type = item.get("type")
            if item_type == "file":
                item_path = str(item.get("path", ""))
                item_path = ensure_safe_path(item_path)
                target = dest_root / item_path
                if download_file(item_path, target, item.get("size")):
                    downloaded.append(str(target))
            elif item_type == "dir":
                walk_download(str(item.get("path", "")))
            else:
                raise GitHubError(
                    f"Unsupported item type '{item_type}' at {item.get('path')}"
                )

    for entry in selections:
        walk_download(str(entry))

    return downloaded


def _parse_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ValueError("Repo must be in owner/name format.")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ValueError("Repo must be in owner/name format.")
    return owner, name
