import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.config import settings

# 建立 SQLAlchemy 引擎與 Session 類別
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}  # 僅適用於 SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 1. 資料庫模型定義 (ORM Models)
# ==========================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 關聯
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    weaknesses = relationship("WeaknessMemory", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), unique=True, nullable=False)
    file_type = Column(String(10), nullable=False)  # 'pdf', 'md'
    summary = Column(Text, nullable=True)
    tags_json = Column(Text, default="[]")  # 以 JSON 字串儲存標籤列表
    created_at = Column(DateTime, default=datetime.utcnow)


    @property
    def tags(self) -> List[str]:
        try:
            return json.loads(self.tags_json)
        except Exception:
            return []

    @tags.setter
    def tags(self, value: List[str]):
        self.tags_json = json.dumps(value)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(10), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")


class WeaknessMemory(Base):
    __tablename__ = "weakness_memories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(100), nullable=False)  # 知識主題
    error_count = Column(Integer, default=0)     # 答錯次數
    last_tested_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weaknesses")


class KnowledgeGraph(Base):
    __tablename__ = "knowledge_graphs"
    id = Column(Integer, primary_key=True, index=True)
    source_node = Column(String(100), nullable=False)
    target_node = Column(String(100), nullable=False)
    relation_type = Column(String(50), nullable=False)  # e.g., 'depends_on', 'contains'
    weight = Column(Float, default=1.0)


# ==========================================
# 2. 初始化資料庫與常用 CRUD 輔助函式
# ==========================================

def init_db():
    """初始化並建立所有資料表，並確認預設使用者存在"""
    Base.metadata.create_all(bind=engine)
    
    # 建立預設使用者 "jeff" 作為期末專題的展示帳戶
    db = SessionLocal()
    try:
        default_user = db.query(User).filter(User.username == "jeff").first()
        if not default_user:
            new_user = User(username="jeff")
            db.add(new_user)
            db.commit()
    finally:
        db.close()

def get_db():
    """FastAPI 依賴注入的 DB Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 輔助函式 ---

def get_default_user_id() -> int:
    """快速取得預設使用者 ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "jeff").first()
        if user:
            return user.id
        return 1
    finally:
        db.close()

def save_chat_message(role: str, content: str) -> Conversation:
    """儲存對話紀錄"""
    db = SessionLocal()
    try:
        user_id = get_default_user_id()
        msg = Conversation(user_id=user_id, role=role, content=content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg
    finally:
        db.close()

def get_chat_history(limit: int = 20) -> List[Dict[str, Any]]:
    """獲取最近的對話歷史"""
    db = SessionLocal()
    try:
        user_id = get_default_user_id()
        msgs = db.query(Conversation)\
                 .filter(Conversation.user_id == user_id)\
                 .order_by(Conversation.created_at.asc())\
                 .limit(limit)\
                 .all()
        return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]
    finally:
        db.close()

def update_weakness(topic: str, correct: bool):
    """更新弱點記憶分數：答錯 +1，答對則減少（最低至 0）"""
    db = SessionLocal()
    try:
        user_id = get_default_user_id()
        weakness = db.query(WeaknessMemory)\
                     .filter(WeaknessMemory.user_id == user_id, WeaknessMemory.topic == topic)\
                     .first()
        
        if not weakness:
            # 首次建立，如果答錯則 error_count = 1，答對則 0
            weakness = WeaknessMemory(
                user_id=user_id, 
                topic=topic, 
                error_count=1 if not correct else 0,
                last_tested_at=datetime.utcnow()
            )
            db.add(weakness)
        else:
            if not correct:
                weakness.error_count += 1
            else:
                weakness.error_count = max(0, weakness.error_count - 1)
            weakness.last_tested_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def get_weaknesses() -> List[Dict[str, Any]]:
    """獲取目前的弱點清單"""
    db = SessionLocal()
    try:
        user_id = get_default_user_id()
        items = db.query(WeaknessMemory)\
                  .filter(WeaknessMemory.user_id == user_id)\
                  .order_by(WeaknessMemory.error_count.desc())\
                  .all()
        return [{"topic": i.topic, "error_count": i.error_count, "last_tested_at": i.last_tested_at.isoformat()} for i in items]
    finally:
        db.close()

def add_graph_edge(source: str, target: str, relation_type: str, weight: float = 1.0):
    """新增知識圖譜關係邊，避免重複建立重複邊"""
    db = SessionLocal()
    try:
        # 清理空格與轉小寫/格式化
        s = source.strip()
        t = target.strip()
        r = relation_type.strip()
        
        edge = db.query(KnowledgeGraph).filter(
            KnowledgeGraph.source_node == s,
            KnowledgeGraph.target_node == t,
            KnowledgeGraph.relation_type == r
        ).first()
        
        if not edge:
            edge = KnowledgeGraph(source_node=s, target_node=t, relation_type=r, weight=weight)
            db.add(edge)
            db.commit()
    finally:
        db.close()

def get_knowledge_graph() -> Dict[str, List[Dict[str, Any]]]:
    """獲取完整的節點與邊，供圖譜可視化使用"""
    db = SessionLocal()
    try:
        edges = db.query(KnowledgeGraph).all()
        
        # 收集所有不重複節點
        nodes_set = set()
        nodes_info = {}
        
        edges_list = []
        for e in edges:
            nodes_set.add(e.source_node)
            nodes_set.add(e.target_node)
            edges_list.append({
                "source": e.source_node,
                "target": e.target_node,
                "relation": e.relation_type,
                "weight": e.weight
            })
            
        # 獲取標籤出現頻率作為節點大小的計算依據，或是預設大小
        # 我們希望圖譜更漂亮，我們可以為每個節點標記其是否出現在 Documents 標籤中
        docs = db.query(Document).all()
        tag_freq = {}
        for d in docs:
            for tag in d.tags:
                tag_freq[tag] = tag_freq.get(tag, 0) + 1
                
        nodes_list = []
        for node in nodes_set:
            freq = tag_freq.get(node, 1)
            nodes_list.append({
                "id": node,
                "label": node,
                "size": 10 + freq * 5,  # 依據出現頻率動態調整節點大小
                "type": "concept"
            })
            
        return {"nodes": nodes_list, "edges": edges_list}
    finally:
        db.close()
