# FailureLogAnalyzer

大模型评测日志错因分析系统。

## 项目结构

```
docs/superpowers/
  specs/    # 设计文档
  plans/    # 实现计划
backend/    # Python 3.11+ / FastAPI / LangGraph
frontend/   # React + TypeScript + Ant Design
```

## 开发规范

- 后端：Python 3.11+，FastAPI，SQLAlchemy 2（async），Alembic，Celery + Redis
- 前端：React + TypeScript + Ant Design + ECharts
- 测试：pytest（后端），Jest + React Testing Library（前端）
- 代码风格：ruff（lint + format），mypy（类型检查）

## Worktrees

- 使用 `.worktrees/` 目录（已加入 .gitignore）
- 每个功能分支在独立 worktree 中开发

## 分支约定

- `master`：主分支，保持可部署状态
- `feature/<name>`：功能开发分支（在 worktree 中）
