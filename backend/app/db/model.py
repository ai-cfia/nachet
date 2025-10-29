from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    JSON,
    ForeignKey,
    Double,
    UUID,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.sql import func
from beartype.typing import List, Optional
from uuid import uuid4  # , UUID
from datetime import datetime, date


class Base(AsyncAttrs, DeclarativeBase):
    pass


class ModelTask(Base):
    __tablename__ = "model_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # description: Mapped[Optional[str]] = mapped_column(Text) # test change

    # Relationships
    models: Mapped[List["Model"]] = relationship("Model", back_populates="model_task")


class Seed(Base):
    __tablename__ = "seed"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    seed_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name_code: Mapped[str] = mapped_column(Text, nullable=False)
    family: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    genus: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    species: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    original_ista_2025: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    objects_top_1: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.top_id", back_populates="seed_top_1"
    )
    objects_top_2: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.top_id_2", back_populates="seed_top_2"
    )
    objects_top_3: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.top_id_3", back_populates="seed_top_3"
    )


class Model(Base):
    __tablename__ = "model"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_task.id"), nullable=False
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_model_training: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        Text, nullable=False, default="application/json"
    )
    deployment_platform: Mapped[str] = mapped_column(
        Text, nullable=False, default="on-prem"
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint_name: Mapped[str] = mapped_column(Text, nullable=False)
    api_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    job_name: Mapped[Optional[str]] = mapped_column(Text, comment="Training job name")
    dataset: Mapped[Optional[str]] = mapped_column(Text, comment="training dataset id")
    artifacts_url: Mapped[Optional[str]] = mapped_column(Text)
    sha256: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    model_task: Mapped["ModelTask"] = relationship("ModelTask", back_populates="models")
    pipeline_models: Mapped[List["PipelineModel"]] = relationship(
        "PipelineModel", back_populates="model"
    )


class Pipeline(Base):
    __tablename__ = "pipeline"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)

    # New normalized columns from JSON data field
    created_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    identifiable: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    default: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=False
    )

    # Keep data field for backward compatibility during migration
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    pipeline_models: Mapped[List["PipelineModel"]] = relationship(
        "PipelineModel", back_populates="pipeline"
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="pipeline"
    )
    objects: Mapped[List["Object"]] = relationship("Object", back_populates="pipeline")


class PipelineDefault(Base):
    __tablename__ = "pipeline_default"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("pipeline.id"), nullable=False, unique=True
    )

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline")


class PipelineModel(Base):
    __tablename__ = "pipeline_model"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("pipeline.id"), nullable=False
    )
    model_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("model.id"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    request_function: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline", back_populates="pipeline_models"
    )
    model: Mapped["Model"] = relationship("Model", back_populates="pipeline_models")


class RbacRole(Base):
    __tablename__ = "rbac_role"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_rbac_role_org_name"),
    )

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("organization.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="rbac_roles"
    )
    user_roles: Mapped[List["RbacUserRole"]] = relationship(
        "RbacUserRole", back_populates="role"
    )
    role_permission_resources: Mapped[List["RbacRolePermissionResource"]] = (
        relationship("RbacRolePermissionResource", back_populates="role")
    )
    folders: Mapped[List["Folder"]] = relationship(
        "Folder",
        foreign_keys="[Folder.org_admin_role_id]",
        back_populates="org_admin_role",
    )
    pictures: Mapped[List["Picture"]] = relationship(
        "Picture",
        foreign_keys="[Picture.org_admin_role_id]",
        back_populates="org_admin_role",
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation",
        foreign_keys="[Annotation.org_admin_role_id]",
        back_populates="org_admin_role",
    )
    objects: Mapped[List["Object"]] = relationship(
        "Object",
        foreign_keys="[Object.org_admin_role_id]",
        back_populates="org_admin_role",
    )


class RbacPermission(Base):
    __tablename__ = "rbac_permission"
    __table_args__ = (UniqueConstraint("name", name="uq_rbac_permission_name"),)

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    role_permission_resources: Mapped[List["RbacRolePermissionResource"]] = (
        relationship("RbacRolePermissionResource", back_populates="permission")
    )


class RbacResource(Base):
    __tablename__ = "rbac_resource"
    __table_args__ = (UniqueConstraint("name", name="uq_rbac_resource_name"),)

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    role_permission_resources: Mapped[List["RbacRolePermissionResource"]] = (
        relationship("RbacRolePermissionResource", back_populates="resource")
    )


class RbacRolePermissionResource(Base):
    __tablename__ = "rbac_role_permission_resource"

    role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_permission.id"), primary_key=True
    )
    resource_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_resource.id"), primary_key=True
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    role: Mapped["RbacRole"] = relationship(
        "RbacRole", back_populates="role_permission_resources"
    )
    permission: Mapped["RbacPermission"] = relationship(
        "RbacPermission", back_populates="role_permission_resources"
    )
    resource: Mapped["RbacResource"] = relationship(
        "RbacResource", back_populates="role_permission_resources"
    )


class Organization(Base):
    __tablename__ = "organization"
    # __table_args__ = (
    #     Index(
    #         "ix_organization_name_prefix",
    #         func.substring(func.lower(name), 1, 10),
    #         unique=True,
    #     ),
    # )

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    folder_prefix: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    users: Mapped[List["Users"]] = relationship(
        "Users", back_populates="organization_ref"
    )
    rbac_roles: Mapped[List["RbacRole"]] = relationship(
        "RbacRole", back_populates="organization"
    )


class Users(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    default_folder_id: Mapped[Optional[UUID]] = mapped_column(UUID)
    organization: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("organization.id"), nullable=False
    )
    registered_by: Mapped[Optional[UUID]] = mapped_column(UUID)

    # Relationships
    organization_ref: Mapped["Organization"] = relationship(
        "Organization", back_populates="users"
    )
    folders: Mapped[List["Folder"]] = relationship("Folder", back_populates="user")
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="user"
    )
    objects: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.user_id", back_populates="user"
    )
    objects_feedback: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.feedback_user_id", back_populates="feedback_user"
    )
    objects_verifier: Mapped[List["Object"]] = relationship(
        "Object", foreign_keys="Object.verifier_user_id", back_populates="verifier_user"
    )
    user_roles: Mapped[List["RbacUserRole"]] = relationship(
        "RbacUserRole", back_populates="user"
    )
    change_logs: Mapped[List["ChangeLog"]] = relationship(
        "ChangeLog", back_populates="user"
    )


class Folder(Base):
    __tablename__ = "folder"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    folder_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    user: Mapped["Users"] = relationship("Users", back_populates="folders")
    pictures: Mapped[List["Picture"]] = relationship("Picture", back_populates="folder")
    org_admin_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_admin_role_id],
        back_populates="folders",
    )
    org_user_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_user_role_id],
    )


class Picture(Base):
    __tablename__ = "picture"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    folder_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("folder.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    blob_url_original: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    size_on_disk_original: Mapped[float] = mapped_column(Double, nullable=False)
    size_on_disk_sanitized: Mapped[Optional[float]] = mapped_column(Double)
    magnification: Mapped[Optional[float]] = mapped_column(Double)
    blob_url_sanitized: Mapped[Optional[str]] = mapped_column(Text)
    device_model_id: Mapped[Optional[UUID]] = mapped_column(UUID)
    device_lens_id: Mapped[Optional[UUID]] = mapped_column(UUID)
    single_species_image: Mapped[Optional[UUID]] = mapped_column(
        UUID,
        comment="for training, multiple seeds of the same species will be in the image, this value is specified by uploader, null if multi spp",
    )
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    folder: Mapped["Folder"] = relationship("Folder", back_populates="pictures")
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="picture"
    )
    objects: Mapped[List["Object"]] = relationship("Object", back_populates="picture")
    org_admin_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_admin_role_id],
        back_populates="pictures",
    )
    org_user_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_user_role_id],
    )
    processing_state: Mapped[Optional["ImageProcessingState"]] = relationship(
        "ImageProcessingState",
        back_populates="picture",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ImageProcessingState(Base):
    """
    Tracks the state of image processing pipeline (upload → scan → sanitize).

    Separate from Picture model to maintain clean separation of concerns
    and allow independent state management.

    Note: Inference workflow state is tracked in InferenceRequestState table
    to support multiple inference runs per image.
    """

    __tablename__ = "image_processing_state"

    # Primary key - matches Picture.id
    picture_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("picture.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Reference to Picture being processed",
    )

    # Current processing status (MVP scope only)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending|uploaded|defender_scanning|defender_scanned|sanitizing|sanitized|completed|failed|cancelled",
    )

    # Ownership tracking (for authorization)
    user_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who initiated the workflow",
    )
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("rbac_role.id"),
        nullable=False,
        comment="User's role in their organization",
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("rbac_role.id"),
        nullable=False,
        comment="Admin role for cross-org access (CFIA admins)",
    )

    # DBOS workflow tracking
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="DBOS workflow UUID for image processing workflow (upload/scan/sanitize)",
    )

    # Stage timestamps (MVP: upload → scan → sanitize only)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    defender_scan_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    defender_scan_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    sanitization_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    sanitization_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Azure Defender scan results
    defender_scan_result: Mapped[Optional[dict]] = mapped_column(
        JSON, comment="Defender scan tags and metadata"
    )
    malware_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if malware detected by Defender",
    )

    # Blob storage URLs
    blob_url_original: Mapped[Optional[str]] = mapped_column(String(500))
    blob_url_sanitized: Mapped[Optional[str]] = mapped_column(String(500))

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(String(1000))
    error_details: Mapped[Optional[dict]] = mapped_column(
        JSON, comment="Detailed error information including stack traces"
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Progress tracking
    progress_percentage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="0-100 progress indicator"
    )

    # Relationship back to Picture
    picture: Mapped["Picture"] = relationship(
        "Picture", back_populates="processing_state"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_processing_state_status", "status"),
        Index("idx_processing_state_workflow", "workflow_id"),
        Index("idx_processing_state_created", "created_at"),
        Index("idx_processing_state_user", "user_id"),
    )


class InferenceRequestState(Base):
    """
    Tracks the state of image inference requests.

    Separate from Picture model to maintain clean separation of concerns
    and allow independent state management.
    """

    __tablename__ = "inference_request_state"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    picture_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("picture.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to Picture for which inference is requested",
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("pipeline.id"),
        nullable=False,
        comment="Pipeline used for inference",
    )

    # Ownership tracking (for authorization)
    user_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who initiated the inference request",
    )
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("rbac_role.id"),
        nullable=False,
        comment="User's role in their organization",
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("rbac_role.id"),
        nullable=False,
        comment="Admin role for cross-org access (CFIA admins)",
    )

    # DBOS workflow tracking
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="DBOS workflow UUID for tracking and recovery",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending|in_progress|completed|failed",
    )
    request_payload: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Payload sent for inference request"
    )
    response_payload: Mapped[Optional[dict]] = mapped_column(
        JSON, comment="Response received from inference request"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(String(1000))

    # Relationship back to Picture
    picture: Mapped["Picture"] = relationship("Picture")
    pipeline: Mapped["Pipeline"] = relationship("Pipeline")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_inference_request_state_user", "user_id"),
        Index("idx_inference_request_state_workflow", "workflow_id"),
        Index("idx_inference_request_state_picture", "picture_id"),
    )


class Annotation(Base):
    __tablename__ = "annotation"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    picture_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("picture.id", ondelete="CASCADE"), nullable=False
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("pipeline.id"),
        comment="pipeline used, human should be an entry in pipeline table",
    )
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    picture: Mapped["Picture"] = relationship("Picture", back_populates="annotations")
    user: Mapped["Users"] = relationship("Users", back_populates="annotations")
    pipeline: Mapped[Optional["Pipeline"]] = relationship(
        "Pipeline", back_populates="annotations"
    )
    objects: Mapped[List["Object"]] = relationship(
        "Object", back_populates="annotation"
    )
    org_admin_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_admin_role_id],
        back_populates="annotations",
    )
    org_user_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_user_role_id],
    )


class Object(Base):
    __tablename__ = "object"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    org_user_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    org_admin_role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), nullable=False
    )
    inference_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("annotation.id", ondelete="CASCADE"), nullable=False
    )
    picture_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("picture.id"), nullable=False
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("pipeline.id"), nullable=False
    )
    valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bot_y_abs: Mapped[int] = mapped_column(Integer, nullable=False)
    bot_x_abs: Mapped[int] = mapped_column(Integer, nullable=False)
    top_y_abs: Mapped[int] = mapped_column(Integer, nullable=False)
    top_x_abs: Mapped[int] = mapped_column(Integer, nullable=False)
    top_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("seed.id"), nullable=False)
    top_id_2: Mapped[Optional[UUID]] = mapped_column(UUID, ForeignKey("seed.id"))
    top_id_3: Mapped[Optional[UUID]] = mapped_column(UUID, ForeignKey("seed.id"))
    top_score: Mapped[float] = mapped_column(Double, nullable=False)
    top_score_2: Mapped[Optional[float]] = mapped_column(Double)
    top_score_3: Mapped[Optional[float]] = mapped_column(Double)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_verified: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    date_feedback: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    box_update: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    species_update: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    feedback_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID, ForeignKey("users.id")
    )
    verifier_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID, ForeignKey("users.id")
    )

    # Relationships
    annotation: Mapped["Annotation"] = relationship(
        "Annotation", back_populates="objects"
    )
    seed_top_1: Mapped[Optional["Seed"]] = relationship(
        "Seed", foreign_keys=[top_id], back_populates="objects_top_1"
    )
    seed_top_2: Mapped[Optional["Seed"]] = relationship(
        "Seed", foreign_keys=[top_id_2], back_populates="objects_top_2"
    )
    seed_top_3: Mapped[Optional["Seed"]] = relationship(
        "Seed", foreign_keys=[top_id_3], back_populates="objects_top_3"
    )
    user: Mapped["Users"] = relationship(
        "Users", foreign_keys=[user_id], back_populates="objects"
    )
    picture: Mapped["Picture"] = relationship("Picture", back_populates="objects")
    feedback_user: Mapped[Optional["Users"]] = relationship(
        "Users", foreign_keys=[feedback_user_id], back_populates="objects_feedback"
    )
    verifier_user: Mapped[Optional["Users"]] = relationship(
        "Users", foreign_keys=[verifier_user_id], back_populates="objects_verifier"
    )
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="objects")
    org_admin_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_admin_role_id],
        back_populates="objects",
    )
    org_user_role: Mapped["RbacRole"] = relationship(
        "RbacRole",
        foreign_keys=[org_user_role_id],
    )


class RbacUserRole(Base):
    __tablename__ = "rbac_user_role"

    user_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("rbac_role.id"), primary_key=True
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped["Users"] = relationship("Users", back_populates="user_roles")
    role: Mapped["RbacRole"] = relationship("RbacRole", back_populates="user_roles")


class DeviceModel(Base):
    __tablename__ = "device_model"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    device_brand_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("device_brand.id"), nullable=False
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    device_brand: Mapped["DeviceBrand"] = relationship(
        "DeviceBrand", back_populates="device_models"
    )


class DeviceLens(Base):
    __tablename__ = "device_lens"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    device_brand_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("device_brand.id"), nullable=False
    )
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    device_brand: Mapped["DeviceBrand"] = relationship(
        "DeviceBrand", back_populates="device_lenses"
    )


class DeviceBrand(Base):
    __tablename__ = "device_brand"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    device_models: Mapped[List["DeviceModel"]] = relationship(
        "DeviceModel", back_populates="device_brand"
    )
    device_lenses: Mapped[List["DeviceLens"]] = relationship(
        "DeviceLens", back_populates="device_brand"
    )


class ChangeLog(Base):
    __tablename__ = "change_log"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.current_timestamp(), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    table: Mapped[Optional[str]] = mapped_column("table", Text)
    entry_id: Mapped[Optional[UUID]] = mapped_column(UUID)
    action_id: Mapped[Optional[UUID]] = mapped_column(UUID)
    value_prev: Mapped[Optional[dict]] = mapped_column(JSON)
    value_new: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    user: Mapped[Optional["Users"]] = relationship(
        "Users", back_populates="change_logs"
    )


class PendingRegistration(Base):
    __tablename__ = "pending_registration"

    azure_ad_oid: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
