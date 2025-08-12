# Nachet CLASSIFY Button Data Journey

This document maps the complete data flow when a user clicks the "CLASSIFY" button in the Nachet frontend, tracing the journey from UI interaction through API calls to database persistence and blob storage.

## Data Journey Overview

### 1. Frontend Button Click

**Location**: `/frontend/src/components/body/microscope_feed/MicroscopeFeed.tsx:427-433`

```tsx
<ButtonMicroscopeFeed
  label="CLASSIFY"
  icon={<CropFreeIcon color="inherit" style={iconStyle} />}
  disabled={isWebcamActive || imageCache.length == 0}
  onClick={() => {
    handleInference();
  }}
/>
```

**Trigger**: User clicks CLASSIFY button
**Handler**: `handleInference()` prop function

---

### 2. Root Handler Function

**Location**: `/frontend/src/root/body/body.tsx:171-202`

```tsx
const handleInferenceRequest = (): void => {
  // makes a post request to the backend to get inference data for the current image
  if (curDir !== "") {
    const imageObject = imageCache.find((item) => item.index === imageIndex);
    if (imageObject === undefined) {
      return;
    }
    setIsLoading(true);
    inferenceRequest(
      backendUrl,
      selectedModel,
      imageObject,
      curDir,
      props.uuid,
      props.uuid,
    )
    .then((response) => {
      setReadAzureStorage(!readAzureStorage);
      setImageCache(loadResultsToCache(response, imageCache, imageIndex));
      setModelDisplayName(selectedModel);
    })
    // ... error handling
  }
}
```

**Data Passed**:

- `selectedModel`: ML model name (e.g., "Swin transformer")
- `imageObject`: Current image from cache with base64 data
- `curDir`: Target directory name
- `uuid`: User identifier
- `backendUrl`: API endpoint URL

---

### 3. Frontend API Call

**Location**: `/frontend/src/common/api.ts:128-168`

```tsx
export const inferenceRequest = async (
  backendUrl: string,
  selectedModel: string,
  imageObject: Images,
  curDir: string,
  uuid: string,
  container_uuid: string,
): Promise<ApiInferenceData> => {
  const request = {
    method: "post",
    url: `${backendUrl}/inf`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {
      model_name: selectedModel,
      image: imageObject.src, // base64 encoded image
      imageDims: imageObject.imageDims,
      folder_name: curDir,
      user_id: uuid,
      container_name: container_uuid,
    },
  };
  return handleAxios<ApiInferenceData>(request);
};
```

**HTTP Request**:

- **Method**: POST
- **Endpoint**: `/inf`
- **Payload**: JSON with image data, model selection, and user context

---

### 4. Backend API Endpoint

**Location**: `/backend/app.py:641-761`

```python
@app.post("/inf")
async def inference_request():
    """
    Performs inference on an image, and returns the results.
    The image and inference results are uploaded to a folder in the user's container.
    """
    # Extract request data
    data = await request.get_json()
    pipeline_name = data.get("model_name")
    folder_name = data.get("folder_name")
    container_name = data.get("container_name")
    imageDims = data.get("imageDims")
    image_base64 = data.get("image")
    user_id = container_name
    
    # Validation and setup...
    
    # Key operations:
    # 1. Mount Azure container
    # 2. Get/create picture ID in database
    # 3. Run ML pipeline
    # 4. Save inference results to database
    # 5. Return results to frontend
```

**Key Operations**:

1. **Azure Container Mount** (line 690-692)
2. **Database Picture ID Resolution** (line 701-703)  
3. **ML Pipeline Execution** (line 712-720)
4. **Results Processing** (line 724-726)
5. **Database Persistence** (line 739-741)

---

### 5. Azure Blob Storage Operations

**Location**: `/backend/app.py:690-692`

```python
container_client = await azure_storage.mount_container(
    CONNECTION_STRING, container_name, create_container=True
)
```

**Purpose**: Establish connection to user's blob storage container
**Result**: `container_client` for image upload/download operations

---

### 6. Database Picture ID Resolution  

**Location**: `/backend/app.py:701-703` → `/backend/storage/datastore_storage_api.py:109-116`

```python
# Backend endpoint
picture_id = await datastore.get_picture_id(
    cursor, user_id, image_bytes, container_client
)

# Datastore function
async def get_picture_id(cursor, user_id, image, container_client):
    """
    Return the picture_id of the image
    """
    return await nachet_datastore.upload_picture_unknown(cursor, str(user_id), image, container_client)
```

**Database Operations**:

- Check if image already exists in database
- If new image: Create new picture record and upload to blob storage
- If existing: Return existing picture_id
- **Tables Affected**: `picture_set`, potentially `picture` tables

---

### 7. ML Pipeline Execution

**Location**: `/backend/app.py:712-720`

```python
pipeline = pipelines_endpoints.get(pipeline_name)

for idx, model in enumerate(pipeline):
    print(f"Entering {model.name.upper()} model")
    result_json = await model.request_function(model, cache_json_result[idx])
    cache_json_result.append(result_json)
```

**Process**:

- Retrieve ML pipeline configuration from cache
- Execute each model in sequence (detection → classification)
- Cache intermediate results between models
- **External Dependencies**: ML model HTTP endpoints (Azure ML)

---

### 8. Results Processing

**Location**: `/backend/app.py:724-726`

```python
processed_result_json = await inference.process_inference_results(
    cache_json_result[-1], imageDims, area_ratio, color_format
)
```

**Processing**:

- Transform raw ML outputs into structured format
- Apply coordinate scaling based on image dimensions
- Apply area ratio filtering and color formatting
- **Result**: Structured inference data with bounding boxes, classifications, scores

---

### 9. Database Inference Persistence

**Location**: `/backend/app.py:739-741` → `/backend/storage/datastore_storage_api.py:142-146`

```python
# Backend endpoint  
saved_result_json = await datastore.save_inference_result(
    cursor, user_id, processed_result_json[0], picture_id, pipeline_name, 1
)

# Datastore function
async def save_inference_result(cursor, user_id:str, inference_dict, picture_id:str, pipeline_id:str, type:int):
    return await nachet_datastore.register_inference_result(cursor, user_id, inference_dict, picture_id, pipeline_id, type)
```

**Database Operations**:

- Insert inference record with results JSON
- Link inference to picture_id and user_id  
- Store pipeline/model metadata
- **Tables Affected**: `inference` table
- **Schema**: `nachet_0.0.12.inference`

---

### 10. Response to Frontend

**Location**: `/backend/app.py:751`

```python
return jsonify(saved_result_json), 200
```

**Response Data**: Complete inference results including:

- Inference ID
- Bounding box coordinates  
- Classification labels and confidence scores
- Processing metadata

---

### 11. Frontend Results Handling

**Location**: `/frontend/src/root/body/body.tsx:187-190`

```tsx
.then((response) => {
  setReadAzureStorage(!readAzureStorage);
  setImageCache(loadResultsToCache(response, imageCache, imageIndex));
  setModelDisplayName(selectedModel);
})
```

**Frontend Updates**:

- Update image cache with inference results
- Trigger Azure storage re-read for updated folder status
- Update UI to display model name
- **UI Components Updated**: Inference boxes, results tables, image annotations

---

## Database Schema Impact

### Tables Modified During CLASSIFY Operation

1. **`nachet_0.0.12.picture_set`**
   - New records created for first-time image uploads
   - Links images to user containers and folders

2. **`nachet_0.0.12.inference`**
   - New inference record created every time CLASSIFY is clicked
   - Stores complete ML results as JSON
   - Links to picture_id, user_id, and pipeline information

### SQL Verification Queries for E2E Tests

```sql
-- Verify picture was stored
SELECT ps.id, ps.name, ps.upload_date 
FROM "nachet_0.0.12".picture_set ps 
WHERE ps.owner_id = 'test-user-uuid';

-- Verify inference was recorded
SELECT i.id, i.status, i.created_date, i.inference_dict 
FROM "nachet_0.0.12".inference i
JOIN "nachet_0.0.12".picture_set ps ON i.picture_set_id = ps.id
WHERE ps.owner_id = 'test-user-uuid'
ORDER BY i.created_date DESC;

-- Verify ML pipeline was recorded
SELECT i.pipeline_name, i.type, COUNT(*) as inference_count
FROM "nachet_0.0.12".inference i
JOIN "nachet_0.0.12".picture_set ps ON i.picture_set_id = ps.id  
WHERE ps.owner_id = 'test-user-uuid'
GROUP BY i.pipeline_name, i.type;
```

## Performance Characteristics

**Typical Response Time**: 5-15 seconds
**Rate Limiting**: Per user, based on container quotas
**Failure Points**:

- ML model endpoint availability
- Azure blob storage connectivity  
- Database connection pool exhaustion
- Base64 image size limits

## Security Considerations

**Data Isolation**: User images stored in separate Azure containers
**Authentication**: User UUID validation throughout pipeline
**Data Persistence**: All images and results permanently stored
**Audit Trail**: Complete inference history maintained in database

This data journey shows the complete flow from a simple button click through complex ML processing to persistent storage, making it ideal for comprehensive E2E testing with both UI automation and database verification.

## Deep Dive: Database Picture ID Resolution

### The Misleading Function Name

The function called `get_picture_id()` is actually misleading - it doesn't just "get" an existing picture ID, but **creates new database records and uploads to blob storage every single time**.

### Complete Picture ID Resolution Flow

#### 1. Entry Point

**Location**: `/backend/app.py:701-703`

```python
picture_id = await datastore.get_picture_id(
    cursor, user_id, image_bytes, container_client
)
```

#### 2. Datastore Wrapper  

**Location**: `/backend/storage/datastore_storage_api.py:109-116`

```python
async def get_picture_id(cursor, user_id, image, container_client):
    """
    Return the picture_id of the image
    """
    return await nachet_datastore.upload_picture_unknown(cursor, str(user_id), image, container_client)
```

#### 3. Core Upload Logic

**Location**: `/datastore/nachet/__init__.py:62-119`

```python
async def upload_picture_unknown(
    cursor, user_id, picture_hash, container_client, picture_set_id=None
):
    """
    Upload a picture that we don't know the seed to the user container
    """
    try:
        # 1. Validate user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(f"User not found: {user_id}")

        empty_picture = json.dumps([])  # Empty metadata initially

        # 2. Determine target folder
        default_picture_set = str(user.get_default_picture_set(cursor, user_id))
        if picture_set_id is None or str(picture_set_id) == default_picture_set:
            picture_set_id = default_picture_set
            folder_name = "General"  # Default folder
        else:
            folder_name = picture.get_picture_set_name(cursor, picture_set_id)

        # 3. Create NEW database record (always creates new, no duplicate detection!)
        picture_id = picture.new_picture_unknown(
            cursor=cursor,
            picture=empty_picture,           # Start with empty metadata 
            picture_set_id=picture_set_id,   # Link to folder
        )
        
        # 4. Upload to Azure Blob Storage
        response = await azure_storage.upload_image(
            container_client, folder_name, str(picture_set_id), picture_hash, str(picture_id)
        )
        
        # 5. Update database with blob storage link
        data = {
            "link": azure_storage.build_blob_name(folder_name, str(picture_id)),
            "description": "Uploaded through the API",
        }
        picture.update_picture_metadata(cursor, picture_id, json.dumps(data), 0)

        return picture_id
    except Exception:
        # Error handling...
```

#### 4. Database INSERT Operation

**Location**: `/datastore/datastore/db/queries/picture/picture.py:78-108`

```sql
INSERT INTO "nachet_0.0.12".picture(
    picture,           -- JSON metadata (initially empty [])
    picture_set_id,    -- UUID of folder (General or custom)
    nb_obj             -- Number of objects (0 initially)
)
VALUES (?, ?, ?)
RETURNING id          -- New UUID generated for picture
```

### Key Behavioral Insights

#### No Duplicate Detection

- **Every CLASSIFY click creates a NEW picture record** - no deduplication
- Same image uploaded multiple times = multiple database entries  
- Each gets unique `picture_id` UUID

#### Database Operations Per Classification

```sql
-- 1. Insert new picture record
INSERT INTO "nachet_0.0.12".picture (picture, picture_set_id, nb_obj) 
VALUES ('[]', 'user-folder-uuid', 0);

-- 2. Update picture metadata with blob link  
UPDATE "nachet_0.0.12".picture 
SET picture = '{"link": "General/picture-uuid", "description": "Uploaded through the API"}'
WHERE id = 'new-picture-uuid';
```

#### Blob Storage Operations

- Image uploaded to: `{container}/{folder_name}/{picture_id}`
- Folder structure: `General/` (default) or custom folder names
- Blob name format: `azure_storage.build_blob_name(folder_name, picture_id)`

### E2E Testing Verification Points

For every CLASSIFY button click, you can verify:

```sql
-- Verify new picture was created
SELECT COUNT(*) FROM "nachet_0.0.12".picture 
WHERE picture_set_id = 'test-user-folder-uuid'
AND created_date > 'test-start-time';

-- Verify blob storage metadata  
SELECT picture FROM "nachet_0.0.12".picture 
WHERE id = 'new-picture-uuid';
-- Should contain: {"link": "General/picture-uuid", "description": "Uploaded through the API"}

-- Verify folder assignment
SELECT ps.name FROM "nachet_0.0.12".picture p
JOIN "nachet_0.0.12".picture_set ps ON p.picture_set_id = ps.id  
WHERE p.id = 'new-picture-uuid';

-- Verify complete classification record linkage
SELECT p.id as picture_id, i.id as inference_id, i.status 
FROM "nachet_0.0.12".picture p
LEFT JOIN "nachet_0.0.12".inference i ON i.picture_set_id = p.picture_set_id
WHERE p.picture_set_id = 'test-user-folder-uuid'
ORDER BY p.created_date DESC;
```

### Testing Implications

**Critical Insight**: Every classification creates a complete audit trail:

1. **New picture record** with unique UUID
2. **Blob storage upload** with predictable path structure  
3. **Metadata updates** linking database to storage
4. **Inference record** linking results to picture

This makes each CLASSIFY operation fully traceable and verifiable in E2E tests through both database state and blob storage verification.
