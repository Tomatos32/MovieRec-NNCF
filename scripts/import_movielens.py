"""
MovieLens 32M -> MySQL 导入脚本
将 data/movies.csv 和 data/ratings.csv 批量写入 movierec_db。

用法:
  pip install pymysql pandas
  python scripts/import_movielens.py

注意: ratings.csv 约 877MB / 3200万行，采用 LOAD DATA LOCAL INFILE 或高速批量写入。
"""

import os
import re
import sys
import csv
import time
import tempfile
import pandas as pd
import pymysql

# ---------- 配置 ----------
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USERNAME', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '123456'),
    'database': os.getenv('MYSQL_DATABASE', 'movierec_db'),
    'charset': 'utf8mb4',
    'local_infile': True,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MOVIES_CSV = os.path.join(DATA_DIR, 'movies.csv')
RATINGS_CSV = os.path.join(DATA_DIR, 'ratings.csv')

# 高速批量插入：每批次行数
BATCH_SIZE = 10_000


def get_connection():
    conn = pymysql.connect(**DB_CONFIG)
    return conn


def extract_year(title: str) -> int:
    match = re.search(r'\((\d{4})\)\s*$', str(title))
    return int(match.group(1)) if match else 0


def import_movies(conn):
    """导入 movies.csv -> movies 表 (约 87,000 部电影)"""
    print(f'\n{"="*50}')
    print(f'[1/3] 导入电影数据: movies.csv')
    print(f'{"="*50}')

    if not os.path.exists(MOVIES_CSV):
        print(f'  ✗ 文件不存在: {MOVIES_CSV}')
        return

    df = pd.read_csv(MOVIES_CSV)
    print(f'  读取到 {len(df):,} 部电影')

    df['release_year'] = df['title'].apply(extract_year)

    cursor = conn.cursor()
    cursor.execute('DELETE FROM movies')
    conn.commit()

    sql = """INSERT INTO movies (id, title, genres, release_year)
             VALUES (%s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE title=VALUES(title), genres=VALUES(genres), release_year=VALUES(release_year)"""

    # 使用 values.tolist() 比 iterrows 快 50 倍
    rows = df[['movieId', 'title', 'genres', 'release_year']].values.tolist()

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        cursor.executemany(sql, batch)
        conn.commit()
        print(f'  进度: {min(i + BATCH_SIZE, len(rows)):,}/{len(rows):,}', end='\r')

    print(f'\n  ✓ 电影导入完成: {len(rows):,} 条')
    cursor.close()


def import_ratings(conn):
    """高速分块导入 ratings.csv -> ratings 表 (约 3200 万行)"""
    print(f'\n{"="*50}')
    print(f'[2/3] 导入评分数据: ratings.csv (~32M 行)')
    print(f'{"="*50}')

    if not os.path.exists(RATINGS_CSV):
        print(f'  ✗ 文件不存在: {RATINGS_CSV}')
        return

    cursor = conn.cursor()

    # 关闭索引检查和唯一性检查，大幅加速批量写入
    cursor.execute('SET unique_checks = 0')
    cursor.execute('SET foreign_key_checks = 0')
    cursor.execute('SET autocommit = 0')

    # 清空旧数据 (TRUNCATE 比 DELETE 快得多)
    cursor.execute('TRUNCATE TABLE ratings')
    conn.commit()

    sql = """INSERT INTO ratings (user_id, movie_id, rating, timestamp)
             VALUES (%s, %s, %s, %s)"""

    total = 0
    start_time = time.time()

    # 用原生 csv.reader 比 pandas 内存开销小，速度也不差
    with open(RATINGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头 userId,movieId,rating,timestamp

        batch = []
        for row in reader:
            # row: [userId, movieId, rating, timestamp]
            batch.append((int(row[0]), int(row[1]), float(row[2]), int(row[3])))

            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                total += len(batch)
                batch.clear()

                # 每 50 万条 commit 一次，平衡速度和安全性
                if total % 500_000 == 0:
                    conn.commit()
                    elapsed = time.time() - start_time
                    speed = total / elapsed
                    print(f'  已写入: {total:>12,} 条 | 速度: {speed:>8,.0f} rows/s | 耗时: {elapsed:>6.1f}s', end='\r')

        # 写入最后一批
        if batch:
            cursor.executemany(sql, batch)
            total += len(batch)

    conn.commit()

    # 恢复检查
    cursor.execute('SET unique_checks = 1')
    cursor.execute('SET foreign_key_checks = 1')
    cursor.execute('SET autocommit = 1')
    conn.commit()

    elapsed = time.time() - start_time
    print(f'\n  ✓ 评分导入完成: {total:,} 条 | 总耗时: {elapsed:.1f}s')
    cursor.close()


def import_users_from_ratings(conn):
    """从 ratings 表中提取去重的 user_id 写入 users 表"""
    print(f'\n{"="*50}')
    print(f'[3/3] 从评分数据同步用户表')
    print(f'{"="*50}')

    cursor = conn.cursor()
    cursor.execute("""
        INSERT IGNORE INTO users (id, username)
        SELECT DISTINCT user_id, CONCAT('user_', user_id)
        FROM ratings
    """)
    affected = cursor.rowcount
    conn.commit()
    print(f'  ✓ 同步了 {affected:,} 个用户')
    cursor.close()


def print_summary(conn):
    """打印导入汇总"""
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM movies')
    movies_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM ratings')
    ratings_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users')
    users_count = cursor.fetchone()[0]

    print(f'\n{"="*50}')
    print(f'导入汇总')
    print(f'{"="*50}')
    print(f'  movies  表: {movies_count:>12,} 条')
    print(f'  ratings 表: {ratings_count:>12,} 条')
    print(f'  users   表: {users_count:>12,} 条')
    cursor.close()


def main():
    print('=' * 50)
    print('MovieLens 32M -> MySQL 数据导入工具')
    print('=' * 50)
    print(f'数据库: {DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}')
    print(f'数据目录: {os.path.abspath(DATA_DIR)}')

    try:
        conn = get_connection()
        print('✓ 数据库连接成功')
    except Exception as e:
        print(f'✗ 数据库连接失败: {e}')
        print(f'  请确认 MySQL 已启动，且 .env 中的连接信息正确')
        sys.exit(1)

    try:
        import_movies(conn)
        import_ratings(conn)
        import_users_from_ratings(conn)
        print_summary(conn)
    finally:
        conn.close()

    print('\n全部导入完成! 现在可以重启 Spring Boot 后端测试推荐功能了。')


if __name__ == '__main__':
    main()
