# OAuth 2.0 Setup Guide

This guide explains how to configure OAuth 2.0 authentication for the Nachet frontend using Azure AD/Entra ID.

## Overview

The application now uses Microsoft Authentication Library (MSAL) for React to implement OAuth 2.0 authentication with Azure Active Directory (Azure AD) / Microsoft Entra ID.

## Prerequisites

1. An Azure AD tenant
2. App registration in Azure AD
3. Client ID and tenant ID from the app registration

## Azure AD App Registration Setup

1. **Register Application**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to Azure Active Directory → App registrations
   - Click "New registration"
   - Enter application name (e.g., "Nachet Frontend")
   - Select "Single-page application (SPA)"
   - Add redirect URI: `http://localhost:5173` (for development)

2. **Configure Authentication**:
   - In the app registration, go to "Authentication"
   - Under "Single-page application", add your redirect URIs:
     - Development: `http://localhost:5173`
     - Production: `https://your-production-domain.com`
   - Enable "Access tokens" and "ID tokens" under implicit grant flow
   - Save the configuration

3. **Get Client Information**:
   - Note down the "Application (client) ID"
   - Note down the "Directory (tenant) ID"

## Environment Configuration

Create a `.env` file in the frontend directory with the following variables:

```bash
# Backend Configuration
VITE_BACKEND_URL="http://localhost:8080"

# OAuth 2.0 / Azure AD Configuration
VITE_AZURE_AUTH_ENABLED="true"
VITE_AZURE_CLIENT_ID="your-application-client-id"
VITE_AZURE_AUTHORITY="https://login.microsoftonline.com/your-tenant-id"
VITE_AZURE_REDIRECT_URI="http://localhost:5173"
VITE_AZURE_POST_LOGOUT_REDIRECT_URI="http://localhost:5173"
```

### Configuration Options

- **VITE_AZURE_CLIENT_ID**: The Application (client) ID from your Azure AD app registration
- **VITE_AZURE_AUTHORITY**: The authority URL for your tenant. Replace `your-tenant-id` with your actual tenant ID, or use `common` for multi-tenant applications
- **VITE_AZURE_REDIRECT_URI**: The URI where users will be redirected after authentication
- **VITE_AZURE_POST_LOGOUT_REDIRECT_URI**: The URI where users will be redirected after logout
- **VITE_AZURE_AUTH_ENABLED**: Defaults to `"true"`. Use `"false"` only for
  local development with backend `AZURE_AUTH_ENABLED="false"`.

### Local Development Without Entra

If you do not have Entra credentials locally, set:

```bash
VITE_AZURE_AUTH_ENABLED="false"
VITE_DEV_USER_ID="8ea46a6b-7d37-4fbb-a66f-775112376e16"
VITE_DEV_USER_EMAIL="test.user@inspection.gc.ca"
VITE_DEV_ACCESS_TOKEN="local-dev-auth-disabled"
```

The frontend skips the MSAL sign-in flow and sends the placeholder bearer token.
The backend must also disable auth and run with `NACHET_ENV="local"` or
`NACHET_ENV="development"`.

## Architecture

### Components

1. **AuthContext**: React context providing authentication state and methods
2. **useAuth**: Custom hook for accessing authentication functionality
3. **OAuthLogin**: Login component that triggers OAuth flow
4. **MSAL Configuration**: Configuration for Microsoft Authentication Library

### Authentication Flow

1. User clicks "Sign In" button
2. Application redirects to Microsoft login page
3. User authenticates with their organizational account
4. Microsoft redirects back to the application with tokens
5. Application extracts user information and maintains session
6. Backend API calls can now include authentication tokens

### Token Management

- Tokens are stored in session storage
- Access tokens are automatically refreshed when needed
- Silent token renewal is attempted first, falling back to interactive authentication

## API Integration

The OAuth implementation provides user email from the authentication token, which is used with the existing `requestUUID` API to maintain compatibility with the backend.

## Testing

Run the application in development mode:

```bash
npm run dev
```

The OAuth login flow should work with a properly configured Azure AD app registration.

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure your redirect URIs are properly configured in Azure AD
2. **Invalid Client**: Verify the client ID matches your app registration
3. **Authority Not Found**: Check that the tenant ID is correct in the authority URL
4. **Redirect URI Mismatch**: Ensure the redirect URI in your environment matches what's configured in Azure AD

### Debug Mode

Set browser console to view detailed authentication logs from MSAL library.

## Security Considerations

- Tokens are stored in session storage (cleared when browser closes)
- No sensitive information is stored in localStorage
- All authentication flows use secure HTTPS in production
- Tokens are automatically refreshed to maintain security

## Migration from Previous Authentication

The OAuth implementation replaces the previous cookie-based authentication system. The backend `requestUUID` API remains unchanged, but now receives user email from OAuth tokens instead of cookies.
