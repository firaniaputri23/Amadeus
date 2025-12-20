# Health Check Microservice Flow

## Overview

The Health Check Microservice provides functionality for testing API endpoints and verifying their operational status. It allows users to make requests to different API endpoints, with or without authentication, and examine the responses. This tool is essential for debugging, ensuring system availability, and validating API functionality. This document explains the application flow and details the data requirements.

## Application Components

1. **Frontend UI (`health.html`)**
   - Provides an interface for configuring and executing health checks
   - Includes configuration options for API URL, endpoint, and authentication
   - Displays request details and response information
   - Features a simple, intuitive UI for quick health checks

2. **Frontend Logic (`health.js`)**
   - Handles all client-side interactions and API calls
   - Manages the configuration of health check requests
   - Processes and displays API responses
   - Controls UI elements based on user selection

3. **Backend API**
   - Health check endpoints (e.g., `/health`) on various services
   - Responds with status information and service details
   - May require authorization for certain endpoints

## User Flow

### 1. Configure Health Check

**Frontend:**
1. User selects the API URL type from the dropdown:
   - Regular API URL (default port 8000)
   - Invoke API URL (default port 8001)
   - Custom URL (user-specified)
2. If "Custom URL" is selected, user enters the complete base URL
3. User specifies the endpoint to test (default is `/health`)
4. User decides whether to include authorization by checking/unchecking the "Include Authorization Header" checkbox

### 2. Execute Health Check

**Frontend:**
1. User clicks the "Check Health" button
2. The UI displays the complete request URL and headers
3. A loading message is shown while the request is in progress
4. The `checkHealth()` function sends a GET request to the specified endpoint with the configured headers
5. The response is processed and displayed in the UI

### 3. View Results

**Frontend:**
1. The UI displays:
   - HTTP status code and status text
   - Response headers
   - Response body (formatted as JSON if possible, or as plain text)
2. If an error occurs, an error message is shown with possible causes
3. User can modify the configuration and run additional health checks as needed

## Data Requirements

### Request Configuration Data

1. **API URL Selection**:
   - `api-url-select`: Dropdown selection for API URL type (regular, invoke, custom)
   - `custom-url`: Custom URL input field (visible only when "Custom URL" is selected)
   - Values are retrieved from localStorage or default to localhost with appropriate ports

2. **Endpoint Configuration**:
   - `endpoint`: The API endpoint to test (e.g., `/health`)
   - Default is `/health` but can be changed to any endpoint

3. **Authentication Configuration**:
   - `include-auth`: Boolean flag indicating whether to include the authorization header
   - When enabled, retrieves the JWT token from localStorage

### Response Data

1. **Request Information**:
   - Complete URL used for the request
   - Headers sent with the request

2. **Response Information**:
   - HTTP status code and status text (e.g., `200 OK`)
   - Response headers received from the server
   - Response body (typically JSON data or plain text)
   - Error messages and suggestions in case of failures

## API Endpoints

The Health Check tool can test any endpoint, but it is primarily designed to work with:

| Endpoint | Description | Authentication Required |
|----------|-------------|-------------------------|
| `/health` | Basic health check endpoint | Typically No |
| `/health/detailed` | Detailed health status | Possibly Yes |
| Any other API endpoint | Any endpoint the user wants to test | Depends on endpoint |

## Expected Backend Implementation

For the health check system to work effectively, backend services should implement:

1. **Basic Health Endpoint**:
   - A `/health` endpoint that returns a simple status response
   - Typically returns HTTP 200 with minimal information
   - Example response: `{"status": "ok", "timestamp": "2023-06-01T12:00:00Z"}`

2. **Detailed Health Endpoint**:
   - A more comprehensive health check endpoint (e.g., `/health/detailed`)
   - May require authentication
   - Provides information about:
     - Service uptime
     - Database connectivity
     - External dependencies
     - System resources
   - Example response:
     ```json
     {
       "status": "ok",
       "timestamp": "2023-06-01T12:00:00Z",
       "version": "1.2.3",
       "services": {
         "database": "connected",
         "cache": "connected",
         "external_api": "connected"
       },
       "uptime": "3d 2h 5m 12s"
     }
     ```

## UI Components

1. **Configuration Card**:
   - API URL selector dropdown
   - Custom URL input field (conditionally displayed)
   - Endpoint input field
   - Authorization checkbox
   - "Check Health" button

2. **Results Card**:
   - Request details section
     - URL display
     - Headers display
   - Response section
     - Status display
     - Headers display
     - Body display (formatted as pre-formatted text)

## Error Handling

The frontend handles various error scenarios:

1. **Network Errors**:
   - Failed to fetch: Indicates server unreachable or network issues
   - Displays helpful suggestions for troubleshooting

2. **Response Parsing Errors**:
   - JSON parsing failure: Falls back to displaying raw text
   - Text extraction failure: Shows a generic error message

3. **Server Errors**:
   - Displays the error status code and message from the server
   - Shows the error response body for debugging 