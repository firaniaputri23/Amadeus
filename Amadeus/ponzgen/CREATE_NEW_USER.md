# Create New Test User: kachponz@gmail.com

## Step 1: Go to Supabase Dashboard
1. Visit [https://app.supabase.com](https://app.supabase.com)
2. Select your project: `wxunkovembyfyeocdxnh`
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**

## Step 2: Run the SQL to Create the New User

Copy and paste this SQL query:

```sql
-- Insert a new test user with kachponz@gmail.com
-- This will generate a new UUID automatically
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
  gen_random_uuid(),
  'kachponz@gmail.com',
  crypt('password123', gen_salt('bf')),
  NOW(),
  '{"provider":"github","providers":["github","google"]}',
  '{"avatar_url":"https://avatars.githubusercontent.com/u/kachponz","email":"kachponz@gmail.com","full_name":"Kachponz","name":"Kachponz","preferred_username":"kachponz","user_name":"kachponz"}',
  NOW(),
  NOW(),
  'authenticated',
  'authenticated'
)
RETURNING id, email;
```

## Step 3: Execute the Query
Click **Run** (or press `Ctrl+Enter`)

## Step 4: Copy the User ID
The query will return something like:
```
id                                    | email
--------------------------------------|--------------------
550e8400-e29b-41d4-a716-446655440000 | kachponz@gmail.com
```

Copy the UUID (the long ID in the first column).

## Step 5: Update user_static.json

Now update the `user_static.json` file with the new user ID:

1. Open `/home/ubuntu/skripsi/indonesia/astroid-swarm-vanilla/ponzgen/others/user_jwt/user_static.json`
2. Replace the old user ID `9489c4d4-b30c-41df-a3d7-0062e2848343` with your new UUID
3. Update the email from `nick@chi.app` to `kachponz@gmail.com`
4. Update the name fields from `Nick` to `Kachponz`
5. Save the file

### Example changes:
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",  // <- NEW UUID
    "email": "kachponz@gmail.com",  // <- NEW EMAIL
    "user_metadata": {
      "email": "kachponz@gmail.com",  // <- NEW EMAIL
      "full_name": "Kachponz",  // <- NEW NAME
      "name": "Kachponz",  // <- NEW NAME
      "preferred_username": "kachponz",  // <- NEW USERNAME
      "user_name": "kachponz"  // <- NEW USERNAME
    }
    // ... rest of the file
  }
}
```

## Step 6: Restart Your Backend
```bash
# Stop the current backend (Ctrl+C)
# Then restart it
python app.py
```

## Step 7: Test the API
```bash
curl -X GET http://localhost:8080/agents/ \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

You should now be able to create agents with the new user!
