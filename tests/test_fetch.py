import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyleary import GitHubError, fetch


class StubResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data=None,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json = json_data
        self._content = content
        self.headers = headers or {}
        self.text = "" if self.ok else "error"

    def json(self):
        return self._json

    def iter_content(self, chunk_size: int = 1):
        for index in range(0, len(self._content), chunk_size):
            yield self._content[index : index + chunk_size]


def api_url(repo: str, path: str) -> str:
    owner, name = repo.split("/", 1)
    path = path.strip("/")
    if path:
        return f"https://api.github.com/repos/{owner}/{name}/contents/{path}"
    return f"https://api.github.com/repos/{owner}/{name}/contents"


class FetchTests(unittest.TestCase):
    def test_list_uses_timeout(self):
        calls = []

        def stub_get(self, url, *args, **kwargs):
            calls.append(kwargs)
            return StubResponse(
                json_data=[{"name": "file.txt", "path": "file.txt", "type": "file"}]
            )

        with patch("pyleary.__init__.requests.Session.get", new=stub_get):
            items = fetch("owner/repo", timeout=7)

        self.assertEqual(calls[0]["timeout"], 7)
        self.assertEqual(items[0]["path"], "file.txt")

    def test_download_refuses_overwrite_by_default(self):
        repo = "owner/repo"
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "file.txt"
            target.write_text("existing", encoding="utf-8")

            def stub_get(self, url, *args, **kwargs):
                if url == api_url(repo, "file.txt"):
                    return StubResponse(
                        json_data={"type": "file", "path": "file.txt", "size": 8}
                    )
                raise AssertionError(f"Unexpected URL {url}")

            with patch("pyleary.__init__.requests.Session.get", new=stub_get):
                with self.assertRaises(GitHubError):
                    fetch(repo, selections=["file.txt"], dest=tmpdir)

    def test_download_respects_max_bytes(self):
        repo = "owner/repo"

        def stub_get(self, url, *args, **kwargs):
            if url == api_url(repo, "file.txt"):
                return StubResponse(
                    json_data={"type": "file", "path": "file.txt", "size": 10}
                )
            raise AssertionError(f"Unexpected URL {url}")

        with patch("pyleary.__init__.requests.Session.get", new=stub_get):
            with self.assertRaises(GitHubError):
                fetch(
                    repo,
                    selections=["file.txt"],
                    dest=".",
                    max_bytes=5,
                    on_exists="overwrite",
                )

    def test_unsupported_type_raises(self):
        repo = "owner/repo"

        def stub_get(self, url, *args, **kwargs):
            if url == api_url(repo, "link"):
                return StubResponse(json_data={"type": "symlink", "path": "link"})
            raise AssertionError(f"Unexpected URL {url}")

        with patch("pyleary.__init__.requests.Session.get", new=stub_get):
            with self.assertRaises(GitHubError):
                fetch(repo, selections=["link"])

    def test_download_writes_file(self):
        repo = "owner/repo"
        content = b"hello"

        def stub_get(self, url, *args, **kwargs):
            accept = (kwargs.get("headers") or {}).get("Accept")
            if url == api_url(repo, "file.txt") and accept == "application/vnd.github.raw":
                return StubResponse(
                    content=content,
                    headers={"Content-Length": str(len(content))},
                )
            if url == api_url(repo, "file.txt"):
                return StubResponse(
                    json_data={"type": "file", "path": "file.txt", "size": len(content)}
                )
            raise AssertionError(f"Unexpected URL {url}")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pyleary.__init__.requests.Session.get", new=stub_get):
                downloaded = fetch(
                    repo,
                    selections=["file.txt"],
                    dest=tmpdir,
                    on_exists="overwrite",
                )

            target = Path(tmpdir) / "file.txt"
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(downloaded, [str(target)])


if __name__ == "__main__":
    unittest.main()
