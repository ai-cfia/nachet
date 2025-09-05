# Data Model Rationale 0.2.0

```text
classDiagram
direction BT
class annotation {
   json raw_data
   uuid picture_id
   timestamp with time zone date_created
   uuid user_id
   uuid pipeline_id
   uuid org_admin_id
   uuid id
}
class change_log {
   timestamp with time zone date_created
   uuid schema_version_id
   uuid user_id
   text table
   uuid entry_id
   uuid action_id
   json value_prev
   json value_new
   uuid id
}
class device_brand {
   text name
   text description
   boolean active
   uuid id
}
class device_lens {
   text name
   text description
   boolean active
   uuid device_brand_id
   uuid id
}
class device_model {
   text name
   text description
   boolean active
   uuid device_brand_id
   uuid id
}
class folder {
   uuid user_id
   timestamp with time zone date_created
   text name
   text folder_prefix
   text description
   uuid org_admin_id
   boolean active
   uuid id
}
class model {
   text name
   text endpoint_name
   integer task_id
   timestamp with time zone date_created
   text version
   text api_url
   text api_key
   text content_type
   text deployment_platform
   text created_by
   timestamp with time zone date_model_training
   text description
   text job_name  /* Training job name */
   text dataset  /* training dataset id */
   text artifacts_url
   text sha256
   uuid id
}
class object {
   uuid inference_id
   uuid top_id
   uuid top_id_2
   timestamp with time zone date_verified
   double precision top_score
   double precision top_score_2
   uuid top_id_3
   double precision top_score_3
   timestamp with time zone date_created
   boolean valid
   boolean box_update
   boolean species_update
   uuid user_id
   uuid picture_id
   uuid org_admin_id
   uuid feedback_user_id
   uuid verifier_user_id
   uuid pipeline_id
   timestamp with time zone date_feedback
   integer bot_y_abs
   integer bot_x_abs
   integer top_y_abs
   integer top_x_abs
   uuid id
}
class organization {
   text name
   text folder_prefix
   boolean active
   uuid id
}
class picture {
   uuid folder_id
   boolean active
   timestamp with time zone date_created
   text sha256
   double precision magnification
   uuid single_species_image  /* for training, multiple seeds of the same species will be in t... */
   uuid user_id
   uuid org_admin_id
   text name
   uuid device_model_id
   uuid device_lens_id
   integer blob_url
   text format
   integer width
   integer height
   text description
   double precision size_on_disk
   uuid id
}
class pipeline {
   text name
   boolean active
   boolean is_default
   json data
   uuid id
}
class pipeline_model {
   uuid pipeline_id
   uuid model_id
   uuid id
}
class rbac_permission {
   text name
   uuid id
}
class rbac_resource {
   text name
   uuid id
}
class rbac_role {
   text name
   text description
   boolean active
   uuid id
}
class rbac_role_permission_resource {
   uuid role_id
   uuid permission_id
   uuid resource_id
}
class rbac_user_role {
   timestamp with time zone date_created
   boolean active
   uuid user_id
   uuid role_id
}
class schema_version {
   uuid id
   text semver
   timestamp with time zone date_created
}
class seed {
   json metadata
   boolean active
   timestamp with time zone date_created
   timestamp with time zone date_updated
   text name_code
   text family
   text genus
   text species
   text original_ista_2025
   uuid id
}
class task {
   text name
   integer id
}
class user_role_permissions {
   uuid user_id
   uuid role_id
   text role_name
   uuid rp_id
   text permission_name
   uuid rr_id
   text resource_name
}
class users {
   text email
   timestamp with time zone date_created
   timestamp with time zone date_updated
   uuid default_folder_id
   uuid organization
   boolean active
   uuid id
}

annotation  -->  picture : picture_id:id
annotation  -->  pipeline : pipeline_id:id
annotation  -->  users : user_id:id
change_log  -->  schema_version : schema_version_id:id
change_log  -->  users : user_id:id
device_lens  -->  device_brand : device_brand_id:id
device_model  -->  device_brand : device_brand_id:id
folder  -->  users : user_id:id
model  -->  task : task_id:id
object  -->  annotation : inference_id:id
object  -->  picture : picture_id:id
object  -->  pipeline : pipeline_id:id
object  -->  seed : top_id:id
object  -->  users : user_id:id
picture  -->  device_lens : device_lens_id:id
picture  -->  device_model : device_model_id:id
picture  -->  folder : folder_id:id
picture  -->  users : user_id:id
pipeline_model  -->  model : model_id:id
pipeline_model  -->  pipeline : pipeline_id:id
rbac_role_permission_resource  -->  rbac_permission : permission_id:id
rbac_role_permission_resource  -->  rbac_resource : resource_id:id
rbac_role_permission_resource  -->  rbac_role : role_id:id
rbac_user_role  -->  rbac_role : role_id:id
rbac_user_role  -->  users : user_id:id
user_role_permissions  -->  users : user_id:id
users  -->  organization : organization:id
```

## schema_version

```text
class schema_version {
   uuid id
   text semver
   timestamp with time zone date_created
}
```

- The `schema_version` table tracks the version of the database schema using semantic versioning (semver). This table is essential for managing and documenting changes to the database structure over time. Previously new schemas were created without moving data. In production, migrations are necessary to preserve data and this table helps track which version of the schema is currently in use. This is in addition to using a migration tool like Alembic which is tracked in the codebase.
- The `id` field is a unique identifier for each schema version entry.
- The `semver` field contains the semantic version string (e.g., "1.0.0") representing the version of the schema.
- The `date_created` field records the timestamp when the schema version entry was created.
- create access - cfia admin
- select access - cfia admin
- update access - none
- delete access - none

## annotation

```text
class annotation {
   json raw_data
   uuid picture_id
   timestamp with time zone date_created
   uuid user_id
   uuid pipeline_id
   uuid org_admin_id
   uuid id
}
```

- The `annotation` table stores the results of image annotations, including raw data, associated picture, user, and pipeline information. Each annotation is linked to a specific picture and user, ensuring traceability and accountability.
- The `raw_data` field contains the annotation details in JSON format, allowing for flexibility in storing various types of annotation data.
- The `date_created` field records the timestamp when the annotation was created, which is essential for tracking the history of annotations.
- The `org_admin_id` field links to the organization administrator role id
- The `id` field is a unique identifier for each annotation, ensuring that each entry can be distinctly referenced.
- Indexes on `picture_id`, `user_id`, and `pipeline_id` can be created to optimize query performance when filtering annotations by these fields.
- Foreign key constraints should be established for `picture_id`, `user_id`, and `pipeline_id` to maintain referential integrity with the respective tables.
- Immutable after creation, corrections and feedback should be handled via a new annotation entry and corresponding object records.
- Immutable so we can track pipeline performance and feedback over time.
- create access - authenticated users
- select access - authenticated users with row level security to limit to their user_id or org_admin_id or cfia admin
- update access - none
- delete access - none

## change_log

```text
class change_log {
   timestamp with time zone date_created
   uuid schema_version_id
   uuid user_id
   text table
   uuid entry_id
   uuid action_id
   json value_prev
   json value_new
   uuid id
}
```

- The `change_log` table is designed to track changes made to various entries in the database, providing a historical record of data changes initiated by users. This is in contrast to migrations, which are schema changes managed by developers. The `change_log` captures user-initiated modifications to data entries, ensuring transparency and accountability.
- The `date_created` field records the timestamp of when the change was made.
- The `schema_version_id` field links to the version of the database schema at the time of the change, which helps in understanding the context of the change.
- The `user_id` field identifies the user who made the change.
- The `table` field specifies the name of the table where the change occurred, allowing for easy identification of the affected data.
- The `entry_id` field is the unique identifier of the specific entry that was changed.
- The `action_id` field indicates the type of action performed (e.g., create, update, delete).
- The `value_prev` and `value_new` fields store the previous and new values of the entry in JSON format, providing a clear record of what was changed.
- The `id` field is a unique identifier for each change log entry.
- Indexes on `user_id`, `table`, and `entry_id` can be created to optimize query performance when filtering change logs by these fields.
- Foreign key constraints should be established for `user_id` and `schema_version_id` to maintain referential integrity with the respective tables.
- Immutable after creation to ensure an accurate historical record of changes.
- create access - authenticated users
- select access - cfia admin
- update access - none
- delete access - none

## device_brand

```text
class device_brand {
   text name
   text description
   boolean active
   uuid id
}
```

- The `device_brand` table stores information about different brands of devices used for capturing images. This table is essential for categorizing and managing device-related data, which can impact image quality and analysis results.
- The `name` field contains the name of the device brand.
- The `description` field provides additional details about the brand, which can be useful for users to understand the characteristics of the devices associated with that brand.
- The `active` field indicates whether the brand is currently active or disabled, allowing for easy management of available brands.
- The `id` field is a unique identifier for each device brand.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## device_lens

```text
class device_lens {
   text name
   text description
   boolean active
   uuid device_brand_id
   uuid id
}
```

- The `device_lens` table stores information about different lenses associated with device brands. This table is crucial for capturing the specifics of the lenses used in image acquisition, which can significantly affect image quality and analysis outcomes.
- The `name` field contains the name of the device lens.
- The `description` field provides additional details about the lens, which can help users understand its characteristics and suitability for various imaging tasks.
- The `active` field indicates whether the lens is currently active or disabled, allowing for effective management of available lenses.
- The `device_brand_id` field links to the `device_brand` table, establishing a relationship between lenses and their respective brands.
- The `id` field is a unique identifier for each device lens.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## device_model

```text
class device_model {
   text name
   text description
   boolean active
   uuid device_brand_id
   uuid id
}
```

- The `device_model` table stores information about different models of devices associated with device brands. This table is vital for capturing the specifics of the devices used in image acquisition, which can significantly influence image quality and analysis results.
- The `name` field contains the name of the device model.
- The `description` field provides additional details about the model, which can help users understand its features and capabilities.
- The `active` field indicates whether the model is currently active or disabled, allowing for effective management of available models.
- The `device_brand_id` field links to the `device_brand` table, establishing a relationship between models and their respective brands.
- The `id` field is a unique identifier for each device model.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## folder

```text
class folder {
   uuid user_id
   timestamp with time zone date_created
   text name
   text folder_prefix
   text description
   uuid org_admin_id
   boolean active
   uuid id
}
```

- The `folder` table organizes images into user-defined folders.
- folders are virtual and do not represent actual filesystem directories.
- image blobs are stored in object storage with a flat namespace identified by uuids.
- since folders are also virtual in object storage, this will avoid renaming blobs which results in a full read and write of the object, saving on bandwidth and costs.
- `folder_prefix` is a string for display purposes only in the frontend.
- `active` allows users to disable folders without deleting them, preserving data integrity.
- create access - authenticated users
- select access - authenticated users with row level security to limit to their user_id or org_admin_id or cfia admin
- update access - none
- delete access - none

## model

```text
class model {
   text name
   text endpoint_name
   integer task_id
   timestamp with time zone date_created
   text version
   text api_url
   text api_key
   text content_type
   text deployment_platform
   text created_by
   timestamp with time zone date_model_training
   text description
   text job_name  /* Training job name */
   text dataset  /* training dataset id */
   text artifacts_url
   text sha256
   uuid id
}
```

- The `model` table stores information about machine learning models used for image annotation and analysis. This table is essential for managing and tracking the various models deployed in the system, including their configurations, versions, and deployment details.
- The `name` field contains the name of the model
- The `endpoint_name` field specifies the name of the endpoint where the model is deployed, which is crucial for making API calls to the model.
- The `task_id` field links to the `task` table, indicating the specific task the model is designed to perform (e.g., classification, detection).
- The `date_created` field records the timestamp when the model entry was created.
- The `version` field indicates the version of the model
- The `api_url` field contains the URL of the API endpoint for accessing the model.
- The `api_key` field stores the API key required for authenticating requests to the model endpoint.
- The `content_type` field specifies the content type expected by the model API (e.g., application/json, image/jpeg).
- The `deployment_platform` field indicates the platform where the model is deployed (e.g., AWS SageMaker, Azure ML).
- The `created_by` field identifies the user who created the model.
- The `date_model_training` field records the timestamp when the model was trained.
- The `description` field provides additional details about the model, which can be useful for users to understand its purpose and capabilities.
- The `job_name` field stores the name of the training job associated with the model for cross-referencing.
- The `dataset` field contains the identifier of the dataset used for training the model.
- The `artifacts_url` field provides a URL to access the model artifacts, such as weights and configuration files.
- The `sha256` field stores the SHA-256 hash of the model artifacts for integrity verification.
- The `id` field is a unique identifier for each model entry.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## object

```text
class object {
   uuid inference_id
   uuid top_id
   uuid top_id_2
   timestamp with time zone date_verified
   double precision top_score
   double precision top_score_2
   uuid top_id_3
   double precision top_score_3
   timestamp with time zone date_created
   boolean valid
   boolean box_update
   boolean species_update
   uuid user_id
   uuid picture_id
   uuid org_admin_id
   uuid feedback_user_id
   uuid verifier_user_id
   uuid pipeline_id
   timestamp with time zone date_feedback
   integer bot_y_abs
   integer bot_x_abs
   integer top_y_abs
   integer top_x_abs
   uuid id
}
```

- The `object` table stores information about individual objects detected in images during the annotation process. This table is crucial for capturing the details of each detected object, including its classification, confidence scores, bounding box coordinates, and verification status.
- The `object` table also stores user provided corrections and feedback on the annotations.
- The `inference_id` field links to the `annotation` table, indicating the specific annotation (inference) that detected the object.
- The `top_id`, `top_id_2`, and `top_id_3` fields link to the `seed` table, representing the top three predicted species for the detected object.
- The `top_score`, `top_score_2`, and `top_score_3` fields store the confidence scores associated with the top three predictions.
- The `date_verified` field records the timestamp when the object was verified by a cfia admin.
- The `date_created` field records the timestamp when the object entry was created.
- The `date_feedback` field records the timestamp when feedback was provided by a user.
- The `valid` field indicates whether the detected object is considered valid based on user feedback.
- The `box_update` field indicates whether the bounding box of the object has been updated based on user feedback. This specifies that the coordinates of the bounding box on this object have been modified from the original inference.
- The `species_update` field indicates whether the species classification of the object has been updated based on user feedback. This specifies that the top_id fields have been modified from the original inference. The top 2 and 3 fields should be null if species_update is true.
- The `user_id` field identifies the user who generated the original inference.
- The `picture_id` field links to the `picture` table, indicating the image in which the object was detected.
- The `org_admin_id` field links to the organization administrator role id
- The `feedback_user_id` field identifies the user who provided feedback on the object. This field is null if no feedback has been provided. Positive feedback is indicated by setting the `valid` field to true, while negative feedback is indicated by setting it to false.
- The `verifier_user_id` field identifies the cfia admin who verified the object. This field is null if the object has not been verified.
- The `pipeline_id` field links to the `pipeline` table, indicating the pipeline used for the annotation.
- The `bot_y_abs`, `bot_x_abs`, `top_y_abs`, and `top_x_abs` fields store the absolute coordinates of the bounding box for the detected object within the image.
- The `id` field is a unique identifier for each object entry.
- Positive feedback is indicated by setting the `valid` field to true, while negative feedback is indicated by setting it to false.
- Negative feedback does not delete the object, it simply marks it as invalid.
- Negative feedback should result in a new object entry with the corrected information and the original object entry should remain for historical purposes.
- Verifiers will verify all objects in an annotation, not just those with feedback.
- create access - authenticated users
- select access - authenticated users with row level security to limit to their user_id or org_admin_id or cfia admin
- update access - authenticated users can update their own objects with feedback, cfia admin can update any object for verification
- delete access - none

## organization

```text
class organization {
   text name
   text folder_prefix
   boolean active
   uuid id
}
```

- The `organization` table stores information about different organizations using the system. This table is essential for managing and categorizing users and their associated data based on organizational affiliation.
- create access - cfia admin
- select access - cfia admin
- update access - cfia admin
- delete access - none

## picture

```text
class picture {
   uuid folder_id
   boolean active
   timestamp with time zone date_created
   text sha256
   double precision magnification
   uuid single_species_image  /* for training, multiple seeds of the same species will be in t... */
   uuid user_id
   uuid org_admin_id
   text name
   uuid device_model_id
   uuid device_lens_id
   integer blob_url
   text format
   integer width
   integer height
   text description
   double precision size_on_disk
   uuid id
}
```

- The `picture` table stores metadata about images uploaded to the system. This table is crucial for managing and organizing images, as well as linking them to users, folders, and device information. It is critical that this table stay in sync with blob storage where the actual image files are stored.
- The `folder_id` field links to the `folder` table, indicating the folder in which the picture is stored. this is a virtual folder and does not represent an actual filesystem directory. This is solely for the purpose of organizing images in the frontend.
- The `active` field indicates whether the picture is currently active or disabled.
- The `date_created` field records the timestamp when the picture entry was created.
- The `sha256` field stores the SHA-256 hash of the picture file.
- The `magnification` field captures the magnification level used when capturing the image, which can be important for analysis.
- The `single_species_image` field links to the `seed` table, indicating the species depicted in the image if it contains a single species. This is primarily used for training purposes.
- The `user_id` field identifies the user who uploaded the picture.
- The `org_admin_id` field links to the organization administrator role id
- The `name` field contains the name of the picture.
- The `device_model_id` field links to the `device_model` table.
- The `device_lens_id` field links to the `device_lens` table.
- The `blob_url` field stores the URL or identifier for accessing the actual image file in blob storage.
- The `format` field specifies the image format (e.g., JPEG, PNG).
- The `width` and `height` fields store the dimensions of the image in pixels.
- The `description` field provides additional details about the picture.
- The `size_on_disk` field records the size of the image file in bytes.
- The `id` field is a unique identifier for each picture entry.
- pictures are deduplicated based on sha256, if a picture with the same sha256 already exists, the existing entry is returned and no new entry is created.
- pictures are deduplicated on an organization level, meaning two different organizations can upload the same picture and it will be stored twice, once for each organization.
- pictures are immutable, if a user wants to update the metadata, they must upload a new picture.
- pictures are never deleted, they are only marked as inactive. This is to ensure that annotations and objects linked to the picture remain valid.
- create access - authenticated users
- select access - authenticated users with row level security to limit to their user_id or org_admin_id or cfia admin
- update access - none
- delete access - none

## pipeline

```text
class pipeline {
   text name
   boolean active
   boolean is_default
   json data
   uuid id
}
```

- The `pipeline` table stores information about annotation pipelines used in the system. This table is essential for managing and configuring the various pipelines that process images and generate annotations.
- pipelines specify the sequence of models to be used for annotation and any parameters required for each model.
- pipelines are versioned by creating a new pipeline entry, existing annotations are linked to the pipeline used at the time of annotation.
- pipelines are hard linked to model versions via the pipeline_model table. A version change of a model requires a new pipeline_model entry.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## pipeline_model

```text
class pipeline_model {
   uuid pipeline_id
   uuid model_id
   uuid id
}
```

- The `pipeline_model` table establishes a many-to-many relationship between pipelines and models. This table is crucial for defining which models are included in each pipeline, allowing for flexible and modular pipeline configurations.
- create access - cfia admin
- select access - authenticated users
- update access - none
- delete access - none

## seed

```text
class seed {
   json metadata
   boolean active
   timestamp with time zone date_created
   timestamp with time zone date_updated
   text name_code
   text family
   text genus
   text species
   text original_ista_2025
   uuid id
}
```

- The `seed` table stores information about different seed species. This table is essential for managing and categorizing the various species that can be identified in images, providing a reference for annotations and analyses.
- The `metadata` field contains additional information about the seed species in JSON format.
- The `active` field indicates whether the seed species is currently active or disabled.
- The `date_created` field records the timestamp when the seed entry was created.
- The `date_updated` field records the timestamp when the seed entry was last updated.
- The `name_code` field contains a unique code representing the seed species. Based on ISTA list.
- The `family`, `genus`, and `species` fields store the taxonomic classification of the seed species.
- The `original_ista_2025` field contains the original ISTA 2025 name entry.
- The `id` field is a unique identifier for each seed entry.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## task

```text
class task {
   text name
   integer id
}
```

- The `task` table stores information about different tasks that machine learning models can perform. This table is essential for categorizing models based on their intended function, such as classification or detection.
- create access - cfia admin
- select access - authenticated users
- update access - cfia admin
- delete access - none

## users

```text
class users {
   text email
   timestamp with time zone date_created
   timestamp with time zone date_updated
   uuid default_folder_id
   uuid organization
   boolean active
   uuid id
}
```

- The `users` table stores information about users of the system. This table is crucial for managing user accounts, their associated data, and organizational affiliations.
- The `email` field contains the user's email address, which serves as a unique identifier for each user.
- The `date_created` field records the timestamp when the user account was created.
- The `date_updated` field records the timestamp when the user account was last updated.
- The `default_folder_id` field links to the `folder` table, indicating the user's default folder for organizing images.
- The `organization` field links to the `organization` table, indicating the organization to which the user belongs.
- The `active` field indicates whether the user account is currently active or disabled.
- The `id` field is a unique identifier for each user account.
- create access - cfia admin
- select access - cfia admin
- update access - cfia admin
- delete access - none

## RBAC Tables

```text
class rbac_permission {
   text name
   uuid id
}
class rbac_resource {
   text name
   uuid id
}
class rbac_role {
   text name
   text description
   boolean active
   uuid id
}
class rbac_role_permission_resource {
   uuid role_id
   uuid permission_id
   uuid resource_id
}
class rbac_user_role {
   timestamp with time zone date_created
   boolean active
   uuid user_id
   uuid role_id
}
class user_role_permissions {
   uuid user_id
   uuid role_id
   text role_name
   uuid rp_id
   text permission_name
   uuid rr_id
   text resource_name
}
```

- The RBAC (Role-Based Access Control) tables manage permissions, roles, and resources within the system. These tables are essential for implementing a robust access control mechanism, ensuring that users have appropriate access to system functionalities based on their roles.
- The `rbac_permission` table defines various permissions that can be granted to roles. example permissions include create, read, update, delete, get, list, allow
- The `rbac_resource` table defines different resources within the system that can be protected by permissions. example resources api end points, e.g., picture, annotation, object, model, pipeline, folder, seed, user, organization
- The `rbac_role` table defines roles that can be assigned to users. Each role can have multiple permissions associated with it.
- The `rbac_role_permission_resource` table establishes a many-to-many relationship between roles, permissions, and resources. This table specifies which permissions are granted to which roles for specific resources.
- The `rbac_user_role` table establishes a many-to-many relationship between users and roles. This table indicates which roles are assigned to which users.
- The `user_role_permissions` table is a denormalized view that combines information from the `rbac_user_role` and `rbac_role_permission_resource` tables. This view provides a comprehensive overview of the permissions assigned to each user based on their roles.
- create access - cfia admin
- select access - cfia admin
- update access - cfia admin
- delete access - none
