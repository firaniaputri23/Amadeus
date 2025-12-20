# Agent Creator Microservice Flow

## Overview

The Agent Creator Microservice provides functionality for creating AI agents through a user-friendly interface that leverages natural language processing. It allows users to describe the agent they want in plain text, and the system extracts the necessary configuration parameters automatically. This document explains the application flow from the frontend UI through to the backend API and details the data requirements.

## Application Components

1. **Frontend UI (`agent-creator.html`)**
   - Provides an intuitive chat-like interface for describing and creating agents
   - Includes sections for inputting agent descriptions, viewing extracted agent parameters, and managing tools
   - Features a multi-agent creation toggle for creating multiple related agents at once
   - Offers example prompts to help users get started

2. **Frontend Logic (`agent-creator.js`)**
   - Handles all client-side interactions and API calls
   - Manages the chat interface for agent description input
   - Processes NLP-extracted data and presents it as a structured agent preview
   - Provides functionality for creating single or multiple agents
   - Handles tool selection and integration with agent configuration

3. **Backend API (`user_input_routes.py` and `autofill.py`)**
   - Provides RESTful endpoints for parsing natural language descriptions
   - Handles authentication, permission checks, and data validation
   - Processes user input to extract agent configuration fields
   - Recommends appropriate tools based on agent description
   - Manages interactions with the database for agent creation and tool retrieval

## User Flow

### 1. Describe an Agent

**Frontend:**
- User enters a natural language description of the agent they want to create
- User can toggle between single agent and multi-agent creation modes
- User can select from example prompts to get started quickly
- The description is sent to the backend via the `parse-stream` endpoint (or `parse-multi-agent` for multi-agent mode)

**Backend:**
- The `/parse-stream` endpoint receives the request with the user's description
- The system processes the description using an LLM (default: GPT-4o Mini)
- Extracts relevant agent configuration fields like name, description, instructions, etc.
- Returns structured data that represents the described agent

### 2. Review and Refine Agent Parameters

**Frontend:**
1. The extracted agent data is displayed in a preview panel
2. User can see all the extracted fields and their values
3. User can continue the conversation to refine or add to the agent description
4. The system updates the agent preview as more information is provided

**Backend:**
1. Each additional user input is processed to extract more fields or refine existing ones
2. The backend maintains context of the conversation to improve extraction accuracy
3. Specialized field parsing can be requested for specific fields that need refinement

### 3. Tool Selection and Configuration

**Frontend:**
1. The system automatically recommends tools based on the agent description
2. User can manually select or deselect tools from the available options
3. Tool checkboxes are organized by category for easy navigation
4. Selected tools are incorporated into the agent configuration

**Backend:**
1. The `/tools` endpoint provides a list of available tools the user has access to
2. The `/invoke` autofill endpoint recommends appropriate tools based on the agent description
3. Tool recommendations consider the user's permissions and company access

### 4. Create the Agent

**Frontend:**
1. Once all required fields are filled, the Create Agent button becomes enabled
2. User clicks the Create button to finalize the agent
3. The system prepares the agent data and sends it to the agent creation endpoint
4. For multi-agent mode, the system prepares variations for each described agent

**Backend:**
1. The agent creation request is validated for required fields
2. The system creates the agent record(s) in the database
3. Tool associations are created for the agent
4. A success response is returned with the created agent details

## Data Requirements

### Core Data Entities

1. **Agent Configuration Data**:
   - `name`: Name of the agent (string)
   - `description`: Brief description of the agent's purpose (string)
   - `instructions`: Detailed instructions for the agent (string)
   - `model_name`: LLM model to use (string)
   - `model_provider`: Provider of the LLM (string)
   - `temperature`: Temperature setting for randomness (decimal)
   - `tools`: Array of tool IDs the agent can use (array of strings)
   - `welcome_message`: Initial message the agent sends (string)
   - `context`: Additional context for the agent (string, optional)
   - `avatar_url`: URL to the agent's avatar image (string, optional)
   - `metadata`: Additional configuration parameters (JSON object, optional)

2. **Multi-Agent Configuration Data**:
   - Common fields shared by all agents in the group
   - Variations for each agent (name, description, instructions, etc.)
   - Relations between agents if they work together

3. **Tool Data**:
   - `id`: Unique identifier for the tool (string)
   - `name`: Display name of the tool (string)
   - `description`: Description of what the tool does (string)
   - `category`: Category the tool belongs to (string)
   - `auth_type`: Authentication type required (string)
   - `company_id`: Associated company if applicable (UUID, optional)
   - `user_id`: Owner of the tool (UUID, optional)
   - `is_public`: Whether the tool is publicly available (boolean)

### Parser Request Data

1. **Base Parser Request**:
   - `user_input`: Natural language input from the user (string)
   - `model_name`: LLM model to use for parsing (string, default: "openai/gpt-4o-mini")
   - `temperature`: Temperature setting (decimal, default: 0)

2. **Field-Specific Parse Request**:
   - All base parser fields
   - `field_name`: Specific field to extract (string)
   
3. **Multi-Agent Parse Request**:
   - All base parser fields
   - `existing_data`: Any existing agent data to build upon (JSON object, optional)

### Autofill Request Data

1. **Tool Recommendation Input**:
   - `agent_data`: Current agent configuration (JSON object)
   - `json_field`: Target field for autofill (string)
   - `company_id`: Company context for tool access (UUID, optional)
   - `available_tools`: List of tools the user has access to (array)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parse-stream` | POST | Parse user input and extract agent fields with streaming response |
| `/parse-field` | POST | Parse a specific field from user input |
| `/field-metadata` | GET | Get metadata about available fields |
| `/field-description/{field_name}` | GET | Get description for a specific field |
| `/tools` | GET | Get available tools (filtered by user or company) |
| `/invoke` | POST | Get tool recommendations for an agent |
| `/parse-multi-agent` | POST | Parse user input for creating multiple agents |
| `/extract-keywords` | POST | Extract keywords from agent description |

## Data Validation

The backend implements robust validation for incoming data:

1. **Required Fields**:
   - Agent name, description, and instructions are required
   - Model name and temperature must be valid
   - At least one tool should be selected (recommended but not enforced)

2. **Field Format Validation**:
   - Temperature must be a decimal between 0 and 1
   - Tool IDs must be valid and accessible to the user
   - JSON fields must be properly formatted

## Access Control

The microservice implements the following access control rules:

1. **User Authentication**:
   - All requests require a valid user token
   - User ID is extracted from the token for permission checking

2. **Tool Access Control**:
   - Users can only select tools they have access to
   - Company tools are available to users within the company
   - Public tools are available to all users

3. **Permission Verification**:
   - Each endpoint verifies the user has appropriate access
   - Company-level permissions are verified for company tools

## UI Components

1. **Chat Interface**:
   - Text area for inputting agent descriptions
   - Message display for conversation history
   - Example prompt suggestions
   - Toggle for multi-agent creation mode
   - Typing indicator for feedback during processing

2. **Agent Preview**:
   - Structured display of extracted agent fields
   - Visual indication of filled vs. missing fields
   - Formatting of special fields (JSON, arrays, etc.)

3. **Tool Selection**:
   - Checkbox grid for selecting agent tools
   - Categorized tool listings
   - Autofill recommendations based on agent description
   - Visual feedback for recommended tools

4. **Agent Creation Controls**:
   - Create button (enabled when required fields are present)
   - Reset button to start over
   - Field help modal for understanding available fields 