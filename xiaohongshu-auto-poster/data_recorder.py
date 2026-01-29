"""
数据记录模块
记录每次发帖的元数据和后续互动数据，用于分析和优化
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


class DataRecorder:
    """数据记录器 - 使用 SQLite 存储发帖和互动数据"""
    
    def __init__(self, db_path: str = "posts_data.db"):
        """
        初始化数据记录器
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 发帖记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    level TEXT,
                    prompt_version TEXT,
                    title TEXT,
                    tags TEXT,  -- JSON 格式存储标签列表
                    image_suggestion TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    post_url TEXT,  -- 小红书帖子链接（如果有）
                    UNIQUE(word, level, prompt_version, created_at)
                )
            """)
            
            # 互动数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    likes INTEGER DEFAULT 0,
                    favorites INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    UNIQUE(post_id)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式的行
        try:
            yield conn
        finally:
            conn.close()
    
    def record_post(
        self,
        word: str,
        level: str,
        prompt_version: str,
        title: str,
        tags: List[str],
        image_suggestion: Optional[str] = None,
        post_url: Optional[str] = None,
    ) -> int:
        """
        记录一次发帖
        
        Args:
            word: 单词
            level: 难度水平
            prompt_version: Prompt 版本
            title: 标题
            tags: 标签列表
            image_suggestion: 配图建议
            post_url: 帖子链接
        
        Returns:
            插入的记录 ID
        """
        import json
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (
                    word, level, prompt_version, title, tags, 
                    image_suggestion, published_at, post_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                word,
                level,
                prompt_version,
                title,
                json.dumps(tags, ensure_ascii=False),  # 标签存为 JSON
                image_suggestion,
                datetime.now().isoformat(),
                post_url,
            ))
            
            post_id = cursor.lastrowid
            
            # 同时创建互动数据记录（初始值为 0）
            cursor.execute("""
                INSERT INTO interactions (post_id) VALUES (?)
            """, (post_id,))
            
            conn.commit()
            return post_id
    
    def update_interactions(
        self,
        post_id: int,
        likes: Optional[int] = None,
        favorites: Optional[int] = None,
        comments: Optional[int] = None,
        views: Optional[int] = None,
    ) -> bool:
        """
        更新互动数据
        
        Args:
            post_id: 帖子 ID
            likes: 点赞数
            favorites: 收藏数
            comments: 评论数
            views: 浏览量
        
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if likes is not None:
            updates.append("likes = ?")
            params.append(likes)
        if favorites is not None:
            updates.append("favorites = ?")
            params.append(favorites)
        if comments is not None:
            updates.append("comments = ?")
            params.append(comments)
        if views is not None:
            updates.append("views = ?")
            params.append(views)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(post_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE interactions 
                SET {', '.join(updates)}
                WHERE post_id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_post_stats(
        self,
        prompt_version: Optional[str] = None,
        level: Optional[str] = None,
        word: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取帖子统计数据
        
        Args:
            prompt_version: 筛选特定 Prompt 版本
            level: 筛选特定难度
            word: 筛选特定单词
        
        Returns:
            统计字典：平均点赞、收藏、评论等
        """
        conditions = []
        params = []
        
        if prompt_version:
            conditions.append("p.prompt_version = ?")
            params.append(prompt_version)
        if level:
            conditions.append("p.level = ?")
            params.append(level)
        if word:
            conditions.append("p.word = ?")
            params.append(word)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_posts,
                    AVG(i.likes) as avg_likes,
                    AVG(i.favorites) as avg_favorites,
                    AVG(i.comments) as avg_comments,
                    AVG(i.views) as avg_views,
                    SUM(i.likes) as total_likes,
                    SUM(i.favorites) as total_favorites,
                    SUM(i.comments) as total_comments
                FROM posts p
                LEFT JOIN interactions i ON p.id = i.post_id
                {where_clause}
            """, params)
            
            row = cursor.fetchone()
            if row:
                return {
                    "total_posts": row["total_posts"],
                    "avg_likes": round(row["avg_likes"] or 0, 2),
                    "avg_favorites": round(row["avg_favorites"] or 0, 2),
                    "avg_comments": round(row["avg_comments"] or 0, 2),
                    "avg_views": round(row["avg_views"] or 0, 2),
                    "total_likes": row["total_likes"] or 0,
                    "total_favorites": row["total_favorites"] or 0,
                    "total_comments": row["total_comments"] or 0,
                }
            return {}
    
    def compare_prompt_versions(self) -> List[Dict[str, Any]]:
        """
        对比不同 Prompt 版本的表现
        
        Returns:
            各版本统计数据列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.prompt_version,
                    COUNT(*) as total_posts,
                    AVG(i.likes) as avg_likes,
                    AVG(i.favorites) as avg_favorites,
                    AVG(i.comments) as avg_comments
                FROM posts p
                LEFT JOIN interactions i ON p.id = i.post_id
                GROUP BY p.prompt_version
                ORDER BY avg_likes DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "prompt_version": row["prompt_version"],
                    "total_posts": row["total_posts"],
                    "avg_likes": round(row["avg_likes"] or 0, 2),
                    "avg_favorites": round(row["avg_favorites"] or 0, 2),
                    "avg_comments": round(row["avg_comments"] or 0, 2),
                })
            return results
    
    def compare_levels(self) -> List[Dict[str, Any]]:
        """
        对比不同难度水平的表现
        
        Returns:
            各难度统计数据列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.level,
                    COUNT(*) as total_posts,
                    AVG(i.likes) as avg_likes,
                    AVG(i.favorites) as avg_favorites,
                    AVG(i.comments) as avg_comments
                FROM posts p
                LEFT JOIN interactions i ON p.id = i.post_id
                WHERE p.level IS NOT NULL
                GROUP BY p.level
                ORDER BY avg_likes DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "level": row["level"],
                    "total_posts": row["total_posts"],
                    "avg_likes": round(row["avg_likes"] or 0, 2),
                    "avg_favorites": round(row["avg_favorites"] or 0, 2),
                    "avg_comments": round(row["avg_comments"] or 0, 2),
                })
            return results
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的发帖记录
        
        Args:
            limit: 返回数量限制
        
        Returns:
            帖子列表
        """
        import json
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id,
                    p.word,
                    p.level,
                    p.prompt_version,
                    p.title,
                    p.tags,
                    p.created_at,
                    i.likes,
                    i.favorites,
                    i.comments,
                    i.views
                FROM posts p
                LEFT JOIN interactions i ON p.id = i.post_id
                ORDER BY p.created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "word": row["word"],
                    "level": row["level"],
                    "prompt_version": row["prompt_version"],
                    "title": row["title"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "created_at": row["created_at"],
                    "likes": row["likes"] or 0,
                    "favorites": row["favorites"] or 0,
                    "comments": row["comments"] or 0,
                    "views": row["views"] or 0,
                })
            return results
