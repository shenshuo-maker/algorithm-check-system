# 算法备案文本智能合规检测系统

## 项目简介

本项目基于深度学习 BERT 模型，对企业向监管部门提交的**算法备案文件**（备案说明、主体信息、算法机制说明等正式材料）做智能合规性辅助检测，支持单段文本与批量文件（CSV / TXT / PDF），并结合法规要求给出风险提示与条款依据说明。

### 检测对象说明（请勿混淆）

- **应当上传 / 粘贴的内容**：企业算法备案相关正式文本或从这些材料导出的 PDF、TXT，以及按行组织的 CSV（`content` 列为单条备案文本）。
- **不是本系统的检测对象**：大创项目申请书、课程作业、一般论文等——这类文件仅用于说明「项目做什么」，与备案合规字段、表述习惯不同，**不应**当作企业备案文件来测；若误用，模型与规则提示的参考价值会明显下降。

## 功能模块

1. **单文本检测**：粘贴算法备案文本，返回合规评分、风险点及条款依据提示  
2. **批量文件检测**：支持上传 `csv` / `txt` / `pdf`，CSV 批量生成统计并可下载结果  
3. **系统状态**：展示后端服务与运行设备（CPU/CUDA）

## 技术栈

- **前端**：Vue 3（本地 `frontend/lib/vue.global.prod.js`）+ 原生 CSS  
- **后端**：FastAPI + Uvicorn  
- **模型**：`transformers` 的 `BertForSequenceClassification`（本地 `backend/bert_algorithm_model` 含权重时优先加载；否则自动从 Hugging Face 拉取备用中文 BERT 并初始化二分类头）

## 快速开始

### 端口说明

- **后端**：`http://127.0.0.1:8000`（见 `backend/main.py`，可用环境变量 `PORT` 修改）  
- **前端静态页**：`http://localhost:5500/index.html`（与后端端口错开，避免冲突）

### 1. 安装并启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

首次运行若 `bert_algorithm_model` 目录下没有 `pytorch_model.bin` / `model.safetensors` 等权重文件，会自动使用环境变量 `BERT_FALLBACK_MODEL` 指定的模型（默认 `bert-base-chinese`），**需要联网下载**（体积约数百 MB，视模型而定）。

仅想验证前后端与接口是否打通时，可临时使用极小随机模型（**不适用于真实中文合规判断**）：

```text
# Windows CMD
set BERT_FALLBACK_MODEL=hf-internal-testing/tiny-random-bert
python main.py
```

### 2. 启动前端

另开终端：

```bash
cd frontend
python -m http.server 5500
```

浏览器打开：`http://localhost:5500/index.html`

### 3. Windows 一键启动

双击项目根目录 `start_system.bat`（会安装依赖、启动后端 8000、前端 5500 并尝试打开浏览器）。

## CSV 格式

批量检测用的 CSV **必须包含列名** `content`，每行一条**企业算法备案相关**文本（例如从各家企业备案说明中摘出的一段或一条记录）。

## 接入真实训练模型

将训练好的 Hugging Face 格式权重放入 `backend/bert_algorithm_model/`（与现有 `config.json`、词表等一致），确保目录中存在 `pytorch_model.bin` 或 `model.safetensors` 之一，重启后端即可优先加载本地模型。
