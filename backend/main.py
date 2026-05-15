
import io
import os
import re

import chardet
import pandas as pd
import PyPDF2
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from transformers import BertForSequenceClassification, BertTokenizer

# -------------------------- 配置 --------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BACKEND_DIR, "bert_algorithm_model")
# 本地无权重时自动使用该中文 BERT（首次会从 Hugging Face 下载）
HF_FALLBACK_MODEL = os.environ.get("BERT_FALLBACK_MODEL", "bert-base-chinese")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_SEQ_LEN = 512
BATCH_RESULT_FILE = "batch_result.csv"
PORT = int(os.environ.get("PORT", "8000"))
# -----------------------------------------------------------

app = FastAPI(
    title="算法备案文本合规检测系统",
    version="1.0",
    description="检测对象为企业算法备案正式材料（非大创申报书等课题文档）。",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _model_dir_has_weights(path: str) -> bool:
    for name in ("pytorch_model.bin", "model.safetensors", "pytorch_model.safetensors"):
        if os.path.isfile(os.path.join(path, name)):
            return True
    return False


def load_tokenizer_and_model():
    print(f"正在加载模型，使用设备：{DEVICE}")
    if _model_dir_has_weights(MODEL_PATH):
        tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
        model = BertForSequenceClassification.from_pretrained(MODEL_PATH).to(DEVICE)
    else:
        print(
            f"未在 {MODEL_PATH} 发现模型权重文件，"
            f"将使用 Hugging Face 模型「{HF_FALLBACK_MODEL}」并初始化二分类头（演示/开发用，首次需联网下载）"
        )
        tokenizer = BertTokenizer.from_pretrained(HF_FALLBACK_MODEL)
        model = BertForSequenceClassification.from_pretrained(
            HF_FALLBACK_MODEL, num_labels=2, ignore_mismatched_sizes=True
        ).to(DEVICE)
    model.eval()
    print("模型加载完成！")
    return tokenizer, model


tokenizer, model = load_tokenizer_and_model()

COMPLIANCE_RULES = {
    "完整性": "算法备案文件需包含算法基本信息、应用场景、数据来源、风险防控措施",
    "准确性": "备案信息需与实际算法一致，无虚假、简略表述",
    "一致性": "备案文本内术语、逻辑一致，与国家政策条款无冲突",
    "合规性": "符合《算法推荐管理规定》《数据安全法》《个人信息保护法》",
}


def preprocess_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？：；""''()（）【】]', "", text
    )
    return text[: MAX_SEQ_LEN - 2]


def pdf_bytes_to_text(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return preprocess_text("".join(parts))


def txt_bytes_to_text(data: bytes) -> str:
    enc = chardet.detect(data).get("encoding") or "utf-8"
    text = data.decode(enc, errors="ignore")
    return preprocess_text(text)


def csv_bytes_to_dataframe(data: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(data), encoding="utf-8")
    if "content" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="CSV文件必须包含「content」列（算法备案文本内容）",
        )
    df["content"] = df["content"].astype(str).apply(preprocess_text)
    return df


def predict_single_text(text: str) -> dict:
    if not text or len(text) < 10:
        return {
            "score": 0.0,
            "result": "无效文本",
            "risk": "文本过短，无法检测",
            "rules": [],
        }
    inputs = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=MAX_SEQ_LEN,
        return_tensors="pt",
    ).to(DEVICE)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        prob = torch.softmax(logits, dim=1).cpu().numpy()[0]
        pred_label = int(torch.argmax(logits, dim=1).cpu().numpy()[0])
    compliance_score = (
        round(float(prob[1]) * 100, 2)
        if pred_label == 1
        else round(float(prob[0]) * 100, 2)
    )
    result = "合规" if pred_label == 1 else "不合规"
    risk_points = []
    match_rules = []
    if pred_label == 0:
        if not re.search(r"数据来源|训练数据", text):
            risk_points.append("未提及算法数据来源，违反「完整性」要求")
            match_rules.append(COMPLIANCE_RULES["完整性"])
        if not re.search(r"风险防控|安全措施", text):
            risk_points.append("未说明风险防控措施，违反「完整性」要求")
            match_rules.append(COMPLIANCE_RULES["完整性"])
        if re.search(r"模糊|暂未|不详", text):
            risk_points.append("备案信息存在简略/模糊表述，违反「准确性」要求")
            match_rules.append(COMPLIANCE_RULES["准确性"])
        if not risk_points:
            risk_points.append("模型判断为不合规，请对照备案要求与法规进行全文复核")
            match_rules.append(COMPLIANCE_RULES["合规性"])
    else:
        risk_points.append("无明显风险点")
        match_rules = list(COMPLIANCE_RULES.values())
    return {
        "score": compliance_score,
        "result": result,
        "risk": "；".join(risk_points),
        "rules": match_rules,
    }


@app.post("/api/predict/single", summary="单文本合规检测")
async def predict_single(text: str = Form(...)):
    cleaned = preprocess_text(text)
    result = predict_single_text(cleaned)
    return {"code": 200, "msg": "检测成功", "data": result}


@app.post("/api/predict/batch", summary="批量文件合规检测（csv/txt/pdf）")
async def predict_batch(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="仅支持csv/txt/pdf格式文件")
    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取上传文件失败：{e}") from e

    try:
        if name.endswith(".csv"):
            df = csv_bytes_to_dataframe(raw)
            df["检测结果"] = df["content"].apply(
                lambda x: predict_single_text(x)["result"]
            )
            df["合规评分"] = df["content"].apply(
                lambda x: predict_single_text(x)["score"]
            )
            df["风险点"] = df["content"].apply(lambda x: predict_single_text(x)["risk"])
            save_path = os.path.join(BACKEND_DIR, BATCH_RESULT_FILE)
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
            return {
                "code": 200,
                "msg": "批量检测成功",
                "data": {
                    "file_path": BATCH_RESULT_FILE,
                    "total": len(df),
                    "compliance_num": int((df["检测结果"] == "合规").sum()),
                    "non_compliance_num": int((df["检测结果"] == "不合规").sum()),
                },
            }
        if name.endswith(".txt"):
            text = txt_bytes_to_text(raw)
            result = predict_single_text(text)
            return {"code": 200, "msg": "检测成功", "data": result}
        text = pdf_bytes_to_text(raw)
        result = predict_single_text(text)
        return {"code": 200, "msg": "检测成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败：{str(e)}") from e


@app.get("/api/health", summary="系统状态检测")
async def health_check():
    return {
        "code": 200,
        "msg": "系统运行正常",
        "status": "ok",
        "model": "BERT算法备案合规检测模型",
        "device": DEVICE,
    }


@app.get("/health", summary="系统状态（兼容旧前端路径）")
async def health_alias():
    return await health_check()


@app.get("/api/download/batch", summary="下载最近一次批量CSV检测结果")
async def download_batch_result():
    path = os.path.join(BACKEND_DIR, BATCH_RESULT_FILE)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="暂无批量检测结果文件，请先上传CSV检测")
    return FileResponse(
        path,
        filename=BATCH_RESULT_FILE,
        media_type="text/csv; charset=utf-8",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        workers=1,
    )
