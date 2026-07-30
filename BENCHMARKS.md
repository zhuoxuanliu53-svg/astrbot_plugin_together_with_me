# AstrBot 插件对标记录

下载日期：2026-07-30。样本仅用于本地只读学习，位于工作区 `benchmarks/`，不随本插件发布。

| 插件 | GitHub Stars（调研时） | 学到的做法 | 本插件落实 |
| --- | ---: | --- | --- |
| `astrbot_plugin_qq_group_daily_analysis` | 432 | 使用 `StarTools`/插件数据目录、明确适配器和测试目录 | 元数据补齐版本/平台；SQLite 放入 `data/plugin_data/<plugin-name>`；保留独立测试。 |
| `astrbot_plugin_self_learning` | 371 | 任务集合追踪、卸载时取消任务；大功能有迁移与测试 | 清理任务统一注册到集合，并在 `terminate` 中取消/等待；SQLite 初始化补齐旧表字段。 |
| `astrbot_plugin_meme_manager` | 366 | 对输入、异步工作和安全回归做专项测试 | 对创建参数加入重复字段、长度和数值检查；搜索通配符转义；补充回归测试。 |
| `astrbot_plugin_proactive_chat` | 352 | 清晰的生命周期管理、可维护的配置/贡献约定 | 明确数据库目录和 Docker 卷要求；后台任务不再裸启动。 |
| `astrbot_plugin_steam_status_monitor` | 188 | 群维度持久化与长期运行的异常日志 | 条目码与查询严格按群隔离；数据库故障向用户返回可读错误并记录日志。 |

## 本轮发现并修正的问题

- 原内部名称不带 `astrbot_plugin_` 前缀，现改为 `astrbot_plugin_together_with_me`；展示名仍为 **together with me**。
- 原 `repo` 为无效示例地址，现明确留空并要求发布前填写。
- 原搜索会把 `%`、`_` 当作 SQLite `LIKE` 通配符，现转义为字面量；同时对大小写、全半角和空白做统一。
- 原可选字段允许重复且没有长度限制，现拒绝重复/空/超长/非法人数。
- 原后台任务只有单一引用，现统一放入任务集合并在插件卸载时取消、等待。
- 原测试覆盖面仅限基本存储流程，现增加生命周期、竞态、命令解析、特殊字符和四命令端到端烟雾测试。
