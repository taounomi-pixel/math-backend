from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone

def get_utc_now():
    return datetime.now(timezone.utc)

# -----------------
# User Models
# -----------------
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)

class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str
    created_at: datetime = Field(default_factory=get_utc_now)

    # Relationship Back-references
    videos: List["Video"] = Relationship(back_populates="uploader")
    comments: List["Comment"] = Relationship(back_populates="user")
    likes: List["Like"] = Relationship(back_populates="user")

# -----------------
# Video Models
# -----------------
class VideoBase(SQLModel):
    title: str
    video_url: str  # Direct AWS S3 Object URL (.mp4)
    manim_source_url: Optional[str] = None # Optional AWS S3 URL (.py file)
    view_count: int = Field(default=0)

class Video(VideoBase, table=True):
    __tablename__ = "videos"
    id: Optional[int] = Field(default=None, primary_key=True)
    uploader_id: int = Field(foreign_key="users.id")
    upload_time: datetime = Field(default_factory=get_utc_now)

    # Relationship Back-references
    uploader: User = Relationship(back_populates="videos")
    comments: List["Comment"] = Relationship(back_populates="video")
    likes: List["Like"] = Relationship(back_populates="video")

# -----------------
# Comment Models
# -----------------
class CommentBase(SQLModel):
    content: str

class Comment(CommentBase, table=True):
    __tablename__ = "comments"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    video_id: int = Field(foreign_key="videos.id")
    created_at: datetime = Field(default_factory=get_utc_now)

    # Relationships
    user: User = Relationship(back_populates="comments")
    video: Video = Relationship(back_populates="comments")

# -----------------
# Like Many-To-Many
# -----------------
class Like(SQLModel, table=True):
    __tablename__ = "likes"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    video_id: int = Field(foreign_key="videos.id", primary_key=True)
    created_at: datetime = Field(default_factory=get_utc_now)

    # Relationships
    user: User = Relationship(back_populates="likes")
    video: Video = Relationship(back_populates="likes")
