from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest


class _Logger:
    def info(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


class _Star:
    def __init__(self, context):
        self.name = "astrbot_plugin_together_with_me"


class _Event:
    def __init__(self, message: str, user_id: str = "user"):
        self._message = message
        self._user_id = user_id

    def get_group_id(self):
        return "group"

    def get_sender_id(self):
        return self._user_id

    def get_message_str(self):
        return self._message

    def plain_result(self, text):
        return text


def _install_astrbot_stubs(tmp_path: Path):
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    api.logger = _Logger()
    event = types.ModuleType("astrbot.api.event")
    event.AstrMessageEvent = object
    event.filter = types.SimpleNamespace(command=lambda _: lambda function: function)
    star = types.ModuleType("astrbot.api.star")
    star.Context = object
    star.Star = _Star
    star.register = lambda *args: lambda cls: cls
    path = types.ModuleType("astrbot.core.utils.astrbot_path")
    path.get_astrbot_data_path = lambda: str(tmp_path)
    sys.modules.update(
        {
            "astrbot": astrbot,
            "astrbot.api": api,
            "astrbot.api.event": event,
            "astrbot.api.star": star,
            "astrbot.core": types.ModuleType("astrbot.core"),
            "astrbot.core.utils": types.ModuleType("astrbot.core.utils"),
            "astrbot.core.utils.astrbot_path": path,
        },
    )


@pytest.mark.asyncio
async def test_all_commands_and_task_cleanup(tmp_path: Path):
    _install_astrbot_stubs(tmp_path)
    sys.modules.pop("astrbot_plugin_together_with_me.main", None)
    from astrbot_plugin_together_with_me.main import TogetherWithMePlugin

    plugin = TogetherWithMePlugin(object())
    await plugin.initialize()
    created = [
        item
        async for item in plugin.together_create(
            _Event("togethercreate code｜绝地潜兵2｜备注=东线样本｜上限=2", "owner"),
        )
    ]
    assert "#TW0001" in created[0]
    found = [
        item
        async for item in plugin.together_find(_Event("togetherfind 样本", "member"))
    ]
    assert "#TW0001" in found[0]
    joined = [
        item
        async for item in plugin.together_with(_Event("togetherwith #TW0001", "member"))
    ]
    assert "报名成功" in joined[0]
    deleted = [
        item
        async for item in plugin.together_delete(_Event("togetherdelete #TW0001", "owner"))
    ]
    assert deleted == ["条目已删除。"]
    await plugin.terminate()
    await asyncio.sleep(0)
    assert not plugin._background_tasks
