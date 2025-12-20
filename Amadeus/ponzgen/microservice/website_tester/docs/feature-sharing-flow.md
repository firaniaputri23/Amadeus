# Feature Sharing Microservice Flow

## Overview

The Feature Sharing Microservice provides functionality for sharing agents and conversation threads with other users. It enables users to create public links for agents and threads, share them with specific users as editors (read-write access) or visitors (read-only access), and check user access permissions. This document explains the application flow from the frontend UI through to the backend API and details the data requirements.

## Application Components

1. **Frontend UI (`feature-sharing.html`)**
   - Provides an interface for testing and using the sharing features
   - Includes sections for sharing agents and threads, viewing shared content, and checking access permissions
   - Features forms for generating public links and verifying user access

2. **Frontend Logic (`feature-sharing.js`)**
   - Handles all client-side interactions and API calls
   - Manages agent and thread selection, sharing operations, and access checks
   - Loads available agents for dropdowns and displays API responses

3. **Backend API (`feature_sharing.py`)**
   - Provides RESTful endpoints for sharing operations
   - Handles authentication, permission checks, and data validation
   - Manages interactions with the database for storing sharing information

## User Flow

### 1. Share an Agent with Public Link

**Frontend:**
1. User selects an agent from the dropdown list
2. User checks/unchecks the "Make Public" checkbox (default is checked)
3. User clicks the "Share Agent" button
4. The `shareAgentForm` event listener triggers a POST request to `/feature-sharing/agent/share-anyone-with-link/{agent_id}/`
5. The response includes a public hash that can be used to access the agent

**Backend:**
1. The endpoint verifies the user's permission to share the agent:
   - User must be the agent owner, belong to the agent's company, or be an editor
2. Generates a public hash if one doesn't exist
3. Sets the agent's `is_public` flag to `true`
4. Updates the agent record in the database
5. Returns the success status and public hash

### 2. Share a Thread with Public Link

**Frontend:**
1. User selects an agent from the dropdown list
2. User selects a thread from the populated thread dropdown
3. User checks/unchecks the "Make Public" checkbox (default is checked)
4. User clicks the "Share Thread" button
5. The `shareThreadForm` event listener triggers a POST request to `/feature-sharing/thread/share-anyone-with-link/{agent_id}/{thread_id}`
6. The response includes a public hash that can be used to access the thread

**Backend:**
1. The endpoint verifies the user's permission to share the thread by checking:
   - If the user is the agent owner
   - If the user belongs to the agent's company
   - If the user is an editor of the agent
2. Retrieves the chat history and initializes share_info if it doesn't exist
3. Generates a public hash if one doesn't exist
4. Sets the thread's `is_public` flag to `true`
5. Updates the agent log in the database
6. Returns the success status and public hash

### 3. View a Shared Agent

**Frontend:**
1. User enters the agent's public hash
2. User clicks the "View Agent" button
3. The `viewSharedAgentForm` event listener triggers a GET request to `/agent-invoke/shared-agent/{hash}`
4. The response includes the agent information

**Backend:**
- The backend verifies the public hash and returns the agent information if it's valid and publicly shared

### 4. View a Shared Thread

**Frontend:**
1. User enters the thread's public hash
2. User clicks the "View Thread" button
3. The `viewSharedThreadForm` event listener triggers a GET request to `/agent-invoke/shared-thread/{hash}`
4. The response includes the thread/conversation information

**Backend:**
- The backend verifies the public hash and returns the thread information if it's valid and publicly shared

### 5. Check User Access to an Agent

**Frontend:**
1. User selects an agent from the dropdown list
2. User enters an email address
3. User clicks the "Check Access" button
4. The `checkEditorAccessForm` event listener triggers a POST request to `/feature-sharing/agent/from_email/{agent_id}`
5. The response includes the user's access status (editor, visitor, or no access)

**Backend:**
- The backend checks if the email exists in the agent's share_editor_with or share_visitor_with lists
- Returns the appropriate access status

## Data Requirements

### Core Data Entities

1. **Agent Sharing Data**:
   - `is_public`: Boolean flag indicating if the agent is publicly accessible
   - `public_hash`: Unique hash for public access link
   - `share_editor_with`: List of email addresses with editor (read-write) access
   - `share_visitor_with`: List of email addresses with visitor (read-only) access

2. **Thread Sharing Data** (stored in chat_history as share_info):
   - `is_public`: Boolean flag indicating if the thread is publicly accessible
   - `public_hash`: Unique hash for public access link
   - `share_editor_with`: List of email addresses with editor access
   - `share_visitor_with`: List of email addresses with visitor access

### Database Tables & Relationships

The microservice relies on the following database tables:

- `agents`: Stores agent information and sharing settings
- `agent_logs`: Stores agent execution logs, including conversation threads
- `user_companies`: Maps users to companies with roles (for permission checking)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/feature-sharing/agent/share-editor-with/{agent_id}/` | POST | Share an agent with specific users as editors |
| `/feature-sharing/agent/share-visitor-with/{agent_id}/` | POST | Share an agent with specific users as visitors |
| `/feature-sharing/agent/share-anyone-with-link/{agent_id}/` | POST | Generate a public link for an agent |
| `/feature-sharing/thread/share-editor-with/{agent_id}/{thread_id}` | POST | Share a thread with specific users as editors |
| `/feature-sharing/thread/share-visitor-with/{agent_id}/{thread_id}` | POST | Share a thread with specific users as visitors |
| `/feature-sharing/thread/share-anyone-with-link/{agent_id}/{thread_id}` | POST | Generate a public link for a thread |
| `/agent-invoke/shared-agent/{hash}` | GET | View a shared agent using its public hash |
| `/agent-invoke/shared-thread/{hash}` | GET | View a shared thread using its public hash |
| `/feature-sharing/agent/from_email/{agent_id}` | POST | Check a user's access permissions for an agent |

## Data Validation

The backend implements validation for sharing operations:

1. **Permission Validation**:
   - Validates that the user has permission to share the agent or thread
   - Checks ownership, company membership, or editor status

2. **Hash Generation**:
   - Creates a unique 16-character hash for public links
   - Reuses existing hashes if they already exist

## Access Control

The microservice implements the following access control rules:

1. **Agent Sharing Permissions**:
   - Agents can be shared by their owners, company members, or editors
   - Public sharing makes the agent accessible to anyone with the hash

2. **Thread Sharing Permissions**:
   - Threads can be shared by the agent owner, company members, or agent editors
   - Public sharing makes the thread accessible to anyone with the hash

3. **Access Levels**:
   - Editor access allows viewing and modifying the agent
   - Visitor access allows viewing but not modifying the agent
   - Public access allows anyone with the hash to view the agent or thread

## UI Components

1. **Agent Sharing Section**:
   - Agent dropdown for selection
   - Make Public checkbox
   - Share button
   - Result display with public hash

2. **Thread Sharing Section**:
   - Agent dropdown for selection
   - Thread dropdown that populates based on selected agent
   - Make Public checkbox
   - Share button
   - Result display with public hash

3. **View Shared Content Sections**:
   - Hash input fields
   - View buttons
   - Result displays for API responses

4. **Access Checking Section**:
   - Agent dropdown for selection
   - Email input field
   - Check Access button
   - Result display showing access status 