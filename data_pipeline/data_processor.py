import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
import random
import os

class MovieLensProcessor:
    """
    数据特征管道：负责 MovieLens 原始数据的清洗、二值化及基于时间序列的留一法切分。
    """
    def __init__(self, ratings_path: str):
        self.ratings_path = ratings_path
        self.user_mapping = {}
        self.movie_mapping = {}
        self.user_interacted_movies = {}
        self.all_movies_list = []
        
    def process(self):
        # 1. 兼容加载逻辑 (支持 ML-1M 的 :: 分隔符与标准 csv)
        if not os.path.exists(self.ratings_path):
            # To allow import without local file
            print(f"Warning: Data file {self.ratings_path} not found. Running in dry-run mode.")
            return None, None, None

        with open(self.ratings_path, 'r') as f:
            first_line = f.readline()
            
        if '::' in first_line:
            df = pd.read_csv(self.ratings_path, sep='::', engine='python', 
                             names=['user_id', 'movie_id', 'rating', 'timestamp'])
        else:
            df = pd.read_csv(self.ratings_path, names=['user_id', 'movie_id', 'rating', 'timestamp'], 
                             engine='python', sep=',')
        
        # 2. 隐式反馈二值化 (全部视为有交互的 1 正样本)
        df['implicit_rating'] = 1.0  
        
        # 3. 特征映射: 离散 ID 转为从 0 开始的连续整数 (严格适配 PyTorch Embedding)
        user_ids = df['user_id'].unique()
        movie_ids = df['movie_id'].unique()
        self.user_mapping = {uid: idx for idx, uid in enumerate(user_ids)}
        self.movie_mapping = {mid: idx for idx, mid in enumerate(movie_ids)}
        
        df['user_idx'] = df['user_id'].map(self.user_mapping)
        df['movie_idx'] = df['movie_id'].map(self.movie_mapping)
        
        self.all_movies_list = list(self.movie_mapping.values())
        
        # 构建负采样查找字典
        for user, group in df.groupby('user_idx'):
            self.user_interacted_movies[user] = set(group['movie_idx'].tolist())
            
        # 4. 留一法划分验证与测试 (严格按时间戳排序，杜绝未来数据穿越 Leakage)
        df = df.sort_values(by=['user_idx', 'timestamp'])
        df['rank_latest'] = df.groupby('user_idx')['timestamp'].rank(method='first', ascending=False)
        
        # 约定：最后一次交互为 Test，倒数第二次为 Valid，其余为 Train
        train_df = df[df['rank_latest'] > 2].copy()
        valid_df = df[df['rank_latest'] == 2].copy()
        test_df = df[df['rank_latest'] == 1].copy()
        
        print(f"[Feature Pipeline] Mapped {len(user_ids)} Users, {len(movie_ids)} Movies.")
        print(f"[Feature Pipeline] Plit: Train {len(train_df)}, Valid {len(valid_df)}, Test {len(test_df)}")
        return train_df, valid_df, test_df


class MovieLensDataset(Dataset):
    """
    自定义 PyTorch Dataset：在训练集 getitem 时进行 OOT (On-the-fly) 动态负采样，严格保证 1:4 比例
    """
    def __init__(self, df: pd.DataFrame, user_interacted_movies: dict, all_movies_list: list, 
                 num_negatives: int = 4, is_training: bool = True):
        self.users = df['user_idx'].values
        self.movies = df['movie_idx'].values
        self.labels = df['implicit_rating'].values
        
        self.user_interacted_movies = user_interacted_movies
        self.all_movies_list = all_movies_list
        self.num_negatives = num_negatives
        self.is_training = is_training
        
    def __len__(self):
        # 训练过程：1个正样本搭配4个负样本，样本池放大了 5 倍
        if self.is_training:
            return len(self.users) * (1 + self.num_negatives)
        return len(self.users)
        
    def __getitem__(self, idx):
        if not self.is_training:
            # 验证与测试阶段不作随机负采样返回（或者交给专门的 Evaluator 单独处理全体未交互评估）
            return torch.tensor(self.users[idx], dtype=torch.long), \
                   torch.tensor(self.movies[idx], dtype=torch.long), \
                   torch.tensor(self.labels[idx], dtype=torch.float32)
                   
        # 训练阶段动态采样逻辑
        pos_idx = idx // (1 + self.num_negatives)
        is_pos = (idx % (1 + self.num_negatives)) == 0
        
        user = self.users[pos_idx]
        
        if is_pos:
            return torch.tensor(user, dtype=torch.long), \
                   torch.tensor(self.movies[pos_idx], dtype=torch.long), \
                   torch.tensor(1.0, dtype=torch.float32)
        else:
            # 随机抽样池中抽取负样本
            neg_candidate = random.choice(self.all_movies_list)
            # 确保避开此用户交互过的正样本
            while neg_candidate in self.user_interacted_movies[user]:
                neg_candidate = random.choice(self.all_movies_list)
                
            return torch.tensor(user, dtype=torch.long), \
                   torch.tensor(neg_candidate, dtype=torch.long), \
                   torch.tensor(0.0, dtype=torch.float32)

if __name__ == '__main__':
    # 模拟入口
    processor = MovieLensProcessor('../data/ratings.csv')
    train_df, valid_df, test_df = processor.process()
    if train_df is not None:
        train_dataset = MovieLensDataset(
            train_df, 
            processor.user_interacted_movies, 
            processor.all_movies_list, 
            num_negatives=4, 
            is_training=True
        )
        # 确保数据集可以被实例化并提取第一项
        u, m, l = train_dataset[0]
        print(f"Sample 0 (Positive): User {u}, Movie {m}, Label {l}")
        u, m, l = train_dataset[1]
        print(f"Sample 1 (Negative): User {u}, Movie {m}, Label {l}")
