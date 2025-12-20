from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response, RedirectResponse
from supabase import Client
import json

# Define public and protected routes
PUBLIC_ROUTES = ["/", "/public", "/health", "/docs", "/openapi.json", "/mcp-tools/refresh", "/get-llms", "/mcp-logs", "/api/avatars/tools/*", "/api/avatars/agents/*", "/sendgrid/webhook", "/sendgrid/webhook/test", "/sendgrid/webhook/simple", "/sendgrid/outbound"]  # Add any public routes here
PUBLIC_PATH_PREFIXES = [
    "/website",
    "/agent-invoke/shared-agent",
    "/agent-invoke/shared-thread",
    "/view/agent",
    "/view/thread",
    "/sendgrid/emails",  # Add SendGrid email endpoints
]  # Add any path prefixes that should be public

# Middleware for JWT Authentication
class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, supabase_client: Client):
        super().__init__(app)
        self.supabase = supabase_client
        self.processed_users = set()  # Track which users have already been processed

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight requests (OPTIONS) to pass through without authentication
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response
        
        # Check if the path is public
        path = request.url.path
        is_public = path in PUBLIC_ROUTES or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES) or path.endswith(".html")
        
        if not is_public:
            authorization: str = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid token")
            
            jwt_token = authorization.replace("Bearer ", "")

            try: 
                flag_bypass = True
                if flag_bypass:
                    # Load JSON from a file
                    with open("./others/user_jwt/user_static.json", "r") as file:
                        response = json.load(file)
                        print(response)
                else:
                    # Fetch user from Supabase
                    print(jwt_token)
                    response = self.supabase.auth.get_user(jwt_token)
                    response = response.dict()
                
                
                request.state.user = response["user"]
                request.state.user_id = response["user"]["id"]
                
                # Only run once per user
                if request.state.user_id not in self.processed_users:
                    await self._ensure_user_in_predefined_company(request.state.user_id)
                    self.processed_users.add(request.state.user_id)
                
                company_id = None
                path_parts = request.url.path.split('/')
                for i, part in enumerate(path_parts):
                    if part == "companies" and i + 1 < len(path_parts):
                        company_id = path_parts[i + 1]
                        break
                
                # If not found in path, check query parameters
                if not company_id:
                    query_params = dict(request.query_params)
                    company_id = query_params.get("company_id")
                
                # If company_id is provided, verify user's access to the company
                if company_id:
                    request.state.company_id = company_id
                    user_company_response = (
                        self.supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", request.state.user_id)
                        .eq("company_id", company_id)
                        .execute()
                    )
                    
                    if not user_company_response.data:
                        raise HTTPException(status_code=403, detail="You don't have access to this company")
                    
                    # Store the user's role for this company
                    request.state.role_id = user_company_response.data[0]["role_id"]
                    # Get the role name
                    role_response = (
                        self.supabase.table("roles")
                        .select("role_name")
                        .eq("role_id", request.state.role_id)
                        .execute()
                    )
                    
                    if role_response.data:
                        request.state.role_name = role_response.data[0]["role_name"]
                    else:
                        request.state.role_name = "unknown"
                else:
                    # No company_id provided, user is accessing personal resources
                    request.state.company_id = None
                    request.state.role_id = None
                    request.state.role_name = None
                    
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
        
        response = await call_next(request)
        
        # True If For Deployment; When working in local, set to False
        deployement = False
        
        if deployement:
            
            # Get the original location header and replace http:// with https://
            if "location" in response.headers:
                response.headers["Location"] = response.headers.get("location").replace("http://", "https://")
            
        
        if response.status_code in [301, 302]:  
            new_location = response.headers.get("location")
            if new_location:
                return RedirectResponse(url=new_location, status_code=307)  

        return response
        
    async def _ensure_user_in_predefined_company(self, user_id):
        """
        Check if user is already a member of the "Predefined" company.
        If not, add them to it.
        """
        try:
            print(f"Ensuring user {user_id} is in Predefined company")
            
            
            predefined_company_response = (
                self.supabase.table("companies")
                .select("company_id")
                .eq("name", "Predefined")
                .execute()
            )
            
            # If Predefined company doesn't exist, create it
            if not predefined_company_response.data:
                print("Creating Predefined company as it doesn't exist")
                predefined_company_response = (
                    self.supabase.table("companies")
                    .insert({
                        "name": "Predefined",
                        "description": "Template company - not displayed in company listings"
                    })
                    .execute()
                )
                
                if not predefined_company_response.data:
                    print("Failed to create Predefined company")
                    return
                print(f"Created Predefined company with ID: {predefined_company_response.data[0]['company_id']}")
            
            predefined_company_id = predefined_company_response.data[0]["company_id"]
            print(f"Found Predefined company with ID: {predefined_company_id}")
            
            # Check if user is already a member
            user_company_response = (
                self.supabase.table("user_companies")
                .select("*")
                .eq("user_id", user_id)
                .eq("company_id", predefined_company_id)
                .execute()
            )
            
            if not user_company_response.data:
                print(f"User {user_id} not found in Predefined company, adding now")
                # Add user to the company with a standard user role
                # First, get the user role_id
                role_response = (
                    self.supabase.table("roles")
                    .select("role_id")
                    .eq("role_name", "guest")
                    .execute()
                )
                
                if role_response.data:
                    user_role_id = role_response.data[0]["role_id"]
                    print(f"Found user role with ID: {user_role_id}")
                    
                    # Add user to the Predefined company
                    result = self.supabase.table("user_companies").insert({
                        "user_id": user_id,
                        "company_id": predefined_company_id,
                        "role_id": user_role_id
                    }).execute()
                    
                    print(f"Added user {user_id} to Predefined company {predefined_company_id}, result: {result.data}")
                else:
                    print("User role not found, cannot add user to Predefined company")
            else:
                print(f"User {user_id} is already in the Predefined company")
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Error in _ensure_user_in_predefined_company: {str(e)}")
