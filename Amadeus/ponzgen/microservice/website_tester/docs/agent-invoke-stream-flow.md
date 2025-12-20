# Agent Invoke Stream Microservice Flow

## Overview

The Agent Invoke Stream microservice provides a real-time, streaming interface for interacting with AI agents in the system. Unlike the standard invoke endpoint, this implementation uses Server-Sent Events (SSE) to stream agent responses token by token, providing a more interactive and dynamic user experience. This document explains the application flow, streaming mechanism, and data requirements.

## Application Components

1. **Frontend UI (`agent-invoke-stream.html`)**
   - Provides a chat-like interface for interacting with agents
   - Includes sections for agent selection, configuration options, and a chat window
   - Styled with CSS to represent a conversational UI with user and agent messages
   - Handles real-time rendering of streamed tokens

2. **Frontend Logic (`agent-invoke-stream.js`)**
   - Manages the streaming connection to the backend
   - Processes various event types (tokens, status updates, tool statuses)
   - Handles special content formatting (images, videos, markdown, HTML, JSON)
   - Maintains conversation state and history

3. **Backend API (same as regular invoke)**
   - Provides the `/agent-invoke/{agent_id}/invoke-stream` endpoint
   - Uses a streaming response mechanism to send tokens and status updates
   - Handles authentication, permissions, and agent execution

## Streaming Implementation

The streaming implementation uses a combination of server-sent events and client-side processing:

1. **Server-Side Events**
   - The backend emits several types of events:
     - `token`: Individual text tokens from the agent's response
     - `status`: Agent processing status updates
     - `tool_status`: Updates on tool executions and their results

2. **Client-Side Processing**
   - The frontend establishes a connection to the streaming endpoint
   - Processes incoming events and updates the UI accordingly
   - Implements buffering for special content blocks
   - Renders different content types appropriately (markdown, images, etc.)

## User Flow

### 1. Select an Agent

**Frontend:**
- On page load, the system loads available agents via `loadAgentsForDropdown()`
- The function makes a GET request to the `/agents` endpoint
- Results are displayed in a dropdown for user selection
- When an agent is selected, its details are fetched automatically

**Backend:**
- Same as the regular invoke endpoint, providing agent information

### 2. View Agent Details

**Frontend:**
- When a user selects an agent, the `getAgentDetails()` function is called
- Makes a GET request to `/agents/{agent_id}`
- Agent details including tools are displayed
- Details are stored in the `currentAgentDetails` variable for invocation

**Backend:**
- Retrieves agent details and tools from the database

### 3. Configure Settings

**Frontend:**
- Users can set various parameters:
  - Context (optional background information)
  - Thread ID (for conversation continuity, defaults to "1")
  - Model name (selected from available models)
  - Reset Memory (checkbox to clear conversation history)
  - Load From JSON (checkbox for configuration loading)
  - Agent Style (optional override for agent personality)

### 4. Start Conversation

**Frontend:**
1. User types a message in the input field
2. Clicks the send button or presses Enter to invoke the agent
3. The message appears in the chat interface
4. The `invokeAgentStream()` function is called to initiate the streaming connection

**Backend:**
1. Receives the request at `/agent-invoke/{agent_id}/invoke-stream`
2. Validates permissions, agent existence, and request parameters
3. Initiates the agent execution process
4. Streams responses back as they're generated

### 5. Process Streaming Response

**Frontend:**
1. Establishes a streaming connection using `fetch` API with streaming response
2. Processes incoming chunks of data from the stream
3. Parses SSE events and dispatches to appropriate handlers:
   - `handleStatusEvent`: Updates the status display
   - `handleToolStatusEvent`: Shows tool execution status
   - `handleTokenEvent`: Adds tokens to the agent's response
4. Renders the agent's message token by token in real-time
5. Processes any special content blocks (marked with `!#block#!` and `!#/block#!` delimiters)

### 6. Special Content Rendering

**Frontend:**
- Implements special content parsing and rendering:
  - Images: Displays images with captions
  - Videos: Embeds video players
  - Markdown: Renders formatted text using the marked library
  - HTML: Safely renders HTML content with script execution
  - JSON: Formats and displays JSON data

### 7. Conversation Management

**Frontend:**
- Maintains conversation history in the `conversationHistory` array
- Provides a "Clear Chat" button to reset the conversation
- Allows continuous back-and-forth interaction with the agent

## Data Requirements

### Core Data Entities

1. **Agent Input Data**:
   - `input`: Contains messages and context
     - `messages`: User's message to the agent (string, required)
     - `context`: Additional context (string, optional)
   - `config`: Configuration options
     - `configurable`: Contains configurable options
       - `thread_id`: Identifier for conversation continuity (string, required)
   - `metadata`: Additional settings
     - `model_name`: The language model to use (string)
     - `reset_memory`: Whether to reset agent memory (boolean)
     - `load_from_json`: Whether to load from JSON (boolean)
     - `agent_style`: Custom agent style (string, optional)
   - `agent_config`: Full agent configuration (object)

2. **Agent Config Data**:
   - `agent_id`: Unique identifier for each agent (UUID)
   - `agent_name`: Name of the agent (string)
   - `description`: Optional description (string)
   - `agent_style`: Style/personality configuration (string)
   - `on_status`: Active status flag (boolean)
   - `tools`: Array of tool IDs (UUID[])
   - `company_id`: Optional association with a company (UUID)
   - `user_id`: Owner of the agent (UUID)
   - `share_editor_with`: Array of email addresses with editor access
   - `share_visitor_with`: Array of email addresses with visitor access

3. **Event Data Types**:
   - `token`: 
     - `token`: The text token being sent (string)
   - `status`:
     - `status`: Current status message (string)
     - `final_answer`: Complete response when execution ends (optional)
   - `tool_status`:
     - `tool_name`: Name of the tool being executed (string)
     - `status`: Tool execution status (string)
     - `is_start`: Whether this is start or end of execution (boolean)
     - `input`: Tool input parameters (optional)
     - `output`: Tool execution results (optional)

4. **Special Content Block Format**:
   - Delimited by `!#block#!` and `!#/block#!`
   - Contains JSON with:
     - `type`: Content type (image, video, markdown, html, json)
     - `content`: The content to render (varies by type)
     - Additional optional fields (alt, additional)

### Database Dependencies

The streaming microservice relies on the same database tables as the regular invoke endpoint:

- `agents`: Stores agent information
- `tools_with_decrypted_keys`: View with decrypted environment variables
- `user_companies`: Maps users to companies with roles
- `users`: Stores user information
- `agent_logs`: Stores agent conversation history

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent-invoke/{agent_id}/invoke-stream` | POST | Invoke an agent with streaming response |
| `/agents` | GET | Get all agents (filtered by user or company) |
| `/agents/{agent_id}` | GET | Get a specific agent by ID with tool details |
| `/get-llms` | GET | Get available language models |

## Streaming Performance Considerations

1. **Memory Management**
   - The frontend needs to efficiently manage appending tokens to avoid performance issues
   - Uses buffering mechanism to handle special content blocks
   - Implements scroll management to ensure the chat window follows new content

2. **Error Handling**
   - Connection interruptions are handled gracefully
   - The UI prevents interaction during active streams
   - Error messages are displayed in the chat window

3. **Content Safety**
   - Special content rendering includes security measures
   - HTML content is processed to safely execute scripts
   - JSON content is validated before rendering

## UI Components

1. **Chat Interface**
   - Styled to resemble a modern chat application
   - User messages right-aligned with blue background
   - Agent messages left-aligned with light background
   - Timestamps on messages
   - Scrollable container with auto-scroll

2. **Status Displays**
   - Current status indicator shows agent processing state
   - Tool status display shows detailed information about tool executions
   - Clear visual indicators for active processing

3. **Input Controls**
   - Text input for user messages
   - Send button with arrow icon
   - Configuration options panel
   - Clear chat button 