# User Info Microservice Flow

## Overview

The User Info Microservice provides functionality for displaying detailed information about the authenticated user and analyzing the JWT token being used for authentication. This tool allows users to verify their identity, check token validity, and understand the data structure associated with their user account. This document explains the application flow and details the data requirements for proper operation.

## Application Components

1. **Frontend UI (`user-info.html`)**
   - Provides an interface for viewing user profile information
   - Displays JWT token structure and expiration details
   - Features a simple, card-based layout for clear information presentation
   - Includes a refresh button for updating user information

2. **Frontend Logic (`user-info.js`)**
   - Handles fetching user data from the backend
   - Parses and displays JWT token information
   - Processes and formats user profile data
   - Manages error handling and loading states

3. **Backend API**
   - Provides user information through the `/user/info` endpoint
   - Requires JWT authentication for access
   - Returns user profile data in JSON format

## User Flow

### 1. Page Initialization

**Frontend:**
1. When the page loads, the application first checks if the user is authenticated:
   - If not authenticated, redirects to the home page with a warning message
   - If authenticated, proceeds with loading user information
2. The `loadUserInfo()` function is called to fetch user data from the API
3. The `displayTokenInfo()` function is called to parse and display the JWT token data
4. A loading indicator is shown while data is being fetched

### 2. View User Profile Information

**Frontend:**
1. The application sends a GET request to `/user/info` with the JWT token
2. When the response is received, the user profile information is displayed in a card layout:
   - User ID
   - Email address
   - Name
   - Creation date
   - Last sign-in date
   - User role
3. The complete JSON representation of the user data is also displayed for reference
4. If an error occurs, an error message is shown with details about the problem

**Backend:**
1. Receives the authenticated request
2. Validates the JWT token
3. Retrieves the user information from the database
4. Returns the user data in JSON format

### 3. View JWT Token Information

**Frontend:**
1. The application retrieves the JWT token from localStorage
2. The token is parsed into its three components:
   - Header
   - Payload
   - Signature (not displayed but validated)
3. The header and payload are decoded from base64 and displayed as formatted JSON
4. If the token contains expiration information:
   - The expiration date is calculated and displayed
   - A status indicator shows whether the token is valid or expired
   - For valid tokens, the remaining time until expiration is shown
5. If the token is invalid or improperly formatted, an error message is displayed

### 4. Refresh User Information

**Frontend:**
1. User clicks the "Refresh" button in the user details card
2. The `loadUserInfo()` function is called again
3. The latest user information is fetched from the API
4. The display is updated with the new information
5. The JWT token information remains unchanged

## Data Requirements

### User Profile Data

The API should return a user object containing:

1. **Basic User Information**:
   - `id` or `user_id`: Unique identifier for the user
   - `email`: User's email address
   - `name` or `user_name`: User's display name

2. **Account Information**:
   - `created_at`: Date when the user account was created
   - `last_sign_in_at`: Date of the user's most recent login
   - `role`: User's role in the system

3. **Additional Information**:
   - Any other user-related data provided by the API

### JWT Token Data

The JWT token should be structured as a standard JWT with:

1. **Header Section**:
   - `alg`: Algorithm used for signing the token
   - `typ`: Token type (typically "JWT")

2. **Payload Section**:
   - `sub`: Subject (typically the user ID)
   - `exp`: Expiration timestamp
   - `iat`: Issued at timestamp
   - Other claims as defined by the authentication system

## API Endpoints

| Endpoint | Method | Description | Authentication Required |
|----------|--------|-------------|-------------------------|
| `/user/info` | GET | Retrieve information about the authenticated user | Yes |

## Expected Response Format

The `/user/info` endpoint should return a JSON object with at least:

```json
{
  "id": "user-uuid-here",
  "email": "user@example.com",
  "name": "User Name",
  "created_at": "2023-01-01T12:00:00Z",
  "last_sign_in_at": "2023-06-01T12:00:00Z",
  "role": "user"
}
```

## Error Handling

The frontend handles various error scenarios:

1. **Authentication Errors**:
   - Redirects unauthenticated users to the home page
   - Displays appropriate warning messages

2. **API Errors**:
   - Shows error alerts with details from the API response
   - Provides guidance on how to resolve common issues

3. **Token Parsing Errors**:
   - Validates token format and structure
   - Displays specific error messages for malformed tokens

## UI Components

1. **User Details Card**:
   - Displays formatted user profile information
   - Shows creation and last sign-in dates
   - Includes a refresh button
   - Contains a JSON representation of the complete user data

2. **JWT Token Information Card**:
   - Shows decoded header and payload sections
   - Displays expiration status and remaining validity time
   - Uses color-coded alerts for expiration status

## Helper Functions

The application includes several helper functions:

1. **Token Handling**:
   - `atob()`: Custom implementation for decoding base64url strings
   - Handles padding and character replacement for proper base64 decoding

2. **Data Loading**:
   - `loadUserInfo()`: Fetches and displays user information
   - Uses the API utility from main.js for authenticated requests

3. **Date Formatting**:
   - Uses `Utils.formatDate()` from the shared utilities
   - Converts ISO date strings to localized formats

## Required Backend Implementation

For the User Info functionality to work properly, the backend should implement:

1. **User Information Endpoint**:
   - A `/user/info` endpoint that returns the authenticated user's data
   - Proper JWT token validation
   - Comprehensive user profile information

2. **Authentication System**:
   - Standard JWT token format
   - Proper expiration handling
   - Clear error responses for authentication issues 