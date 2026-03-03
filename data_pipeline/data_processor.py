import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from collections import defaultdict
import random
import os
import gc


class MovieLensProcessor:
    """
    数据特征管道：负责 MovieLens 原始数据的清洗、二值化及基于时间序列的留一法切分。
    针对 ML-32M (3200万条) + 16GB RAM 场景，做了严格的内存峰值管控。
    """
    def __init__(self, ratings_path: str):
        self.ratings_path = ratings_path
        self.user_mapping = {}
        self.movie_mapping = {}
        self.user_interacted_movies = {}  # {user_idx: np.array (sorted)}
        self.all_movies_list = []
        
    def process(self):
        # 1. 内存优化的高效加载逻辑
        if not os.path.exists(self.ratings_path):
            print(f"Warning: Data file {self.ratings_path} not found.")
            return None, None, None

        print("[Feature Pipeline] Loading dataset via Pandas with memory optimization...")
        
        dtype_spec = {
            'user_id': np.int32,     
            'movie_id': np.int32,    
            'rating': np.float32,    
            'timestamp': np.int32    
        }
        
        with open(self.ratings_path, 'r') as f:
            first_line = f.readline()
            
        if '::' in first_line:
            df = pd.read_csv(self.ratings_path, sep='::', engine='python', 
                             names=['user_id', 'movie_id', 'rating', 'timestamp'],
                             dtype=dtype_spec)
        else:
            df = pd.read_csv(self.ratings_path, names=['user_id', 'movie_id', 'rating', 'timestamp'], 
                             engine='c', sep=',', header=0, 
                             dtype=dtype_spec)
        
        # 释放不再需要的评分列
        df.drop(columns=['rating'], inplace=True)
        
        # 2. 隐式反馈二值化
        df['implicit_rating'] = np.ones(len(df), dtype=np.float32)
        
        # 3. 特征映射
        print("[Feature Pipeline] Mapping IDs...")
        user_ids = df['user_id'].unique()
        movie_ids = df['movie_id'].unique()
        self.user_mapping = {uid: idx for idx, uid in enumerate(user_ids)}
        self.movie_mapping = {mid: idx for idx, mid in enumerate(movie_ids)}
        
        df['user_idx'] = df['user_id'].map(self.user_mapping).astype(np.int32)
        df['movie_idx'] = df['movie_id'].map(self.movie_mapping).astype(np.int32)
        
        # 清除原始ID列释放内存
        df.drop(columns=['user_id', 'movie_id'], inplace=True)
        gc.collect()
        
        self.all_movies_list = list(self.movie_mapping.values())
        
        # ============================================================
        # 关键调整: 先做时间切分, 释放大 DataFrame 后再构建负采样字典
        # 这样避免 df + dict 同时驻留内存导致 OOM
        # ============================================================
        
        # 4. 留一法划分验证与测试
        print("[Feature Pipeline] Sorting and splitting data temporally (Leave-One-Out)...")
        df.sort_values(by=['user_idx', 'timestamp'], inplace=True)
        df['rank_latest'] = df.groupby('user_idx')['timestamp'].rank(
            method='first', ascending=False
        ).astype(np.int16)
        
        # 释放 timestamp
        df.drop(columns=['timestamp'], inplace=True)
        gc.collect()
        
        train_df = df[df['rank_latest'] > 2].copy()
        valid_df = df[df['rank_latest'] == 2].copy()
        test_df = df[df['rank_latest'] == 1].copy()
        
        num_users = len(user_ids)
        num_movies = len(movie_ids)
        
        print(f"[Feature Pipeline] Mapped {num_users} Users, {num_movies} Movies.")
        print(f"[Feature Pipeline] Split: Train {len(train_df)}, Valid {len(valid_df)}, Test {len(test_df)}")
        
        # 彻底释放原始大表
        del df
        gc.collect()
        
        # 5. 从训练集构建负采样查找字典
        # 使用 numpy 排序数组代替 Python set, 内存效率提升 ~12x
        # Python set: 200K users × ~8KB/set ≈ 1.6GB
        # NumPy int32 array: 200K users × ~640B/arr ≈ 128MB
        print("[Feature Pipeline] Building negative sampling dictionary (numpy sorted arrays)...")
        self._build_interaction_dict(train_df)
        
        return train_df, valid_df, test_df

    def _build_interaction_dict(self, train_df: pd.DataFrame):
        """
        用 numpy 排序数组构建用户交互字典, 内存远小于 Python set。
        查询时使用 np.searchsorted 实现 O(log n) 命中检测。
        """
        # 先按 (user_idx, movie_idx) 排序
        sorted_df = train_df[['user_idx', 'movie_idx']].sort_values(
            by=['user_idx', 'movie_idx']
        )
        
        user_arr = sorted_df['user_idx'].values
        movie_arr = sorted_df['movie_idx'].values
        del sorted_df
        gc.collect()
        
        # 找到每个用户的起止位置, 一次性切割
        change_points = np.where(np.diff(user_arr) != 0)[0] + 1
        starts = np.concatenate([[0], change_points])
        ends = np.concatenate([change_points, [len(user_arr)]])
        user_ids_at_starts = user_arr[starts]
        
        self.user_interacted_movies = {}
        for uid, s, e in zip(user_ids_at_starts, starts, ends):
            self.user_interacted_movies[int(uid)] = movie_arr[s:e].copy()
        
        del user_arr, movie_arr, change_points, starts, ends
        gc.collect()


class MovieLensDataset(Dataset):
    """
    自定义 PyTorch Dataset：在训练集 getitem 时进行 OOT (On-the-fly) 动态负采样，严格保证 1:4 比例。
    使用 np.searchsorted 替代 set.__contains__ 进行快速交互检测。
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
        
    def _is_interacted(self, user: int, movie: int) -> bool:
        """使用 np.searchsorted 在排序数组上做 O(log n) 的交互检测"""
        arr = self.user_interacted_movies.get(user)
        if arr is None:
            return False
        idx = np.searchsorted(arr, movie)
        return idx < len(arr) and arr[idx] == movie
        
    def __len__(self):
        if self.is_training:
            return len(self.users) * (1 + self.num_negatives)
        return len(self.users)
        
    def __getitem__(self, idx):
        if not self.is_training:
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
            # 随机抽样负样本, 使用 searchsorted 快速校验
            neg_candidate = random.choice(self.all_movies_list)
            while self._is_interacted(user, neg_candidate):
                neg_candidate = random.choice(self.all_movies_list)
                
            return torch.tensor(user, dtype=torch.long), \
                   torch.tensor(neg_candidate, dtype=torch.long), \
                   torch.tensor(0.0, dtype=torch.float32)


if __name__ == '__main__':
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
        u, m, l = train_dataset[0]
        print(f"Sample 0 (Positive): User {u}, Movie {m}, Label {l}")
        u, m, l = train_dataset[1]
        print(f"Sample 1 (Negative): User {u}, Movie {m}, Label {l}")
