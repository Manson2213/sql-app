"""
資料庫配置文件
支援 SQLite 和 PostgreSQL 兩種資料庫
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# 載入環境變數
load_dotenv()

logger = logging.getLogger(__name__)

# 資料庫配置
class DatabaseConfig:
    def __init__(self):
        # 從環境變數或預設值獲取配置
        self.db_type = os.getenv("DB_TYPE", "sqlite")  # sqlite 或 postgresql
        
        # SQLite 配置
        self.sqlite_path = os.getenv("SQLITE_PATH", "local_database.db")
        
        # PostgreSQL 配置
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = os.getenv("POSTGRES_PORT", "5432")
        self.postgres_db = os.getenv("POSTGRES_DB", "your_database")
        self.postgres_user = os.getenv("POSTGRES_USER", "your_username")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "your_password")
        
    def get_database_url(self):
        """根據配置返回資料庫連接URL"""
        if self.db_type.lower() == "postgresql":
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"sqlite:///{self.sqlite_path}"
    
    def create_engine(self):
        """建立資料庫引擎"""
        database_url = self.get_database_url()
        
        if self.db_type.lower() == "postgresql":
            # PostgreSQL 引擎配置
            engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False  # 設為 True 可以看到 SQL 查詢
            )
        else:
            # SQLite 引擎配置
            engine = create_engine(
                database_url,
                echo=False,
                connect_args={"check_same_thread": False}
            )
        
        return engine

# 全域資料庫實例
db_config = DatabaseConfig()
engine = db_config.create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_database_info():
    """獲取資料庫資訊"""
    return {
        "type": db_config.db_type,
        "url": db_config.get_database_url().replace(db_config.postgres_password, "***") if db_config.db_type == "postgresql" else db_config.get_database_url(),
        "engine": str(engine.url).replace(db_config.postgres_password, "***") if db_config.db_type == "postgresql" else str(engine.url)
    }

def test_connection():
    """測試資料庫連接"""
    try:
        with engine.connect() as connection:
            if db_config.db_type.lower() == "postgresql":
                result = connection.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL連接成功: {version}")
                return True, f"PostgreSQL連接成功: {version}"
            else:
                result = connection.execute(text("SELECT sqlite_version()"))
                version = result.fetchone()[0]
                logger.info(f"SQLite連接成功: {version}")
                return True, f"SQLite連接成功: {version}"
                
    except Exception as e:
        error_msg = f"資料庫連接失敗: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_tables():
    """獲取資料庫中的所有表格"""
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        tables = list(metadata.tables.keys())
        logger.info(f"找到 {len(tables)} 個表格: {tables}")
        return tables
    except Exception as e:
        logger.error(f"獲取表格列表失敗: {str(e)}")
        return []

def get_table_schema(table_name):
    """獲取指定表格的結構"""
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        if table_name not in metadata.tables:
            return None
            
        table = metadata.tables[table_name]
        schema = []
        
        for column in table.columns:
            schema.append({
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "default": str(column.default) if column.default else None
            })
        
        return schema
        
    except Exception as e:
        logger.error(f"獲取表格結構失敗: {str(e)}")
        return None

def execute_query(query, params=None):
    """執行SQL查詢"""
    try:
        with engine.connect() as connection:
            if params:
                result = connection.execute(text(query), params)
            else:
                result = connection.execute(text(query))
            
            # 如果是SELECT查詢，返回結果
            if query.strip().upper().startswith('SELECT'):
                return result.fetchall()
            else:
                connection.commit()
                return result.rowcount
                
    except Exception as e:
        logger.error(f"查詢執行失敗: {str(e)}")
        raise e

# 初始化範例資料（僅用於SQLite）
def init_sample_data():
    """初始化範例資料"""
    if db_config.db_type.lower() != "sqlite":
        logger.info("非SQLite資料庫，跳過範例資料初始化")
        return
    
    try:
        # 建立範例表格
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            description TEXT,
            created_date TEXT
        )
        """
        
        execute_query(create_table_sql)
        
        # 檢查是否已有資料
        count_result = execute_query("SELECT COUNT(*) FROM products")
        if count_result[0][0] > 0:
            logger.info("範例資料已存在，跳過初始化")
            return
        
        # 插入範例資料
        sample_data = [
            ("筆記型電腦", "電子產品", 25000.0, "高效能筆記型電腦", "2024-01-15"),
            ("無線滑鼠", "電子產品", 800.0, "藍牙無線滑鼠", "2024-01-16"),
            ("辦公椅", "家具", 3500.0, "人體工學辦公椅", "2024-01-17"),
            ("咖啡杯", "生活用品", 150.0, "陶瓷咖啡杯", "2024-01-18"),
            ("書桌燈", "家具", 1200.0, "LED護眼檯燈", "2024-01-19"),
        ]
        
        for item in sample_data:
            insert_sql = """
            INSERT INTO products (name, category, price, description, created_date) 
            VALUES (:name, :category, :price, :description, :created_date)
            """
            execute_query(insert_sql, {
                "name": item[0],
                "category": item[1], 
                "price": item[2],
                "description": item[3],
                "created_date": item[4]
            })
        
        logger.info("範例資料初始化完成")
        
    except Exception as e:
        logger.error(f"範例資料初始化失敗: {str(e)}")
        raise e