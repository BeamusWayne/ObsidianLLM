# ObsidianLLM

**作者 / Author:** Beamus Wayne

[English](README.en.md) | 中文

一个本地知识库工具——剪藏网页文章，用 LLM 处理后整理成可浏览的 Wiki，全程运行在你自己的机器上。

## 功能

- **剪藏** — 粘贴 URL，自动抓取并提取干净的 Markdown
- **入库** — LLM 读取文章，将结构化 Wiki 页面写入 `wiki/`
- **浏览** — 在浏览器中查阅 Wiki 条目和实体关系图

### 特性

- 多后端 LLM 链 — Ollama（本地）、Claude API、任意 OpenAI 兼容接口
- 命名预设支持：`["preset:qwen-plus", "preset:glm-5", "ollama"]`，余额不足时自动切换
- 并行 Ingest 工作线程，按文件大小路由到不同模型
- 手动处理入口：单文件悬浮按钮、批量勾选、一键处理全部待处理文件
- 图片视觉理解：含图文章由视觉模型自动描述图片内容
- Wiki 图谱视图 — 实体与关系以力导向图呈现
- 深色 / 浅色 / 跟随系统 三种主题

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python · FastAPI · Uvicorn |
| 抓取 | Trafilatura |
| 前端 | Vue 3 · Vite |
| LLM | Ollama / Anthropic Claude / OpenAI 兼容接口 |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- 至少一个 LLM 后端：
  - 本地运行 [Ollama](https://ollama.com)（`ollama serve`），**或**
  - Claude API Key，**或**
  - 任意 OpenAI 兼容接口（DashScope、OpenRouter 等）

### 安装

```bash
git clone https://github.com/BeamusWayne/ObsidianLLM.git
cd ObsidianLLM

# Python 依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置
cp settings.json.example settings.json
# 编辑 settings.json，填写后端和 API Key
```

### 启动

```bash
bash start.sh
# 打开 http://localhost:8000
```

`start.sh` 先构建前端，再启动服务器。后续运行若前端无变化会跳过 npm install。

## 配置说明

将 `settings.json.example` 复制为 `settings.json` 并按需修改：

```json
{
  "mode": "ollama",
  "fallback_chain": ["ollama"],
  "ollama": {
    "base_url": "http://localhost:11434",
    "text_model": "qwen3.5:9b",
    "vision_model": "qwen3-vl:8b"
  },
  "claude": {
    "api_key": "sk-ant-...",
    "text_model": "claude-sonnet-4-6"
  },
  "custom": {
    "base_url": "https://api.example.com/v1",
    "api_key": "sk-...",
    "text_model": "your-model"
  },
  "custom_presets": [
    {
      "name": "qwen-plus",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key": "sk-...",
      "text_model": "qwen-plus"
    }
  ],
  "parallel": {
    "enabled": true,
    "workers": 3,
    "size_threshold_chars": 3000,
    "small_backend": "ollama",
    "large_backend": "custom"
  }
}
```

### 推理顺序（Fallback Chain）

系统按顺序尝试各后端，遇到余额不足或配额错误时自动切换到下一个。可以在链中直接引用命名预设：

```json
"fallback_chain": ["preset:qwen-plus", "preset:glm-5", "ollama"]
```

预设在 `custom_presets` 中定义，每个预设都是独立的 OpenAI 兼容接口配置。

## 项目结构

```
ObsidianLLM/
├── server.py           # FastAPI 应用及路由
├── start.sh            # 构建前端并启动服务
├── scripts/
│   ├── clip.py         # URL 抓取与 Markdown 提取
│   ├── ingest.py       # LLM 处理与 Wiki 写入
│   ├── llm.py          # 多后端 LLM 封装
│   └── query.py        # Wiki 查询
├── frontend/
│   └── src/views/
│       ├── ClipperView.vue   # 剪藏与入库面板
│       ├── WikiView.vue      # Wiki 浏览
│       ├── GraphView.vue     # 实体图谱
│       └── SettingsView.vue  # 后端配置
├── raw/                # 剪藏的文章和图片（已 gitignore）
├── wiki/               # 生成的 Wiki 页面（已 gitignore）
└── settings.json       # 你的配置文件（已 gitignore）
```

## License

MIT
