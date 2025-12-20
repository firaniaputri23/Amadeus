# Companies Microservice Flow

## Overview

The Companies Microservice provides functionality for managing company data, including creating, reading, updating, and deleting companies, as well as managing user associations and permissions within those companies. This document explains the application flow from the frontend UI through to the backend API and details the data requirements.

## Application Components

1. **Frontend UI (`companies.html`)**
   - Provides a comprehensive interface for managing companies and their users
   - Includes sections for viewing company listings, managing company details, and administering company users
   - Features forms for creating/editing companies and adding users with specified roles

2. **Frontend Logic (`companies.js`)**
   - Handles all client-side interactions and API calls
   - Manages company data loading, creation, editing, and deletion
   - Provides functionality for managing user-company relationships
   - Handles role assignments and permission checking

3. **Backend API (`companies.py`)**
   - Provides RESTful endpoints for company operations
   - Handles authentication, permission checks, and data validation
   - Manages interactions with the database for company and user-company relationship storage
   - Enforces role-based access control for company management

## User Flow

### 1. View Companies

**Frontend:**
- On page load, the frontend automatically calls `loadCompanies()` function
- The function makes a GET request to the `/companies` endpoint
- Companies are displayed as cards with company name, description, and action buttons

**Backend:**
- The `/companies` endpoint retrieves companies based on:
  - User ID from the authentication token
  - User's company associations from the `user_companies` table
- The backend returns all companies the user has access to

### 2. Create a New Company

**Frontend:**
1. User clicks the "Create Company" button
2. A modal dialog appears with a form
3. User fills out the company details:
   - Company name (required)
   - Description (optional)
4. User submits the form by clicking "Save"
5. The `saveCompany()` function sends a POST request to `/companies`

**Backend:**
1. The POST `/companies` endpoint receives the request
2. Validates user permissions (only super admins in the "Predefined" company can create companies)
3. Creates a new record in the `companies` table
4. Adds the creating user as a super admin of the new company
5. Returns the created company data

### 3. Edit a Company

**Frontend:**
1. User clicks the "Edit" button on a company card
2. A modal dialog appears with pre-filled company details
3. User modifies the company information
4. User submits the form by clicking "Save"
5. The `saveCompany()` function sends a PUT request to `/companies/{company_id}`

**Backend:**
1. The PUT `/companies/{company_id}` endpoint receives the request
2. Validates user permissions (must be an admin or super admin of the company, or a super admin in the "Predefined" company)
3. Updates the company record in the database
4. Returns the updated company data

### 4. Delete a Company

**Frontend:**
1. User clicks the "Delete" button on a company card
2. A confirmation dialog appears
3. User confirms the deletion
4. The `deleteCompany()` function sends a DELETE request to `/companies/{company_id}`

**Backend:**
1. The DELETE `/companies/{company_id}` endpoint receives the request
2. Validates user permissions (similar to edit permissions)
3. Checks for associated agents (deletion is prevented if agents exist)
4. Deletes all user-company relationships from the `user_companies` table
5. Deletes the company from the `companies` table
6. Returns a success message

### 5. View Company Users

**Frontend:**
1. User clicks the "View Users" button on a company card
2. The `loadCompanyUsers()` function sends a GET request to `/companies/{company_id}/users`
3. Results are displayed in a table showing:
   - User ID
   - Role
   - Action buttons (Remove)

**Backend:**
1. The GET `/companies/{company_id}/users` endpoint receives the request
2. Validates user permissions for the specified company
3. Retrieves all users associated with the company from the `user_companies` table
4. Returns the user data with role information

### 6. Add User to Company

**Frontend:**
1. User clicks the "Add User" button in the company users section
2. A modal dialog appears with a form
3. User fills out:
   - User ID (UUID format)
   - Role (selected from dropdown)
4. User submits the form by clicking "Add"
5. The `addUserToCompany()` function sends a POST request to `/companies/{company_id}/users`

**Backend:**
1. The POST `/companies/{company_id}/users` endpoint receives the request
2. Validates user permissions (must be admin or super admin)
3. Checks if the user already has a role in the company
   - If yes, updates the existing role
   - If no, creates a new user-company relationship
4. Returns a success message

### 7. Remove User from Company

**Frontend:**
1. User clicks the "Remove" button for a specific user
2. A confirmation dialog appears
3. User confirms the removal
4. The `removeUserFromCompany()` function sends a DELETE request to `/companies/{company_id}/users/{user_id}`

**Backend:**
1. The DELETE `/companies/{company_id}/users/{user_id}` endpoint receives the request
2. Validates user permissions (must be admin or super admin)
3. Prevents removal if the user is the last admin of the company
4. Deletes the user-company relationship from the database
5. Returns a success message

## Data Requirements

### Core Data Entities

1. **Company Data**:
   - `company_id`: Unique identifier for the company (UUID, auto-generated)
   - `name`: Name of the company (string)
   - `description`: Description of the company (string, optional)
   - `created_at`: Timestamp of creation (datetime, auto-generated)

2. **User-Company Relationship Data**:
   - `user_id`: Reference to the user (UUID)
   - `company_id`: Reference to the company (UUID)
   - `role_id`: Reference to the role (integer)

3. **Role Data**:
   - `role_id`: Unique identifier for the role (integer)
   - `role_name`: Name of the role (string)
   - `permissions`: Permissions associated with the role (JSON object)

### Database Tables & Relationships

The microservice relies on the following database tables:

- `companies`: Stores company information
- `user_companies`: Maps users to companies with roles
- `roles`: Defines role permissions
- `users`: Stores user information
- `agents`: Stores agent information (referenced for deletion constraints)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies` | GET | Get all companies the user has access to |
| `/companies` | POST | Create a new company |
| `/companies/{company_id}` | GET | Get details of a specific company |
| `/companies/{company_id}` | PUT | Update a specific company |
| `/companies/{company_id}` | DELETE | Delete a specific company |
| `/companies/{company_id}/users` | GET | Get all users in a specific company |
| `/companies/{company_id}/users` | POST | Add a user to a company with a role |
| `/companies/{company_id}/users/{user_id}` | DELETE | Remove a user from a company |
| `/roles` | GET | Get all available roles (used in frontend dropdowns) |

## Data Validation

The backend implements robust validation for incoming data:

1. **Company Data**:
   - Company name is required
   - Description is optional

2. **User-Company Relationship**:
   - User ID must be a valid UUID
   - Role ID must reference an existing role
   - User ID and company ID must be unique together (one role per user per company)

## Access Control

The microservice implements the following access control rules:

1. **Company Creation**:
   - Only super admin users from the "Predefined" company can create new companies
   - The creator is automatically added as a super admin of the new company

2. **Company Management**:
   - Company details can be viewed and edited by users with admin or super admin roles in that company
   - Companies can be deleted only by admins or super admins, and only if no agents are associated with them

3. **User Management**:
   - Only admins and super admins can add or remove users from a company
   - Users cannot remove themselves if they are the last admin of a company
   - The "Predefined" company has special protections to ensure its super admin always remains

4. **Role-Based Control**:
   - Two primary admin roles exist: super admin (role_id: 1) and admin (role_id: 2)
   - Different operations require different role levels
   - Super admins in the "Predefined" company have system-wide admin privileges

## UI Components

1. **Company Listing**:
   - Cards displaying company information
   - Action buttons for view users, edit, and delete
   - Create company button

2. **Company Form Modal**:
   - Input fields for company name and description
   - Save and cancel buttons

3. **Company Users Table**:
   - List of users with their roles
   - Remove user buttons
   - Add user button

4. **Add User Modal**:
   - User ID input field with UUID validation
   - Role selection dropdown
   - Add and cancel buttons 