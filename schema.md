# Wiki Schema

This document defines the structure, conventions, and workflows for this knowledge base.
All LLM operations on this wiki must follow these rules.

---

## Language Rule

**ALL page content MUST be written in Chinese (Simplified).**
This includes: H1 titles, section headings, body text, bullet points, descriptions, summaries.

**Keep in English (machine-readable metadata only):**
- File names: `attention-mechanism.md` (lowercase hyphens)
- Wikilink slugs: `[[attention-mechanism]]`
- Metadata field labels: `**Type:**`, `**Domain:**`, `**Status:**`, `**Last updated:**`
- Metadata field values where they are identifiers: `concept`, `entity`, `topic`, `stub`, `draft`, `complete`

**Example:**
```markdown
# 注意力机制          ← Chinese title

**Type:** concept     ← English metadata label + value
**Domain:** 机器学习  ← English label, Chinese value OK here
**Status:** complete

## 概述               ← Chinese section heading

注意力机制是...       ← Chinese body
```

---

## Directory Structure

```
wiki/
├── index.md          # 目录和导航
├── log.md            # 所有 ingest 和变更的时间记录
├── concepts/         # 原子知识单元（每个文件一个概念）
├── entities/         # 命名实体：人物、论文、项目、工具、数据集
└── topics/           # 综合页面，连接多个概念和实体
```

---

## File Naming

- All lowercase, words separated by hyphens
- No spaces, no special characters except `-`
- Always English, even if the concept has a Chinese name
- Examples: `attention-mechanism.md`, `andrej-karpathy.md`, `transformer-architecture.md`

---

## Page Types

### Concept Page (`wiki/concepts/`)

一个原子概念、技术或术语。应自成一体且可被链接。

```markdown
# <中文概念名称>

**Type:** concept
**Domain:** <领域，如：机器学习 / 系统 / 生物学>
**Status:** stub | draft | complete
**Last updated:** YYYY-MM-DD

## 概述

一段话。通俗语言。这是什么，为什么重要。

## 详述

更深层的解释。可以包含机制、公式、图示说明。

## 主要特性

- 特性 1
- 特性 2

## 关联

- 相关概念：[[concept-b]]、[[concept-c]]
- 被使用于：[[entity-x]]、[[topic-y]]
- 与之对比：[[concept-d]]

## 来源

- [[raw/articles/source-article.md]]
- 作者等，年份 — 关键引述或发现
```

---

### Entity Page (`wiki/entities/`)

世界中的命名事物：人物、论文、项目、工具、数据集、组织。

```markdown
# <中文实体名称>

**Type:** person | paper | project | tool | dataset | organization
**Domain:** <领域>
**Status:** stub | draft | complete
**Last updated:** YYYY-MM-DD

## 概述

这个实体是什么。一段话。

## 主要贡献 / 特性

- 要点 1
- 要点 2

## 关联

- 创建者：[[person-name]]
- 引入了：[[concept-name]]
- 基于：[[entity-b]]
- 被用于：[[topic-name]]

## 时间线

- YYYY年：事件
- YYYY年：事件

## 来源

- [[raw/articles/source.md]]
```

---

### Topic Page (`wiki/topics/`)

综合性页面，综述某个研究领域或主题，连接多个概念和实体。

```markdown
# <中文主题名称>

**Type:** topic
**Domain:** <领域>
**Status:** stub | draft | complete
**Last updated:** YYYY-MM-DD

## 概述

这个主题的内容和重要性。2-3 段。

## 核心概念

- [[concept-a]] — 一行描述
- [[concept-b]] — 一行描述

## 核心实体

- [[entity-a]] — 一行描述
- [[entity-b]] — 一行描述

## 开放问题

- 问题 1
- 问题 2

## 来源

- [[raw/articles/source.md]]
```

---

## index.md Format

```markdown
# 知识库目录

最后更新：YYYY-MM-DD
总页数：N

## 领域

### <领域名称>
- **主题：** [[topic-a]]、[[topic-b]]
- **核心概念：** [[concept-a]]、[[concept-b]]
- **核心实体：** [[entity-a]]、[[entity-b]]

## 最近添加

- YYYY-MM-DD [[page-name]] — 一行描述
```

---

## LLM Operation Rules

### Ingest

处理新的源文件时：

1. 完整阅读源文件后再开始写作
2. 识别其中所有的概念、实体和主题
3. 对每个识别到的内容：检查 wiki 中是否已有对应页面
   - 若有：更新它，合并新信息，不重复
   - 若无：使用对应模板创建新页面
4. 每次 ingest 最多更新 12 个页面（优先处理最重要的）
5. 若添加了新领域或重要页面，更新 `index.md`
6. 在 `log.md` 追加一条记录
7. 所有交叉引用使用 `[[wikilinks]]`，不用纯文本名称

### Query

回答问题时：

1. 说明哪些 wiki 页面与问题相关
2. 基于这些页面综合回答，不凭空捏造 wiki 中没有的内容
3. 若 wiki 缺少相关信息，明确说明
4. 可选：若答案具有可复用价值，可起草一个新 wiki 页面

### Lint

定期健康检查——报告并修复：

1. **孤立页面**：没有入链的页面 → 从相关页面添加链接
2. **Stub 页面**：只有概述的页面 → 若有来源则补充内容
3. **断链**：指向不存在页面的 `[[links]]` → 创建 stub 或修复
4. **矛盾**：不同页面间的冲突声明 → 标记并用来源解决
5. **缺失字段**：缺少必填元数据字段的页面 → 补充
6. **过期日期**：有新相关来源但未更新的页面 → 更新

---

## Cross-Linking Rules

- 始终使用 `[[filename-without-extension]]` Obsidian wikilink 语法
- 每个页面必须至少有 2 个出链
- 同时适用时，优先链接到 concept 页面而非 entity 页面
- 除了 Sources 部分，不创建指向 `raw/` 文件的链接

---

## Quality Standards

- **不重复**：一个事实只存在于一个地方，其他页面通过链接引用
- **来源标注**：每个非显而易见的声明都有来源
- **先通俗后术语**：在使用专业术语之前先用通俗语言解释
- **增量式**：stub 页面可以接受，空页面不行
