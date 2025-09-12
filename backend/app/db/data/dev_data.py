"""
Dev database seeding script using ORM syntax.

This script contains functions to seed the development database with initial data
using SQLAlchemy ORM models instead of raw SQL.
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

from .database import (
    Base,
    ModelTask,
    Model,
    Pipeline,
    PipelineModel,
    Organization,
    Users,
    Folder,
    RbacRole,
)


def seed_dev_data(session: Session) -> None:
    """
    Seed the development database with initial data using ORM models.

    Args:
        session: SQLAlchemy session object
    """

    # Create model tasks first
    detection_task = ModelTask(
        id=1,
        name="Detection",
        active=True,
    )
    classification_task = ModelTask(
        id=2,
        name="Classification",
        active=True,
    )
    session.add_all([detection_task, classification_task])

    # Create models
    swin_15_model = Model(
        id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
        name="swin-15e-spp",
        endpoint_name="swin-15-spp-endpoint-2025",
        task_id=2,
        date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
        api_url="http://nachet-15spp-classifier:5001/score",
        api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
        created_by="Test User",
        version="0.0.1",
        description="15spp-e",
    )

    swin_27_model = Model(
        id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
        name="swin-27-spp",
        endpoint_name="swin-27-spp-endpoint-2025",
        task_id=2,
        date_model_training=datetime(2025, 3, 4, 5, 44, 8, 393911),
        api_url="http://nachet-27spp-classifier:8080/predictions/27spp_120250130",
        api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
        created_by="Test User",
        version="0.0.1",
        description="27spp",
    )

    seed_detector_model = Model(
        id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
        name="seed-detector-rcnn-1",
        endpoint_name="seed-detector-2024",
        task_id=1,
        date_model_training=datetime(2024, 11, 13, 7, 40, 25, 867369),
        api_url="http://nachet-detector:5001/score",
        api_key="gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg",
        created_by="Test User",
        version="0.0.1",
        description="",
    )

    session.add_all([swin_15_model, swin_27_model, seed_detector_model])

    # Create pipeline
    pipeline = Pipeline(
        id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
        name="27 spp RCNN SWIN",
        active=True,
        data={
            "models": ["seed-detector-rcnn-1", "swin-27-spp", "swin-15e-spp"],
            "created_by": "Test User",
            "creation_date": "2025-01-30",
            "description": "Use a Swin transformer to classify the seeds",
            "job_name": "",
            "version": "1",
            "dataset": "",
        },
    )
    session.add(pipeline)

    # Create pipeline-model relationships
    pipeline_model_1 = PipelineModel(
        id=uuid.UUID("0704a8a6-7853-4530-a49a-d98a884a3f71"),
        pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
        model_id=uuid.UUID("52fd7ca2-8101-4541-ae49-d6d92ac69196"),
    )

    pipeline_model_2 = PipelineModel(
        id=uuid.UUID("3dad6eb9-56c6-4bc1-b8ab-c683f186b874"),
        pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
        model_id=uuid.UUID("e83ee51e-830e-403a-a48f-d216ae91abb9"),
    )

    pipeline_model_3 = PipelineModel(
        id=uuid.UUID("b2d0f715-7d64-48ed-8f5f-b3ce338918c4"),
        pipeline_id=uuid.UUID("cc901051-34e0-4e21-803f-76e159848046"),
        model_id=uuid.UUID("ecef8395-e6d5-47a3-8f3d-8424b4dd3816"),
    )

    session.add_all([pipeline_model_1, pipeline_model_2, pipeline_model_3])

    # Create organization
    organization = Organization(
        id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        name="Test Organization",
        description="Default test organization for development",
    )
    session.add(organization)

    # Create RBAC role (basic admin role)
    admin_role = RbacRole(
        id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
        organization_id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        name="Admin",
        description="Administrator role with full access",
    )
    session.add(admin_role)

    # Create test user
    test_user = Users(
        id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
        email="test.user@inspection.gc.ca",
        date_created=datetime(2024, 10, 30, 19, 59, 56, 653932),
        date_updated=datetime(2024, 10, 30, 19, 59, 56, 653932),
        organization=uuid.UUID("12345678-1234-1234-1234-123456789012"),
    )
    session.add(test_user)

    # Create default folder
    default_folder = Folder(
        id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        user_id=uuid.UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16"),
        org_admin_id=uuid.UUID("87654321-4321-4321-4321-210987654321"),
        name="default",
        folder_prefix="test-org/test-user",
        description="Default folder for test user",
    )
    session.add(default_folder)

    # Commit all changes
    session.commit()

    # Update user's default folder (after folder is created)
    test_user.default_folder_id = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")
    session.commit()

    print("✅ Development database seeded successfully!")


def run_seeding(database_url: str) -> None:
    """
    Run the seeding process with a database URL.

    Args:
        database_url: SQLAlchemy database connection string
    """
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_dev_data(session)


if __name__ == "__main__":
    # Example usage - replace with your actual database URL
    database_url = "postgresql://username:password@localhost/nachet_dev"
    run_seeding(database_url)

# schema version 0.2.0
# --
# -- Data for Name: model; Type: TABLE DATA; Schema: nachet; Owner: nachet
# -- Insert models without active_version first to avoid circular dependency
# --

# INSERT INTO "nachet".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('ecef8395-e6d5-47a3-8f3d-8424b4dd3816', 'swin-15e-spp', 'swin-15-spp-endpoint-2025', 2, '2025-03-04 05:44:08.393911', NULL);
# INSERT INTO "nachet".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('e83ee51e-830e-403a-a48f-d216ae91abb9', 'swin-27-spp', 'swin-27-spp-endpoint-2025', 2, '2025-03-04 05:44:08.393911', NULL);
# INSERT INTO "nachet".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('52fd7ca2-8101-4541-ae49-d6d92ac69196', 'seed-detector-rcnn-1', 'seed-detector-2024', 1, '2024-11-13 07:40:25.867369', NULL);


# --
# -- Data for Name: model_version; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --

# INSERT INTO "nachet".model_version (id, model_id, data, version, upload_date) VALUES ('6bb13a0a-d292-49f7-b2dd-358c307f00e3', '52fd7ca2-8101-4541-ae49-d6d92ac69196', '{"endpoint": "http://nachet-detector:5001/score", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2023-12-21", "description": "", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2024-11-13 07:46:54.147204');
# INSERT INTO "nachet".model_version (id, model_id, data, version, upload_date) VALUES ('744b2f56-5fb3-406a-b04a-5e66074ed688', 'e83ee51e-830e-403a-a48f-d216ae91abb9', '{"endpoint": "http://nachet-27spp-classifier:8080/predictions/27spp_120250130", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2025-01-30", "description": "27spp", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2025-03-04 05:46:53.56912');
# INSERT INTO "nachet".model_version (id, model_id, data, version, upload_date) VALUES ('56234613-2790-42ba-8f32-85cec3129bbf', 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816', '{"endpoint": "http://nachet-15spp-classifier:5001/score", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2025-01-30", "description": "15spp-e", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2025-03-04 05:46:53.56912');

# --
# -- Update model active_version after model_version data is inserted
# --

# UPDATE "nachet".model SET active_version = '56234613-2790-42ba-8f32-85cec3129bbf' WHERE id = 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816';
# UPDATE "nachet".model SET active_version = '744b2f56-5fb3-406a-b04a-5e66074ed688' WHERE id = 'e83ee51e-830e-403a-a48f-d216ae91abb9';
# UPDATE "nachet".model SET active_version = '6bb13a0a-d292-49f7-b2dd-358c307f00e3' WHERE id = '52fd7ca2-8101-4541-ae49-d6d92ac69196';


# --
# -- Data for Name: pipeline; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --

# INSERT INTO "nachet".pipeline (id, name, active, is_default, data) VALUES ('cc901051-34e0-4e21-803f-76e159848046', '27 spp RCNN SWIN', true, true, '{"models": ["seed-detector-rcnn-1", "swin-27-spp", "swin-15e-spp"], "created_by": "Test User", "creation_date": "2025-01-30", "description": "Use a Swin transformer to classify the seeds", "job_name": "", "version": "1", "dataset": ""}');


# --
# -- Data for Name: pipeline_default; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --


# --
# -- Data for Name: pipeline_model; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --

# INSERT INTO "nachet".pipeline_model (id, pipeline_id, model_id) VALUES ('0704a8a6-7853-4530-a49a-d98a884a3f71', 'cc901051-34e0-4e21-803f-76e159848046', '52fd7ca2-8101-4541-ae49-d6d92ac69196');
# INSERT INTO "nachet".pipeline_model (id, pipeline_id, model_id) VALUES ('3dad6eb9-56c6-4bc1-b8ab-c683f186b874', 'cc901051-34e0-4e21-803f-76e159848046', 'e83ee51e-830e-403a-a48f-d216ae91abb9');
# INSERT INTO "nachet".pipeline_model (id, pipeline_id, model_id) VALUES ('b2d0f715-7d64-48ed-8f5f-b3ce338918c4', 'cc901051-34e0-4e21-803f-76e159848046', 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816');


# --
# -- Data for Name: users; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --

# INSERT INTO "nachet".users (id, email, registration_date, updated_at, default_set_id) VALUES ('8ea46a6b-7d37-4fbb-a66f-775112376e16', 'test.user@inspection.gc.ca', '2024-10-30 19:59:56.653932', '2024-10-30 19:59:56.653932', null);


# --
# -- Data for Name: picture_set; Type: TABLE DATA; Schema: nachet; Owner: nachet
# --

# INSERT INTO "nachet".picture_set (id, name, picture_set, owner_id, upload_date) VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'default', '{}', '8ea46a6b-7d37-4fbb-a66f-775112376e16', '2024-10-30');


# --
# -- Update user default_set_id after picture_set is inserted
# --

# UPDATE "nachet".users SET default_set_id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479' WHERE id = '8ea46a6b-7d37-4fbb-a66f-775112376e16';
