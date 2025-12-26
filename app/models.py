from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt

from .database import Base


# Association table for many-to-many relationship between articles and tags
article_tags = Table(
    'article_tags',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    icon = Column(String(10), nullable=True, default="📁")
    description = Column(String(255), nullable=True)

    articles = relationship("Article", back_populates="category")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=True)
    source_name = Column(String(100), nullable=True)  # e.g., "OpenAI Blog", "TechCrunch AI"
    credibility_score = Column(Integer, default=3, nullable=False)  # 1-5 scale
    image_url = Column(String(500), nullable=True)
    
    # English translations
    title_en = Column(String(255), nullable=True)
    summary_en = Column(Text, nullable=True)
    content_en = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    ai_generated = Column(Boolean, default=True)
    editor_comment = Column(Text, nullable=True)

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="articles")
    
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=article_tags, back_populates="articles")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    is_subscribed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    
    user = relationship("User", back_populates="comments")
    article = relationship("Article", back_populates="comments")


class Newsletter(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    unsubscribe_token = Column(String(64), unique=True, nullable=True)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    articles = relationship("Article", secondary=article_tags, back_populates="tags")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id = Column(Integer, primary_key=True, index=True)
    term_it = Column(String(255), nullable=False)  # The correct term (e.g. "LLM")
    banned_term = Column(String(255), nullable=False)  # The bad term (e.g. "Modelli di linguaggio grande")
    created_at = Column(DateTime, default=datetime.utcnow)

