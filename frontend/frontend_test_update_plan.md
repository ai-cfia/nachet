# Frontend Test Update Plan

## Executive Summary

**Current State**: 39.66% test coverage with 42 passing tests across 10 test files  
**Target State**: 80%+ test coverage with comprehensive testing across all critical components  
**Timeline**: 4-6 weeks for complete implementation  
**Priority**: Critical areas first (API layer, core components), then systematic expansion

## Current Coverage Analysis

### ✅ Well-Tested Areas (>90% coverage)

- **Directory List Components**: 98.55% - Excellent coverage with comprehensive mocking
- **Model Popup**: 95.6% - Well-tested component interactions  
- **Custom Hooks**: 100% - Complete coverage with environment variable testing
- **Classifier Pages**: 100% - Full page-level testing

### ⚠️ Moderately Tested Areas (30-60% coverage)

- **Common API Layer**: 42.85% - Critical but incomplete
- **Cache Utils**: 37.55% - Important image processing logic partially covered
- **Root Body Component**: 55.91% - Main application logic needs expansion

### ❌ Critical Gaps (0% coverage)

- **App.tsx**: 0% - Root application component untested
- **main.tsx**: 0% - Application entry point  
- **Header/Navigation**: 0% - User interface components
- **Footer**: 0% - Application footer
- **Environment Config**: 0% - Configuration management

### 🐛 Active Issues

- **Runtime Error**: `TypeError: Cannot read properties of undefined (reading 'forEach')` at `body.tsx:301`
- **API Response Mocking**: Incomplete mocking causing undefined data access

## Testing Strategy Framework

### Testing Philosophy

1. **API-First Testing**: All external dependencies properly mocked
2. **Component Isolation**: Each component tested in isolation with minimal dependencies
3. **User Journey Testing**: Critical user workflows thoroughly tested
4. **Error Boundary Testing**: Comprehensive error handling validation
5. **Type Safety**: TypeScript interfaces validated through testing

### Testing Patterns (Based on Existing Codebase)

```typescript
// API Testing Pattern
vi.mock("axios");
const mockedAxios = vi.mocked(axios);

// Component Testing Pattern  
import { render, fireEvent, screen } from "@testing-library/react";
import { describe, expect, vi } from "vitest";

// Hook Testing Pattern
import { renderHook, waitFor } from "@testing-library/react";

// Error Testing Pattern
const consoleError = console.error;
console.error = vi.fn();
// ... test code ...
console.error = consoleError;
```

## Priority Implementation Plan

### Phase 1: Critical Infrastructure (Week 1-2)

**Priority: CRITICAL**

#### 1.1 Fix Runtime Errors

- **Target**: `body.tsx:301` forEach error
- **Root Cause**: API response mocking incomplete in tests
- **Solution**:

  ```typescript
  // Proper API response mocking
  mockedAxios.mockResolvedValue({
    status: 200,
    data: {
      folders: [] // Ensure folders array is always present
    }
  });
  ```

#### 1.2 API Layer Expansion (`common/api.ts`)

**Current**: 42.85% → **Target**: 85%

**Missing Test Cases:**

- `inferenceRequest` error scenarios
- `fetchModelMetadata` validation  
- `createAzureStorageDir` edge cases
- `deleteAzureStorageDir` permission errors
- Network timeout handling
- Invalid response format handling

**Implementation Strategy:**

```typescript
describe("inferenceRequest", () => {
  // Existing: Basic success case
  // Add: Image validation errors
  // Add: Invalid UUID handling  
  // Add: Network timeouts
  // Add: Backend service errors (500, 503)
  // Add: Malformed response handling
});
```

#### 1.3 Cache Utils Testing (`common/cacheutils.ts`)

**Current**: 37.55% → **Target**: 75%

**Critical Missing Tests:**

- `fetchArrayBuffer` with invalid TIFF files
- `decodeTiff` error handling
- Canvas rendering edge cases
- Label occurrence calculation accuracy
- Image dimension calculation
- Box drawing validation

### Phase 2: Core Components (Week 2-3)

**Priority: HIGH**

#### 2.1 Root Application Testing (`App.tsx`)

**Current**: 0% → **Target**: 80%

**Test Categories:**

```typescript
describe("App Component", () => {
  it("renders without crashing");
  it("handles window resize events");
  it("manages creative commons agreement state");
  it("handles language switching");
  it("manages authentication state");
  it("handles routing correctly");
  it("manages UUID state properly");
});
```

**Mock Strategy:**

- Mock `react-router-dom` components
- Mock `js-cookie` functionality
- Mock window resize events
- Mock child components (Navbar, Body, Footer)

#### 2.2 Body Component Expansion (`root/body/body.tsx`)

**Current**: 55.91% → **Target**: 85%

**Focus Areas:**

- Directory loading state management
- Image capture workflows
- Model metadata handling
- Error state rendering
- Popup state management
- Backend integration flows

**Critical Test Scenarios:**

```typescript
describe("Body Component - Backend Integration", () => {
  it("handles API failures gracefully");
  it("manages loading states correctly");
  it("validates image upload workflows");
  it("handles inference request errors");
  it("manages cache state properly");
});
```

### Phase 3: User Interface Components (Week 3-4)

**Priority: HIGH**

#### 3.1 Header Components (`components/header/`)

**Current**: 0% → **Target**: 75%

**Components to Test:**

- `navbar/index.tsx` - Navigation functionality
- `appbar/index.tsx` - Application bar interactions

**Test Focus:**

- Authentication state rendering
- Language switching functionality
- Navigation link behavior
- Responsive design behavior
- User interaction flows

#### 3.2 Footer Component (`components/footer/`)

**Current**: 0% → **Target**: 70%

**Test Scenarios:**

- External link rendering
- UUID display functionality
- Responsive layout
- Accessibility compliance

### Phase 4: Feature Components (Week 4-5)

**Priority: MEDIUM**

#### 4.1 Popup Components Enhancement

**Current**: 10-40% → **Target**: 70%

**Components Needing Expansion:**

- `authentication/signup.tsx` (18.93% → 70%)
- `batch_upload_popup/` (12.58% → 70%)
- `feedback_form/` (12.54% → 70%)
- `save_capture_popup/` (24.91% → 70%)

**Testing Strategy:**

- Form validation testing
- File upload simulation
- User interaction workflows
- Error message display
- State management validation

#### 4.2 Specialized Components

- `microscope_feed/` - Camera integration testing
- `classification_results/` - ML result display testing
- `image_cache/` - Cache management testing

### Phase 5: Integration & Performance (Week 5-6)

**Priority: MEDIUM**

#### 5.1 Integration Testing

- Complete user workflows
- Multi-component interactions
- State management across components
- Error propagation testing

#### 5.2 Performance Testing

- Large dataset handling
- Image processing performance
- Memory leak detection
- Cache efficiency testing

## Implementation Guidelines

### Test Structure Standards

```typescript
// File naming: ComponentName.test.tsx
// Location: co-located with source in /tests/ subdirectory

describe("ComponentName", () => {
  // Setup
  beforeEach(() => {
    // Reset mocks and state
  });

  describe("Rendering", () => {
    // Basic rendering tests
  });

  describe("User Interactions", () => {
    // Event handling tests
  });

  describe("Error Handling", () => {
    // Error scenario tests
  });

  describe("Integration", () => {
    // Component integration tests
  });
});
```

### Mocking Standards

#### API Mocking

```typescript
// Standard API mock setup
vi.mock("axios");
const mockedAxios = vi.mocked(axios);

beforeEach(() => {
  mockedAxios.mockClear();
});
```

#### Component Mocking

```typescript
// Mock child components
vi.mock("../ChildComponent", () => ({
  default: vi.fn(() => <div data-testid="mocked-child">Mocked Child</div>)
}));
```

#### Environment Mocking

```typescript
// Environment variable testing
const OLD_ENV = process.env;
beforeEach(() => {
  vi.resetModules();
  process.env = { ...OLD_ENV };
});
afterAll(() => {
  process.env = OLD_ENV;
});
```

### Coverage Targets by Component Type

| Component Type | Target Coverage | Rationale |
|---------------|----------------|-----------|
| API Layer | 85% | Critical infrastructure |
| Core Components | 80% | Main application logic |
| UI Components | 75% | User interface reliability |
| Utility Functions | 90% | Pure function testing |
| Hooks | 95% | Isolated business logic |
| Configuration | 60% | Simple configuration files |

## Risk Mitigation

### Technical Risks

1. **Complex Component Dependencies**: Use comprehensive mocking strategies
2. **Async Testing Complexity**: Leverage `waitFor` and proper async patterns
3. **Canvas/Image Testing**: Mock canvas APIs and use image fixtures
4. **Camera API Testing**: Mock webcam functionality

### Process Risks

1. **Test Maintenance Overhead**: Establish clear testing patterns and documentation
2. **False Positives**: Focus on meaningful test scenarios over coverage metrics
3. **Integration Complexity**: Phase implementation to avoid overwhelming changes

## Success Metrics

### Quantitative Targets

- **Overall Coverage**: 39.66% → 80%
- **API Layer**: 42.85% → 85%
- **Core Components**: 55.91% → 80%
- **Zero Runtime Errors**: Fix existing TypeError in body.tsx
- **Test Count**: 42 → 150+ tests

### Qualitative Targets

- All critical user workflows tested
- Comprehensive error handling validation
- Consistent testing patterns across codebase
- Maintainable and readable test suite
- Fast test execution (<30 seconds)

## Resource Requirements

### Development Time

- **Phase 1**: 16-20 hours (Critical fixes and API expansion)
- **Phase 2**: 20-24 hours (Core component testing)
- **Phase 3**: 16-20 hours (UI component testing)
- **Phase 4**: 20-24 hours (Feature component expansion)
- **Phase 5**: 8-12 hours (Integration and performance)

**Total Estimated Effort**: 80-100 hours

### Tools and Dependencies

- **Existing**: Vitest, React Testing Library, Jest DOM - ✅ Already configured
- **Additional**: Consider adding `@testing-library/user-event` for advanced interactions
- **Fixtures**: Create test data fixtures for complex API responses

## Maintenance Strategy

### Ongoing Practices

1. **Coverage Gates**: Enforce minimum 70% coverage for new components
2. **Test-First Development**: Write tests before implementing new features  
3. **Regular Review**: Monthly test suite health checks
4. **Documentation**: Maintain testing patterns documentation
5. **Continuous Integration**: Ensure tests run on every PR

### Quality Assurance

- **Test Review Process**: Peer review for all test additions
- **Coverage Monitoring**: Track coverage trends over time
- **Performance Monitoring**: Ensure test suite remains fast
- **Maintenance Windows**: Quarterly test suite cleanup and optimization

---

**Next Steps**: Begin with Phase 1 implementation, focusing on fixing the runtime error in `body.tsx` and expanding API layer test coverage to establish a solid foundation for subsequent phases.
