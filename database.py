#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据持久化模块
支持 SQLite 和 MySQL
"""

import sqlite3
import pymysql
from typing import List, Dict, Optional
from datetime import datetime
from contextlib import contextmanager
import json


class DatabaseConfig:
    """数据库配置"""

    def __init__(self, db_type: str = "sqlite", **kwargs):
        self.db_type = db_type

        if db_type == "sqlite":
            self.db_path = kwargs.get("db_path", "products.db")
        elif db_type == "mysql":
            self.host = kwargs.get("host", "localhost")
            self.port = kwargs.get("port", 3306)
            self.user = kwargs.get("user", "root")
            self.password = kwargs.get("password", "")
            self.database = kwargs.get("database", "price_compare")
            self.charset = kwargs.get("charset", "utf8mb4")

    @classmethod
    def from_dict(cls, config: Dict) -> 'DatabaseConfig':
        """从字典创建配置"""
        db_type = config.get("type", "sqlite")
        return cls(db_type=db_type, **config)


class BaseDatabase:
    """数据库基类"""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        raise NotImplementedError

    def init_tables(self):
        """初始化数据表"""
        raise NotImplementedError

    def save_product(self, product: Dict) -> int:
        """保存商品"""
        raise NotImplementedError

    def save_products(self, products: List[Dict]) -> int:
        """批量保存商品"""
        raise NotImplementedError

    def get_products(self, keyword: str = None, platform: str = None,
                     min_price: float = None, max_price: float = None,
                     limit: int = 100) -> List[Dict]:
        """查询商品"""
        raise NotImplementedError

    def get_price_history(self, product_name: str, days: int = 30) -> List[Dict]:
        """获取价格历史"""
        raise NotImplementedError

    def delete_old_products(self, days: int = 30):
        """删除旧数据"""
        raise NotImplementedError


class SQLiteDatabase(BaseDatabase):
    """SQLite数据库实现"""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.db_path = config.db_path

    @contextmanager
    def get_connection(self):
        """获取SQLite连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_tables(self):
        """初始化数据表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 商品表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    sales INTEGER DEFAULT 0,
                    shop_name TEXT,
                    shop_score REAL DEFAULT 0,
                    url TEXT UNIQUE,
                    platform TEXT,
                    image_url TEXT,
                    category TEXT,
                    collected_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 价格历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    price REAL NOT NULL,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)

            # 搜索记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    result_count INTEGER DEFAULT 0,
                    searched_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_collected_at ON products(collected_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id)")

    def save_product(self, product: Dict) -> int:
        """保存单个商品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT id FROM products WHERE url = ?", (product['url'],))
            existing = cursor.fetchone()

            if existing:
                # 更新现有商品
                product_id = existing[0]
                cursor.execute("""
                    UPDATE products
                    SET price = ?, sales = ?, shop_name = ?, shop_score = ?,
                        collected_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    product['price'], product['sales'], product['shop_name'],
                    product['shop_score'], product['collected_at'], product_id
                ))

                # 记录价格历史
                cursor.execute("""
                    INSERT INTO price_history (product_id, price)
                    VALUES (?, ?)
                """, (product_id, product['price']))
            else:
                # 插入新商品
                cursor.execute("""
                    INSERT INTO products
                    (name, price, sales, shop_name, shop_score, url, platform,
                     image_url, category, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product['name'], product['price'], product['sales'],
                    product['shop_name'], product['shop_score'], product['url'],
                    product['platform'], product['image_url'], product['category'],
                    product['collected_at']
                ))
                product_id = cursor.lastrowid

                # 记录初始价格
                cursor.execute("""
                    INSERT INTO price_history (product_id, price)
                    VALUES (?, ?)
                """, (product_id, product['price']))

            return product_id

    def save_products(self, products: List[Dict]) -> int:
        """批量保存商品"""
        count = 0
        for product in products:
            try:
                self.save_product(product)
                count += 1
            except Exception as e:
                print(f"⚠️  保存商品失败: {e}")
        return count

    def get_products(self, keyword: str = None, platform: str = None,
                     min_price: float = None, max_price: float = None,
                     limit: int = 100) -> List[Dict]:
        """查询商品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM products WHERE 1=1"
            params = []

            if keyword:
                query += " AND name LIKE ?"
                params.append(f"%{keyword}%")

            if platform:
                query += " AND platform = ?"
                params.append(platform)

            if min_price is not None:
                query += " AND price >= ?"
                params.append(min_price)

            if max_price is not None:
                query += " AND price <= ?"
                params.append(max_price)

            query += " ORDER BY price ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_price_history(self, product_name: str, days: int = 30) -> List[Dict]:
        """获取价格历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT ph.price, ph.recorded_at
                FROM price_history ph
                JOIN products p ON ph.product_id = p.id
                WHERE p.name LIKE ?
                AND ph.recorded_at >= datetime('now', '-{} days')
                ORDER BY ph.recorded_at ASC
            """.format(days), (f"%{product_name}%",))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def log_search(self, keyword: str, result_count: int):
        """记录搜索日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_logs (keyword, result_count)
                VALUES (?, ?)
            """, (keyword, result_count))

    def delete_old_products(self, days: int = 30):
        """删除旧数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM products
                WHERE collected_at < datetime('now', '-{} days')
            """.format(days))

            deleted_count = cursor.rowcount

            # 同时清理价格历史
            cursor.execute("""
                DELETE FROM price_history
                WHERE product_id NOT IN (SELECT id FROM products)
            """)

            return deleted_count

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # 总商品数
            cursor.execute("SELECT COUNT(*) FROM products")
            stats['total_products'] = cursor.fetchone()[0]

            # 各平台商品数
            cursor.execute("""
                SELECT platform, COUNT(*) as count
                FROM products
                GROUP BY platform
            """)
            stats['by_platform'] = {row[0]: row[1] for row in cursor.fetchall()}

            # 价格范围
            cursor.execute("SELECT MIN(price), MAX(price), AVG(price) FROM products")
            row = cursor.fetchone()
            stats['price_range'] = {
                'min': row[0],
                'max': row[1],
                'avg': row[2]
            }

            # 最近搜索
            cursor.execute("""
                SELECT keyword, result_count, searched_at
                FROM search_logs
                ORDER BY searched_at DESC
                LIMIT 10
            """)
            stats['recent_searches'] = [dict(row) for row in cursor.fetchall()]

            return stats


class MySQLDatabase(BaseDatabase):
    """MySQL数据库实现"""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)

    @contextmanager
    def get_connection(self):
        """获取MySQL连接"""
        conn = pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            charset=self.config.charset,
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_tables(self):
        """初始化数据表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 商品表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(500) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    sales INT DEFAULT 0,
                    shop_name VARCHAR(200),
                    shop_score DECIMAL(3, 2) DEFAULT 0,
                    url VARCHAR(1000) UNIQUE,
                    platform VARCHAR(50),
                    image_url VARCHAR(1000),
                    category VARCHAR(100),
                    collected_at DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_platform (platform),
                    INDEX idx_price (price),
                    INDEX idx_collected_at (collected_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 价格历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    product_id INT,
                    price DECIMAL(10, 2) NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    INDEX idx_product_id (product_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 搜索记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    keyword VARCHAR(200) NOT NULL,
                    result_count INT DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

    def save_product(self, product: Dict) -> int:
        """保存单个商品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT id FROM products WHERE url = %s", (product['url'],))
            existing = cursor.fetchone()

            if existing:
                product_id = existing['id']
                cursor.execute("""
                    UPDATE products
                    SET price = %s, sales = %s, shop_name = %s, shop_score = %s,
                        collected_at = %s
                    WHERE id = %s
                """, (
                    product['price'], product['sales'], product['shop_name'],
                    product['shop_score'], product['collected_at'], product_id
                ))

                cursor.execute("""
                    INSERT INTO price_history (product_id, price)
                    VALUES (%s, %s)
                """, (product_id, product['price']))
            else:
                cursor.execute("""
                    INSERT INTO products
                    (name, price, sales, shop_name, shop_score, url, platform,
                     image_url, category, collected_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product['name'], product['price'], product['sales'],
                    product['shop_name'], product['shop_score'], product['url'],
                    product['platform'], product['image_url'], product['category'],
                    product['collected_at']
                ))
                product_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO price_history (product_id, price)
                    VALUES (%s, %s)
                """, (product_id, product['price']))

            return product_id

    def save_products(self, products: List[Dict]) -> int:
        """批量保存商品"""
        count = 0
        for product in products:
            try:
                self.save_product(product)
                count += 1
            except Exception as e:
                print(f"⚠️  保存商品失败: {e}")
        return count

    def get_products(self, keyword: str = None, platform: str = None,
                     min_price: float = None, max_price: float = None,
                     limit: int = 100) -> List[Dict]:
        """查询商品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM products WHERE 1=1"
            params = []

            if keyword:
                query += " AND name LIKE %s"
                params.append(f"%{keyword}%")

            if platform:
                query += " AND platform = %s"
                params.append(platform)

            if min_price is not None:
                query += " AND price >= %s"
                params.append(min_price)

            if max_price is not None:
                query += " AND price <= %s"
                params.append(max_price)

            query += " ORDER BY price ASC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            return cursor.fetchall()

    def get_price_history(self, product_name: str, days: int = 30) -> List[Dict]:
        """获取价格历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT ph.price, ph.recorded_at
                FROM price_history ph
                JOIN products p ON ph.product_id = p.id
                WHERE p.name LIKE %s
                AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY ph.recorded_at ASC
            """, (f"%{product_name}%", days))

            return cursor.fetchall()

    def log_search(self, keyword: str, result_count: int):
        """记录搜索日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_logs (keyword, result_count)
                VALUES (%s, %s)
            """, (keyword, result_count))

    def delete_old_products(self, days: int = 30):
        """删除旧数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM products
                WHERE collected_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,))

            return cursor.rowcount


def create_database(config: DatabaseConfig) -> BaseDatabase:
    """工厂方法：创建数据库实例"""
    if config.db_type == "sqlite":
        db = SQLiteDatabase(config)
    elif config.db_type == "mysql":
        db = MySQLDatabase(config)
    else:
        raise ValueError(f"不支持的数据库类型: {config.db_type}")

    db.init_tables()
    return db


if __name__ == '__main__':
    # 测试数据库
    config = DatabaseConfig(db_type="sqlite", db_path="test.db")
    db = create_database(config)

    # 测试保存
    test_product = {
        "name": "测试商品",
        "price": 99.99,
        "sales": 1000,
        "shop_name": "测试店铺",
        "shop_score": 4.8,
        "url": "https://example.com/test",
        "platform": "京东",
        "image_url": "https://example.com/image.jpg",
        "category": "测试",
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    product_id = db.save_product(test_product)
    print(f"保存商品ID: {product_id}")

    # 测试查询
    products = db.get_products(keyword="测试")
    print(f"查询到 {len(products)} 个商品")

    # 测试统计
    stats = db.get_statistics()
    print(f"统计信息: {stats}")
