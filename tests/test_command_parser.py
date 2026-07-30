import pytest

from astrbot_plugin_together_with_me.command_parser import (
    MAX_NOTE_LENGTH,
    parse_create_payload,
    parse_search_query,
)


def test_create_uses_required_fields_and_defaults():
    parsed = parse_create_payload("code｜绝地潜兵2")
    assert parsed["locator_text"] == "code"
    assert parsed["game_or_platform"] == "绝地潜兵2"
    assert parsed["initial_count"] == 1
    assert parsed["max_count"] is None
    assert parsed["is_long_term"] is False


def test_create_accepts_named_fields_in_any_order():
    parsed = parse_create_payload(
        "code|Steam｜长期｜上限：4｜备注=东线 样本｜初始=2",
    )
    assert parsed["note"] == "东线 样本"
    assert parsed["initial_count"] == 2
    assert parsed["max_count"] == 4
    assert parsed["is_long_term"] is True


@pytest.mark.parametrize(
    "payload, error",
    [
        ("code", "必填"),
        ("｜Game", "必填"),
        ("code｜Game｜初始=2｜初始=3", "不能重复"),
        ("code｜Game｜初始=5｜上限=4", "不能大于"),
        ("code｜Game｜上限=0", "正整数"),
        ("code｜Game｜未知=1", "无法识别"),
        (f"code｜Game｜备注={'a' * (MAX_NOTE_LENGTH + 1)}", "不能超过"),
    ],
)
def test_create_rejects_invalid_input(payload, error):
    with pytest.raises(ValueError, match=error):
        parse_create_payload(payload)


def test_search_groups_are_and_with_or_alternatives():
    assert parse_search_query("绝地潜兵2｜东线/南线/样本") == [
        ["绝地潜兵2"],
        ["东线", "南线", "样本"],
    ]
