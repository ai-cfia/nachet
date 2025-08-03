# Input Field Audit

This document lists all frontend components containing input fields (TextField, Input, Select, Checkbox, etc.) in the codebase.

---

## Components with Input Fields

### 1. `load_image_popup/index.tsx`

- Uses: `<Input />` (MUI)
- Path: `frontend/src/components/body/load_image_popup/index.tsx`

### 2. `create_directory_popup/index.tsx`

- Uses: `<TextField />` (MUI)
- Path: `frontend/src/components/body/create_directory_popup/index.tsx`

### 3. `switch_device_popup/index.tsx`

- Uses: `<Select />` (MUI)
- Path: `frontend/src/components/body/switch_device_popup/index.tsx`

### 4. `authentication/signup.tsx`

- Uses: `<TextField />`, `<Checkbox />` (MUI)
- Path: `frontend/src/components/body/authentication/signup.tsx`

### 5. `batch_upload_popup/BatchUploadPopup.tsx`

- Uses: `<TextField />`, `<input />` (MUI and native)
- Path: `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx`

### 6. `save_capture_popup/index.tsx`

- Uses: `<TextField />` (MUI)
- Path: `frontend/src/components/body/save_capture_popup/index.tsx`

### 7. `feedback_form/FeedbackForm.tsx`

- Uses: `<TextField />` (MUI)
- Path: `frontend/src/components/body/feedback_form/FeedbackForm.tsx`

### 8. `creative_commons_popup/index.tsx`

- Uses: `<TextArea />` (custom styled)
- Path: `frontend/src/components/body/creative_commons_popup/index.tsx`

---

**Note:**

- Only direct usages of input components are listed.
- For more details, see the respective component files.
