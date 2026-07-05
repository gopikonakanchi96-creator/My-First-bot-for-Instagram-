from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, func, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    caption = Column(Text, nullable=False)
    hashtags = Column(Text)
    image_path = Column(String(512))
    posted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    path = Column(String(512))
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    post = relationship('Post', backref='images')

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    level = Column(String(50))
    message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class Error(Base):
    __tablename__ = 'errors'
    id = Column(Integer, primary_key=True)
    context = Column(String(255))
    message = Column(Text)
    traceback = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
