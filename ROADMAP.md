# AI Resume Tailor — 开发路线图 (ROADMAP)

> 这是本项目的**主线控制文件 (single source of truth)**。
> 每次开发前先读它确认当前所在阶段，开发后更新对应复选框与"进度日志"。
> 任何偏离主线的想法先记到 "Backlog / 未来扩展"，不要直接插入当前里程碑。

**项目一句话定义：** 输入目标岗位 JD + 用户素材库 → 自动挑选/改写最相关经历 → 产出严格一页的定制简历 PDF 和对应 cover letter；同时作为学习 AI agent 概念的载体（核心是 Step 6 的"编译-检查-修正"循环）。

**Phase 1 (MVP) 边界：**
- ✅ 做：JD 分析、经历筛选、内容改写、LaTeX 渲染、一页编译循环、cover letter。
- ❌ 不做：LinkedIn cold message、公司信息搜索、embedding 检索、上传简历自动拆解。
  （这些只在数据结构/代码接口上预留扩展点。）

---

## 总体原则（每个里程碑都要遵守）

1. 每个 pipeline step = 独立模块/函数，输入输出严格用 Pydantic schema，可单独测试。
2. 所有 LLM 调用集中在 `llm` 模块；prompt 模板单独存放为文件/常量。
3. "打分函数""检索"等易替换部分要抽成单独函数，方便日后换成 embedding。
4. 变量名/函数名一律英文；注释可中英混合。
5. 每完成一个里程碑，跑通它的"验收标准"才算 done，并在本文件打勾 + 写进度日志。

---

## 阶段与里程碑

### M1 — 项目骨架 + Schema + 示例数据  ⬅️ 当前阶段
**目标：** 搭好可运行的后端骨架，定义全部 Pydantic 模型，准备示例素材库。
- [ ] 项目目录结构 + git 初始化 + `.gitignore` + `.env.example`
- [ ] `requirements.txt`（fastapi, uvicorn, anthropic, pydantic, jinja2, pypdf, pytest 等）
- [ ] 全部 schema 的 Pydantic 模型：materials / jd_profile / selection
- [ ] 一份合法的示例 `materials.sample.json`（用于全程开发测试）
- [ ] FastAPI app 骨架 + `GET /health` + 启动时检测 pdflatex/tectonic 并打印提示
- [ ] `config.py` 读取 `.env`（API key、模型名、路径）
- [ ] 初版 `README.md`
- **验收标准：** `uvicorn` 能启动，`GET /health` 返回 200；`python -c "load + validate materials.sample.json"` 通过 schema 校验；pytest 至少 1 个 schema 测试通过。

### M2 — JD 分析模块 (Step 2)
**目标：** JD 原文 → 结构化 JD 画像。
- [ ] `llm/client.py`：封装 Anthropic 调用，支持 JSON/structured output + 重试
- [ ] prompt 模板：约束只输出 JSON、category 枚举固定 `[AI,DS,DE,MLE,SDE]`
- [ ] `pipeline/step2_jd_analysis.py`：返回 `JDProfile`
- [ ] `POST /jd/analyze` 接口
- **验收标准：** 给一段真实 JD，返回符合 `JDProfile` schema 的 JSON；category 落在枚举内；无 key 时给清晰报错。

### M3 — 经历匹配与筛选模块 (Step 3)
**目标：** JD 画像 + 素材库 → 初步筛选结果（未改写）。
- [ ] category 交集过滤出候选池
- [ ] `scoring.py`：独立打分函数（关键词重合度），**可替换接口**
- [ ] 按 分数+priority 排序，控制每段经历 bullet 数（可传 `target_bullet_count`）
- [ ] 输出 `SelectionResult`（pre-rewrite）
- **验收标准：** 纯函数，无需 LLM 即可单测；给定 mock JD 画像能稳定选出预期 bullet；打分函数有独立单测。

### M4 — 内容改写模块 (Step 4)
**目标：** 选中 bullets + JD 画像 → 改写后结果（带 matched_keywords）。
- [ ] 批量打包 bullets 一次 LLM 调用，返回 JSON 数组
- [ ] prompt 约束：不编造、用 JD 关键词、长度相近、标注命中关键词
- [ ] 输出符合"经历筛选与改写结果 Schema"
- **验收标准：** 改写结果长度与原文相近；`matched_keywords` 只含确实出现的关键词；schema 校验通过。

### M5 — LaTeX 模板 + 渲染模块 (Step 5)
**目标：** 改写结果 → `.tex` 文件（先不管页数）。
- [ ] `resume.tex.j2` 模板（基于用户现有简历样式）
- [ ] Jinja2 环境 + 自定义 LaTeX 转义过滤器（`& % _ # $` 等）
- [ ] 关键词高亮：preamble 定义 `\hlkw`，渲染时包裹 matched_keywords
- [ ] 输出 `.tex` 到临时目录
- **验收标准：** 能渲染出合法 `.tex`；含特殊字符的 bullet 不破坏编译；若已装 latex 能生成 PDF。
- **⚠️ 依赖：** 需要安装 tectonic（推荐，单文件免装 TeX 发行版）或 pdflatex；需要用户提供现有简历 `.tex` 作为模板蓝本。

### M6 — 编译 + 一页校验循环 (Step 6, 核心 agent 循环)
**目标：** `.tex` → 编译 → 检查页数 → 超长则压缩重试，状态机/循环实现。
- [ ] 编译封装（捕获日志/错误）
- [ ] pypdf 读页数
- [ ] 超过 1 页：挑最长/最低 priority 的 bullet → LLM 压缩 → 重渲染重编译
- [ ] 最大迭代次数（默认 5），超限返回当前最优 + 提示
- [ ] 编译失败：捕获日志，定位疑似转义问题，详细记录
- [ ] 每次迭代输入/输出/状态变化都有结构化日志
- **验收标准：** 故意塞超长内容能在 ≤5 次迭代内压到一页或明确报告失败；全过程有可读日志；编译错误能定位到具体内容。

### M7 — Cover Letter 生成 (Step 7)
**目标：** JD 画像 + 改写经历摘要 + 基本信息 → cover letter PDF。
- [ ] LLM 生成正文；预留 `company_context` 字段（Phase 2 用）
- [ ] 独立简单 LaTeX 模板 + 同样的转义
- [ ] 渲染编译成 PDF
- **验收标准：** 生成结构合理的 cover letter PDF；特殊字符不破坏编译。

### M8 — 前端整合 + 串联 `/generate`
**目标：** 打通端到端流程并最简前端展示。
- [ ] `POST /generate`：串联 Step 2-7，返回两个 PDF 链接 + 中间结果
- [ ] `GET /materials` / `PUT /materials`
- [ ] 前端（Vite React 最简版）：JD 输入框 → 展示 JD 画像/筛选结果 → 下载 PDF
- **验收标准：** 从前端粘贴 JD，点一次按钮，能看到中间结果并下载两个 PDF。

---

## 进度日志 (Changelog)
> 倒序记录。格式：`日期 — 里程碑 — 做了什么 / 验收结果`
- 2026-06-14 — M1 — 启动项目，创建 ROADMAP。环境已确认（Python3.13/Node24/Git ok；缺 latex 与 API key）。

## Backlog / 未来扩展（Phase 2+，先别做）
- LinkedIn cold message 生成
- 公司信息搜索注入 cover letter（`company_context`）
- embedding 语义检索替换关键词打分（替换 `scoring.py`）
- 上传现有简历 → LLM 自动拆解填充素材库
- 一页但内容偏少时自动补充内容（Step 6.4 的 TODO）

## 当前阻塞 / 待用户提供
- [ ] 设置 `ANTHROPIC_API_KEY`（M2 起需要）
- [ ] 安装 tectonic 或 pdflatex（M5 起需要）
- [ ] 提供现有简历的 `.tex` 源文件作为简历模板蓝本（M5 需要）
