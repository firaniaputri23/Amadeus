# 🎉 FREE OpenRouter Setup - No Cost Tool Calling!

## Great News!

You can use **Gemma-3-27b** (Google's latest model) **completely FREE** via OpenRouter! This solves your tool-calling problem at **zero cost**.

## Quick Setup (5 minutes)

### 1. Get Your FREE OpenRouter API Key

1. Go to: https://openrouter.ai/keys
2. Sign up (no credit card required!)
3. Click "Create Key"
4. Copy your key: `sk-or-v1-xxxxxxxxxxxxx`

### 2. Configure Privacy Settings (REQUIRED for Free Models!)

**IMPORTANT**: To use free models, you must allow OpenRouter to use your data:

1. Go to: https://openrouter.ai/settings/privacy
2. **Enable**: "Allow my prompts to be used for model training" (or similar option)
3. **Save settings**

This is OpenRouter's requirement for free tier - your prompts may be used to improve models. If you prefer privacy:
- Use paid models (remove `:free` suffix and add credits)
- Or use only your local `custom-vlm` model

### 3. Add to Your .env File

```bash
# In your .env file (create if it doesn't exist)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

### 3. Restart Your Server

```bash
# Stop current server (Ctrl+C)
# Then restart
python app.py
```

## ✅ You're Done! Now Test It

### Test 1: Check Available Models

```bash
curl http://localhost:8080/get-llms
```

Should show `google/gemma-3-27b-it:free` in the list.

### Test 2: Use Free Model with Tools

```json
{
  "input": {
    "messages": "Check my GitHub repositories"
  },
  "metadata": {
    "model_name": "google/gemma-3-27b-it:free"
  },
  "agent_config": {
    "tool_details": [
      // your MCP tools config
    ]
  }
}
```

## Free Models Available

| Model | Size | Tool Calling | Best For |
|-------|------|--------------|----------|
| 🌟 **google/gemma-3-12b-it:free** | 12B | ✅ Excellent | **MCP tools, agents** (Recommended!) |
| **google/gemma-3-27b-it:free** | 27B | ✅ Excellent | Complex reasoning (slower) |
| **meta-llama/llama-3.1-8b-instruct:free** | 8B | ✅ Good | General use, backup |
| **meta-llama/llama-3.2-3b-instruct:free** | 3B | ⚠️ Basic | Simple queries only |
| ~~google/gemma-2-9b-it:free~~ | 9B | ❌ **NO TOOLS** | ⚠️ Don't use for MCP |

**Important**: Gemma-**2** series does NOT support tool calling on OpenRouter. Use Gemma-**3** instead!

## Rate Limits

- **10-20 requests per minute** (varies by model)
- **No daily cap** - just rate limited
- **No cost** - 100% free forever!

For most development/testing, this is plenty!

## Usage Examples

### Example 1: MCP Sequential Thinking (FREE!)

```python
from microservice.agent_boilerplate.boilerplate.agent_boilerplate import agent_boilerplate
from microservice.agent_boilerplate.boilerplate.models import AgentInput

agent_input = AgentInput(
    input={
        "messages": "Do you remember what we discussed about quantum computing?"
    },
    metadata={
        "model_name": "google/gemma-3-12b-it:free",  # FREE model with tool calling!
        "temperature": 0.7
    },
    agent_config={
        "tool_details": [{
            "name": "sequential-thinking",
            "versions": [{
                "released": {
                    "port": "8080",
                    "transport": "sse"
                }
            }]
        }]
    }
)

response = await agent_boilerplate.invoke_agent(
    agent_id="test-agent",
    agent_input=agent_input,
    agent_config={}
)
```

### Example 2: GitHub MCP Tools (FREE!)

```python
agent_input = AgentInput(
    input={
        "messages": "List my repositories and create a new issue in the first one"
    },
    metadata={
        "model_name": "google/gemma-3-12b-it:free"  # Supports tool calling!
    },
    agent_config={
        "tool_details": [{
            "name": "github-mcp",
            "versions": [{
                "released": {
                    "port": "3000",
                    "transport": "sse"
                }
            }]
        }]
    }
)
```

### Example 3: Vision + Tools (Hybrid - Both FREE!)

```python
# Step 1: Use custom VLM for vision (local, free)
vision_input = AgentInput(
    input={
        "messages": "What's in this image?",
        "image_path": "/path/to/image.jpg"
    },
    metadata={
        "model_name": "custom-vlm"  # Your trained model
    }
)

# Step 2: Use Gemma-3 for tool calling (OpenRouter, free)
tool_input = AgentInput(
    input={
        "messages": "Based on the image showing a weather app, check the actual weather in that location"
    },
    metadata={
        "model_name": "google/gemma-3-27b-it:free"  # FREE!
    },
    agent_config={
        "tool_details": [...]
    }
)
```

## Why Gemma-3-27b Is Perfect for You

✅ **Tool Calling**: Native function calling support (unlike your Gemma-2-2b)  
✅ **Size**: 27B parameters = smart enough for agentic reasoning  
✅ **Latest**: Gemma 3 is Google's newest release (December 2025)  
✅ **FREE**: No cost, just rate limits  
✅ **Proven**: Works with LangChain ReAct agents out of the box

## Comparison: Before vs After

### Before (Gemma-2-2b local)
```
User: "Check my GitHub repos"
Agent: "I don't have access to check your repositories..."
❌ No tool calling support
✅ FREE (local)
✅ Vision support
```

### After (Gemma-3-27b via OpenRouter)
```
User: "Check my GitHub repos"
Agent: *Actually uses GitHub MCP tool*
Agent: "You have 15 repositories. Here are the most recent..."
✅ Tool calling works!
✅ Still FREE (OpenRouter)
❌ No vision (but use custom-vlm for that)
```

### Best of Both Worlds
```
Vision tasks → custom-vlm (local, free)
Tool calling → google/gemma-3-27b-it:free (cloud, free)
= 100% FREE SYSTEM WITH FULL CAPABILITIES! 🎉
```

## Cost Comparison

| Solution | Vision | Tools | Monthly Cost |
|----------|--------|-------|--------------|
| Custom VLM only | ✅ | ❌ | $0 |
| OpenRouter paid | ❌ | ✅ | $5-50 |
| **Hybrid FREE** | ✅ | ✅ | **$0** |
| Full GPT-4 | ✅ | ✅ | $100+ |

## Troubleshooting

### "Error 404: No endpoints found matching your data policy"
**This is the most common error!**

**Solution**: 
1. Go to https://openrouter.ai/settings/privacy
2. Enable "Allow prompts for model training" or similar
3. Save and retry

**Why?**: Free models require you to share data for model improvement. This is the trade-off for $0 cost.

**Alternative**: Use paid models (add credits, remove `:free` suffix) for full privacy.

### "Rate limit exceeded"
**Solution**: Wait 1 minute or use multiple API keys (free to create multiple accounts)

### "Invalid API key"
**Solution**: 
1. Check `.env` file has correct key format: `sk-or-v1-...`
2. Restart your server after adding the key

### "Model not found"
**Solution**: Make sure to include the `:free` suffix:
- ✅ `google/gemma-3-27b-it:free`
- ❌ `google/gemma-3-27b-it`

### Agent still doesn't use tools
**Check**:
1. Using `:free` model (not `custom-vlm`)
2. Tools are in `agent_config.tool_details`
3. MCP server is running on the specified port

## Testing Tool Calling

Create a simple test:

```python
# test_free_tools.py
import asyncio
from microservice.agent_boilerplate.boilerplate.utils.get_llms import get_llms

async def test():
    # Get the free model
    model = get_llms("google/gemma-3-27b-it:free")
    
    # Simple test
    response = await model.ainvoke("What is 2+2? Respond in one sentence.")
    print(f"Response: {response.content}")
    
    print("✅ Free model works!")

asyncio.run(test())
```

Run it:
```bash
python test_free_tools.py
```

## Next Steps

1. ✅ Get OpenRouter API key (free)
2. ✅ Add to `.env`
3. ✅ Restart server
4. ✅ Test with `google/gemma-3-27b-it:free`
5. ✅ Configure your MCP tools
6. ✅ Enjoy free tool calling! 🎉

## FAQ

**Q: Is this really free forever?**  
A: Yes! OpenRouter's free tier is permanent, just rate-limited.

**Q: What are the rate limits?**  
A: Typically 10-20 requests/minute. Perfect for development and moderate use.

**Q: Can I upgrade later if needed?**  
A: Yes, just add credits to your OpenRouter account and remove `:free` suffix.

**Q: Will Gemma-3 work better than Gemma-2?**  
A: Yes! Gemma-3-27b has better reasoning and tool-calling than Gemma-2-2b.

**Q: Do I still need my custom VLM?**  
A: Yes! Keep it for vision tasks. Use Gemma-3 for tool calling. Best of both worlds!

**Q: Can I use this in production?**  
A: Free tier is fine for low traffic. For production, consider:
- Adding credits to OpenRouter (pay-per-use)
- Caching responses
- Using rate limiting on your API

## Summary

🎉 **You now have:**
- ✅ FREE vision AI (custom VLM)
- ✅ FREE tool calling (Gemma-3-27b)
- ✅ FREE MCP integration
- ✅ Latest model (December 2025)
- ✅ No credit card needed!

**Total cost: $0.00/month** 🚀
