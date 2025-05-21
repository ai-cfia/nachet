# Testing Documentation

This document provides detailed instructions and procedures for manually
testing
the various functionalities of Nachet, ensuring that all features operate
correctly and as expected before deployment or release.

## Test Case: Backend URL Warning Functionality

**Objective:** Verify the application correctly displays a warning if
the
backend URL is not set or is non-responsive.

**Preconditions:**

- [ ] The application is open.
- [ ] Nachet Backend is set up and running locally. The Nachet Backend can be
found at:
[Nachet Backend GitHub
Repository](https://github.com/ai-cfia/nachet-backend).
To run the application locally, use the command `hypercorn -b :8080
app:app` in the terminal.
- [ ] The backend URL environment variable is either not set, empty, or
pointing
to a non-responsive server.

**Test Steps:**

1. Start the application.
2. Observe the application's behavior during initialization.

**Expected Results:**

- [ ] If the backend URL is not correctly configured or the server is non-
responsive, a warning message should appear at the top of the screen.
- [ ] The warning message should correctly indicate the issue with the
backend
URL.
- [ ] If the backend URL is correctly configured and the server is
responsive,
no warning message should be displayed.

**Actual Results:**

- [ ] Describe the actual outcome of the test.

**Pass/Fail Criteria:**

- [ ] Pass if the warning message accurately reflects the state of the
backend
URL.
- [ ] Fail if no warning is displayed in the case of a misconfigured or non-
responsive backend, or if a false warning is displayed when the backend is
correctly configured and responsive.

---

## Testing Capture Button Functionality

### Test 1: Capture Snapshot from Microscope/Camera Device

**Objective:** Ensure that the capture button takes a snapshot of the
current
view from the microscope/camera device.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).
- [ ] The microscope/camera device is connected and streaming live feed to
the
application.

**Test Steps:**

1. Navigate to the view where the live feed from the microscope/camera device
is
displayed.
2. Click on the 'Capture' button to take a snapshot of the current view.

**Expected Results:**

- [ ] Upon clicking 'Capture', a snapshot of the live feed is taken and
displayed to the user.
- [ ] The 'Capture' button should become inactive or show a visual cue that
the
snapshot has been taken.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the snapshot is successfully taken and displayed.
- [ ] Fail if the snapshot is not taken, not displayed, or the button does
not
react as expected.

---

### Test 2: Capture Button Disabled on Capture Component View

**Objective:** Validate that the capture button is disabled when the user
is
viewing the captured snapshot.

**Preconditions:**

- [ ] A snapshot has been taken and the user is on the Capture component view
where the snapshot is displayed.

**Test Steps:**

1. Observe the 'Capture' button while on the Capture component view.

**Expected Results:**

- [ ] The 'Capture' button should be visibly disabled or inactive.
- [ ] The user should not be able to click the 'Capture' button again until
they
toggle back to the live feed view.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the 'Capture' button is disabled and cannot be clicked.
- [ ] Fail if the 'Capture' button remains active or can be clicked.

## Testing Switch Button Functionality

### Test 1: Switching Between Webcam Devices

**Objective:** Ensure that the switch button allows the user to change
between
different webcam devices.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).
- [ ] Multiple webcam devices are connected and recognized by the application.

**Test Steps:**

1. Navigate to the view where the live feed from the webcam is displayed.
2. Click on the 'Switch' button.
3. Observe the popup window listing available webcam devices.
4. Select a different webcam device from the list.
5. Confirm the selection and observe the change in the webcam feed.

**Expected Results:**

- [ ] On clicking 'Switch', a popup window appears listing the available
webcam
devices.
- [ ] The webcam feed updates to show the feed from the selected device.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the webcam feed switches correctly to the selected device.
- [ ] Fail if the feed does not switch, the popup does not appear, or the
wrong
feed is displayed.

---

### Test 2: Switch Button Disabled on Capture Component View

**Objective:** Validate that the switch button is disabled when the user
is
viewing the captured snapshot.

**Preconditions:**

- [ ] The user has navigated to the Capture component view, where a
previously
captured snapshot is displayed.

**Test Steps:**

1. Observe the 'Switch' button while on the Capture component view.

**Expected Results:**

- [ ] The 'Switch' button should be visibly disabled or inactive.
- [ ] The user should not be able to interact with the 'Switch' button while
in
the Capture view.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the 'Switch' button is disabled and not interactive.
- [ ] Fail if the 'Switch' button remains active or can be interacted with.

## Testing Classify Button Functionality

### Test 1: Classification and Result Population

**Objective:** Ensure that the classify button correctly triggers
the
classification process and populates the results in the results
table.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).
- [ ] An image or a snapshot is ready for classification.

**Test Steps:**

1. Click on the 'Classify' button after loading an image or taking a snapshot.
2. Wait for a few seconds to allow the classification process to complete.
3. Observe the results table for populated classification results.
4. Check for red boxes overlaying each classified seed in the image.

**Expected Results:**

- [ ] Classification results appear in the results table within a few seconds
after clicking 'Classify'.
- [ ] Each classified seed in the image is overlaid with a red box.
- [ ] Each red box has an associated number that correlates with an entry in
the
results table.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the results are correctly populated and red boxes appear as
expected.
- [ ] Fail if the classification takes too long, results do not appear, or
overlays are incorrect.

---

### Test 2: Classify Button Disabled in Webcam Feed View

**Objective:** Verify that the classify button is disabled when the user
is
viewing the webcam feed.

**Preconditions:**

- [ ] The user is on the webcam feed view, displaying live feed from the
camera.

**Test Steps:**

1. Observe the 'Classify' button while in the webcam feed view.

**Expected Results:**

- [ ] The 'Classify' button should be visibly disabled or inactive.
- [ ] The user should not be able to interact with the 'Classify' button in
this
view.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the 'Classify' button is disabled and non-interactive in the
webcam feed view.
- [ ] Fail if the button remains active or can be interacted with.

## Testing Load Button Functionality

### Test 1: Loading an Image for Classification

**Objective:** Ensure that the load button allows users to select and load
an
image for classification.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).

**Test Steps:**

1. Click on the 'Load' button.
2. Navigate through the file explorer to find an image for classification.
3. Select an image and confirm the selection.
4. Observe whether the selected image is displayed in the capture component and
added to the Captures table.

**Expected Results:**

- [ ] The file explorer opens upon clicking 'Load'.
- [ ] The selected image is displayed in the capture component.
- [ ] The image is added to the Captures table.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the image is loaded and displayed correctly.
- [ ] Fail if the file explorer does not open, the image is not displayed, or
is
not added to the Captures table.

---

### Test 2: Load Button Disabled in Webcam Feed View

**Objective:** Verify that the load button is disabled when viewing the
webcam
feed.

**Preconditions:**

- [ ] The user is on the webcam feed view.

**Test Steps:**

1. Observe the 'Load' button while in the webcam feed view.

**Expected Results:**

- [ ] The 'Load' button should be visibly disabled or inactive.
- [ ] The user should not be able to interact with the 'Load' button in this
view.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the 'Load' button is disabled and non-interactive in the webcam
feed view.
- [ ] Fail if the button remains active or can be interacted with.

## Testing Save Button Functionality

### Test 1: Saving Images and Captures

**Objective:** Ensure that the save button allows users to save images
and
captures locally.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).
- [ ] An image is loaded or a snapshot is taken for saving.

**Test Steps:**

1. Click on the 'Save' button.
2. In the 'Save Capture' pop-out window, navigate between the 'Capture' and
'Cache' tabs.
3. In the 'Capture' tab, enter a filename and select an image format (PNG,
JPEG).
4. In the 'Cache' tab, select images from the 'Captures' table to be saved.
5. Confirm the save action and observe if the image(s) are saved locally on the
computer.

**Expected Results:**

- [ ] The 'Save Capture' pop-out window appears with options to save the
capture
and cache.
- [ ] The image(s) are saved in the selected format to the local storage.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the images are saved successfully in the chosen format.
- [ ] Fail if the save functionality does not work or the saved images are
not
as expected.

---

### Test 2: Save Button Disabled in Webcam Feed View

**Objective:** Verify that the save button is disabled when viewing the
webcam
feed.

**Preconditions:**

- [ ] The user is on the webcam feed view.

**Test Steps:**

1. Observe the 'Save' button while in the webcam feed view.

**Expected Results:**

- [ ] The 'Save' button should be visibly disabled or inactive.
- [ ] The user should not be able to interact with the 'Save' button in this
view.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the 'Save' button is disabled and non-interactive in the webcam
feed view.
- [ ] Fail if the button remains active or can be interacted with.

## Testing Directories Component

### Test 1: Creating a New Directory

**Objective:** Ensure that users can create a new directory successfully.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).

**Test Steps:**

1. Click on the folder icon with a miniature '+' symbol.
2. Observe the 'Create New Directory' pop-up widget.
3. Enter a new directory name in the provided input field.
4. Click on the 'Create' button to create the new directory.
5. Check the DIRECTORIES table to see if the new directory is listed.

**Expected Results:**

- [ ] The 'Create New Directory' pop-up appears upon clicking the folder icon.
- [ ] A new directory is created and appears in the DIRECTORIES table.
- [ ] The user can cancel the creation process by clicking 'Cancel'.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if a new directory is created and listed correctly.
- [ ] Fail if the directory is not created, does not appear, or the pop-up
does
not function correctly.

---

### Test 2: Deleting a Directory

**Objective:** Verify that users can delete an existing directory.

**Preconditions:**

- [ ] The application is open and the user is logged in (if required).
- [ ] There are existing directories in the DIRECTORIES table.

**Test Steps:**

1. Click on the 'X' button beside a directory name in the DIRECTORIES table.
2. Observe the 'Delete Directory' pop-up widget.
3. Confirm the deletion by clicking on the delete button.
4. Check the DIRECTORIES table to ensure the directory is removed.
5. Optionally, click 'Cancel' to cancel the deletion process.

**Expected Results:**

- [ ] The 'Delete Directory' pop-up appears upon clicking the 'X' button.
- [ ] The selected directory is removed from the DIRECTORIES table upon
confirmation.
- [ ] The user can cancel the deletion process by clicking 'Cancel'.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if the directory is deleted successfully.
- [ ] Fail if the directory is not deleted, or if the pop-up does not
function
correctly.

## Testing Directory Selection and Upload Functionality

### Test 1: Selecting a Directory for Uploads

**Objective:** Ensure that users can select a directory to save new captures
or
uploaded images.

**Preconditions:**

- [ ] The application is open, and the user is logged in (if required).
- [ ] Multiple directories are available for selection.

**Test Steps:**

1. Select a directory from the available list in the DIRECTORIES table.
2. Capture a new image or upload an existing image.
3. Check if the new image is added to the currently selected directory folder.

**Expected Results:**

- [ ] The user can successfully select a directory from the DIRECTORIES table.
- [ ] New captures or uploads are added to the selected directory folder.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if new images are correctly added to the selected directory.
- [ ] Fail if images are not added to the selected directory or if directory
selection does not work.

---

### Test 2: Emptying the Captures Table

**Objective:** Verify that users can remove all captures from the
Captures
table.

**Preconditions:**

- [ ] The application is open, and the user is logged in (if required).
- [ ] The Captures table contains one or more captures.

**Test Steps:**

1. Click on the trash icon located in the CAPTURES table title header.
2. Confirm the action if prompted.
3. Observe if all captures are removed from the table.

**Expected Results:**

- [ ] All captures are removed from the Captures table upon clicking the
trash
icon.
- [ ] The user is potentially prompted for confirmation before the captures
are
emptied.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if all captures are successfully removed from the table.
- [ ] Fail if captures remain in the table or the trash icon does not
function
as expected.

## Testing Results Component Functionality

### Test 1: Toggling Between Grouped or Individual Reporting

**Objective:** Ensure that users can toggle between grouped and
individual
reporting in the RESULTS table.

**Preconditions:**

- [ ] The application is open, and the user is logged in (if required).
- [ ] The RESULTS table is populated with classification results.

**Test Steps:**

1. Click on the group/ungroup icon in the RESULTS table.
2. Observe the changes in the presentation of the classification results.
3. Toggle between grouped and individual reporting to test both views.

**Expected Results:**

- [ ] Clicking the icon toggles between grouped and individual reporting
styles.
- [ ] The RESULTS table correctly displays the data according to the selected
reporting style.

**Actual Results:**

- [ ] Describe what actually happened when the test was executed.

**Pass/Fail:**

- [ ] Pass if toggling between the two reporting styles works correctly.
- [ ] Fail if the table does not update or displays the data incorrectly.

---

## Test Case: Populating Model List Based on Environment Setting

**Objective:** Verify that the Results Tuner Popup correctly populates the
model list with real data or test data based on the `VITE_APP_MODE`
environment variable.

### Test 1: Populating with Real Data

**Preconditions:**

- [ ] The application is open and running.
- [ ] The backend server is operational.
- [ ] The `VITE_APP_MODE` environment variable is set to any value other than
`"test"`.

**Test Steps:**

1. Start the application.
2. Navigate to the Results Tuner Popup.
3. Observe the model list to verify that it is populated.
4. Check that the models in the list correspond to data fetched from the
backend server.

**Expected Results:**

- [ ] The model list in the Results Tuner Popup is populated with real data
fetched from the backend server.

**Actual Results:**

- [ ] Describe the actual outcome of the test.

**Pass/Fail Criteria:**

- [ ] Pass if the model list displays real data as expected.
- [ ] Fail if the model list does not populate, populates incorrectly, or
displays test data.

### Test 2: Populating with Test Data

**Preconditions:**

- [ ] The application is open and running.
- [ ] The `VITE_APP_MODE` environment variable is set to `"test"`.

**Test Steps:**

1. Start the application.
2. Navigate to the Results Tuner Popup.
3. Observe the model list to verify that it is populated.
4. Check that the models in the list correspond to the static test data defined
in the application.

**Expected Results:**

- [ ] The model list in the Results Tuner Popup is populated with static test
data.

**Actual Results:**

- [ ] Describe the actual outcome of the test.

**Pass/Fail Criteria:**

- [ ] Pass if the model list displays test data as expected.
- [ ] Fail if the model list does not populate, populates incorrectly, or
displays real data.

## Test Case: Model Selection and Classification Process

**Objective:** Verify the enhanced process where users select an image
classification model through a new popup after clicking the CLASSIFY button,
ensuring the model label is populated in the results only after successful
classification (indicated by a 200 status code from the backend), and that the
user's selection is retained for subsequent uses.

## Test Case: Enhanced Model Selection and Classification Process

### Objective

Verify that the application allows users to select a classification model via a
dedicated "Model Selection" button, which opens a popup for model choice.
Ensure that the "CLASSIFY" button triggers an inference request using the
selected model. Additionally, confirm that a loading icon appears during the
inference request and disappears once the request is completed.

### Test 1: Model Selection via Dedicated Button

**Preconditions:**

- [ ] The application is open and running.
- [ ] The backend server is operational.

**Test Steps:**

1. Click on the "Model Selection" button.
2. Observe the popup to ensure it displays a list of available models.
3. Select a model from the list and close the popup.
4. Verify the selected model is displayed or indicated outside the popup.

**Expected Results:**

- [ ] The popup with the list of models appears upon clicking the "Model
Selection" button.
- [ ] The user can successfully select a model, and the selection is visibly
confirmed.

**Actual Results:**

- [ ] Describe the actual outcome of the test.

**Pass/Fail Criteria:**

- [ ] Pass if the model selection popup functions correctly and the user's
selection is clearly indicated.
- [ ] Fail if the popup does not appear, model selection does not work, or the
selected model is not indicated.

### Test 2: Inference Request and Loading Icon Display

**Preconditions:**

- [ ] A model has been selected using the "Model Selection" button.
- [ ] The "CLASSIFY" button is enabled.

**Test Steps:**

1. Click on the "CLASSIFY" button to start the inference process.
2. Observe the interface for a loading icon indicating the process is in
progress.
3. Wait for the inference request to complete.

**Expected Results:**

- [ ] A loading icon appears immediately after the "CLASSIFY" button is
clicked, signaling that the inference request is in progress.
- [ ] The loading icon disappears, and the results of the inference are
displayed once the request completes successfully.

**Actual Results:**

- [ ] Describe the actual outcome of the test.

**Pass/Fail Criteria:**

- [ ] Pass if the loading icon appears during the inference process and
disappears upon completion, followed by the display of inference results.
- [ ] Fail if the loading icon does not appear, remains visible after
completion, or if the inference results are not displayed.

## Test Case: Viewing Top 5 Classification Results

### Objective: Single Row Expansion

Verify that users can view the top 5 classification results by expanding a
single table row at a time in the RESULTS panel.

### Test 1: Single Row Expansion Functionality

**Objective:** Validate the functionality that allows users to expand a single
row at a time to view detailed classification results.

**Preconditions:**

- The application is open, and the user is logged in (if required).
- The RESULTS table is populated with classification results.

**Test Steps:**

1. Locate a row in the RESULTS table that represents an image classification.
2. Click on the row to trigger the expand functionality.
3. Observe the behavior and check if only the clicked row expands to show
additional information.
4. Click on another row and observe that the previously expanded row collapses
and the new one expands.

**Expected Results:**

- Only the clicked row expands upon selection, revealing the top 5
classification results.
- Upon selecting another row, the previously expanded row collapses
automatically, and the new one expands to show its top 5 results.

**Actual Results:**

- Describe the actual behavior observed when performing the test steps.

**Pass/Fail:**

- Pass if only one row expands at a time and the expansion toggles between rows
correctly.
- Fail if multiple rows can be expanded simultaneously or if the toggling does
not work as expected.

### Test 2: Display Accuracy of Top 5 Results

**Objective:** Verify the accuracy and correct display of the top 5
classification results in an expanded row.

**Preconditions:**

- A row in the RESULTS table is expanded to show the top 5 classification
results.

**Test Steps:**

1. Compare the displayed top 5 results with the expected results based on the
data from the backend.
2. Ensure that the labels and scores are correctly displayed.
3. Verify that scores are formatted correctly (e.g., no scientific notation for
small numbers) and match the backend data.

**Expected Results:**

- The labels and scores of the top 5 results are correctly displayed as per the
backend data.
- Scores are presented in a readable percentage format.

**Actual Results:**

- Describe the actual scores and labels displayed and any discrepancies from
expected data.

**Pass/Fail:**

- Pass if the top 5 results are displayed accurately and match the backend
data.
- Fail if there are inaccuracies in the labels, scores, or formatting issues.

### Test 3: Consistency and Responsiveness of UI/UX

**Objective:** Assess the UI/UX consistency and responsiveness when expanding
and collapsing rows in the RESULTS table.

**Preconditions:**

- At least one row in the RESULTS table can be expanded to view the top 5
classification results.

**Test Steps:**

1. Expand a row and then expand another row to ensure that the application only
allows one expanded row at a time.
2. Resize the browser window to test responsiveness and ensure that the
expanded content adjusts appropriately.
3. Navigate away from and back to the RESULTS table to ensure that the expanded
state is not preserved when navigating away.

**Expected Results:**

- Only one row can be expanded at any given time, and expanding another row
collapses the previously expanded one.
- The UI layout and expanded content adjust correctly to browser window
resizing.
- The expanded state of a row does not persist when navigating away from the
RESULTS table.

**Actual Results:**

- Note any UI glitches, performance issues, or state inconsistencies observed.

**Pass/Fail:**

- Pass if the UI maintains quality and functionality throughout the tests,
allowing only one expanded row at a time.
- Fail if the application allows multiple rows to be expanded simultaneously or
if there are issues with the UI layout or state management.

---
