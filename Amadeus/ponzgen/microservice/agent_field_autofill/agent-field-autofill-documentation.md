# Agent Field Autofill Microservice Documentation

This document provides a comprehensive overview of the Agent Field Autofill microservice, which facilitates the automatic generation of agent field values based on existing field data and context.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [Components](#components)
   - [Core Class](#core-class)
   - [API Routes](#api-routes)
   - [Models](#models)
   - [Utilities](#utilities)
4. [API Routes](#api-routes-details)
   - [Autofill Routes](#autofill-routes)
5. [Data Models](#data-models)
6. [Field Autofill Process](#field-autofill-process)
7. [Configuration](#configuration)

## Overview

The Agent Field Autofill microservice provides a framework for:

1. Automatically generating agent field values based on context and existing field values
2. Providing both direct and streaming responses for field generation
3. Integrating with LLMs to generate high-quality field content
4. Supporting the agent creation workflow with intelligent field suggestions

It is a simplified version of the agent boilerplate, specifically focused on the field autofill functionality without requiring memory, tools, or other complex features of the full agent system.

## Required Infrastructure

The Agent Field Autofill microservice requires the following infrastructure:

1. **Configuration Files**:
   - `config/field_desc.json`: Contains descriptions for each field type

2. **Environment Variables**:
   - `OPEN_ROUTER_API_KEY`: API key for OpenRouter (LLM provider)
   - `OPEN_ROUTER_BASE_URL`: Base URL for OpenRouter API

3. **External Services**:
   - LLM providers (OpenAI via OpenRouter)

## Components

### Core Class

The core functionality is implemented in the `agent_field_autofill.py` file:

#### `AgentFieldAutofill`

The main class that handles:
- Field autofill generation using LLMs
- System prompt construction for field generation
- Error handling for LLM invocations
- Streaming responses for real-time updates

**Key Functions:**
- `get_llm`: Configures and returns an LLM instance
- `generate_autofill`: Generates field values based on context
- `generate_autofill_stream`: Streaming version of field generation

### API Routes

The API routes for the Agent Field Autofill are defined in the `routes/autofill.py` file:

#### `autofill.py`

Routes for field autofill generation:
- `POST /agent_field_autofill/invoke`: Generate field values
- `GET/POST /agent_field_autofill/invoke-stream`: Stream field generation results

### Models

The data models for the Agent Field Autofill are defined in `models.py`:

- `RecommendationInput`: Input structure for autofill requests
- `RecommendationResponse`: Output structure for autofill responses

### Utilities

Utility functions in the `utils/` directory:

#### `field_utils.py`

Contains utilities for:
- Loading field descriptions from configuration files
- Constructing system prompts for LLM field generation

## API Routes Details

### Autofill Routes

#### `POST /agent_field_autofill/invoke`

Generate a value for a specified field based on other field values.

**Request Body:**
- `field_name` (string): Name of the field to generate
- `json_field` (object): JSON object containing other field values
- `existing_field_value` (string, optional): Existing value of the field to continue from

**Authentication Requirements:**
- Valid user authentication (user_id in request state)

**Responses:**
- `200`: Successfully generated field value
- `400`: Bad request (invalid parameters)
- `500`: Internal server error
- `503`: Service unavailable (LLM service error)

#### `POST /agent_field_autofill/invoke-stream`

Streaming version of the autofill endpoint.

**Request Body:** Same as non-streaming version

**Query Parameters (for GET requests):**
- `field_name` (string): Name of the field to generate
- `json_field` (string): JSON-encoded object containing other field values
- `existing_field_value` (string, optional): Existing value of the field
- `token` (string, optional): Authentication token for EventSource

**Authentication Requirements:**
- Valid user authentication (user_id in request state)

**Responses:**
- Streaming response with event types:
  - `status`: Status updates (processing, complete)
  - `token`: Individual tokens for progressive rendering
  - `error`: Error messages
- Error responses for validation failures or server errors

## Data Models

### RecommendationInput

Input structure for field autofill generation:

```python
class RecommendationInput(BaseModel):
    field_name: str = Field(..., description="The name of the field to generate")
    json_field: Dict[str, Any] = Field(..., description="JSON object containing other field values")
    existing_field_value: str = Field("", description="Existing value of the field to continue from (if any)")
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
   - Validate the field name and JSON field structure
   - Check for required parameters and proper formatting

2. **System Prompt Construction**:
   - Load field descriptions from configuration
   - Create a detailed system prompt with context from other fields
   - Include instructions for generating the target field

3. **LLM Invocation**:
   - Configure the LLM with appropriate parameters
   - Send the system prompt to the LLM
   - Process the response (either full or streaming)

4. **Response Formatting**:
   - Format the LLM response into the expected structure
   - For streaming responses, send appropriately formatted SSE events
   - Include error handling and status updates

## Configuration

The Agent Field Autofill microservice requires the following configuration:

### Field Descriptions

Field descriptions are stored in `config/field_desc.json` with the following structure:

```json
{
  "field_name": "Description of the field and its purpose",
  "agent_name": "The name that identifies the agent",
  "description": "A detailed description of what the agent does",
  ...
}
```

These descriptions are used to:
1. Provide context for the LLM when generating field values
2. Guide the generation process with field-specific instructions
3. Ensure generated content matches the expected format and purpose

### Environment Variables

Required environment variables:

```
OPEN_ROUTER_API_KEY=<your-api-key>
OPEN_ROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions
```

If these variables are not set, the service uses default values for development purposes, but production deployments should set proper API keys. 