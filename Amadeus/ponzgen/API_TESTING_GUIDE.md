# API Testing Guide

## Current Status

✅ Backend is running on `http://localhost:8080`
✅ Frontend tester is running on `http://localhost:8008`
⚠️ Database setup needed for full functionality

---

## Issue: Foreign Key Constraint Error

When you try to create an agent, you get this error:
```
Key (user_id)=(9489c4d4-b30c-41df-a3d7-0062e2848343) is not present in table "users"
```

**Reason:** The test user from `user_static.json` doesn't exist in your Supabase database yet.

---

## Solution: Create the Test User in Supabase

### Step 1: Go to Supabase Dashboard
1. Visit [https://app.supabase.com](https://app.supabase.com)
2. Select your project: `wxunkovembyfyeocdxnh`
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Run the SQL to Create the User

Copy and paste this SQL query:

```sql
-- Insert the test user into auth.users table
INSERT INTO auth.users (
  id,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at,
  role,
  aud
) VALUES (
  '9489c4d4-b30c-41df-a3d7-0062e2848343',
  'nick@chi.app',
  crypt('password123', gen_salt('bf')),
  NOW(),
  '{"provider":"github","providers":["github","google"]}',
  '{"avatar_url":"https://avatars.githubusercontent.com/u/40026523?v=4","email":"nick@chi.app","full_name":"Nick","name":"Nick","preferred_username":"Nick-CHI","user_name":"Nick-CHI"}',
  NOW(),
  NOW(),
  'authenticated',
  'authenticated'
) ON CONFLICT (id) DO NOTHING;
```

### Step 3: Execute the Query
Click **Run** (or press `Ctrl+Enter`)

---

## Testing the API with curl

### 1. Get All Agents (should return empty array initially)
```bash
curl -X GET http://localhost:8080/agents/ \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
[]
```

### 2. Create an Agent
```bash
curl -X POST http://localhost:8080/agents/ \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "My First Agent",
    "description": "A test agent",
    "agent_style": "default",
    "on_status": true,
    "tools": []
  }'
```

**Expected Response:**
```json
{
  "agent_id": "uuid-here",
  "agent_name": "My First Agent",
  "description": "A test agent",
  "agent_style": "default",
  "on_status": true,
  "tools": [],
  "created_at": "2025-11-23T...",
  "updated_at": "2025-11-23T..."
}
```

### 3. Get All Agents (should now show your created agent)
```bash
curl -X GET http://localhost:8080/agents/ \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

---

## Using the Frontend Tester

1. Open the browser preview at `http://localhost:8008`
2. On the **index.html** page:
   - **JWT Token:** Enter any value (e.g., `test-token`)
   - **API URL:** Change from `http://localhost:8000` to **`http://localhost:8080`**
   - Click **Save**
3. Navigate to **Agents** page
4. You should now be able to create, read, update, and delete agents

---

## Configuration Summary

| Component | URL | Port | Status |
|-----------|-----|------|--------|
| Backend API | http://localhost:8080 | 8080 | ✅ Running |
| Frontend Tester | http://localhost:8008 | 8008 | ✅ Running |
| Supabase | https://wxunkovembyfyeocdxnh.supabase.co | - | ✅ Configured |
| Test User ID | 9489c4d4-b30c-41df-a3d7-0062e2848343 | - | ⚠️ Needs creation |

---

## Troubleshooting

### Error: "Failed to fetch" in browser
- Make sure API URL is set to `http://localhost:8080` (not 8000)
- Make sure JWT token is set to any value (e.g., `test-token`)

### Error: "Foreign key constraint" when creating agent
- The test user doesn't exist in Supabase
- Follow Step 1-3 above to create the user

### Error: "Could not find the table 'public.tools_with_decrypted_keys'"
- You need to create a database view in Supabase
- See SUPABASE_SETUP.md for instructions

---

## Next Steps

1. ✅ Create the test user in Supabase (this guide)
2. ⏳ Create the `tools_with_decrypted_keys` view (see SUPABASE_SETUP.md)
3. ⏳ Test all CRUD operations via curl or frontend
