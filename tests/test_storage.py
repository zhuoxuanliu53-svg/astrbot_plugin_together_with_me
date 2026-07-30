from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import pytest

from astrbot_plugin_together_with_me.storage import TogetherStore


@pytest.mark.asyncio
async def test_group_scoped_create_search_join_and_delete(tmp_path: Path):
    store = TogetherStore(tmp_path / "together.db")
    await store.initialize()
    entry = await store.create_entry(
        group_id="group-a",
        owner_id="owner",
        locator_text="1234-5678",
        game_or_platform="绝地潜兵2 / Steam",
        note="东线拿样本",
        initial_count=2,
        max_count=3,
        is_long_term=False,
    )
    assert entry.code == "TW0001"
    assert entry.current_count == 2
    assert len(await store.find_entries("group-a", "绝地潜兵2｜东线/南线")) == 1
    assert await store.find_entries("group-b", "") == []

    joined = await store.join_entry("group-a", "#TW0001", "member")
    assert joined.current_count == 3
    assert joined.is_full
    with pytest.raises(ValueError, match="已满"):
        await store.join_entry("group-a", "TW0001", "another-member")
    assert await store.delete_entry("group-a", "TW0001", "owner")
    assert await store.find_entries("group-a", "") == []
    async with aiosqlite.connect(store.database_path) as db:
        signup_count = await db.execute_fetchall("SELECT COUNT(*) FROM signups")
    assert signup_count[0][0] == 0


@pytest.mark.asyncio
async def test_short_entries_expire_but_long_entries_remain(tmp_path: Path):
    store = TogetherStore(tmp_path / "together.db")
    await store.initialize()
    short_entry = await store.create_entry(
        group_id="group-a",
        owner_id="owner",
        locator_text="short-code",
        game_or_platform="Game",
        note="short",
        initial_count=1,
        max_count=None,
        is_long_term=False,
    )
    long_entry = await store.create_entry(
        group_id="group-a",
        owner_id="owner",
        locator_text="long-code",
        game_or_platform="Game",
        note="long",
        initial_count=1,
        max_count=None,
        is_long_term=True,
    )
    async with aiosqlite.connect(store.database_path) as db:
        await db.execute(
            "UPDATE entries SET expires_at = ? WHERE code = ?",
            ("2000-01-01T00:00:00+00:00", short_entry.code),
        )
        await db.commit()
    assert await store.delete_expired() == 1
    assert await store.get_entry("group-a", short_entry.code) is None
    assert await store.get_entry("group-a", long_entry.code) is not None


@pytest.mark.asyncio
async def test_last_slot_is_claimed_once_under_concurrency(tmp_path: Path):
    store = TogetherStore(tmp_path / "together.db")
    await store.initialize()
    entry = await store.create_entry(
        group_id="group-a",
        owner_id="owner",
        locator_text="code",
        game_or_platform="Game",
        note="",
        initial_count=1,
        max_count=2,
        is_long_term=False,
    )
    results = await asyncio.gather(
        store.join_entry("group-a", entry.code, "first"),
        store.join_entry("group-a", entry.code, "second"),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, ValueError) for result in results) == 1
    updated = await store.get_entry("group-a", entry.code)
    assert updated is not None
    assert updated.current_count == 2


@pytest.mark.asyncio
async def test_search_escapes_like_special_characters(tmp_path: Path):
    store = TogetherStore(tmp_path / "together.db")
    await store.initialize()
    await store.create_entry(
        group_id="group-a",
        owner_id="owner",
        locator_text="code",
        game_or_platform="100% Game_One",
        note="空 白",
        initial_count=1,
        max_count=None,
        is_long_term=False,
    )
    assert len(await store.find_entries("group-a", "100%｜game_one｜空白")) == 1
    assert await store.find_entries("group-a", "100_ Game") == []
