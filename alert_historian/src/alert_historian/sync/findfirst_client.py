import base64
from dataclasses import dataclass
from typing import Any

import requests

from alert_historian.config.settings import Settings


@dataclass
class ClientResponse:
  status_code: int
  data: Any
  text: str


class FindFirstClient:
  def __init__(self, settings: Settings):
    self.base_url = settings.findfirst_base_url.rstrip("/")
    self.username = settings.findfirst_username
    self.password = settings.findfirst_password
    self.session = requests.Session()

  def _url(self, path: str) -> str:
    return f"{self.base_url}{path}"

  def signin(self) -> ClientResponse:
    creds = f"{self.username}:{self.password}"
    token = base64.b64encode(creds.encode("utf-8")).decode("ascii")
    resp = self.session.post(
        self._url("/user/signin"),
        headers={"Authorization": f"Basic {token}"},
        timeout=15,
    )
    data = None
    try:
      data = resp.json()
    except ValueError:
      data = None
    return ClientResponse(resp.status_code, data, resp.text)

  def list_tags(self) -> ClientResponse:
    resp = self.session.get(self._url("/api/tags"), timeout=15)
    data = []
    try:
      data = resp.json()
    except ValueError:
      data = []
    return ClientResponse(resp.status_code, data, resp.text)

  def create_tags(self, tags: list[str]) -> ClientResponse:
    resp = self.session.post(self._url("/api/tags"), json=tags, timeout=20)
    data = []
    try:
      data = resp.json()
    except ValueError:
      data = []
    return ClientResponse(resp.status_code, data, resp.text)

  def bulk_add_bookmarks(self, payload: list[dict[str, Any]]) -> ClientResponse:
    resp = self.session.post(self._url("/api/bookmark/addBookmarks"), json=payload, timeout=45)
    data = []
    try:
      data = resp.json()
    except ValueError:
      data = []
    return ClientResponse(resp.status_code, data, resp.text)
