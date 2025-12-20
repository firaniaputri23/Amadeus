# Tools Microservice Flow

## Overview

The Tools Microservice provides functionality for managing tools in the system. This document explains the application flow from the frontend UI through to the backend API.

## Application Components

1. **Frontend UI (`tools.html`)**
   - Provides the HTML structure for the tools management interface
   - Contains modals for creating, editing, and cloning tools

2. **Frontend Logic (`tools.js`)**
   - Handles all client-side interactions and API calls
   - Manages tool data rendering and form handling

3. **Backend API (`tools.py`)**
   - Provides RESTful endpoints for tool operations
   - Handles database interactions and business logic

## User Flow

### 1. View Tools List

**Frontend:**
- On page load, the frontend automatically calls `loadTools()` function
- The function makes a GET request to the `/tools` endpoint
- Results are displayed in a grid of cards with basic tool information
- Users can filter tools by company using the dropdown

**Backend:**
- The `/tools` endpoint retrieves tools based on:
  - User ID (personal tools)
  - Company ID (if a filter is applied)
- The backend fetches data from the `tools_with_decrypted_keys` table

### 2. View Tool Details

**Frontend:**
- When a user clicks the "View" button on a tool card, the `loadToolDetails()` function is called
- This makes a GET request to `/tools/{tool_id}`
- Tool details are displayed including versions, configuration, etc.

**Backend:**
- The `/tools/{tool_id}` endpoint retrieves the full details of a specific tool
- Data is fetched from the `tools_with_decrypted_keys` table

### 3. Create New Tool

**Frontend:**
1. User clicks "Create Tool" button, opening the tool modal
2. Form is initialized with one version field
3. User fills out the form with:
   - Tool name (validated for uniqueness)
   - Description
   - Company (optional)
   - Version details (version number, environment variables, etc.)
4. User clicks "Save" to submit the form
5. The `saveTool()` function sends a POST request to `/tools`

**Backend:**
1. The POST `/tools` endpoint receives the request
2. Validates the tool name for uniqueness
3. Assigns a free port number for each version
4. Inserts the new tool into the database
5. Refreshes the MCP tools to make the new tool available
6. Returns the created tool data

### 4. Edit Tool

**Frontend:**
1. User clicks "Edit" button on a tool card
2. The `editTool()` function fetches the tool details
3. The tool modal is populated with the existing tool data
4. User makes changes and clicks "Save"
5. The `saveTool()` function sends a PUT request to `/tools/{tool_id}`

**Backend:**
1. The PUT `/tools/{tool_id}` endpoint receives the request
2. Validates permissions based on user role
3. Updates the tool in the database
4. Refreshes the MCP tools to apply changes
5. Returns the updated tool data

### 5. Delete Tool

**Frontend:**
1. User clicks "Delete" button on a tool card
2. A confirmation dialog is shown
3. If confirmed, the `deleteTool()` function sends a DELETE request to `/tools/{tool_id}`

**Backend:**
1. The DELETE `/tools/{tool_id}` endpoint receives the request
2. Checks if the tool is being used by any agents (prevents deletion if it is)
3. Deletes the tool from the database
4. Refreshes the MCP tools to remove the deleted tool
5. Returns a success message

### 6. Clone Tool

**Frontend:**
1. User clicks "Clone" button, opening the clone tool modal
2. Available tools are displayed for selection
3. User selects a tool and clicks "Clone"
4. The `cloneSelectedTool()` function sends a POST request to `/tools/{tool_id}/clone`

**Backend:**
1. The POST `/tools/{tool_id}/clone` endpoint receives the request
2. Verifies user permissions
3. Creates a copy of the tool with:
   - Name prefixed with "Clone of"
   - New port numbers assigned
   - Environment variable values replaced with placeholders
4. Inserts the cloned tool into the database
5. Refreshes the MCP tools to make the cloned tool available
6. Returns the cloned tool data

## Authentication Flow

The application uses a middleware-based authentication system:

1. JWT token is extracted from the Authorization header
2. Token is validated against Supabase (or a static file in development)
3. User information is added to the request state
4. Permissions are checked based on user role and company association

## Technical Details

### Port Assignment

- The system automatically assigns available ports to tool versions
- Free ports are determined by trying to bind to ports in a configured range
- Port information is stored in `config/port_range.json`

### Version Management

- Each tool can have multiple versions
- Versions include configuration details:
  - Version number
  - Environment variables
  - Required environment variables
  - Command arguments
  - Port number
  - Method (currently only "sse" is supported)

### Data Validation

- Tool names must be unique
- Proper JSON format is required for environment variables and required environment variables
- User permissions are validated for company-owned tools

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools` | GET | Get all tools (filtered by user or company) |
| `/tools` | POST | Create a new tool |
| `/tools/{tool_id}` | GET | Get a specific tool by ID |
| `/tools/{tool_id}` | PUT | Update an existing tool |
| `/tools/{tool_id}` | DELETE | Delete a tool |
| `/tools/check-name/{tool_name}` | GET | Check if a tool name exists |
| `/tools/{tool_id}/clone` | POST | Clone an existing tool | 