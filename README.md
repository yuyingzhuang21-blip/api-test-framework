# API 自动化测试框架

基于 pytest + requests + pydantic 分层设计的 API 自动化测试框架，
参考开源项目 API-Test-Automation-Wireframe 从零实现。

## 架构

- `config/` 配置层：pydantic-settings 管理 .env，参数集中可切换
- `models/` 模型层：Pydantic schema 校验，响应结构漂移即时暴露
- `clients/` 客户端层：Session 会话复用、指数退避重试、日志追踪
- `tests/` 测试层：pytest marker 体系（smoke / regression / negative / performance）

## 快速开始

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest -v            # 全量
pytest -m smoke -v   # 冒烟
```

## 设计要点

- 重试机制与性能测量解耦：BaseClient 提供 retries 参数，
  性能用例绕开重试，避免超时拖长测量、掩盖服务端真实劣化
- 性能阈值进配置（PERFORMANCE_THRESHOLD_MS），环境差异不改代码
- 公网 API 的性能用例默认隔离（flaky 隔离管理）

## Roadmap

- [ ] 自建 FastAPI 模拟游戏服务器（登录 / 抽卡保底 / 背包 / 排行榜）
- [ ] 游戏接口测试套件 tests/game/
- [ ] AI 辅助测试：自动生成用例 / 失败日志归因
