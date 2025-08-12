"""
SQLAlchemy models for Nachet database schema nachet_0.0.13
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, 
    Date, 
    DateTime, 
    Float,
    ForeignKey, 
    Integer, 
    String, 
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ObjectType(Base):
    __tablename__ = "object_type"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class PictureSet(Base):
    __tablename__ = "picture_set"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    picture_set: Mapped[dict] = mapped_column(JSON, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        Date, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    name: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="picture_sets")
    pictures: Mapped[list["Picture"]] = relationship("Picture", back_populates="picture_set", cascade="all, delete-orphan")


class Picture(Base):
    __tablename__ = "picture"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    picture: Mapped[dict] = mapped_column(JSON, nullable=False)
    picture_set_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("picture_set.id", ondelete="CASCADE"), 
        nullable=False
    )
    nb_obj: Mapped[int] = mapped_column(Integer, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    picture_set: Mapped["PictureSet"] = relationship("PictureSet", back_populates="pictures")
    inferences: Mapped[list["Inference"]] = relationship("Inference", back_populates="picture", cascade="all, delete-orphan")
    picture_seeds: Mapped[list["PictureSeed"]] = relationship("PictureSeed", back_populates="picture", cascade="all, delete-orphan")


class Pipeline(Base):
    __tablename__ = "pipeline"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Relationships
    pipeline_models: Mapped[list["PipelineModel"]] = relationship("PipelineModel", back_populates="pipeline")
    inferences: Mapped[list["Inference"]] = relationship("Inference", back_populates="pipeline")
    pipeline_defaults: Mapped[list["PipelineDefault"]] = relationship("PipelineDefault", back_populates="pipeline")


class Seed(Base):
    __tablename__ = "seed"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    object_type_id: Mapped[int] = mapped_column(
        Integer, 
        server_default=text("1")
    )
    
    # Relationships
    picture_seeds: Mapped[list["PictureSeed"]] = relationship("PictureSeed", back_populates="seed")
    seed_objs: Mapped[list["SeedObj"]] = relationship("SeedObj", back_populates="seed")


class PictureSeed(Base):
    __tablename__ = "picture_seed"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    picture_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("picture.id", ondelete="CASCADE"), 
        nullable=False
    )
    seed_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("seed.id"), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    picture: Mapped["Picture"] = relationship("Picture", back_populates="picture_seeds")
    seed: Mapped["Seed"] = relationship("Seed", back_populates="picture_seeds")


class Task(Base):
    __tablename__ = "task"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    models: Mapped[list["Model"]] = relationship("Model", back_populates="task")


class Model(Base):
    __tablename__ = "model"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint_name: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("task.id"), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    active_version: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("model_version.id", ondelete="SET NULL")
    )
    
    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="models")
    model_versions: Mapped[list["ModelVersion"]] = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    pipeline_models: Mapped[list["PipelineModel"]] = relationship("PipelineModel", back_populates="model")


class ModelVersion(Base):
    __tablename__ = "model_version"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("model.id", ondelete="CASCADE"), 
        nullable=False
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="model_versions")


class PipelineModel(Base):
    __tablename__ = "pipeline_model"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    pipeline_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("pipeline.id"), nullable=False)
    model_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("model.id"), nullable=False)
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="pipeline_models")
    model: Mapped["Model"] = relationship("Model", back_populates="pipeline_models")


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    default_set_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("picture_set.id")
    )
    
    # Relationships
    picture_sets: Mapped[list["PictureSet"]] = relationship("PictureSet", back_populates="owner")
    inferences: Mapped[list["Inference"]] = relationship("Inference", back_populates="user", foreign_keys="Inference.user_id")
    feedback_inferences: Mapped[list["Inference"]] = relationship("Inference", back_populates="feedback_user", foreign_keys="Inference.feedback_user_id")
    pipeline_defaults: Mapped[list["PipelineDefault"]] = relationship("PipelineDefault", back_populates="user")


class Inference(Base):
    __tablename__ = "inference"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    inference: Mapped[dict] = mapped_column(JSON, nullable=False)
    picture_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("picture.id", ondelete="CASCADE"), 
        nullable=False
    )
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    feedback_user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pipeline_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("pipeline.id", ondelete="SET NULL")
    )
    update_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    picture: Mapped["Picture"] = relationship("Picture", back_populates="inferences")
    user: Mapped["User"] = relationship("User", back_populates="inferences", foreign_keys=[user_id])
    feedback_user: Mapped[Optional["User"]] = relationship("User", back_populates="feedback_inferences", foreign_keys=[feedback_user_id])
    pipeline: Mapped[Optional["Pipeline"]] = relationship("Pipeline", back_populates="inferences")
    objects: Mapped[list["Object"]] = relationship("Object", back_populates="inference", cascade="all, delete-orphan")


class Object(Base):
    __tablename__ = "object"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    box_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    inference_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("inference.id", ondelete="CASCADE"), 
        nullable=False
    )
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("object_type.id"), nullable=False)
    verified_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    valid: Mapped[Optional[bool]] = mapped_column(Boolean)
    top_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    manual_detection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    update_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    inference: Mapped["Inference"] = relationship("Inference", back_populates="objects")
    object_type: Mapped["ObjectType"] = relationship("ObjectType")
    seed_objs: Mapped[list["SeedObj"]] = relationship("SeedObj", back_populates="object", cascade="all, delete-orphan")


class PipelineDefault(Base):
    __tablename__ = "pipeline_default"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    pipeline_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("pipeline.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="pipeline_defaults")
    user: Mapped["User"] = relationship("User", back_populates="pipeline_defaults")


class SeedObj(Base):
    __tablename__ = "seed_obj"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    seed_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("seed.id"), nullable=False)
    object_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("object.id", ondelete="CASCADE"), 
        nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Relationships
    seed: Mapped["Seed"] = relationship("Seed", back_populates="seed_objs")
    object: Mapped["Object"] = relationship("Object", back_populates="seed_objs")