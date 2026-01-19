# Email Assistant Agent 系统 - 需求文档

## 文档信息

| 项目 | 说明 |
|------|------|
| **文档版本** | v1.0 |
| **创建日期** | 2026-01-15 |
| **项目名称** | Email Assistant Agent System |
| **文档类型** | 产品需求文档 (PRD) |

---

## 1. 项目背景

### 1.1 现有系统概述

**Email Assistant Demo** 是一个基于 Next.js + FastAPI 的 AI 驱动邮件管理系统，当前具备以下能力：

- 邮件同步（Zoho Mail OAuth）
- AI 邮件分类（Claude）
- 基础回复生成
- Skills 管理面板

**Support Email Composer Skill** 是独立的邮件处理技能库，具备三阶段工作流：

- **学习阶段**: 从历史邮件中提取 Skill 和规则
- **执行阶段**: 匹配 Skill 并生成回复
- **自进化阶段**: 从人工修改中学习优化

### 1.2 项目目标

将 `support-email-composer-skill` 的能力通过 **Claude Agent SDK** 集成到 `email-assistant-demo` 系统中，构建一个智能 Agent 系统，实现：

1. 从历史客户邮件中自动学习并提取解决问题的 Skill
2. 对新邮件进行精准 Skill 匹配
3. 基于匹配的 Skill 生成高质量的回复内容
4. 从人工反馈中持续优化 Skill 库

### 1.3 核心价值

- **自动化处理**: 减少 60%+ 重复性客服工作
- **知识沉淀**: 将隐性经验转化为显性规则
- **持续学习**: 系统越用越智能
- **质量保障**: 基于规则确定性，降低 AI 幻觉风险

---

## 2. 系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  邮件管理界面  │  │  Skill管理   │  │  Agent配置   │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕ REST API
┌─────────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Agent System (NEW)                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │
│  │  │ Learning    │  │ Execution   │  │ Evolution   │          │    │
│  │  │ Agent       │  │ Agent       │  │ Agent       │          │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │          Support Email Composer Skill (Integration)          │    │
│  │  - Skill Manager (rules, matching)                            │    │
│  │  - Claude Client (AI analysis)                                │    │
│  │  - Email Parser (data processing)                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│  Existing Routers:                                                  │
│  - /api/emails    - /api/skills    - /api/replies                 │
│  - /api/oauth    - /api/status                                     │
│  New Routers:                                                       │
│  - /api/agents/learn     - /api/agents/execute                     │
│  - /api/agents/evolve    - /api/agents/status                      │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Zoho Mail API   │  │   Claude API      │  │   SQLite DB       │
│   (邮件来源)       │  │   (AI引擎)        │  │   (数据存储)       │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

### 2.2 Agent 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Agent SDK                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Agent Orchestration                 │    │
│  │  - Tool Calling                                      │    │
│  │  - Memory Management                                 │    │
│  │  - Context Tracking                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Specialized Agents                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Learning Agent  │    │ Execution Agent │                 │
│  │                 │    │                 │                 │
│  │ 分析历史邮件     │    │ 处理新邮件      │                 │
│  │ 提取 Skill       │    │ 匹配 Skill      │                 │
│  │ 生成规则库       │    │ 生成回复        │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                               │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Evolution Agent │    │ Supervisor      │                 │
│  │                 │    │ Agent           │                 │
│  │ 分析反馈差异     │    │ 协调各Agent     │                 │
│  │ 更新 Skill       │    │ 管理任务队列    │                 │
│  │ 优化规则库       │    │ 监控系统状态    │                 │
│  └─────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 功能需求

### 3.1 学习阶段 (Learning Agent)

**目标**: 从历史邮件中学习并提取 Skill

| 功能编号 | 功能描述 | 优先级 |
|---------|---------|--------|
| L-01 | 从 Zoho/Zendesk 导入历史邮件数据 | P0 |
| L-02 | 使用 Claude 分析邮件对话，提取处理模式 | P0 |
| L-03 | 按问题分类自动创建 Skill | P0 |
| L-04 | 为每个 Skill 提取触发关键词和处理规则 | P0 |
| L-05 | 生成专业友好的回复模板 | P0 |
| L-06 | 识别协作 Skill 关系 | P1 |
| L-07 | 导出/导入 Skill 库 (JSON/Markdown) | P1 |

**输入**:
- 历史邮件数据 (JSON 格式)
- 可选的分类过滤器

**输出**:
- Skill 库文件 (skill_library.json)
- Markdown 文档 (便于人工审核)

**API 接口**:
```
POST /api/agents/learn
- Body: { "emails": [...], "category": "optional" }
- Response: { "skills_created": 5, "rules_extracted": 23 }
```

### 3.2 执行阶段 (Execution Agent)

**目标**: 对新邮件进行 Skill 匹配并生成回复

| 功能编号 | 功能描述 | 优先级 |
|---------|---------|--------|
| E-01 | 接收新邮件，解析内容 | P0 |
| E-02 | 使用 Claude 进行问题分类 | P0 |
| E-03 | 基于关键词匹配相关 Skill | P0 |
| E-04 | 匹配具体的处理规则 | P0 |
| E-05 | 基于规则生成回复草稿 | P0 |
| E-06 | 无匹配时转人工处理 | P0 |
| E-07 | 提供匹配置信度和匹配详情 | P1 |

**输入**:
- 新邮件数据

**输出**:
- 回复草稿
- 匹配的 Skill 和规则
- 置信度评分

**API 接口**:
```
POST /api/agents/execute
- Body: { "email": {...} }
- Response: {
    "status": "draft_ready" | "escalate_to_human",
    "matched_skills": ["equipment-fault-handler"],
    "matched_rules": [...],
    "response": "...",
    "confidence": "high" | "medium" | "low"
  }
```

### 3.3 自进化阶段 (Evolution Agent)

**目标**: 从人工反馈中学习并优化 Skill

| 功能编号 | 功能描述 | 优先级 |
|---------|---------|--------|
| V-01 | 收集 AI 草稿和人工修改版本 | P0 |
| V-02 | 使用 Claude 分析差异 | P0 |
| V-03 | 识别新规则或更新现有规则 | P0 |
| V-04 | 自动更新 Skill 库 | P0 |
| V-05 | 记录变更历史 | P1 |
| V-06 | 提供人工审核机制 | P0 |

**输入**:
- AI 生成的草稿
- 人工修改后的版本
- 目标 Skill 名称

**输出**:
- 更新的 Skill 库
- 变更说明

**API 接口**:
```
POST /api/agents/evolve
- Body: {
    "ai_draft": "...",
    "human_edited": "...",
    "skill_name": "equipment-fault-handler"
  }
- Response: {
    "skill_updated": true,
    "changes": [...],
    "new_rules_added": 1
  }
```

---

## 4. 数据模型

### 4.1 Skill 数据结构

```json
{
  "skill": {
    "name": "设备故障处理",
    "name_en": "equipment-fault-handler",
    "category": "技术支持",
    "description": "处理设备故障相关问题",
    "trigger_keywords": ["故障", "坏了", "不能用", "红灯", "报警"],
    "collaborative_skills": ["refund-handler", "repair-booking"],
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T12:00:00Z",
    "rules": [
      {
        "rule_id": "rule_1",
        "name": "温度计红灯",
        "trigger_keywords": ["温度", "红灯", "过热"],
        "conditions": ["温度", "红灯"],
        "action_steps": [
          "立即停止设备使用",
          "检查环境温度",
          "清洁散热风扇",
          "等待30分钟后重启"
        ],
        "response_template": "尊敬的{customer_name}，您好！...",
        "priority": 10,
        "usage_count": 15,
        "success_count": 14
      }
    ]
  }
}
```

### 4.2 邮件数据结构

```json
{
  "email": {
    "zoho_id": "123456",
    "sender": "customer@example.com",
    "customer_name": "张三",
    "subject": "设备温度报警",
    "body": "我的设备显示温度红灯，怎么办？",
    "received_at": "2026-01-15T10:00:00Z",
    "is_customer_service": true,
    "category": "设备故障",
    "processed": false
  }
}
```

### 4.3 回复数据结构

```json
{
  "reply": {
    "id": "reply_001",
    "email_id": "123456",
    "ai_draft": "AI生成的回复内容...",
    "human_edited": "人工修改后的内容...",
    "matched_skills": ["equipment-fault-handler"],
    "matched_rules": ["rule_1"],
    "confidence": "high",
    "sent_status": "pending",
    "created_at": "2026-01-15T10:05:00Z"
  }
}
```

---

## 5. API 接口设计

### 5.1 学习相关接口

#### POST /api/agents/learn
从历史邮件中学习并提取 Skill

**Request**:
```json
{
  "source": "zoho" | "zendesk" | "upload",
  "data": {
    "emails": [...],           // 邮件数据（upload 模式）
    "start_date": "2024-01-01", // 时间范围（zoho/zendesk 模式）
    "end_date": "2024-12-31",
    "category": "设备故障"      // 可选分类过滤
  }
}
```

**Response**:
```json
{
  "job_id": "learn_job_123",
  "status": "processing" | "completed" | "failed",
  "summary": {
    "emails_analyzed": 150,
    "skills_created": 5,
    "rules_extracted": 23,
    "categories": ["设备故障", "退卡退款", "价格咨询"]
  },
  "skill_library_path": "/data/skill_library.json"
}
```

#### GET /api/agents/learn/status/{job_id}
查询学习任务状态

### 5.2 执行相关接口

#### POST /api/agents/execute
处理新邮件，生成回复

**Request**:
```json
{
  "email": {
    "zoho_id": "123456",
    "sender": "customer@example.com",
    "customer_name": "张三",
    "subject": "设备温度报警",
    "body": "我的设备显示温度红灯，怎么办？"
  },
  "options": {
    "auto_send": false,        // 是否自动发送
    "require_review": true     // 是否需要人工审核
  }
}
```

**Response**:
```json
{
  "status": "draft_ready" | "escalate_to_human",
  "email_id": "123456",
  "reply_id": "reply_001",
  "matched_skills": [
    {
      "name": "设备故障处理",
      "name_en": "equipment-fault-handler",
      "confidence": 0.95
    }
  ],
  "matched_rules": [
    {
      "skill": "equipment-fault-handler",
      "rule": "rule_1",
      "rule_name": "温度计红灯",
      "priority": 10
    }
  ],
  "response": "尊敬的张先生，您好！...",
  "confidence": "high",
  "requires_review": true,
  "escalation_reason": null
}
```

### 5.3 自进化相关接口

#### POST /api/agents/evolve
从人工反馈中学习

**Request**:
```json
{
  "reply_id": "reply_001",
  "ai_draft": "AI生成的原始回复...",
  "human_edited": "人工修改后的回复...",
  "feedback": {
    "rating": 4,              // 1-5 评分
    "comment": "需要添加更多细节"
  }
}
```

**Response**:
```json
{
  "status": "skill_updated",
  "changes": [
    {
      "type": "new_rule",
      "skill": "equipment-fault-handler",
      "rule_id": "rule_16",
      "description": "添加了环境温度检查的详细说明"
    }
  ],
  "skill_library_version": "v2.1"
}
```

### 5.4 监控相关接口

#### GET /api/agents/status
获取 Agent 系统状态

**Response**:
```json
{
  "system_status": "healthy",
  "agents": {
    "learning": { "status": "idle", "jobs_completed": 15 },
    "execution": { "status": "active", "emails_processed": 150 },
    "evolution": { "status": "idle", "skills_updated": 8 }
  },
  "skill_library": {
    "total_skills": 12,
    "total_rules": 58,
    "categories": ["设备故障", "退卡退款", "价格咨询", "技术支持"],
    "last_updated": "2026-01-15T12:00:00Z"
  },
  "performance": {
    "skill_coverage": 0.72,
    "avg_confidence": 0.85,
    "escalation_rate": 0.15
  }
}
```

---

## 6. 技术栈

### 6.1 核心技术

| 层级 | 技术 | 说明 |
|------|------|------|
| **Agent 框架** | Claude Agent SDK | Agent 编排、工具调用 |
| **AI 模型** | Claude 3.5 (Sonnet/Opus) | 分析、分类、生成 |
| **后端框架** | FastAPI | API 服务 |
| **数据库** | SQLite + SQLAlchemy | 数据持久化 |
| **前端框架** | Next.js 14 | 用户界面 |

### 6.2 Claude 模型使用策略

| 阶段 | 模型 | 用途 |
|------|------|------|
| **学习阶段** | Claude Opus | 深度分析、复杂规则提取 |
| **执行阶段** | Claude Sonnet | 快速分类、回复生成 |
| **自进化** | Claude Opus | 差异分析、规则优化 |

### 6.3 依赖集成

```
email-assistant-demo/backend/
├── agents/                    # NEW: Agent 系统
│   ├── __init__.py
│   ├── base_agent.py         # Agent 基类
│   ├── learning_agent.py     # 学习 Agent
│   ├── execution_agent.py    # 执行 Agent
│   ├── evolution_agent.py    # 自进化 Agent
│   └── supervisor_agent.py   # 监控 Agent
│
├── skill_integration/         # NEW: Skill 集成层
│   ├── __init__.py
│   ├── skill_manager.py      # 从 support-email-composer-skill 集成
│   ├── claude_client.py      # Claude API 客户端
│   └── email_parser.py       # 邮件解析
│
├── routers/
│   ├── agents_router.py      # NEW: Agent API 路由
│   └── ...existing routers...
│
└── services/
    ├── agent_service.py      # NEW: Agent 业务逻辑
    └── ...existing services...
```

---

## 7. 工作流程

### 7.1 端到端流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        初始化阶段                                │
└─────────────────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  1. 从 Zendesk/Zoho 导入历史邮件             │
    │     (支持批量导入或指定时间范围)              │
    └─────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  2. 运行 Learning Agent                     │
    │     - Claude 分析邮件对话                    │
    │     - 提取 Skill 和规则                      │
    │     - 生成回复模板                           │
    └─────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  3. 人工审核 Skill 库                        │
    │     (可选，通过 Web 界面)                    │
    └─────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  4. 激活 Skill 库，开始处理新邮件            │
    └─────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        运行阶段                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  新邮件到达                                  │
    └─────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────┐
    │  5. 运行 Execution Agent                    │
    │     - Claude 分类问题                        │
    │     - 匹配相关 Skill                         │
    │     - 匹配具体规则                           │
    │     - 生成回复草稿                           │
    └─────────────────────────────────────────────┘
                           ↓
                  ┌────────┴────────┐
                  │                 │
          ┌───────┴──────┐  ┌─────┴────────┐
          │ 匹配成功      │  │ 无匹配       │
          ↓              ↓  ↓              │
    ┌──────────┐  ┌──────────┐          │
    │ 生成回复  │  │ 转人工    │◄─────────┘
    │ 人工审核  │  │ 处理      │
    └──────────┘  └──────────┘
          ↓
    ┌─────────────────────────────────────────────┐
    │  6. 发送回复                                 │
    └─────────────────────────────────────────────┘
          ↓
    ┌─────────────────────────────────────────────┐
    │  7. (可选) 运行 Evolution Agent             │
    │     - 对比 AI 草稿和人工修改                 │
    │     - 更新 Skill 库                          │
    └─────────────────────────────────────────────┘
```

### 7.2 决策流程

```
新邮件接收
      ↓
┌─────────────────┐
│ 邮件分类         │
│ (Claude Sonnet) │
└─────────────────┘
      ↓
┌─────────────────┐
│ Skill 匹配       │
│ (关键词+条件)    │
└─────────────────┘
      ↓
   ┌──┴──┐
   │     │
匹配     未匹配
   │     │
   ↓     ↓
规则匹配   ┌────────────┐
   │     │ 转人工处理  │
   │     └────────────┘
   ↓
┌─────────────┐
│ 生成回复     │
│ (Claude)    │
└─────────────┘
      ↓
┌─────────────┐
│ 人工审核     │
│ (必选)      │
└─────────────┘
      ↓
   ┌──┴──┐
   │     │
直接发送  修改
   │     │
   │     ↓
   │  ┌────────────┐
   │  │ 自进化学习  │
   │  │ (可选)      │
   │  └────────────┘
   ↓
发送完成
```

---

## 8. 非功能性需求

### 8.1 性能要求

| 指标 | 目标值 |
|------|--------|
| 邮件分类响应时间 | < 2 秒 |
| Skill 匹配时间 | < 500ms |
| 回复生成时间 | < 5 秒 |
| 学习阶段处理速度 | 50 封邮件/分钟 |

### 8.2 质量指标

| 指标 | 目标值 |
|------|--------|
| Skill 覆盖率 | > 60% |
| 回复准确率 | > 85% |
| 人工编辑率 | < 30% |
| 转人工率 | < 20% |

### 8.3 安全要求

- 所有 API 调用需要身份验证
- API Key 加密存储
- 邮件内容不记录敏感信息
- 人工审核为必选步骤

### 8.4 可扩展性

- 支持新增 Skill 类型
- 支持自定义规则
- 支持多语言扩展
- 支持 Agent 插件化

---

## 9. 实施计划

### 9.1 开发阶段

| 阶段 | 任务 | 交付物 |
|------|------|--------|
| **Phase 1** | 基础架构搭建 | Agent 基类、API 路由 |
| **Phase 2** | Learning Agent | 学习功能实现 |
| **Phase 3** | Execution Agent | 执行功能实现 |
| **Phase 4** | Evolution Agent | 自进化功能实现 |
| **Phase 5** | 前端集成 | UI 界面开发 |
| **Phase 6** | 测试与优化 | 系统测试 |

### 9.2 里程碑

| 里程碑 | 说明 |
|--------|------|
| M1 | Agent 系统基础架构完成 |
| M2 | 学习阶段功能可用 |
| M3 | 执行阶段功能可用 |
| M4 | 自进化阶段功能可用 |
| M5 | 端到端流程打通 |
| M6 | 生产环境部署 |

---

## 10. 风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Skill 匹配准确率低 | 高 | 充分的历史数据训练，人工审核 |
| AI 生成回复不准确 | 高 | 必选人工审核，自进化优化 |
| Claude API 成本高 | 中 | 合理选择模型，缓存常用结果 |
| 性能瓶颈 | 中 | 异步处理，任务队列 |
| 邮件数据隐私 | 高 | 数据脱敏，访问控制 |

---

## 11. 成功标准

### 11.1 技术指标

- [ ] 成功集成 Claude Agent SDK
- [ ] 完成三阶段 Agent 开发
- [ ] API 接口测试覆盖率 > 80%
- [ ] 系统响应时间满足要求

### 11.2 业务指标

- [ ] Skill 覆盖率达到 60%+
- [ ] 自动回复准确率达到 85%+
- [ ] 客服工作效率提升 50%+
- [ ] 人工编辑率低于 30%

---

## 12. 附录

### 12.1 术语表

| 术语 | 说明 |
|------|------|
| Skill | 解决特定问题的技能单元，包含触发条件和处理规则 |
| Rule | Skill 内的具体处理规则 |
| Agent | 基于 Claude Agent SDK 的智能代理 |
| 学习阶段 | 从历史邮件中提取 Skill 的过程 |
| 执行阶段 | 处理新邮件并生成回复的过程 |
| 自进化阶段 | 从人工反馈中优化 Skill 的过程 |

### 12.2 参考文档

- [Claude Agent SDK 文档](https://docs.anthropic.com/agent-sdk)
- [Support Email Composer Skill README](../support-email-composer-skill/README.md)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Claude API 文档](https://docs.anthropic.com/claude/reference)

---

**文档结束**
