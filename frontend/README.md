# Nachet Frontend

This is the React TypeScript frontend for the Nachet seed identification system. The project was initialized with [Vite](https://vitejs.dev/), a build tool that aims to provide a faster and leaner development experience for modern web projects.

## Setting up @saithodev/ts-appversion

To ensure a smooth development experience, it's crucial to manage the
application versioning right from the start. We use @saithodev/ts-appversion for
this purpose. Please install it by executing the command below before moving
forward with the development or build process:

```bash
npm install @saithodev/ts-appversion
```

After installing @saithodev/ts-appversion, run the prestart script to ensure
your application version is correctly set based on the latest git tag:

```bash
npm run prestart
```

After installing, you can proceed with the development or build processes of
your project.

```bash
npm run dev
```

This will serve your application on localhost:5173, where you can view it in
your preferred browser. The server is configured to automatically reload upon
any changes to your code, providing instant feedback on your development
progress. Additionally, build errors and lint warnings will be prominently
displayed in the console, helping you maintain a clean and efficient codebase.

The app will automatically reload if you make changes to the code. You will see
the build errors and lint warnings in the console.

## Development Workflow

### Local Development (Recommended)

For the fastest development experience, run the frontend locally:

1. **Install dependencies**: `npm install` (or `npm run update` if `package.json` changed)
2. **Start development server**: `npm run dev`
3. **Access application**: Open `http://localhost:5173`

The development server provides hot reload, instant feedback on errors, and optimal performance.

**When to use `npm run update`:**

- After pulling changes that modified `package.json`
- When switching between branches with different dependencies
- If experiencing dependency-related issues
- After manually editing `package.json`

### Container-based Development

For consistency across different environments, use the Docker development setup (see Development with Docker section below).

## Available Scripts

In the project directory, you can run:

### `npm run update`

**IMPORTANT**: Run this command after any changes to `package.json` or when switching branches with dependency changes.

This command:

- Removes the `node_modules` directory
- Reinstalls all dependencies from scratch
- Regenerates the Software Bill of Materials (SBOM) file
- Ensures a clean dependency state

```bash
npm run update
```

### `npm run dev`

Starts the development server. Open localhost:5173 to view it in your browser.

The app will automatically reload if you make changes to the code. You will see
the build errors and lint warnings in the console.

### `npm run prebuild`

Prepares the application versioning before building. It's an essential step to
ensure that the build includes the correct version of your application.

### `npm run build`

Builds the app for production to the `dist` folder. It correctly bundles React
in production mode and optimizes the build for the best performance. Your app is
ready to be deployed!

### `npm run preview`

Locally preview production build.

### `npm run lint`

Runs eslint to find and fix problems in your JavaScript code.

### `npm run test`

Launches the test runner in the interactive watch mode using Vitest.

### `npm run test:coverage`

Runs tests with coverage reporting to analyze code coverage.

### `npm run format`

Formats all code using Prettier to ensure consistency across the codebase.

### `npm run format:check`

Checks if code formatting is consistent without making changes.

## Code Formatting with Prettier

To ensure your codebase remains clean and consistent, we use
[Prettier](https://prettier.io/) for automatic code formatting. Before
committing your changes, you can format your code by running:

```bash
npm run format
```

This command automatically formats all files in the project. You can also check formatting without making changes using `npm run format:check`.

## Software Bill of Materials (SBOM) with CycloneDX

This project automatically generates a Software Bill of Materials (SBOM) using [CycloneDX](https://cyclonedx.org/), which provides a comprehensive inventory of all project dependencies for security and compliance purposes.

### What is SBOM?

An SBOM is a formal record containing the details and supply chain relationships of various components used in building software. It's essential for:

- **Security vulnerability tracking** - Identify which components may be affected by security issues
- **License compliance** - Understand the licenses of all dependencies
- **Supply chain transparency** - Know exactly what's included in your application
- **Regulatory compliance** - Meet requirements for software transparency

### SBOM Generation

The SBOM is automatically generated when you run:

```bash
npm run update
```

This creates an `sbom.json` file in the project root using the CycloneDX format specification v1.6. The file contains:

- All direct and transitive dependencies
- Package versions and locations
- License information
- Component relationships
- Reproducible output for consistent results

### Manual SBOM Generation

You can also generate the SBOM manually:

```bash
npx cyclonedx-npm package-lock.json --output-reproducible --package-lock-only -v --sv 1.6 -o sbom.json
```

**Note**: The SBOM file (`sbom.json`) is tracked in version control to provide a complete record of dependencies for each release.

### Development with Docker

For a consistent development environment, you can use Docker:

#### Development Container Setup

1. **Prerequisites**: Ensure you have Docker and Docker Compose installed.

2. **Environment Configuration**: Create a `.env.config.local` file with your environment variables (see Environment Variable Setup section below).

3. **Start Development Container**:

   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

   This will:
   - Build a development container with Node.js and npm versions from `package.json`
   - Mount the entire frontend directory for hot reload
   - Install dependencies automatically
   - Start the Vite dev server on `http://localhost:5173`

4. **VS Code Integration**: The development container is configured to work with VS Code's Remote-Containers extension for a full development environment.

5. **Container Management**:

   ```bash
   # Stop the development container
   docker-compose -f docker-compose.dev.yml down

   # Rebuild with fresh dependencies
   docker-compose -f docker-compose.dev.yml up --build --force-recreate

   # Clean up development containers and images
   docker-compose -f docker-compose.dev.yml down --rmi all --volumes
   ```

#### Docker Cleanup

To prevent disk space issues from accumulating Docker images and containers:

```bash
# Remove stopped containers, unused networks, and dangling images
docker system prune

# More aggressive cleanup (removes all unused images, not just dangling ones)
docker system prune -a

# Remove specific development images
docker rmi nachet-frontend-dev_nachet-frontend-dev

# Clean up volumes (be careful - this removes data!)
docker volume prune
```

**Tip**: Run `docker system df` to see Docker disk usage breakdown.

#### Production Docker Build

1. Build the docker image:

   ```bash
   docker build -t nachet-frontend .
   ```

2. Run the image:

   ```bash
   docker run -p 3000:3000 nachet-frontend
   ```

#### Full Stack Development

You can also use `docker-compose` to run the API with the client together. Make sure you have all the environment variables required from the backend (see .env.template in the repository) and then run:

```bash
docker-compose up --build
```

This enables preview of local frontend changes while connecting to the backend services.

## Deployment Environment Configuration Management

For managing and configuring different deployment environments (development,
staging, production), we follow a structured approach to ensure consistency and
reliability across all stages of deployment. Detailed guidelines and practices
can be found in our

This documentation covers:

- Overview and purpose of different environment files (`environment.ts`,
  `environment.staging.ts`, `environment.prod.ts`).
- The process for selecting and applying the correct environment configuration
  during the build and deployment.
- Best practices for maintaining clear, consistent, and secure configuration
  management across all frontend components.

Refer to this documentation to understand how to effectively manage and utilize
environment configurations in your project.

## Environment Variable Setup

To run the application correctly, certain environment variables need to be set.
These variables control various aspects of how the application behaves in
different environments (development, staging, production).

### Required Variables

1. `VITE_BACKEND_URL`: URL of the backend server. This is used to make API calls
   from the frontend.
2. `VITE_APP_MODE`: Determines the mode in which the application runs. Set to
   `"test"` for using test data, any other value will use real data from the
   backend.
3. `VITE_AZURE_AUTH_ENABLED`: Enables Microsoft Entra authentication. Defaults
   to `"true"`. Use `"false"` only for local development, together with backend
   `AZURE_AUTH_ENABLED="false"`.
4. `VITE_DEV_USER_ID`, `VITE_DEV_USER_EMAIL`, `VITE_DEV_ACCESS_TOKEN`: Local dev
   values used only when `VITE_AZURE_AUTH_ENABLED="false"`.

### Setting Up Environment Variables

You can set these variables in a `.env` file in the root of your project.

Remember to replace the values with the appropriate URLs and modes for your
specific environment. Also, ensure that you do not commit sensitive information
like production URLs or credentials in the `.env` file to your version control
system.

### Accessing Environment Variables in the Application

In your React application, you can access these variables using `process.env`.
For example:

- `process.env.VITE_BACKEND_URL` to get the backend URL.
- `process.env.VITE_APP_MODE` to check the current mode of the application.

Note: After changing the values in your `.env` file, you will need to restart
your development server for the changes to take effect.

## Learn More

To learn more about Vite, check out the [Vite
documentation](https://vitejs.dev/guide/).

To learn React, check out the [React documentation](https://reactjs.org/).

npx cyclonedx-npm package-lock.json --output-reproducible --package-lock-only -v --sv 1.6 -o sbom.json && echo "" >> sbom.json
