// src/setupTests.ts

// Import the testing library's cleanup function
import { cleanup } from "@testing-library/react";

// Import any global mocks or configurations here
// For example, if you're using MSW (Mock Service Worker) for API mocking:
// import { server } from './mocks/server';

beforeAll(() => {
  process.env.VITE_APP_MODE = "test";
});

beforeEach(() => {
  // If using MSW, start the server before each test
  // server.listen();
});

afterEach(() => {
  // Ensure all components are unmounted and the DOM is cleaned up after each test
  cleanup();

  // If using MSW, reset handlers to ensure tests are independent
  // server.resetHandlers();
});

afterAll(() => {
  // If using MSW, stop the server after all tests are done to clean up
  // server.close();
});
