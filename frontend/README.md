# Vite React Project

This project was initialized with [Vite](https://vitejs.dev/), a build tool that
aims to provide a faster and leaner development experience for modern web
projects.

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

## Available Scripts

In the project directory, you can run:

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

Launches the test runner in the interactive watch mode.

## Code Formatting with Prettier

To ensure your codebase remains clean and consistent, we use
[Prettier](https://prettier.io/) for automatic code formatting. Before
committing your changes, you can format your code by running the following
command:

```bash
npx prettier --write .
```

Executing this command automatically formats the specified files. You can
replace `.` with the relative path of any specific file or directory you wish to
format. This allows for targeted formatting, ensuring that only the desired
sections of your codebase are adjusted.

### Running the application with docker

1. Build the docker image:

   ```bash
   docker build -t finesse-frontend .
   ```

2. Run the image: `docker run -p 3000:3000 finesse-frontend`.

### Docker-compose (optional)

You can also use `docker-compose` to run the API with the client. The API is the
backend that this client uses and is available at
<https://github.com/ai-cfia/finesse-backend>.

To run the API and the client together, make sure you have all the environment
variables required from the backend (see .env.template in the repository) and
then you can use the following command:

```bash
docker-compose up --build
```

You can then access the client at `http://localhost`. Take note that the backend
image is being pulled from our Github registry and the frontend image is being
built from the Dockerfile in the repository. This enables preview of local
changes in the frontend.

## Deployment Environment Configuration Management

For managing and configuring different deployment environments (development,
staging, production), we follow a structured approach to ensure consistency and
reliability across all stages of deployment. Detailed guidelines and practices
can be found in our [Deployment Environment Configuration Management
documentation](https://github.com/ai-cfia/dev-rel-docs/blob/103-documentation-request-environment-configuration-guidelines/TypeScript-AppVersion/DEPLOYMENT_ENV_CONFIG_MANAGEMENT.md).

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
