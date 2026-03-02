import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

class NeuMF(nn.Module):
    """
    神经矩阵分解 (Neural Matrix Factorization, NeuMF) 模型实现
    内核融合了广义矩阵分解 (GMF) 与多层感知机 (MLP) 双独立通道。
    """
    def __init__(self, num_users: int, num_movies: int, latent_dim: int = 64):
        super(NeuMF, self).__init__()
        
        # ==========================================
        # 1. 广义矩阵分解 (GMF) 路径的独立 Embedding
        # ==========================================
        self.embedding_user_mf = nn.Embedding(num_embeddings=num_users, embedding_dim=latent_dim)
        self.embedding_movie_mf = nn.Embedding(num_embeddings=num_movies, embedding_dim=latent_dim)
        
        # ==========================================
        # 2. 多层感知机 (MLP) 路径的独立 Embedding
        # ==========================================
        self.embedding_user_mlp = nn.Embedding(num_embeddings=num_users, embedding_dim=latent_dim)
        self.embedding_movie_mlp = nn.Embedding(num_embeddings=num_movies, embedding_dim=latent_dim)
        
        # MLP 塔式网络: 接收拼接后的双重 Embedding 输入 (latent_dim * 2)
        # 隐层神经元逐渐减半, 构建强大的非线性特征交叉能力
        self.mlp_layers = nn.Sequential(
            nn.Linear(latent_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU()
        )
        
        # ==========================================
        # 3. 神经融合层 (NeuMF Layer)
        # ==========================================
        # GMF 的输出维度是 latent_dim (64)
        # MLP 的输出维度是 16
        # 拼接后输入维度为 64 + 16 = 80
        self.fusion_layer = nn.Linear(latent_dim + 16, 1)
        self.sigmoid = nn.Sigmoid()
        
        self._init_weights()

    def _init_weights(self):
        """Embedding 权重截断正态或正态分布初始化"""
        nn.init.normal_(self.embedding_user_mf.weight, std=0.01)
        nn.init.normal_(self.embedding_movie_mf.weight, std=0.01)
        nn.init.normal_(self.embedding_user_mlp.weight, std=0.01)
        nn.init.normal_(self.embedding_movie_mlp.weight, std=0.01)

    def forward(self, user_indices: torch.Tensor, movie_indices: torch.Tensor) -> torch.Tensor:
        """
        前向传播计算逻辑
        :param user_indices: Batch 维度的用户索引 Tensor
        :param movie_indices: Batch 维度的电影索引 Tensor
        :return: 区间 (0,1) 的点击/交互概率 Tensor
        """
        # --- GMF Path ---
        user_embedding_mf = self.embedding_user_mf(user_indices)
        movie_embedding_mf = self.embedding_movie_mf(movie_indices)
        # 元素级乘积 (Element-wise product)
        mf_vector = torch.mul(user_embedding_mf, movie_embedding_mf) 
        
        # --- MLP Path ---
        user_embedding_mlp = self.embedding_user_mlp(user_indices)
        movie_embedding_mlp = self.embedding_movie_mlp(movie_indices)
        # 将用户和电影的 Embedding 拼接 (Concatenation)
        mlp_vector = torch.cat([user_embedding_mlp, movie_embedding_mlp], dim=-1)
        # 依次穿过深度塔式网络
        mlp_vector = self.mlp_layers(mlp_vector)
        
        # --- Fusion Path ---
        # 结合双路输出
        fusion_vector = torch.cat([mf_vector, mlp_vector], dim=-1)
        prediction = self.fusion_layer(fusion_vector)
        
        # 应用 Sigmoid 激活产出最终打分
        return self.sigmoid(prediction).squeeze(-1)


def get_optimizer(model: NeuMF, lr: float = 1e-3, weight_decay: float = 1e-4) -> optim.Optimizer:
    """
    创建带有特定部分 L2 正则化的 Adam 优化器。
    工程约束: 仅在 MLP 的 Embedding 和权重上应用轻量级的 L2 正则化。
    """
    mlp_params = []
    mf_params = []
    
    # 按照命名空间拆分参数组
    for name, param in model.named_parameters():
        if 'mlp' in name:
            mlp_params.append(param)
        else:
            mf_params.append(param)
            
    optimizer = optim.Adam([
        {'params': mf_params, 'weight_decay': 0.0},
        {'params': mlp_params, 'weight_decay': weight_decay}
    ], lr=lr)
    
    return optimizer


def train_one_epoch(model: nn.Module, data_loader: DataLoader, 
                    optimizer: optim.Optimizer, criterion: nn.Module, 
                    device: torch.device) -> float:
    """
    控制完成模型单次 Epoch 的标准训练循环
    :return: 批次的均摊损失 Avg Loss
    """
    model.train()
    total_loss = 0.0
    
    for batch_idx, (users, movies, labels) in enumerate(data_loader):
        # 1. 数据转移至加速器 (GPU/CPU)
        users = users.to(device)
        movies = movies.to(device)
        labels = labels.to(device)
        
        # 2. 前向传播
        predictions = model(users, movies)
        
        # 3. 计算损失
        loss = criterion(predictions, labels)
        
        # 4. 优化解算：梯度清零 -> 反向传播 -> 权值更新
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
    avg_loss = total_loss / len(data_loader)
    return avg_loss

if __name__ == '__main__':
    # 简单实例化调试
    dummy_model = NeuMF(num_users=1000, num_movies=1000)
    print("PyTorch NeuMF Init Success.")
