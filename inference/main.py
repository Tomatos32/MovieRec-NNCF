import torch
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import os
import sys

# 本地环境变量与路径兼容
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from model.neumf import NeuMF
except ImportError:
    pass  # 实际集成部署时处理包路径问题

app = FastAPI(
    title="MovieRec NeuMF Sidecar Inference",
    description="基于 PyTorch 神经矩阵分解模型的极低延迟推理边车",
    version="1.0.0"
)

class PredictRequest(BaseModel):
    user_id: int
    candidate_movie_ids: List[int]
    top_k: int = 10

# 全局变量挂载模型实例与设备状态
model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

@app.on_event("startup")
async def startup_event():
    global model
    print("[Sidecar] Loading NeuMF model weights into eval mode...")
    
    # 模拟从环境变量或相对路径加载 .pth
    model_path = os.getenv("MODEL_PATH", "../model/model.pth")
    num_users = int(os.getenv("NUM_USERS", 6040))
    num_movies = int(os.getenv("NUM_MOVIES", 3952))
    
    # 初始化模型结构
    model = NeuMF(num_users=num_users, num_movies=num_movies)
    
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"[Sidecar] Model loaded successfully from {model_path}.")
    else:
        print("[Sidecar] Warning: model.pth not found. Using randomly initialized weights for debugging.")
        
    model.to(device)
    # 锁定为求值模式，切断 dropout 和 batchnorm 更新
    model.eval()

@app.post("/api/predict")
async def predict(request: PredictRequest) -> Dict:
    global model
    
    user_id = request.user_id
    movie_ids = request.candidate_movie_ids
    
    if not movie_ids:
        return {"data": []}
        
    # 构建 batch tensor 以利用 GPU 或 CPU 的矢量化加速
    users_tensor = torch.full((len(movie_ids),), user_id, dtype=torch.long).to(device)
    movies_tensor = torch.tensor(movie_ids, dtype=torch.long).to(device)
    
    # 极速非梯度推理 (避免内存泄漏与反代开销计算)
    with torch.no_grad():
        scores = model(users_tensor, movies_tensor)
        
    # 张量下放到 CPU 并转置列表
    scores_list = scores.cpu().numpy().tolist()
    
    # 将候选电影与预测分数配对，并按降序排列
    results = [{"movie_id": mid, "score": score} for mid, score in zip(movie_ids, scores_list)]
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # 若要求返回 Top-K
    return {"data": results[:request.top_k]}

if __name__ == "__main__":
    import uvicorn
    # 建议部署在与主业务相同的 Pod 或同一物理机内部 (127.0.0.1) 消除网络传输损耗
    uvicorn.run("main:app", host="127.0.0.1", port=8000, workers=1)
