# API 自动化测试框架

基于 **pytest + requests + pydantic + FastAPI** 的 API 自动化测试框架，
参考开源项目 [API-Test-Automation-Wireframe](https://github.com/JasonTeixeira/API-Test-Automation-Wireframe) 从零实现，
并自建了一个**模拟游戏服务器**作为第二测试目标，覆盖登录 / 抽卡保底 / 背包 / 排行榜等游戏特色业务场景。

## 项目结构

```
API-Test-Framework/
├── config/            # 配置层：pydantic-settings 读取 .env，参数集中管理
├── models/            # 模型层：Pydantic schema，自动校验 API 响应结构
├── clients/           # 客户端层：Session 会话复用、指数退避重试、日志追踪
│   ├── base_client.py     # 通用基类（重试/日志/多 base_url 支持）
│   ├── users_client.py    # ReqRes 接口客户端
│   └── game_client.py     # 游戏服务器客户端（token 登录态管理）
├── tests/
│   ├── users/         # ReqRes 套件：CRUD、分页、参数化负向用例
│   ├── negative/      # 负向与边界用例（非法参数、404）
│   └── game/          # 游戏套件：登录边界 / 抽卡 / 保底专项 / 背包 / 排行榜
├── game_server.py     # 自建 FastAPI 模拟游戏服务器（被测对象之一）
├── docs/              # 游戏服务器设计稿（需求文档）
├── pytest.ini         # marker 注册 + 默认配置
└── .env               # 本地配置（不入库）
```

## 测试对象

| 目标 | 地址 | 说明 |
|---|---|---|
| ReqRes（公网练习 API） | `API_BASE_URL` | CRUD、分页、负向场景；部分接口需免费 API Key（`.env` 中配 `REQRES_API_KEY`） |
| 模拟游戏服务器（自建） | `GAME_API_BASE_URL` | FastAPI 内存实现，重启即重置，测试环境天然干净 |

游戏服务器接口：注册 / 登录（token 签发与顶号失效）/ 玩家信息 / 抽卡（软保底 74 抽起概率递增 + 90 抽硬保底）/ 抽卡历史 / 背包查询与使用 / 排行榜（并列同名次、名次跳号）/ 分数提交（仅保留历史最高分）。
另含三个仅供本地测试使用的开发钩子：`/api/dev/reset`、`/api/dev/set_pity`、`/api/dev/ranking/reset`。

## 快速开始

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

跑游戏套件需要先在**另一个终端**启动被测服务器：

```powershell
uvicorn game_server:app --port 8000
```

然后运行测试：

```powershell
pytest -v                    # 全量（性能用例默认隔离）
pytest -m smoke -v           # 冒烟：秒级反馈
pytest -m game -v            # 仅游戏套件
pytest -m regression -v      # 完整回归
```

## 测试设计要点

- **marker 分层体系**：smoke（改代码后快速反馈）/ regression（完整回归）/ negative / performance / game，按需挑选执行；
- **测试自足**：每个用例通过 fixture 注册唯一新账号（uuid 前缀），不依赖任何历史状态，用例间零耦合、可重复执行、可并行；
- **全局资源隔离**：排行榜等共享数据通过「快照 + 重置钩子」在每个用例前恢复初始状态，避免跨用例/跨运行的状态污染；
- **随机系统的可控测试**：抽卡保底这类随机逻辑无法靠撞运气覆盖（软保底下几乎走不到第 90 抽），通过 `set_pity` 测试钩子注入前置状态，把概率分支变成确定性断言；
- **schema 校验**：所有响应经 Pydantic 模型校验，字段漂移（改名/缺失）第一时间暴露，而非静默通过。

## 踩坑记录（真实调试案例）

1. **重试机制会掩盖性能劣化**：功能测试需要重试兜底，但性能测量要求"如实测一次"——重试把服务端慢到超时的事实掩盖成"最终成功"。解决方案：`BaseClient.request` 提供 `retries` 参数，性能用例显式绕开重试；
2. **`requests` 的 timeout 语义**：`timeout=10` 限制的是单次读间隔而非总耗时，服务器慢速吐数据时总耗时可以远超 timeout 不报错；
3. **共享资源的测试污染**：排行榜用例被跨运行累积的历史数据打挂（同分账号靠插入顺序排序），修复方式是给全局资源加重置钩子，而不是放宽断言；
4. **断言不要把"可能"当"必然"**：软保底下 pity=85 起抽，第 1 抽出货率已是 72.6%，"五星必出在第 90 抽"的断言本质是错的——改成与随机性无关的等式（`pity_after == 最后一次五星之后的抽数`）。

## Roadmap

- [x] 四层框架：配置 / 模型 / 客户端 / 测试
- [x] 自建 FastAPI 模拟游戏服务器（登录 / 抽卡保底 / 背包 / 排行榜）
- [x] 游戏接口测试套件 tests/game/
- [ ] AI 辅助测试：自动生成用例 / 失败日志归因
