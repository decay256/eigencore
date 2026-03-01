"""Tests for ConnectionManager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.connection_manager import ConnectionManager


@pytest.fixture
def cm():
    return ConnectionManager()


def make_ws(*, fail_send=False):
    ws = MagicMock()
    ws.send_json = AsyncMock()
    if fail_send:
        ws.send_json.side_effect = RuntimeError("closed")
    return ws


class TestConnectDisconnect:
    def test_connect_adds(self, cm):
        ws = make_ws()
        cm.connect("ROOM1", ws)
        assert cm.count("room1") == 1

    def test_disconnect_removes(self, cm):
        ws = make_ws()
        cm.connect("room1", ws)
        cm.disconnect("room1", ws)
        assert cm.count("room1") == 0
        assert "ROOM1" not in cm.rooms()

    def test_disconnect_nonexistent_no_error(self, cm):
        cm.disconnect("nope", make_ws())

    def test_multiple_connections(self, cm):
        cm.connect("r", make_ws())
        cm.connect("r", make_ws())
        assert cm.count("r") == 2

    def test_rooms_listing(self, cm):
        cm.connect("a", make_ws())
        cm.connect("b", make_ws())
        assert sorted(cm.rooms()) == ["A", "B"]


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_all(self, cm):
        ws1, ws2 = make_ws(), make_ws()
        cm.connect("r", ws1)
        cm.connect("r", ws2)
        await cm.broadcast("r", {"x": 1})
        ws1.send_json.assert_called_once_with({"x": 1})
        ws2.send_json.assert_called_once_with({"x": 1})

    @pytest.mark.asyncio
    async def test_broadcast_except(self, cm):
        ws1, ws2 = make_ws(), make_ws()
        cm.connect("r", ws1)
        cm.connect("r", ws2)
        await cm.broadcast_except("r", {"x": 1}, exclude=ws1)
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once_with({"x": 1})

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed(self, cm):
        good, bad = make_ws(), make_ws(fail_send=True)
        cm.connect("r", good)
        cm.connect("r", bad)
        await cm.broadcast("r", {"x": 1})
        assert cm.count("r") == 1
        good.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_empty_room(self, cm):
        # Should not raise
        await cm.broadcast("empty", {"x": 1})

    @pytest.mark.asyncio
    async def test_case_insensitive(self, cm):
        ws = make_ws()
        cm.connect("Room1", ws)
        await cm.broadcast("room1", {"x": 1})
        ws.send_json.assert_called_once()
