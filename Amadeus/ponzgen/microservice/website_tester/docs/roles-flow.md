# Roles Microservice Flow

## Overview

The Roles Microservice provides functionality for viewing and managing role definitions within the system. Roles define sets of permissions that determine what actions users can perform. This tool allows administrators to view available roles, their descriptions, and associated permissions. This document explains the application flow from the frontend UI through to the backend API and details the data requirements.

## Application Components

1. **Frontend UI (`roles.html`)**
   - Provides an interface for viewing available roles and their details
   - Displays a table of all roles with basic information
   - Features a detailed view section for examining role permissions
   - Includes a refresh button for updating role information

2. **Frontend Logic (`roles.js`)**
   - Handles fetching role data from the backend
   - Manages role selection and detailed view display
   - Processes and formats role data for presentation
   - Handles error states and loading indicators

3. **Backend API (`roles.py`)**
   - Provides endpoints for retrieving role information
   - Manages the initialization of default system roles
   - Handles database interactions for role data
   - Implements proper error handling and response formatting

## User Flow

### 1. Page Initialization

**Frontend:**
1. When the page loads, the application first checks if the user is authenticated:
   - If not authenticated, redirects to the home page with a warning message
   - If authenticated, proceeds with loading role information
2. The `loadRoles()` function is called to fetch all roles from the API
3. A loading indicator is shown while data is being fetched

**Backend:**
1. During application startup, the `initialize_roles()` function checks if roles exist in the database
2. If no roles exist, it creates default ones:
   - super admin
   - admin
   - staff
   - guest

### 2. View Roles List

**Frontend:**
1. The application sends a GET request to `/roles` with the JWT token
2. When the response is received, a table is created showing:
   - Role ID
   - Role Name
   - Description (if available)
   - View button for each role
3. If no roles are found, a message is displayed
4. If an error occurs, an error message is shown with details about the problem

**Backend:**
1. The `/roles` endpoint receives the request
2. Database query fetches all records from the "roles" table
3. Returns the roles data as a JSON array
4. Handles any database errors or unexpected exceptions

### 3. View Role Details

**Frontend:**
1. User clicks the "View" button for a specific role
2. The `loadRoleDetails(roleId)` function is called with the selected role ID
3. A GET request is sent to `/roles/{role_id}` endpoint
4. When the response is received, the role details are displayed, including:
   - Role name
   - Description
   - Role ID
   - Permissions (if available)
   - Complete JSON representation
5. If an error occurs, an error message is shown in the details container

**Backend:**
1. The `/roles/{role_id}` endpoint receives the request
2. Database query fetches the specific role by ID
3. If role doesn't exist, returns a 404 Not Found error
4. If found, returns the role data as a JSON object
5. Handles any database errors or unexpected exceptions

### 4. Refresh Roles

**Frontend:**
1. User clicks the "Refresh" button at the top of the roles list
2. The `loadRoles()` function is called again
3. The latest role information is fetched from the API
4. The display is updated with any changes
5. Any currently displayed role details remain unchanged

## Data Requirements

### Role Data

The API should return role objects containing:

1. **Basic Role Information**:
   - `role_id`: Unique identifier for the role (integer)
   - `role_name`: Name of the role (string)
   - `description`: Description of the role (string, optional)

2. **Permission Information**:
   - `permissions`: Object containing permission key-value pairs (optional)
   - Each key represents a permission name
   - Each value is a boolean indicating whether the permission is granted

### Database Schema

The microservice relies on the following database table:

**roles**:
- `role_id`: Primary key, integer
- `role_name`: String, required
- `description`: String, optional
- `permissions`: JSON object, optional

## API Endpoints

| Endpoint | Method | Description | Authentication Required |
|----------|--------|-------------|-------------------------|
| `/roles` | GET | Retrieve all available roles | Yes |
| `/roles/{role_id}` | GET | Retrieve a specific role by ID | Yes |

## Expected Response Formats

### GET `/roles`

```json
[
  {
    "role_id": 1,
    "role_name": "super admin",
    "description": "Full system access"
  },
  {
    "role_id": 2,
    "role_name": "admin",
    "description": "Administrative access"
  },
  ...
]
```

### GET `/roles/{role_id}`

```json
{
  "role_id": 1,
  "role_name": "super admin",
  "description": "Full system access",
  "permissions": {
    "create_agents": true,
    "delete_agents": true,
    "manage_users": true,
    "manage_companies": true
  }
}
```

## Error Handling

### Frontend Error Handling

The frontend handles various error scenarios:

1. **Authentication Errors**:
   - Redirects unauthenticated users to the home page
   - Displays appropriate warning messages

2. **API Errors**:
   - Shows error alerts with details from the API response
   - Gracefully handles failed requests

3. **Empty Data**:
   - Displays appropriate messages when no roles are found

### Backend Error Handling

The backend implements structured error handling:

1. **Not Found Errors**:
   - When a requested role doesn't exist
   - Returns a 404 status code with descriptive message

2. **Database Errors**:
   - When database operations fail
   - Returns a 500 status code with error details

3. **Unexpected Errors**:
   - Catches any unhandled exceptions
   - Returns a 500 status code with general error information

## UI Components

1. **Roles List Card**:
   - Table displaying all available roles
   - Columns for ID, Name, Description, and Actions
   - Refresh button to update the list
   - Loading indicator during data fetching

2. **Role Details Card**:
   - Displays detailed information about the selected role
   - Shows permissions as a list if available
   - Includes a JSON representation of the complete role data

## System Initialization

The backend automatically initializes the system with default roles:

1. **Default Roles**:
   - `super admin`: Highest level of access
   - `admin`: Administrative access
   - `staff`: Regular staff access
   - `guest`: Limited access

2. **Initialization Process**:
   - Checks if roles already exist in the database
   - If no roles found, creates the default roles
   - Logs the initialization process for debugging

## Required Backend Implementation

For the Roles functionality to work properly, the backend should implement:

1. **Roles Table**:
   - Schema as described in the Data Requirements section
   - Proper indexes for efficient queries

2. **API Endpoints**:
   - `/roles` GET endpoint for listing all roles
   - `/roles/{role_id}` GET endpoint for retrieving specific roles

3. **Authentication System**:
   - JWT token validation for secure access
   - Proper error responses for authentication issues 