# Agent Creator Microservice Documentation

This document provides a comprehensive overview of the Agent Creator microservice, which facilitates the creation, configuration, and management of AI agents through automated field generation and user input parsing.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [Components](#components)
   - [API Routes](#api-routes)
   - [Models](#models)
   - [Field Processing](#field-processing)
4. [API Routes](#api-routes-details)
   - [Autofill Routes](#autofill-routes)
   - [User Input Routes](#user-input-routes)
5. [Data Models](#data-models)
6. [Field Autofill Process](#field-autofill-process)
7. [User Input Parsing Flow](#user-input-parsing-flow)
8. [Tool Integration](#tool-integration)

## Overview

The Agent Creator microservice provides a framework for:

1. Automatically generating agent field values based on context and user input
2. Parsing natural language user input to extract agent configuration information
3. Recommending appropriate tools for agents based on their purpose
4. Managing the agent creation workflow with real-time field generation
5. Supporting stream-based updates for responsive UI experiences

It simplifies the agent creation process by leveraging LLMs to intelligently fill in complex configuration fields and parse user requirements.

## Required Infrastructure

The Agent Creator microservice requires the following infrastructure:

1. **Supabase Database** with the following tables:
   - `tools`: Stores tool configurations for recommendation
   - `users`: Stores user information
   - `companies`: Stores company information for access control

2. **Environment Variables**:
   - `SUPABASE_URL`: URL for the Supabase instance
   - `SUPABASE_KEY`: API key for Supabase
   - LLM provider API keys (OpenAI, etc.)

3. **External Services**:
   - LLM providers (OpenAI, etc.)
   - MCPHub for tool recommendations

## Components

### API Routes

The API routes for the Agent Creator are defined in the `routes` directory:

#### `autofill.py`

Routes for field autofill generation:
- `GET/POST /agent_creator_autofill/invoke`: Generate field values based on context
- `GET/POST /agent_creator_autofill/invoke-stream`: Stream field generation results
- `GET /agent_creator_autofill/tools`: Get available tools for integration

#### `user_input_routes.py`

Routes for parsing natural language user input:
- `POST /user_input/parse-stream`: Stream parsing of user input for multiple fields
- `POST /user_input/parse-field`: Parse user input for a specific field
- `GET /user_input/field-description/{field_name}`: Get field description
- `GET /user_input/field-metadata`: Get metadata for all available fields
- `POST /user_input/extract-keywords`: Extract keywords from agent name and description
- `POST /user_input/parse-multi-agent`: Parse input for multiple agent creation

### Models

The data models for the Agent Creator are defined in `models.py`:

- `Tool`: Represents a tool that can be integrated with agents
- `RecommendationInput`: Input for field autofill generation
- `RecommendationResponse`: Response from field autofill generation

### Field Processing

The field processing components include:

- `agent_field_parser.py`: High-level interface for parsing user input
- `tool_autofill.py`: Handles field autofill generation using LLMs
- `utils/`: Contains utility functions for field processing, input parsing, and field descriptions

## API Routes Details

### Autofill Routes

#### `POST /agent_creator_autofill/invoke`

Generate a value for a specified field based on other field values.

**Request Body:**
- `field_name` (string): Name of the field to generate
- `json_field` (object): JSON object containing other field values
- `existing_field_value` (string, optional): Existing value of the field
- `return_tool_ids` (boolean, optional): Whether to return tool IDs instead of names

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: Successfully generated field value
- `400`: Bad request (invalid parameters)
- `500`: Internal server error

#### `GET /agent_creator_autofill/tools`

Get all available tools that can be used by agents.

**Query Parameters:**
- `company_id` (string, optional): Company ID to filter tools by

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: List of available tools
- `500`: Internal server error

### User Input Routes

#### `POST /user_input/parse-stream`

Stream the parsing of user input to extract field information.

**Request Body:**
- `user_input` (string): Natural language input from the user
- `target_fields` (array, optional): List of field names to extract
- `model_name` (string, optional): Name of the LLM to use
- `temperature` (float, optional): Temperature setting for the model

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- Streaming response with field updates
- Error responses for validation failures or server errors

#### `POST /user_input/parse-field`

Parse user input to extract information for a specific field.

**Request Body:**
- `user_input` (string): Natural language input from the user
- `field_name` (string): Name of the field to extract
- `model_name` (string, optional): Name of the LLM to use
- `temperature` (float, optional): Temperature setting for the model

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: Extracted field value
- `404`: Field not found
- `500`: Internal server error

#### `GET /user_input/field-metadata`

Get metadata for all available fields in a single call.

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: Dictionary containing field names and descriptions
- `500`: Internal server error

## Data Models

### Tool

Represents a tool that can be integrated with agents:

```python
class Tool(BaseModel):
    tool_id: str
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    versions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    on_status: Optional[str] = Field(default="offline")
    company_id: Optional[str] = None
```

### RecommendationInput

Input structure for field autofill generation:

```python
class RecommendationInput(BaseModel):
    field_name: str
    json_field: Dict[str, Any]
    available_tools: List[Tool]
    existing_field_value: str = ""
    return_tool_ids: Optional[bool] = True
```

### RecommendationResponse

Response structure for field autofill generation:

```python
class RecommendationResponse(BaseModel):
    field_name: str
    autofilled_value: Any
    reasoning: Optional[str] = None
```

## Field Autofill Process

The field autofill process follows these steps:

1. **Request Validation**:
   - Validate the field name and JSON field
   - Check for special case fields (tools, mcphub_recommended_tools)

2. **Special Field Handling**:
   - For tools field: Use LLM to recommend tools based on agent purpose
   - For mcphub_recommended_tools: Call MCPHub Compass or use fallback values

3. **Standard Field Generation**:
   - Construct system prompt with field descriptions
   - Include existing field values for context
   - Use LLM to generate appropriate field content

4. **Response Formatting**:
   - Return structured response with field name, value, and reasoning
   - Format special fields (like tools) according to requirements
   - Support streaming responses for real-time UI updates

## User Input Parsing Flow

The user input parsing process follows these steps:

1. **Input Analysis**:
   - Analyze natural language input from the user
   - Detect which fields are mentioned in the input

2. **Field Extraction**:
   - For each detected field, extract relevant information
   - Apply field-specific parsing logic

3. **Multi-field Integration**:
   - Combine extracted fields into a coherent agent configuration
   - Handle conflicts and inconsistencies

4. **Response Formatting**:
   - Return structured response with extracted field values
   - Support streaming responses for real-time UI updates

## Tool Integration

Agent Creator supports tool integration through:

1. **Tool Recommendation**:
   - Analyze agent purpose and keywords
   - Recommend appropriate tools from available options
   - Score tools based on relevance to the agent's purpose

2. **Tool Retrieval**:
   - Fetch tools from the Supabase database
   - Filter tools by company ID when appropriate
   - Present tools with their metadata (name, description, etc.)

3. **MCPHub Integration**:
   - Connect to MCPHub Compass for tool recommendations
   - Use fallback recommendations when API is unavailable
   - Format tool information for consistent presentation 