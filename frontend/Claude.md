General frontend rules
---

description:
globs: **/*.*
alwaysApply: false
---

---

description: Applies general coding principles and preferences across the entire project, emphasizing functional programming and specific tech stack usage.
globs: /**/*.*
---

- You are an expert in TypeScript, Node.js, React, Vite, MaterialUI
- Write concise, technical responses with accurate TypeScript examples.
- Use functional, declarative programming. Avoid classes.
- Prefer iteration and modularization over duplication.
- Use descriptive variable names with auxiliary verbs (e.g., isLoading).
- Use lowercase with dashes for directories (e.g., components/auth-wizard).
- Favor named exports for components.
- Use the Receive an Object, Return an Object (RORO) pattern.

Performance and Optimization
---

description:
globs: **/*.ts,**/*.tsx,**/*.js,**/*.jsx
alwaysApply: false
---

---

description: Focuses on performance optimization techniques for TypeScript, React, and Node.js projects.
globs: **/*.{ts,tsx,js,jsx}
---

Performance Optimization

- Look for ways to make things faster:
  - Use immutable data structures
  - Use efficient data fetching strategies
  - Optimize network requests
  - Use efficient data structures
  - Use efficient algorithms
  - Use efficient rendering strategies
  - Use efficient state management

React Typescript rules
---

description:
globs: **/components/**/*.ts,**/components/**/*.tsx,**/components/**/*.js,**/components/**/*.jsx
alwaysApply: false
---

---

description: Enforces specific React component development practices, including functional components, declarative JSX, UI library usage, and optimization techniques.
globs: components/**/*.{ts,tsx,js,jsx}
---

- Use functional components and TypeScript interfaces.
- Use declarative JSX.
- Use const for components.
- Use mui/material for components and styling.
- Place static content and interfaces at file end.
- Use content variables for static content outside render functions.
- Minimize 'use client', 'useEffect', and 'setState'. Favor RSC.
- Use Zod for form validation.
- Wrap client components in Suspense with fallback.
- Use dynamic loading for non-critical components.
- Use error boundaries for unexpected errors: Implement error boundaries using error.tsx and global-error.tsx files to handle unexpected errors and provide a fallback UI.
- Use useActionState with react-hook-form for form validation.
- Use .tsx extension for files with JSX.
- Implement strict TypeScript checks.
- Utilize React.lazy and Suspense for code-splitting.
- Use type inference where possible.
- Implement error boundaries for robust error handling.
- Follow React and TypeScript best practices and naming conventions.
- Use ESLint with TypeScript and React plugins for code quality.
- Use React.FC for functional components with props.
- Utilize useState and useEffect hooks for state and side effects.
- Implement proper TypeScript interfaces for props and state.
- Use React.memo for performance optimization when needed.
- Implement custom hooks for reusable logic.

Typescript rules
---

description:
globs: **/*.ts,**/*.tsx,**/*.js,**/*.jsx
alwaysApply: false
---

---

description: Defines specific coding style and structure for TypeScript and JavaScript files, including function usage, type preferences, and file organization.
globs: **/*.{ts,tsx,js,jsx}
---

- Do not remove any existing code unless necessary.
- Do not remove my comments or commented-out code unless necessary.
- Do not change the formatting of my imports.
- Do not change the formatting of my code unless important for new functionality.
- Use "function" keyword for pure functions. Omit semicolons.
- Use TypeScript for all code. Prefer interfaces over types. Avoid enums, use maps.
- File structure: Exported component, subcomponents, helpers, static content, types.
- Avoid unnecessary curly braces in conditional statements.
- For single-line statements in conditionals, omit curly braces.
- Use concise, one-line syntax for simple conditional statements (e.g., if (condition) doSomething()).
- Prioritize error handling and edge cases:
  - Handle errors and edge cases at the beginning of functions.
  - Use early returns for error conditions to avoid deeply nested if statements.
  - Place the happy path last in the function for improved readability.
  - Avoid unnecessary else statements; use if-return pattern instead.
  - Use guard clauses to handle preconditions and invalid states early.
  - Implement proper error logging and user-friendly error messages.
  - Consider using custom error types or error factories for consistent error handling.
