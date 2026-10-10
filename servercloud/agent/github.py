"""Минимальный клиент GitHub REST API (только stdlib).

Безопасность токена:
  * токен уходит ТОЛЬКО на https://api.github.com;
  * редиректы запрещены (urllib по умолчанию пересылает заголовки дальше);
  * токен никогда не попадает в вывод — всё проходит через redact().
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from .config import redact

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class GitHubClient:
    def __init__(self, token):
        self._token = token
        self._opener = urllib.request.build_opener(_NoRedirect)

    def request(self, method, path, body=None, params=None):
        if not path.startswith("/"):
            raise GitHubError("path must start with /")
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "servercloud-agent")
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            raise GitHubError(redact(f"GitHub HTTP {e.code}: {msg}"))
        except urllib.error.URLError as e:
            raise GitHubError(redact(f"Нет сети: {e.reason}"))
