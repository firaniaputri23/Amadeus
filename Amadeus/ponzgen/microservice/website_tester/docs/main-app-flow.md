# Main Application Flow

## Overview

The Website Tester is a comprehensive frontend application designed to test and interact with various microservices of the backend API. It provides a user-friendly interface for authentication, configuration, and accessing different testing modules. This document explains the overall application flow, architecture, and the data requirements for it to run properly.

## Application Components

1. **Main Dashboard (`index.html`)**
   - Serves as the central hub for all testing modules
   - Provides authentication configuration
   - Contains navigation cards to access individual testing modules
   - Displays debug information for troubleshooting

2. **Core Utility Module (`main.js`)**
   - Provides essential API communication functions
   - Handles authentication and token management
   - Offers utility functions for UI operations and data formatting
   - Implements error handling and notification systems

3. **Backend Integration**
   - All modules communicate with various backend microservices
   - Uses JWT token-based authentication
   - Supports different API endpoints for specific functionalities

## User Flow

### 1. Application Initialization

**Frontend:**
1. When any page loads, the application checks for existing authentication
2. If accessing a non-index page without authentication, the user is redirected to the main dashboard
3. The main dashboard loads saved authentication settings from localStorage:
   - JWT token for authentication
   - API URL for backend connection

### 2. Authentication Configuration

**Frontend:**
1. User enters a JWT token in the provided input field
2. User configures the API URL (defaults to `http://localhost:8000`)
3. User clicks the "Save" button to store these settings
4. The application saves the configuration to localStorage
5. A success message confirms the settings have been saved

**Backend:**
- The backend expects JWT tokens for authentication
- For testing purposes, the backend uses a bypass flag that doesn't validate the token
- The token must still be present in the correct format (`Bearer <token>`)

### 3. Module Navigation

**Frontend:**
1. User navigates to specific testing modules through card links:
   - Agents
   - Tools
   - Agent Logs
   - Companies
   - Roles
   - User Info
   - Agent Invoke
   - Agent Invoke Stream
   - Agent Creator
   - Health Check
   - Feature Sharing
2. Each module is loaded in a separate HTML page
3. Authentication is verified before allowing access to any module

### 4. API Communication

**Frontend:**
1. All API communication is handled through the `API` utility object with methods:
   - `get()`: For retrieving data
   - `post()`: For creating new resources
   - `put()`: For updating existing resources
   - `delete()`: For removing resources
2. Each request automatically:
   - Includes the appropriate authentication header
   - Sets the correct content type
   - Uses the configured API base URL
   - Handles errors and response formatting

**Backend:**
- Receives requests with JWT authentication
- Processes the request based on the endpoint
- Returns appropriate responses (JSON format)
- May include error details for troubleshooting

## Data Requirements

### Authentication Data

1. **JWT Token**:
   - Stored in localStorage as `jwt_token`
   - Used in the Authorization header as `Bearer <token>`
   - Required for all authenticated API requests

2. **API URL**:
   - Stored in localStorage as `api_url`
   - Default value is `http://localhost:8000`
   - Used as the base URL for all API requests

### API Response Data

Various data structures are returned by the API endpoints, including:

1. **Agent Data**:
   - Information about AI agents
   - Agent capabilities and configurations
   - Associated tools and parameters

2. **Tool Data**:
   - Tool definitions and configurations
   - Parameters and expected responses
   - Usage limitations and requirements

3. **Log Data**:
   - Agent execution logs
   - Error information
   - Performance metrics

4. **Company Data**:
   - Company profile information
   - User associations and permissions
   - Role assignments

5. **User Data**:
   - User profile information
   - Authentication status
   - Role and permission details

## Utility Functions

The application provides several utility functions through the `Utils` object:

1. **Date Formatting**:
   - `formatDate()`: Converts ISO date strings to localized formats

2. **Notification System**:
   - `showNotification()`: Displays temporary notifications for user feedback
   - Supports different message types (success, error, warning)
   - Auto-dismisses after a configurable time period

3. **Authentication Checking**:
   - `checkAuth()`: Verifies user authentication status
   - Redirects unauthenticated users to the login page
   - Prevents unauthorized access to protected modules

4. **Loading Indicators**:
   - `showLoading()`: Displays a loading spinner during async operations
   - `hideLoading()`: Removes the loading spinner when complete

5. **Data Visualization**:
   - `createTable()`: Generates HTML tables from data arrays
   - Supports custom formatters and action buttons
   - Handles empty data sets gracefully

## API Endpoints

The application interacts with various API endpoints, including:

| Category | Endpoint Pattern | Description |
|----------|-------------------|-------------|
| Agents | `/agents` | CRUD operations for agents |
| Tools | `/tools` | CRUD operations for tools |
| Agent Logs | `/agent-logs` | View and manage execution logs |
| Companies | `/companies` | Manage company entities |
| Roles | `/roles` | View available roles |
| User Info | `/user` | Get current user information |
| Agent Invoke | `/agent-invoke` | Test agent execution |
| Health | `/health` | Check API health status |
| Feature Sharing | `/feature-sharing` | Share agents and threads |

## Error Handling

The application implements a comprehensive error handling system:

1. **Network Errors**:
   - Detects connection failures to the backend
   - Provides user-friendly error messages

2. **API Errors**:
   - Captures and formats error responses from the backend
   - Extracts error details for display
   - Logs errors to the console for debugging

3. **UI Feedback**:
   - Shows notifications for operation success/failure
   - Displays loading indicators during async operations
   - Provides debug information for troubleshooting

## Debug Features

The application includes debugging capabilities:

1. **Debug Information Panel**:
   - Displays current JWT token
   - Shows configured API URL
   - Reveals the actual authorization header
   - Includes notes about authentication bypass

2. **Console Logging**:
   - Logs all API requests and responses
   - Records error details
   - Provides detailed execution flow information

## Required Backend Implementation

For the frontend to function correctly, the backend should implement:

1. **Authentication System**:
   - JWT token validation (or bypass for testing)
   - Appropriate CORS headers for cross-origin requests
   - Consistent authorization error responses

2. **Core Endpoints**:
   - CRUD operations for all resource types
   - Health check endpoints
   - User information endpoints

3. **Response Format**:
   - Consistent JSON structure
   - Appropriate status codes
   - Descriptive error messages 