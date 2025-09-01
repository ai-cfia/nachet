# End-to-End Testing with Playwright

This directory contains end-to-end tests for the Nachet application using [Playwright](https://playwright.dev/).

## Overview

The e2e tests verify the complete user workflows of the Nachet seed identification system, testing the integration between the React frontend, Python Quart backend, and external ML services.

## Prerequisites

### 1. Install Dependencies

From the project root:

```bash
npm install
```

### 2. Install Playwright Browsers

```bash
npx playwright install
sudo npx playwright install-deps
```

### 3. Environment Setup

Follow the instructions in the [DEVELOPER.md](../DEVELOPER.md) to set up the development environment:

The tests expect:

- Frontend at `http://localhost:5173`
- Backend API at `http://localhost:8080`

### 4. VS Code Setup (Optional)

If using VS Code, install the [Playwright Test for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-playwright.playwright) extension for enhanced test running and debugging capabilities.

## Running Tests

### Run All Tests

```bash
npx playwright test
```

### Run Tests in Headed Mode

```bash
npx playwright test --headed
```

### Run Specific Test File

```bash
npx playwright test tests/seed-identification.spec.ts
```

### Run Tests with Debug Mode

```bash
npx playwright test --debug
```

### Codegen for Test Creation

if you are running the app locally, you can use codegen to generate test code by running:

```bash
npx playwright codegen <your-frontend-ip>:port
```

This will open a browser window where you can interact with the app, and Playwright will generate the corresponding test code in the terminal.

if you are developing on a remote system via vscode ssh, you can use port forwarding to access the remote app from your local machine. For example, if your remote app is running on port 5173, you can forward it to your local machine using the vscode port forwarding feature. You would have to install the Playwright extension on your local machine separately. then when you run npx playwright codegen localhost:5173, it will open a browser window on your local machine where you can interact with the remote app, and Playwright will generate the corresponding test code in the terminal on your remote machine.

### Other useful commands

```bash
# Runs the end-to-end tests.
  npx playwright test
    
# Starts the interactive UI mode.
  npx playwright test --ui
    
# Runs the tests only on Desktop Chrome.
  npx playwright test --project=chromium
    
# Runs the tests in a specific file.
  npx playwright test example
    
# Runs the tests in debug mode.
  npx playwright test --debug
    
# Auto generate tests with Codegen.
  npx playwright codegen
    

# We suggest that you begin by typing:

    npx playwright test

And check out the following files:
  - ./e2e/example.spec.ts - Example end-to-end test
  - ./e2e/demo-todo-app.spec.ts - Demo Todo App end-to-end tests
  - ./playwright.config.ts - Playwright Test configuration

Visit https://playwright.dev/docs/intro for more information. ✨
```

## Test Structure

### Core Test Scenarios

1. **User Authentication**
   - Login/logout flows
   - Session persistence
   - Access control verification

2. **Image Upload & Processing**
   - Single image upload
   - Batch image processing
   - File validation and error handling

3. **Seed Identification Workflow**
   - ML pipeline execution
   - Results display and interaction
   - Inference history

4. **Data Management**
   - Picture gallery browsing
   - Result filtering and search
   - Export functionality

### Test Organization

```text
e2e/ # test files
playwright.config.ts     # Playwright configuration
```

## Configuration

### Playwright Config

The `playwright.config.ts` file should configure:

- Base URLs for frontend/backend
- Test timeouts appropriate for ML processing
- Browser types (Chromium, Firefox, WebKit)
- Screenshot/video capture on failure
- Test parallelization settings

### Environment Variables

Create `.env.test` file with:

```bash
# Test-specific configuration
NACHET_FRONTEND_URL=http://localhost:5173
NACHET_BACKEND_URL=http://localhost:8080
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpassword
```

## Test Data

### Sample Images

Store test seed images in `fixtures/test-images/`:

- Various seed types for classification testing
- Different image qualities and formats
- Edge cases (blurry, multiple seeds, etc.)

### Test Database

Consider using a separate test database:

- Isolated from development data
- Reset between test runs
- Pre-populated with test users and baseline data

## Best Practices

### Test Writing

- Use descriptive test names that explain the user scenario
- Implement proper wait strategies for async operations (ML inference)
- Use Page Object Model for reusable UI interactions
- Mock external services when appropriate

### Performance Considerations

- ML inference can be slow - set appropriate timeouts
- Consider parallel test execution carefully
- Use test fixtures to share setup between tests

### Debugging

- Use `await page.pause()` for interactive debugging
- Enable trace recording for failed tests
- Take screenshots at key points in complex workflows

## Continuous Integration

### GitHub Actions Integration

```yaml
- name: Run Playwright Tests
  run: |
    npm ci
    npx playwright install --with-deps
    npm run test:e2e
```

### Test Reports

Playwright generates HTML reports by default:

```bash
npx playwright show-report
```

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase timeout for ML inference operations
2. **Authentication Issues**: Verify test user credentials and session handling
3. **Image Upload Failures**: Check Azure Storage connectivity in test environment
4. **Flaky Tests**: Implement proper wait strategies for dynamic content

### Debug Commands

```bash
# Run with verbose output
npx playwright test --verbose

# Generate trace for failed tests
npx playwright test --trace on

# Run single test with debug
npx playwright test --debug tests/specific-test.spec.ts
```

## Contributing

When adding new e2e tests:

1. Follow the existing test structure and naming conventions
2. Add appropriate test data to fixtures
3. Update this README with new test scenarios
4. Ensure tests are deterministic and can run in parallel
5. Add proper error handling and cleanup

## Related Documentation

- [Frontend Testing Guide](../frontend/TESTING.md)
- [Backend Testing Guide](../backend/TESTING.md)
- [Playwright Documentation](https://playwright.dev/docs/intro)
