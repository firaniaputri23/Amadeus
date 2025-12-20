# Feature Sharing Microservice

This microservice provides endpoints for sharing agents and threads with other users.

## Overview

The Feature Sharing microservice allows users to:

1. Share agents with specific users as visitors (read-only access)
2. Share agents with specific users as editors (read-write access)
3. Generate public links for agents that can be accessed by anyone
4. Remove sharing settings from agents

5. Share threads with specific users as visitors (read-only access)
6. Share threads with specific users as editors (read-write access)
7. Generate public links for threads that can be accessed by anyone
8. Remove sharing settings from threads

## Endpoints

### Agent Sharing Endpoints

- `POST /feature-sharing/agent/share-editor-with/{agent_id}/`: Share an agent with specific users as editors
- `POST /feature-sharing/agent/share-visitor-with/{agent_id}/`: Share an agent with specific users as visitors
- `POST /feature-sharing/agent/share-anyone-with-link/{agent_id}/`: Generate a public link for an agent

### Thread Sharing Endpoints

- `POST /feature-sharing/thread/share-editor-with/{agent_id}/{thread_id}`: Share a thread with specific users as editors
- `POST /feature-sharing/thread/share-visitor-with/{agent_id}/{thread_id}`: Share a thread with specific users as visitors
- `POST /feature-sharing/thread/share-anyone-with-link/{agent_id}/{thread_id}`: Generate a public link for a thread

## Data Structure

### Agent Sharing

Agents have the following sharing-related fields:

```json
{
  "share_visitor_with": ["person1@gmail.com"],
  "share_editor_with": ["person2@gmail.com"],
  "public_hash": "061d0a94b6488dab",
  "is_public": true
}
```

### Thread Sharing

Threads (agent_logs) have the following sharing-related fields in their chat_history:

```json
{
  "chat_history": {
    "messages": [...],
    "share_info": {
      "share_visitor_with": ["person1@gmail.com"],
      "share_editor_with": ["person2@gmail.com"],
      "public_hash": "061d0a94b6488dab",
      "is_public": true
    }
  },
  "is_public": true,
  "public_hash": "061d0a94b6488dab"
}
```

## Authentication

All endpoints require JWT authentication, except for the following public endpoints:

### Public Endpoints for Accessing Shared Content:
- `GET /agent-invoke/shared-agent/{agent_hash}`: Get a shared agent by its public hash
- `GET /agent-invoke/shared-thread/{thread_hash}`: Get a shared thread by its public hash

### Public Endpoints for Generating Sharing Links:
- `POST /feature-sharing/agent/share-anyone-with-link/{agent_id}/`: Generate a public link for an agent
- `POST /feature-sharing/thread/share-anyone-with-link/{agent_id}/{thread_id}`: Generate a public link for a thread

## Permissions

- Only the owner of an agent or thread can share it
- Users who belong to the same company as the agent or thread owner can also share it
- Users who have editor access to an agent can share threads created with that agent