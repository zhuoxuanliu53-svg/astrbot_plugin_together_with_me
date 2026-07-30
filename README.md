# together with me

面向 AstrBot 群聊的轻量游戏联机条目插件。它不验证游戏账号或好友码；只将群友给出的主体文本、游戏/平台和备注结构化保存，供群内检索与报名。

## 功能

- `/togethercreate`：创建群内条目并生成群内识别码。
- `/togetherfind`：按游戏/平台和备注检索；不带参数时列出当前群所有未过期条目。
- `/togetherwith`：按识别码报名，人数递增并受上限约束。
- `/togetherdelete`：创建者删除自己的条目。
- 短期条目默认在 24 小时后自动删除；长期条目不自动删除。

## 命令

```text
/togethercreate <主体文本>｜<游戏或平台>｜备注=<文本>｜初始=<数字>｜上限=<数字或∞>｜长期
```

前两段必填，其余均可省略且顺序任意。默认：备注为空、初始人数为 `1`、上限为 `∞`、短期。

```text
/togethercreate 1234-5678｜绝地潜兵2 / Steam｜备注=东线难度7，拿样本｜初始=2｜上限=4
/togethercreate steam:alice｜Steam｜备注=周末合作游戏｜长期
/togetherfind 绝地潜兵2｜东线/样本
/togetherfind
/togetherwith #TW0001
/togetherdelete #TW0001
```

搜索中，不同 `｜` 块为同时匹配；同一块内的 `/` 为任选其一。搜索只匹配“游戏或平台”和“备注”，不搜索主体文本，避免好友码或 ID 被普通搜索误命中。

## 数据和权限

- 每个群的数据相互隔离；`TW0001` 只在其创建群内有效。
- 创建者计入初始人数；同一群友不能重复报名；达到上限后不能报名。
- 条目和报名数据保存在 AstrBot 的 `data/plugin_data/together_with_me/together_with_me.db`，不会因插件更新而被覆盖。
- 条目仅由创建者删除；本版本不提供管理员越权删除或撤销报名命令。

## 安装

将本目录放到 `AstrBot/data/plugins/astrbot_plugin_together_with_me/`，在 AstrBot WebUI 中重载插件。依赖写在 `requirements.txt`；AstrBot 当前版本已包含 `aiosqlite`，但单独声明可保证插件独立安装时可用。

数据库位于 `AstrBot/data/plugin_data/astrbot_plugin_together_with_me/together_with_me.db`。Docker 部署必须持久化 AstrBot 的整个 `data/` 目录，否则容器重建会丢失条目和报名记录。

## 开发说明

实现遵循官方模板的 `Star` 基类、`@register` 和 `@filter.command` 模式。SQLite 使用插件数据目录而非插件安装目录；短期清理在初始化后每小时执行，并在每次读取/写入前补充清理。
