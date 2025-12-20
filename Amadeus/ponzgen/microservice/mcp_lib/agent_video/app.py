import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, Literal
import fal_client
from fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("Fal.ai")

# Valid size presets
ImageSizePreset = Literal[
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]

# Optional real-time log handler
def on_queue_update(update):
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print(log["message"])

# Input schema for the MCP tool
class ImageGenInput(BaseModel):
    prompt: str = Field(..., description="A textual description of the image to generate. Example: 'a cat in space'.")
    image_size_preset: ImageSizePreset = Field(..., description="The desired image aspect ratio preset.")
    num_images: int = Field(..., description="The number of images to generate (1 to 4).", ge=1, le=4)
    seed: Optional[int] = Field(None, description="Optional seed for reproducible image generation. Leave empty for random output.")
    model_name: str = Field("fal-ai/flux/dev", description="The model to use for image generation. Defaults to 'fal-ai/flux/dev'.")


# Video input schema for the MCP tool
class VideoGenInput(BaseModel):
    prompt: str = Field(..., description="A textual description of the video to generate.")
    image_url: str = Field(..., description="URL of the reference image for video generation.")
    model_name: str = Field("fal-ai/kling-video/v2/master/image-to-video", description="The model to use for video generation. Defaults to 'fal-ai/kling-video/v2/master/image-to-video'.")

# Register function as MCP tool
@mcp.tool()
def generate_images(data: ImageGenInput):
    """
    Generate images using the FAL Flux model.

    Parameters:
    - prompt: A textual description of the image to generate.
    - image_size_preset: The desired image aspect ratio preset.
    - num_images: The number of images to generate (1 to 4).
    - seed: Optional seed for reproducible image generation.

    Returns:
    - The result from the FAL API, including image URLs and metadata.
    """
    arguments = {
        "prompt": data.prompt,
        "image_size": data.image_size_preset,
        "num_images": data.num_images
    }

    if data.seed is not None:
        arguments["seed"] = data.seed

    result = fal_client.subscribe(
        data.model_name,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    return result

@mcp.tool()
def generate_video(data: VideoGenInput):
    """
    Generate a video using a prompt and a reference image.

    Parameters:
    - prompt: A textual description of the video to generate.
    - image_url: URL of the reference image for video generation.
    - model_name: The model to use for video generation. Defaults to 'fal-ai/kling-video/v2/master/image-to-video'.

    Returns:
    - The result from the FAL API, including video URL and metadata.
    """
    arguments = {
        "prompt": data.prompt,
        "image_url": data.image_url
    }
    result = fal_client.subscribe(
        data.model_name,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    return result


if __name__ == "__main__":
    mcp.run()
    #  mcp-proxy --sse-port=10100 -- python app.py 