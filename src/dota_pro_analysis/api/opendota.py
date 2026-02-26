"""OpenDota API 客户端：职业比赛列表、对局详情（选禁、胜负）。"""
from __future__ import annotations

import time
from typing import Any

import requests

from ..config import load_config


class OpenDotaClient:
    """OpenDota API 封装，用于获取职业比赛与对局详情。"""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        rate_limit_delay: float | None = None,
    ):
        cfg = load_config()
        od = cfg.get("opendota", {})
        self.base_url = (base_url or od.get("base_url", "https://api.opendota.com/api")).rstrip("/")
        self.api_key = api_key if api_key is not None else od.get("api_key", "")
        self.delay = rate_limit_delay if rate_limit_delay is not None else od.get("rate_limit_delay", 1.0)
        self._last_request_time = 0.0

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{path}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        now = time.monotonic()
        wait = self.delay - (now - self._last_request_time)
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()
        r = requests.get(url, params=params or {}, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_pro_matches(self, limit: int = 100, league_id: int | None = None) -> list[dict[str, Any]]:
        """获取最近职业比赛列表。"""
        params: dict[str, Any] = {}
        if limit > 0:
            params["limit"] = limit
        if league_id is not None and league_id != 0:
            params["league_id"] = league_id
        data = self._request("/proMatches", params=params or None)
        return data if isinstance(data, list) else []

    def get_match(self, match_id: int) -> dict[str, Any]:
        """获取单场对局详情（含 picks_bans、radiant_win、players 等）。"""
        return self._request(f"/matches/{match_id}")

    def get_matches_batch(self, match_ids: list[int]) -> list[dict[str, Any]]:
        """批量获取对局详情；失败的对局会跳过并返回已成功的列表。"""
        results = []
        for mid in match_ids:
            try:
                results.append(self.get_match(mid))
            except requests.RequestException:
                continue
        return results

    def get_teams(self) -> list[dict[str, Any]]:
        """获取战队列表（含 team_id、name），用于按名称查 team_id。"""
        data = self._request("/teams")
        return data if isinstance(data, list) else []

    def get_team_matches(self, team_id: int, limit: int = 100) -> list[dict[str, Any]]:
        """获取某战队的近期比赛列表。"""
        data = self._request(f"/teams/{team_id}/matches", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_player_matches(self, account_id: int, limit: int = 100) -> list[dict[str, Any]]:
        """获取某选手的近期比赛列表。"""
        data = self._request(f"/players/{account_id}/matches", params={"limit": limit})
        return data if isinstance(data, list) else []
