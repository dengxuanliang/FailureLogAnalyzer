# FailureLogAnalyzer — 大模型评测日志错因分析系统设计文档

> 日期: 2026-03-18
> 状态: Draft

## 1. 项目概述

### 1.1 目标

构建一个基于多 Agent 协作的大模型评测日志错因分析系统。系统能够接收自研评测框架产出的 GB 级 JSON/JSONL 日志，通过规则引擎快速预分类与 LLM Judge 深度分析相结合的方式，对模型错题进行多维度错因归类，并提供版本对比、跨 Benchmark 横向分析等能力。

### 1.2 核心需求

- **错因归类（主要）**：对评测错题进行多层级、多维度的错因分析
- **版本对比**：同一模型不同版本间能力变化追踪
- **Benchmark 横向分析**：跨 benchmark 发现系统性弱点
- **Agent 驱动**：多 Agent 协作完成自动化分析工作流
- **用户可控 LLM 分析**：支持全量/规则兜底/采样/手动触发策略
- **可扩展性**：支持 20+ 人团队使用，架构可水平扩展

### 1.3 输入数据

- 自研评测框架产出的 JSON / JSONL 格式日志
- 不同 benchmark 输出字段不同
- 单文件/文件夹可达 GB 级别

---

## 2. 整体架构

采用**流式管道架构 + LangGraph 多 Agent 编排**。

### 2.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Agent (LangGraph)                  │
│         意图识别 · 任务分发 · 结果汇总 · Human-in-the-Loop    │
├──────────┬──────────┬───────────────┬───────────────────────┤
│ Ingestion│  Rule    │  LLM Judge    │    Report             │
│  Agent   │  Agent   │    Agent      │    Agent              │
├──────────┴──────────┴───────────────┴───────────────────────┤
│                    Storage Layer                             │
│            PostgreSQL · Redis · LangGraph Checkpointer       │
├─────────────────────────────────────────────────────────────┤
│                    Query & Aggregation Layer                  │
│                      FastAPI REST API                        │
├─────────────────────────────────────────────────────────────┤
│                    Dashboard Layer                            │
│          React + Ant Design + ECharts + Agent 对话窗口        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层级 | 技术选型 |
|------|---------|
| Agent 编排 | LangGraph (StateGraph) |
| 后端 | Python 3.11+ / FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL 15+ (分区表) |
| 缓存/队列 | Redis |
| 前端 | React + TypeScript + Ant Design |
| 图表 | ECharts / Recharts |
| 实时通信 | WebSocket |
| 流式解析 | ijson / orjson |
| 部署 | Docker Compose → K8s |

---

## 3. Agent 编排层

### 3.1 Orchestrator Agent（主编排）

- **职责**：接收用户指令（自然语言或 API），拆解任务，调度子 Agent，汇总结果
- **实现**：LangGraph StateGraph
- **能力**：意图识别 · 路径选择 · 子 Agent 协调 · 报告生成

### 3.2 子 Agent

| Agent | 职责 |
|-------|------|
| Ingestion Agent | 文件解析、格式适配、流式写入、进度上报 |
| Rule Agent | 规则匹配、标签打标、异常检测、预分类 |
| LLM Judge Agent | 深度错因分析、Prompt 选择、结果结构化、成本控制 |
| Report Agent | 聚合统计、趋势分析、版本对比、报告生成 |

### 3.3 LangGraph 状态图

**主工作流：**

```
START → Route(意图识别)
  ├→ Ingest Subgraph
  ├→ Analyze Subgraph
  ├→ Compare Subgraph
  └→ Query Subgraph
      → Report Agent → Human Loop → END
```

**Analyze Subgraph（核心）：**

```
Select Records → Rule Engine (batch) → LLM Strategy Decision
  ├→ LLM Judge (async) → Merge Results
  └→ Skip LLM → Merge Results
```

### 3.4 全局状态 (SharedState)

```python
class OrchestratorState(TypedDict):
    # 用户交互
    user_input: str
    intent: str
    conversation_history: list[Message]

    # 数据摄入
    ingest_job_id: Optional[str]
    ingest_status: Optional[str]  # pending/running/done/failed

    # 分析上下文
    target_session_ids: list[str]
    target_filters: dict
    analysis_strategy: str

    # 分析结果
    rule_results: list[TaggedRecord]
    llm_results: list[AnalysisResult]
    merged_results: list[dict]

    # 报告
    report: Optional[Report]
    visualizations: list[dict]

    # 流程控制
    current_step: str
    errors: list[str]
    needs_human_input: bool
```

### 3.5 用户交互模式

两种等价交互通道，Agent 统一处理：

1. **自然语言对话**：Dashboard 内嵌对话窗口，自然语言驱动分析
2. **Dashboard 操作联动**：
   - 上传文件 → 触发 Ingestion Agent
   - 点击"分析"→ 触发 Analyze Subgraph
   - 选中记录点"LLM 分析"→ 手动触发 LLM Judge
   - 切换筛选条件 → Query Subgraph
   - 点击"生成报告"→ Report Agent

---

## 4. 数据接入层 (Ingestion Agent)

### 4.1 Benchmark Adapter 注册机制

采用插件化设计，每个 benchmark 注册一个 Adapter，将原始数据映射为标准化记录。

**NormalizedRecord 结构：**

```python
{
    "session_id": "uuid",            # 评测批次 ID
    "benchmark": "mmlu",             # benchmark 名称
    "model": "model-v2.1",           # 模型标识
    "model_version": "v2.1",         # 模型版本
    "task_category": "math/algebra", # 任务类别（层级）
    "question_id": "mmlu_math_042",  # 题目唯一 ID
    "question": "...",               # 题目内容
    "expected_answer": "...",        # 标准答案
    "model_answer": "...",           # 模型回答
    "is_correct": false,             # 是否正确
    "score": 0.0,                    # 得分（支持连续分值）
    "extracted_code": "...",         # 提取的代码部分
    "metadata": { ... },            # benchmark 特有字段（保留原始）
    "raw_json": { ... }             # 原始完整记录
}
```

**Adapter 注册方式：**

- 继承 `BaseAdapter`，实现 `detect(file)` + `normalize(record)`
- 通过 `@register_adapter("benchmark_name")` 装饰器自动注册
- 支持自动检测（遍历 adapter 的 detect 方法匹配文件格式）
- 支持手动指定 adapter（上传时选择 benchmark 类型）

### 4.2 流式解析策略

| 文件格式 | 策略 | 内存 | 实现 |
|---------|------|------|------|
| JSONL（每行一条）| 逐行读取 | O(1) | Python `readline()` |
| 大 JSON（一个大数组）| 流式解析 | O(1) | `ijson.items(f, 'item')` |

- **批量写入**：内存缓冲 1000 条 → 批量 INSERT → 清空缓冲 → 继续
- **进度反馈**：WebSocket 实时推送（已处理条数 / 预估总条数 / 速度 / 剩余时间）
- **容错**：单条失败记录到 error_log 并跳过；批量写入失败逐条重试；支持断点续传（记录字节偏移/行号）
- **内存约束**：单文件处理内存峰值 < 256MB

### 4.3 文件接入方式

1. **Web 上传**：拖拽上传文件/文件夹，分块上传避免超时，自动检测 adapter
2. **目录监听**（推荐生产环境）：配置监听目录，watchdog 监听新文件事件，自动触发解析管道

---

## 5. 规则分析层 (Rule Agent)

### 5.1 错因分类体系（三级）

```
├── L1: 格式与规范错误 (Format Errors)              ← 规则引擎判定
│   ├── L2: 输出格式不符（未按要求格式回答）
│   ├── L2: JSON/代码块解析失败
│   ├── L2: 空回答 / 拒绝回答
│   ├── L2: 语言不匹配（要求中文答英文等）
│   └── L2: 超长/截断回答
│
├── L1: 解析类错误 (Extraction Errors)               ← 规则引擎判定
│   ├── L2: 代码提取为空（extracted_code 为空但模型有输出）
│   ├── L2: 代码提取不完整（截断、缺失关键部分）
│   ├── L2: 答案提取错误（提取结果与模型原始输出不匹配）
│   └── L2: 提取字段类型错误（期望 list 得到 string 等）
│
├── L1: 知识性错误 (Knowledge Errors)                ← LLM 分析为主
│   ├── L2: 事实性错误
│   │   ├── L3: 核心知识点错误
│   │   ├── L3: 边界/细节知识缺失
│   │   └── L3: 过时知识（时效性）
│   ├── L2: 概念混淆
│   └── L2: 领域知识盲区
│
├── L1: 推理性错误 (Reasoning Errors)                ← LLM 分析为主
│   ├── L2: 逻辑推理错误
│   │   ├── L3: 前提正确但推理链断裂
│   │   ├── L3: 错误的因果推断
│   │   └── L3: 遗漏关键条件
│   ├── L2: 数学/计算错误
│   │   ├── L3: 算术错误
│   │   ├── L3: 公式应用错误
│   │   └── L3: 单位/量级错误
│   └── L2: 多步推理退化（前几步对，后面错）
│
├── L1: 理解性错误 (Comprehension Errors)            ← LLM 分析为主
│   ├── L2: 题意理解错误（答非所问）
│   ├── L2: 指令遵循失败（没按要求做）
│   ├── L2: 上下文遗漏（忽略关键信息）
│   └── L2: 歧义理解偏差
│
└── L1: 生成质量问题 (Generation Quality)            ← 规则+LLM 协作
    ├── L2: 幻觉（编造不存在的内容）
    ├── L2: 重复生成
    ├── L2: 不完整回答（有思路但没写完）
    └── L2: 过度对齐（过于保守拒答）
```

设计要点：
- 分类树可配置，用户可新增/修改 L2/L3 节点
- 每条记录可打多个标签（一道错题可能同时有理解错误+推理错误）
- L1 层级稳定，L2/L3 允许按 benchmark 特点自定义扩展

### 5.2 内置规则

| 规则 | 检测逻辑 | 产出标签 |
|------|---------|---------|
| EmptyAnswerRule | 模型回答为空/仅空白 | 格式.空回答 |
| FormatMismatchRule | 要求 JSON 但输出不是 | 格式.输出格式不符 |
| ExactMatchRule | 答案精确匹配检测 | 标记匹配方式 |
| LengthAnomalyRule | 回答长度 vs 同题平均值 | 生成.不完整/重复 |
| LanguageMismatchRule | 检测回答语言 vs 要求语言 | 格式.语言不匹配 |
| RepetitionRule | n-gram 重复率检测 | 生成.重复生成 |
| RefusalRule | 匹配拒答模式 | 生成.过度对齐 |
| ExtractedFieldEmptyRule | extracted_code 等提取字段为空但 model_answer 非空 | 解析.代码提取为空 |
| ExtractionMismatchRule | 提取结果与原始输出明显不一致 | 解析.答案提取错误 |

### 5.3 自定义规则

支持通过 YAML 配置或 Dashboard UI 创建自定义规则：

```yaml
name: "code_syntax_error"
field: "model_answer"
condition:
  type: "regex"
  pattern: "SyntaxError|IndentationError"
tags: ["格式.代码语法错误"]
confidence: 0.9
priority: 10
```

支持的条件类型：regex、contains / not_contains、length_gt / length_lt、field_equals / field_missing、python_expr

---

## 6. LLM 分析层 (LLM Judge Agent)

### 6.1 触发策略（用户可配置）

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| 全量模式 | 所有错题 → LLM 队列 | 重要评测、小数据集 |
| 规则兜底模式 | 规则未分类的 → LLM 队列 | 日常评测、控制成本 |
| 采样模式 | 按类别/比例随机采样 → LLM | 大规模评测、快速摸底 |
| 手动触发 | 用户选择具体记录/批次 → LLM | 深入调查特定问题 |

### 6.2 Prompt 模板机制

- 内置通用错因分析模板（适用大多数 benchmark）
- 支持按 benchmark 注册专属模板（如代码题需要执行结果对比）
- 模板变量：`{question}` `{expected}` `{model_answer}` `{rule_tags}` `{task_category}`
- 版本管理，模板修改历史可追溯

### 6.3 LLM 输出结构

```json
{
    "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
    "root_cause": "模型在第3步推理时错误地将充分条件当作必要条件",
    "severity": "high",
    "confidence": 0.85,
    "evidence": "模型回答中'因为A所以必然B'，但题目条件仅支持...",
    "suggestion": "加强逻辑推理训练数据中条件关系的多样性"
}
```

### 6.4 Worker 并发与成本控制

- Celery Worker 数量可配置（按 LLM API 并发限制调整）
- 支持配置 LLM 提供商（OpenAI / Claude / 本地模型）
- 速率限制：每分钟最大请求数、每日预算上限
- 优先级队列：手动触发 > 全量分析 > 采样分析
- 失败重试：指数退避，3 次失败标记为 analysis_failed
- 实时成本统计：Dashboard 显示当前分析花费

---

## 7. 存储层

### 7.1 核心表结构

**eval_sessions** — 评测批次元信息

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 批次 ID |
| model | VARCHAR | 模型标识 |
| model_version | VARCHAR | 模型版本 |
| benchmark | VARCHAR | benchmark 名称 |
| dataset_name | VARCHAR | 数据集名称 |
| total_count | INT | 总题数 |
| error_count | INT | 错题数 |
| accuracy | FLOAT | 准确率 |
| config | JSONB | 评测配置 |
| tags | VARCHAR[] | 自定义标签 |
| created_at | TIMESTAMP | 创建时间 |

**eval_records** — 单条评测记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 记录 ID |
| session_id | UUID FK | 关联批次 |
| benchmark | VARCHAR | benchmark |
| task_category | VARCHAR | 任务类别 |
| question_id | VARCHAR | 题目 ID |
| question | TEXT | 题目内容 |
| expected_answer | TEXT | 标准答案 |
| model_answer | TEXT | 模型回答 |
| is_correct | BOOLEAN | 是否正确 |
| score | FLOAT | 得分 |
| extracted_code | TEXT | 提取的代码 |
| metadata | JSONB | benchmark 特有字段 |
| raw_json | JSONB | 原始完整记录 |
| created_at | TIMESTAMP | 创建时间 |

**analysis_results** — 分析结果

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 结果 ID |
| record_id | UUID FK | 关联评测记录 |
| analysis_type | ENUM | rule / llm / manual |
| error_types | VARCHAR[] | 错误类型列表 |
| root_cause | TEXT | 根因分析 |
| severity | ENUM | high / medium / low |
| confidence | FLOAT | 置信度 |
| evidence | TEXT | 证据 |
| suggestion | TEXT | 改进建议 |
| llm_model | VARCHAR | 使用的 LLM 模型 |
| llm_cost | FLOAT | 分析成本 |
| prompt_template | VARCHAR | 使用的模板 |
| raw_response | JSONB | LLM 原始响应 |
| created_at | TIMESTAMP | 创建时间 |

**error_tags** — 多标签错因标记

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 标签 ID |
| record_id | UUID FK | 关联评测记录 |
| tag_path | VARCHAR | 标签路径，如 "推理性错误.逻辑推理.推理链断裂" |
| tag_level | INT | 层级 (1/2/3) |
| source | ENUM | rule / llm |
| confidence | FLOAT | 置信度 |
| created_at | TIMESTAMP | 创建时间 |

**analysis_rules** — 用户自定义规则

**analysis_strategies** — LLM 触发策略配置

### 7.2 分区策略

- **eval_records**：按 `benchmark` LIST 分区，每个分区内按 `created_at` RANGE 子分区（按月）
- **analysis_results**：按 `analysis_type` LIST 分区
- **error_tags**：按 `tag_level` LIST 分区

### 7.3 索引策略

**复合索引：**
- `(benchmark, is_correct)` — 按 benchmark 筛错题
- `(session_id, is_correct)` — 按批次查错题
- `(task_category)` — 按类别聚合
- `(model_version, benchmark)` — 版本对比

**GIN 索引：** `metadata` JSONB 字段

**全文索引：** `question`、`model_answer` 字段

---

## 8. 查询聚合层

### 8.1 REST API 端点

**数据摄入 & 会话管理：**
- `POST /api/v1/ingest/upload` — 文件上传
- `POST /api/v1/ingest/directory` — 目录扫描
- `GET /api/v1/ingest/{job_id}/status` — 摄入进度
- `GET /api/v1/sessions` — 评测批次列表
- `GET /api/v1/sessions/{id}` — 批次详情
- `DELETE /api/v1/sessions/{id}` — 删除批次

**错因分析：**
- `GET /api/v1/analysis/summary?benchmark=&model_version=&time_range=` — 分析概览
- `GET /api/v1/analysis/error-distribution?group_by=error_type|category|severity` — 错误分布
- `GET /api/v1/analysis/records?error_type=&page=&size=` — 错题列表（分页）
- `GET /api/v1/analysis/records/{id}/detail` — 单条详情

**版本对比：**
- `GET /api/v1/compare/versions?version_a=&version_b=&benchmark=` — 版本对比
- `GET /api/v1/compare/diff` — 退化/进步/新增错误类型
- `GET /api/v1/compare/radar` — 能力雷达图数据

**LLM 分析控制：**
- `POST /api/v1/llm/trigger` — 触发 LLM 分析
- `GET /api/v1/llm/jobs` — 分析任务列表
- `GET /api/v1/llm/jobs/{id}/status` — 任务状态
- `GET /api/v1/llm/cost-summary` — 成本统计
- `CRUD /api/v1/llm/strategies` — 策略管理
- `CRUD /api/v1/llm/prompt-templates` — 模板管理
- `CRUD /api/v1/rules` — 规则管理

**横向分析：**
- `GET /api/v1/cross-benchmark/matrix` — 模型×Benchmark 能力矩阵
- `GET /api/v1/cross-benchmark/weakness` — 系统性弱点识别
- `GET /api/v1/trends` — 错误率时间趋势

**实时通信：**
- `WS /api/v1/ws/progress` — 摄入/LLM分析 实时进度推送

---

## 9. Dashboard 展示层

### 9.1 全局组件

- 左侧导航栏：页面切换 + 评测批次选择器
- 顶部筛选栏：Benchmark / 模型版本 / 时间范围 / 错误类型（全局联动）
- 右下角 Agent 对话窗口：悬浮可折叠，自然语言交互
- 实时通知：摄入进度、LLM 分析完成等

### 9.2 总览面板 (Overview)

**指标卡片（5 个）：** 总评测数 / 错题总数 / 整体准确率 / 已 LLM 分析数 / LLM 分析成本

**图表：**
- 错误率趋势折线图（X: 模型版本, Y: 错误率）
- L1 错误类型分布环形图

### 9.3 错因分析页（核心）

**三级下钻交互：**
1. Treemap 总览（面积=错题数量，展示 L1 分布）
2. 点击 L1 展开 L2 子类别
3. 点击 L2 展开 L3，进入错题列表
4. 点击单条记录查看详情

**单条详情：**
- 题目 / 标准答案 / 模型回答 三栏对比
- 错因标签展示
- LLM 分析结果（根因、严重度、置信度、证据、建议）
- 操作按钮：重新 LLM 分析 / 人工标注

### 9.4 版本对比页

- 双版本选择器
- 能力雷达图（各维度能力对比）
- 变化摘要：退化题目 / 进步题目 / 新增错误模式
- 支持按 benchmark 筛选对比范围

### 9.5 Benchmark 横向分析页

- 热力图：模型版本 × Benchmark 错误率矩阵（颜色深浅表示错误率）
- Agent 自动生成的系统性弱点识别报告
- 跨 benchmark 共性错误模式分析

### 9.6 分析配置页

**规则管理：**
- 查看/编辑/启停内置规则
- 创建自定义规则的可视化编辑界面
- 规则执行优先级排序

**LLM 策略管理：**
- 配置触发策略参数（采样率、类别筛选等）
- LLM 提供商配置（API Key、模型选择、并发数）
- 每日预算上限、速率限制

**Prompt 模板管理：**
- 查看/编辑 LLM 分析 Prompt 模板
- 按 benchmark 绑定不同模板
- 模板版本历史

**Benchmark Adapter 管理：**
- 查看已注册的 Adapter
- 配置字段映射关系

### 9.7 Agent 对话窗口

- 右下角悬浮，可折叠展开
- 支持自然语言交互，驱动所有分析功能
- 回答会联动 Dashboard 高亮/跳转对应页面
- 对话和 Dashboard 操作是等价的两种交互通道

---

## 10. 部署架构

### 10.1 Docker Compose（开发/小规模）

```
services:
  - api (FastAPI + LangGraph)
  - worker (Celery Workers)
  - frontend (React)
  - postgres (PostgreSQL 15)
  - redis (Redis)
```

### 10.2 Kubernetes（生产/可扩展）

- API 和 Worker 支持水平扩展（HPA）
- Worker 按 LLM API 并发限制配置副本数
- PostgreSQL 使用 PG Operator 或托管服务
- Redis Sentinel / Cluster
- Ingress 统一入口
