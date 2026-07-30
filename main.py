"""AstrBot entrypoint for the together with me plugin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .command_parser import parse_create_payload
from .storage import TogetherEntry, TogetherStore

USAGE = """用法：
/togethercreate 主体文本｜游戏或平台｜备注=<文本>｜初始=<数字>｜上限=<数字或∞>｜长期
必填：主体文本、游戏或平台。可选字段可省略，默认备注为空、初始=1、上限=∞、短期（24 小时）。
搜索：/togetherfind [词块｜词块/同义词]
报名：/togetherwith #TW0001
删除：/togetherdelete #TW0001"""


@register(
    "astrbot_plugin_together_with_me",
    "LiuJuan",
    "在群聊中创建、检索和报名游戏联机条目。",
    "0.1.0",
)
class TogetherWithMePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.store = TogetherStore(data_dir / "together_with_me.db")
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def initialize(self) -> None:
        await self.store.initialize()
        self._spawn(self._cleanup_loop())

    async def terminate(self) -> None:
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @filter.command("togethercreate")
    async def together_create(self, event: AstrMessageEvent):
        """创建群内联机条目。"""
        group_id, owner_id = _group_and_user(event)
        if not group_id or not owner_id:
            yield event.plain_result("/togethercreate 只能在群聊中使用。")
            return
        try:
            payload = _command_payload(event)
            parsed = parse_create_payload(payload)
            entry = await self.store.create_entry(
                group_id=group_id,
                owner_id=owner_id,
                **parsed,
            )
        except ValueError as exc:
            yield event.plain_result(f"创建失败：{exc}\n\n{USAGE}")
            return
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to create together entry")
            yield event.plain_result("创建失败：数据库暂时不可用，请稍后重试。")
            return
        logger.info("Created together entry %s in group %s", entry.code, group_id)
        yield event.plain_result(_render_entry(entry, include_locator=True))

    @filter.command("togetherfind")
    async def together_find(self, event: AstrMessageEvent):
        """按游戏或备注检索当前群的联机条目。"""
        group_id, _ = _group_and_user(event)
        if not group_id:
            yield event.plain_result("/togetherfind 只能在群聊中使用。")
            return
        try:
            entries = await self.store.find_entries(group_id, _command_payload(event))
        except ValueError as exc:
            yield event.plain_result(f"搜索失败：{exc}")
            return
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to find together entries")
            yield event.plain_result("搜索失败：数据库暂时不可用，请稍后重试。")
            return
        if not entries:
            yield event.plain_result("没有找到可用条目。")
            return
        lines = [f"找到 {len(entries)} 个条目："]
        lines.extend(_render_entry(entry, include_locator=True) for entry in entries)
        yield event.plain_result("\n\n".join(lines))

    @filter.command("togetherwith")
    async def together_with(self, event: AstrMessageEvent):
        """向指定条目报名。"""
        group_id, user_id = _group_and_user(event)
        code = _command_payload(event).split(maxsplit=1)[0] if _command_payload(event) else ""
        if not group_id or not user_id:
            yield event.plain_result("/togetherwith 只能在群聊中使用。")
            return
        if not code:
            yield event.plain_result("请提供条目识别码，例如 /togetherwith #TW0001")
            return
        try:
            entry = await self.store.join_entry(group_id, code, user_id)
        except ValueError as exc:
            yield event.plain_result(f"报名失败：{exc}")
            return
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to join together entry")
            yield event.plain_result("报名失败：数据库暂时不可用，请稍后重试。")
            return
        yield event.plain_result("报名成功。\n" + _render_entry(entry, include_locator=True))

    @filter.command("togetherdelete")
    async def together_delete(self, event: AstrMessageEvent):
        """删除自己创建的条目。"""
        group_id, owner_id = _group_and_user(event)
        code = _command_payload(event).split(maxsplit=1)[0] if _command_payload(event) else ""
        if not group_id or not owner_id:
            yield event.plain_result("/togetherdelete 只能在群聊中使用。")
            return
        if not code:
            yield event.plain_result("请提供条目识别码，例如 /togetherdelete #TW0001")
            return
        try:
            deleted = await self.store.delete_entry(group_id, code, owner_id)
        except (aiosqlite.Error, OSError):
            logger.exception("Failed to delete together entry")
            yield event.plain_result("删除失败：数据库暂时不可用，请稍后重试。")
            return
        yield event.plain_result("条目已删除。" if deleted else "删除失败：条目不存在，或你不是创建者。")

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(60 * 60)
            try:
                deleted = await self.store.delete_expired()
                if deleted:
                    logger.info("Removed %s expired together entries", deleted)
            except Exception:  # noqa: BLE001 - background cleanup must keep running.
                logger.exception("Failed to clean expired together entries")

    def _spawn(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


def _group_and_user(event: AstrMessageEvent) -> tuple[str, str]:
    return event.get_group_id().strip(), event.get_sender_id().strip()


def _command_payload(event: AstrMessageEvent) -> str:
    """Return text after the command name; command filtering has already matched it."""
    message = event.get_message_str().strip()
    return message.partition(" ")[2].strip()

def _render_entry(entry: TogetherEntry, *, include_locator: bool) -> str:
    limit = str(entry.max_count) if entry.max_count is not None else "∞"
    lifetime = "长期" if entry.is_long_term else "短期"
    if entry.is_full:
        lifetime += "，已满"
    elif entry.expires_at:
        lifetime += f"，至 {entry.expires_at.astimezone().strftime('%m-%d %H:%M')}"
    lines = [
        f"[#{entry.code}] {entry.game_or_platform}",
        entry.note or "（无备注）",
        f"{entry.current_count} / {limit} 人｜{lifetime}",
    ]
    if include_locator:
        lines.append(f"主体：{entry.locator_text}")
    return "\n".join(lines)
