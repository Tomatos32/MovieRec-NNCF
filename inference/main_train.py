import os
import sys
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.data_processor import MovieLensProcessor, MovieLensDataset
from model.neumf import NeuMF, get_optimizer, train_one_epoch

def main():
    # 1. 检查数据路径
    data_path = '../data/ratings.csv'
    if not os.path.exists(data_path):
        print(f"Error: 找不到数据文件 {data_path}")
        print("请检查 ML-32M 数据集是否已正确解压到 data 目录。")
        return

    # 2. 运行数据处理管道
    print(">>> 1. 启动数据预处理管道 (ML-32M)...")
    processor = MovieLensProcessor(data_path)
    train_df, valid_df, test_df = processor.process()
    
    if train_df is None:
        return
        
    num_users = len(processor.user_mapping)
    num_movies = len(processor.movie_mapping)
    print(f"    - 总用户数: {num_users}, 总电影数: {num_movies}")

    # 3. 构建 PyTorch Dataset 与 DataLoader
    print("\n>>> 2. 构建 Dataset 与动态负采样 DataLoader...")
    train_dataset = MovieLensDataset(
        train_df, 
        processor.user_interacted_movies, 
        processor.all_movies_list, 
        num_negatives=4, 
        is_training=True
    )
    
    # 根据电脑内存和显存调整 batch_size 和 num_workers
    # 32M 数据集非常大，batch_size 建议设大一些
    batch_size = 4096 
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=0, # Windows 下有时候多进程 dataloader 容易卡死，设为 0 求稳
        pin_memory=True
    )

    # 4. 初始化模型
    print(f"\n>>> 3. 初始化 NeuMF 模型 (Latent Dim = 64)...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"    - 使用计算设备: {device}")
    
    model = NeuMF(num_users=num_users, num_movies=num_movies, latent_dim=64)
    model.to(device)

    # 5. 配置优化器与损失函数
    print("\n>>> 4. 配置优化器 (带选择性 L2 正则化) & BCELoss...")
    # 根据 README 规范，仅对 MLP 通道执行 weight_decay
    optimizer = get_optimizer(model, lr=1e-3, weight_decay=1e-4)
    criterion = nn.BCELoss()

    # 6. 开始训练
    epochs = 3 # 演示时跑较少 epoch，视效果可增加
    print(f"\n>>> 5. 开始训练 (Total Epochs: {epochs})...")
    
    # 确保保存模型的目录存在
    os.makedirs('../model', exist_ok=True)
    
    for epoch in range(1, epochs + 1):
        print(f"\n--- Epoch {epoch}/{epochs} ---")
        avg_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        print(f"    - Epoch {epoch} 执行完毕, 平均损失 (Avg Loss): {avg_loss:.4f}")
        
    # 7. 保存权重
    save_path = '../model/model.pth'
    torch.save(model.state_dict(), save_path)
    print(f"\n>>> 6. 训练完成！模型已持久化保存至: {save_path}")
    
    print("\n请记下以下环境参数，用于后续推理边车的环境变量配置：")
    print("=========================================")
    print(f"export NUM_USERS={num_users}")
    print(f"export NUM_MOVIES={num_movies}")
    print(f"export MODEL_PATH=\"{save_path}\"")
    print("=========================================")

if __name__ == '__main__':
    main()
