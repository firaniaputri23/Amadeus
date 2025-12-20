# LLM Upgrade Guide: Hybrid Model System

## What Changed?

Your system now supports **multiple LLM providers** while keeping your custom VLM:

- ✅ **Custom VLM** (Gemma-2-2b + CLIP) - For vision tasks (FREE, local)
- ✅ **OpenRouter** - Access to Gemma-2-9b, Gemma-2-27b, GPT, Claude (Pay-per-use)
- ✅ **OpenAI Direct** - Direct OpenAI API access

## Why This Is Better Than "Upgrading to Gemma 3"

| Approach | Pros | Cons |
|----------|------|------|
| **Upgrade to Gemma 3** | Newer model | Need to retrain adapter ($$$), still no guaranteed tool support |
| **Hybrid System** ✅ | Keep vision, add tool calling | Small API costs, need API keys |

## Setup Instructions

### 1. Get API Keys (Choose one or both)

#### Option A: OpenRouter (Recommended - Access to 100+ models)
1. Go to https://openrouter.ai
2. Sign up and get your API key
3. Add to your `.env` file:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
```

#### Option B: OpenAI Direct
1. Go to https://platform.openai.com/api-keys
2. Create an API key
3. Add to your `.env` file:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 2. Install Dependencies

```bash
# Already have langchain-openai, but update it
pip install --upgrade langchain-openai
```

### 3. Test the Setup

```python
# Test file: test_models.py
from microservice.agent_boilerplate.boilerplate.utils.get_llms import get_llms

# Test 1: Custom VLM (should work without API keys)
model = get_llms("custom-vlm")
print("✅ Custom VLM loaded")

# Test 2: Gemma-2-9b via OpenRouter (needs API key)
model = get_llms("google/gemma-2-9b-it", temperature=0.7)
response = model.invoke("Say hello!")
print(f"✅ Gemma-2-9b response: {response.content}")

# Test 3: GPT-4o-mini via OpenRouter
model = get_llms("openai/gpt-4o-mini")
response = model.invoke("What is 2+2?")
print(f"✅ GPT-4o-mini response: {response.content}")
```

Run it:
```bash
python test_models.py
```

## Usage Examples

### Example 1: Vision Task (Use Custom VLM - FREE)
```json
{
  "agent_input": {
    "input": {
      "messages": "What's in this image?",
      "image_path": "/path/to/image.jpg"
    },
    "metadata": {
      "model_name": "custom-vlm"
    }
  }
}
```

### Example 2: Tool Calling Task (Use Gemma-2-9b)
```json
{
  "agent_input": {
    "input": {
      "messages": "Check my GitHub repositories"
    },
    "metadata": {
      "model_name": "google/gemma-2-9b-it"
    }
  },
  "agent_config": {
    "tool_details": [...]
  }
}
```

### Example 3: Complex Reasoning (Use GPT-4o-mini)
```json
{
  "agent_input": {
    "input": {
      "messages": "Analyze this code and suggest improvements"
    },
    "metadata": {
      "model_name": "openai/gpt-4o-mini"
    }
  }
}
```

## Available Models

| Model | Provider | Tool Calling | Vision | Cost | Best For |
|-------|----------|--------------|--------|------|----------|
| `custom-vlm` | Local | ❌ | ✅ | FREE | Image analysis |
| `google/gemma-2-9b-it` | OpenRouter | ✅ | ❌ | $0.08/1M | Budget tool calling |
| `google/gemma-2-27b-it` | OpenRouter | ✅ | ❌ | $0.27/1M | Better reasoning |
| `openai/gpt-4o-mini` | OpenRouter | ✅ | ✅ | $0.15/1M | Best balance |
| `openai/gpt-3.5-turbo` | OpenRouter | ✅ | ❌ | $0.50/1M | Reliable & fast |
| `anthropic/claude-3-haiku` | OpenRouter | ✅ | ✅ | $0.25/1M | Fast Claude |
| `anthropic/claude-3-5-sonnet` | OpenRouter | ✅ | ✅ | $3.00/1M | Best reasoning |
| `gpt-3.5-turbo` | OpenAI | ✅ | ❌ | $0.50/1M | Direct OpenAI |
| `gpt-4o-mini` | OpenAI | ✅ | ✅ | $0.15/1M | Direct OpenAI |

## Cost Comparison

**Example: 1000 requests with 500 tokens each**

| Scenario | Model | Cost |
|----------|-------|------|
| Vision only | custom-vlm | **$0.00** |
| Tool calling | google/gemma-2-9b-it | **$0.04** |
| Mixed (vision + tools) | custom-vlm + gemma-2-9b | **$0.02** |
| Premium | gpt-4o-mini | **$0.38** |

## Troubleshooting

### Error: "OPENROUTER_API_KEY not found"
**Solution:** Add the API key to your `.env` file and restart the server.

### Error: "Model returned no response"
**Solution:** Check your API key balance at https://openrouter.ai/credits

### Agent still won't use tools
**Possible causes:**
1. Using `custom-vlm` (doesn't support tools) - Switch to `google/gemma-2-9b-it`
2. Tools not configured in `agent_config.tool_details`
3. Model needs stronger prompting (see below)

### Improve Tool Usage

Add this to your agent's `agent_style`:
```
When the user asks about specific tasks (GitHub, files, weather, etc.), 
you MUST use the available tools. Do not make up information.
Check what tools you have and use them proactively.
```

## Testing MCP Sequential Thinking

Now that you have tool-calling models, test Sequential Thinking:

```python
# Configure your agent with Sequential Thinking MCP
agent_config = {
    "tool_details": [{
        "name": "sequential-thinking",
        "versions": [{
            "released": {
                "port": "8080",  # Your MCP port
                "transport": "sse"
            }
        }]
    }]
}

# Use a tool-capable model
agent_input = {
    "input": {
        "messages": "Do you remember what we talked about earlier?"
    },
    "metadata": {
        "model_name": "google/gemma-2-9b-it"  # NOT custom-vlm!
    },
    "agent_config": agent_config
}
```

## Next Steps

1. ✅ Get OpenRouter API key
2. ✅ Add to `.env`
3. ✅ Test with `google/gemma-2-9b-it`
4. ✅ Monitor costs at https://openrouter.ai/activity
5. ✅ Create agents with different models for different tasks

## FAQ

**Q: Can I still use my custom VLM?**  
A: Yes! It's the default and best for vision tasks.

**Q: Will this break existing agents?**  
A: No. Agents using `custom-vlm` work exactly as before.

**Q: Which model should I use for MCP tools?**  
A: Start with `google/gemma-2-9b-it` (cheap, capable). Upgrade to `openai/gpt-4o-mini` if needed.

**Q: What about Gemma 3?**  
A: When Gemma 3 releases, you can add it via OpenRouter. But current Gemma 2 models already support tool calling at larger sizes (9B, 27B).

**Q: Can I use local Gemma-2-9b instead of OpenRouter?**  
A: Yes, but you'll need ~20GB VRAM and setup is complex. OpenRouter is easier and pay-per-use.
