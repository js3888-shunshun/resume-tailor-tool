# AI Resume Tailor

根据目标岗位 JD，从个人"经历素材库"中自动挑选并改写最相关的经历，生成一份严格一页的定制简历 PDF（LaTeX）和对应的 cover letter。同时是一个学习 AI agent 概念的项目，核心是 Step 6 的"编译-检查-修正"循环。

> 开发主线见 [`ROADMAP.md`](./ROADMAP.md)。每个阶段都有可验证的 milestone。

## 项目结构

```
job application tool/
├── ROADMAP.md              # 主线控制文件
├── requirements.txt
├── .env.example
└── backend/
    ├── app/
    │   ├── main.py         # FastAPI 入口 (/health, 启动检测)
    │   ├── config.py       # 读取 .env
    │   ├── latex_tools.py  # 检测 tectonic/pdflatex
    │   ├── materials_store.py   # Step 1: 素材库读写校验
    │   └── schemas/        # 全部 Pydantic 模型
    ├── data/
    │   └── materials.sample.json   # 开发用示例素材库
    └── tests/
```

## 环境依赖

- Python 3.11+（已在 3.13 测试）
- Node 18+（前端，M8 才需要）
- LaTeX 引擎（M5 起需要）：推荐 **Tectonic**（单文件，自动下载宏包）
  - `winget install TectonicProject.Tectonic` 或 `scoop install tectonic`
  - 备选 MiKTeX（提供 pdflatex）：https://miktex.org/download

## 快速开始

```powershell
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置 API key（M2 起需要）
Copy-Item .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 3. 启动后端
cd backend
uvicorn app.main:app --reload

# 4. 健康检查
# 浏览器或 curl 访问 http://127.0.0.1:8000/health
```

## 准备素材库

Phase 1 由用户手动整理 `backend/data/materials.json`（schema 见 `backend/app/schemas/materials.py`）。未创建时系统自动回退到 `materials.sample.json`，可先用示例数据跑通流程。

## 运行测试

```powershell
cd backend
pytest
```

## 当前进度

见 `ROADMAP.md` 的"进度日志"。当前：**M1 项目骨架**。
