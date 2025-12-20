# Agent Video Microservice Documentation

This document provides a comprehensive overview of the Agent Video microservice, which enables AI agents to generate images and videos using the Fal.ai API through FastMCP integration.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [Components](#components)
4. [MCP Tools](#mcp-tools)
   - [Image Generation](#image-generation)
   - [Video Generation](#video-generation)
5. [Data Models](#data-models)
6. [Running the Service](#running-the-service)
7. [Error Handling](#error-handling)

## Overview

The Agent Video microservice provides a framework for:

1. Generating images based on textual descriptions (prompts)
2. Creating videos from reference images and textual prompts
3. Exposing these capabilities as MCP tools for use by AI agents
4. Handling real-time progress logging during generation

The service acts as a wrapper around Fal.ai's image and video generation models, making them available as standardized tools within the Mission Control Panel (MCP) ecosystem.

## Required Infrastructure

The Agent Video microservice requires the following infrastructure:

1. **Environment Variables** (via .env file):
   - `FAL_KEY`: API key for Fal.ai services
   - `FAL_SECRET`: Secret key for Fal.ai authentication

2. **External Dependencies**:
   - `fal_client`: Python client for Fal.ai API
   - `fastmcp`: FastMCP framework for exposing tools to MCP
   - `fastapi`: Web framework for API endpoints
   - `pydantic`: Data validation and settings management
   - `python-dotenv`: Environment variable management

3. **External Services**:
   - [Fal.ai](https://fal.ai): Provider of AI models for image and video generation

## Components

The microservice consists of the following components:

1. **FastMCP Integration**:
   - Initializes FastMCP with service name "Fal.ai"
   - Registers Python functions as MCP tools
   - Handles input validation and serialization

2. **Data Models**:
   - `ImageGenInput`: Schema for image generation parameters
   - `VideoGenInput`: Schema for video generation parameters
   - Type definitions for image size presets

3. **Logging System**:
   - Real-time progress logging via `on_queue_update` callback

## MCP Tools

### Image Generation

**Tool Name**: `generate_images`

**Description**: Generates images using the FAL Flux model based on textual prompts.

**Input Parameters**:
- `prompt` (string, required): Textual description of the image to generate
- `image_size_preset` (string, required): Predefined aspect ratio preset
  - Valid options: "square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3", "landscape_16_9"
- `num_images` (integer, required): Number of images to generate (1-4)
- `seed` (integer, optional): Seed for reproducible image generation
- `model_name` (string, optional): The model to use, defaults to "fal-ai/flux/dev"

**Output**:
- JSON object containing:
  - Image URLs
  - Generation metadata
  - Status information

**Example Usage**:
```json
{
  "prompt": "a cat in space wearing an astronaut helmet",
  "image_size_preset": "square_hd",
  "num_images": 2,
  "seed": 42
}
```

### Video Generation

**Tool Name**: `generate_video`

**Description**: Generates videos based on a reference image and textual prompt.

**Input Parameters**:
- `prompt` (string, required): Textual description of the video to generate
- `image_url` (string, required): URL of the reference image to animate
- `model_name` (string, optional): The model to use, defaults to "fal-ai/kling-video/v2/master/image-to-video"

**Output**:
- JSON object containing:
  - Video URL
  - Generation metadata
  - Status information

**Example Usage**:
```json
{
  "prompt": "a cat floating in space",
  "image_url": "https://example.com/cat_image.jpg"
}
```

## Data Models

### ImageGenInput

```python
class ImageGenInput(BaseModel):
    prompt: str
    image_size_preset: ImageSizePreset
    num_images: int  # Range: 1-4
    seed: Optional[int] = None
    model_name: str = "fal-ai/flux/dev"
```

### VideoGenInput

```python
class VideoGenInput(BaseModel):
    prompt: str
    image_url: str
    model_name: str = "fal-ai/kling-video/v2/master/image-to-video"
```

### ImageSizePreset

```python
ImageSizePreset = Literal[
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]
```

## Running the Service

To run the service locally:

1. Create a `.env` file in the service directory with your Fal.ai credentials:
   ```
   FAL_KEY=your_fal_key
   FAL_SECRET=your_fal_secret
   ```

2. Install dependencies:
   ```bash
   pip install fal-client fastmcp fastapi pydantic python-dotenv
   ```

3. Run the service:
   ```bash
   python app.py
   ```

4. For development with MCP proxy:
   ```bash
   mcp-proxy --sse-port=10100 -- python app.py
   ```

## Error Handling

The service handles errors through the following mechanisms:

1. **Input Validation**:
   - Pydantic models enforce type checking and value constraints
   - Field validation ensures values are within acceptable ranges

2. **API Errors**:
   - Fal.ai API errors are propagated through the response
   - Real-time logs provide information about generation progress

3. **Progress Monitoring**:
   - The `on_queue_update` callback displays real-time logs during generation
   - Status updates are shown in the console for debugging 