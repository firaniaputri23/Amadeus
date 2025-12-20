from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from supabase import Client

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ValidationError, ERROR_RESPONSES
)

# Pydantic models for request and response
class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    company_id: UUID
    created_at: Optional[str] = None

class UserCompanyRole(BaseModel):
    user_id: UUID
    role_id: int

# Constants
SUPER_ADMIN_ROLE_ID = 1
ADMIN_ROLE_ID = 2
ADMIN_ROLES = [SUPER_ADMIN_ROLE_ID, ADMIN_ROLE_ID]

# Create router
router = APIRouter(
    prefix="/companies",
    tags=["companies"],
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# Utility function to check if a user is a super admin in the Predefined company
async def is_predefined_super_admin(user_id: UUID, supabase: Client) -> Tuple[bool, Optional[str]]:
    try:
        # Get the "Predefined" company ID
        predefined_company_response = (
            supabase.table("companies")
            .select("company_id")
            .eq("name", "Predefined")
            .execute()
        )
        
        if not predefined_company_response.data:
            return False, None
        
        predefined_company_id = predefined_company_response.data[0]["company_id"]
        
        # Check if the user is a super admin in the "Predefined" company
        admin_check_response = (
            supabase.table("user_companies")
            .select("role_id")
            .eq("user_id", user_id)
            .eq("company_id", predefined_company_id)
            .eq("role_id", SUPER_ADMIN_ROLE_ID)  # role_id 1 is super admin
            .execute()
        )
        
        return bool(admin_check_response.data), predefined_company_id
    except Exception as e:
        raise InternalServerError(f"Error checking admin status: {str(e)}")

# Utility function to check if a user has admin access to a company
async def has_company_admin_access(user_id: UUID, company_id: UUID, supabase: Client) -> Tuple[bool, Optional[int]]:
    try:
        user_company_response = (
            supabase.table("user_companies")
            .select("role_id")
            .eq("user_id", user_id)
            .eq("company_id", str(company_id))
            .execute()
        )
        
        if not user_company_response.data:
            return False, None
        
        role_id = user_company_response.data[0]["role_id"]
        is_admin = role_id in ADMIN_ROLES
        
        return is_admin, role_id
    except Exception as e:
        raise InternalServerError(f"Error checking company access: {str(e)}")

# CRUD operations
@router.post("/", response_model=CompanyResponse, responses={**ERROR_RESPONSES})
async def create_company(
    company: CompanyCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if the user is a super admin in the Predefined company
        is_admin, _ = await is_predefined_super_admin(user_id, supabase)
        
        if not is_admin:
            raise ForbiddenError(
                "Only super admin users from the Predefined company can create companies",
                additional_info={"required_role": "super admin"}
            )
        
        # Insert company into database
        try:
            company_response = (
                supabase.table("companies")
                .insert({
                    "name": company.name,
                    "description": company.description
                })
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error creating company: {str(e)}")
        
        # Check if insert was successful
        if not company_response.data:
            raise InternalServerError("Failed to create company")
        
        created_company = company_response.data[0]
        
        # Add the creator as a super admin of the company
        # First, get the super admin role_id
        try:
            role_response = (
                supabase.table("roles")
                .select("role_id")
                .eq("role_name", "super admin")
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching admin role: {str(e)}")
        
        if not role_response.data:
            raise NotFoundError("Admin role not found", additional_info={"role_name": "super admin"})
        
        admin_role_id = role_response.data[0]["role_id"]
        
        # Add user-company relationship
        try:
            user_company_response = (
                supabase.table("user_companies")
                .insert({
                    "user_id": user_id,
                    "company_id": created_company["company_id"],
                    "role_id": admin_role_id
                })
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error adding user to company: {str(e)}")
        
        if not user_company_response.data:
            # If adding the relationship fails, delete the company
            try:
                (
                    supabase.table("companies")
                    .delete()
                    .eq("company_id", created_company["company_id"])
                    .execute()
                )
            except Exception:
                pass  # If cleanup fails, continue with the original error
            
            raise InternalServerError("Failed to add user to company")
        
        return created_company
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/", response_model=List[CompanyResponse], responses={**ERROR_RESPONSES})
async def get_companies(
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get all companies the user has access to
        try:
            user_companies_response = (
                supabase.table("user_companies")
                .select("company_id, role_id")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching user companies: {str(e)}")
        
        if not user_companies_response.data:
            return []
        
        # Extract company IDs
        company_ids = [uc["company_id"] for uc in user_companies_response.data]
        
        # Get company details
        try:
            companies_response = (
                supabase.table("companies")
                .select("*")
                .in_("company_id", company_ids)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching companies: {str(e)}")
        
        return companies_response.data
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/{company_id}", response_model=CompanyResponse, responses={**ERROR_RESPONSES})
async def get_company(
    company_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if user has access to the company
        has_access, _ = await has_company_admin_access(user_id, company_id, supabase)
        
        if not has_access:
            # Check if user is a predefined super admin
            is_admin, _ = await is_predefined_super_admin(user_id, supabase)
            if not is_admin:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
        
        # Get company details
        try:
            company_response = (
                supabase.table("companies")
                .select("*")
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching company: {str(e)}")
        
        if not company_response.data:
            raise NotFoundError(
                f"Company with ID '{company_id}' not found",
                additional_info={"company_id": str(company_id)}
            )
        
        # when accessed directly by ID
        return company_response.data[0]
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.put("/{company_id}", response_model=CompanyResponse, responses={**ERROR_RESPONSES})
async def update_company(
    company_id: UUID, 
    company: CompanyCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if user is a super admin in the Predefined company
        is_admin, _ = await is_predefined_super_admin(user_id, supabase)
        
        # If not a predefined super admin, check if user has admin access to the company being updated
        if not is_admin:
            has_access, role_id = await has_company_admin_access(user_id, company_id, supabase)
            
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
                
            # Only super admin (role_id = 1) and admin (role_id = 2) can update
            if role_id not in ADMIN_ROLES:
                raise ForbiddenError(
                    "Only company admins can update company details",
                    additional_info={"required_role": "admin or super admin"}
                )
        
        # Update company
        try:
            response = (
                supabase.table("companies")
                .update({
                    "name": company.name,
                    "description": company.description
                })
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating company: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Company with ID '{company_id}' not found",
                additional_info={"company_id": str(company_id)}
            )
        
        return response.data[0]
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{company_id}", responses={**ERROR_RESPONSES})
async def delete_company(
    company_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if this is the Predefined company
        try:
            company_response = (
                supabase.table("companies")
                .select("name")
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking company: {str(e)}")
        
        # Check if user is a super admin in the Predefined company
        is_admin, predefined_company_id = await is_predefined_super_admin(user_id, supabase)
        
        # If user is not a super admin in Predefined company, they must have admin rights in the target company
        if not is_admin:
            has_access, role_id = await has_company_admin_access(user_id, company_id, supabase)
            
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
                
            # Only super admin (role_id = 1) and admin (role_id = 2) can delete their own company
            if role_id not in ADMIN_ROLES:
                raise ForbiddenError(
                    "Only company admins can delete this company",
                    additional_info={"required_role": "admin or super admin"}
                )
        
        # Special check for Predefined company - it can only be deleted by its own super admin
        if company_response.data and company_response.data[0]["name"] == "Predefined":
            if not is_admin or str(predefined_company_id) != str(company_id):
                raise ForbiddenError(
                    "Only super admin of the Predefined company can delete it",
                    additional_info={"company_name": "Predefined"}
                )
        
        # Check if there are any agents associated with this company
        try:
            agents_response = (
                supabase.table("agents")
                .select("agent_id")
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking associated agents: {str(e)}")
        
        if agents_response.data:
            raise BadRequestError(
                f"Cannot delete company as it has {len(agents_response.data)} associated agents. Delete the agents first.",
                additional_info={"agent_count": len(agents_response.data)}
            )
        
        # Delete all user-company relationships
        try:
            (
                supabase.table("user_companies")
                .delete()
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error removing user relationships: {str(e)}")
        
        # Delete company
        try:
            response = (
                supabase.table("companies")
                .delete()
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error deleting company: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Company with ID '{company_id}' not found",
                additional_info={"company_id": str(company_id)}
            )
        
        return {"message": "Company deleted successfully"}
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

# User management endpoints
@router.get("/{company_id}/users", response_model=List[Dict[str, Any]], responses={**ERROR_RESPONSES})
async def get_company_users(
    company_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if user is a super admin in the Predefined company
        is_admin, _ = await is_predefined_super_admin(user_id, supabase)
        
        # If not a super admin in Predefined company, check if user has access to the requested company
        if not is_admin:
            has_access, _ = await has_company_admin_access(user_id, company_id, supabase)
            
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
        
        # Get all users for this company with their roles
        try:
            user_companies_response = (
                supabase.table("user_companies")
                .select("user_id, role_id")
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching company users: {str(e)}")
        
        if not user_companies_response.data:
            return []
        
        # Get all unique role_ids from the user_companies data
        role_ids = list(set(uc["role_id"] for uc in user_companies_response.data))
        
        # Get all role names at once instead of separate queries for each user
        try:
            roles_response = (
                supabase.table("roles")
                .select("role_id, role_name")
                .in_("role_id", role_ids)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching role information: {str(e)}")
        
        # Create a mapping of role_id to role_name
        role_map = {role["role_id"]: role["role_name"] for role in roles_response.data} if roles_response.data else {}
        
        # Map user data with role information
        result = []
        for uc in user_companies_response.data:
            result.append({
                "user_id": uc["user_id"],
                "role_id": uc["role_id"],
                "role_name": role_map.get(uc["role_id"], "unknown")
            })
        
        return result
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.post("/{company_id}/users", responses={**ERROR_RESPONSES})
async def add_user_to_company(
    company_id: UUID,
    user_company: UserCompanyRole,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if user is a super admin in the Predefined company
        is_admin, _ = await is_predefined_super_admin(user_id, supabase)
        
        # If not a super admin in Predefined company, check if user has admin access to the requested company
        if not is_admin:
            has_access, role_id = await has_company_admin_access(user_id, company_id, supabase)
            
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
            
            # For regular companies, only super admin and admin can add users
            if role_id not in ADMIN_ROLES:
                raise ForbiddenError(
                    "Only company admins can add users",
                    additional_info={"required_role": "admin or super admin"}
                )
        
        # Check if the role exists
        try:
            role_check_response = (
                supabase.table("roles")
                .select("role_id")
                .eq("role_id", user_company.role_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking role: {str(e)}")
        
        if not role_check_response.data:
            raise NotFoundError(
                f"Role with ID '{user_company.role_id}' not found",
                additional_info={"role_id": user_company.role_id}
            )
        
        # Check if the user already has a role in the company
        try:
            existing_role_response = (
                supabase.table("user_companies")
                .select("*")
                .eq("user_id", str(user_company.user_id))
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking existing user role: {str(e)}")
        
        if existing_role_response.data:
            # Update the existing role
            try:
                response = (
                    supabase.table("user_companies")
                    .update({"role_id": user_company.role_id})
                    .eq("user_id", str(user_company.user_id))
                    .eq("company_id", str(company_id))
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error updating user role: {str(e)}")
            
            if not response.data:
                raise InternalServerError("Failed to update user role")
            
            return {"message": "User role updated successfully"}
        else:
            # Add a new user-company relationship
            try:
                response = (
                    supabase.table("user_companies")
                    .insert({
                        "user_id": str(user_company.user_id),
                        "company_id": str(company_id),
                        "role_id": user_company.role_id
                    })
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error adding user to company: {str(e)}")
            
            if not response.data:
                raise InternalServerError("Failed to add user to company")
            
            return {"message": "User added to company successfully"}
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{company_id}/users/{user_id_to_remove}", responses={**ERROR_RESPONSES})
async def remove_user_from_company(
    company_id: UUID,
    user_id_to_remove: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if user is a super admin in the Predefined company
        is_admin, _ = await is_predefined_super_admin(user_id, supabase)
        
        # If not a super admin in Predefined company, check if user has admin access to the requested company
        if not is_admin:
            has_access, role_id = await has_company_admin_access(user_id, company_id, supabase)
            
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(company_id)}
                )
            
            # For other companies, both super admin and admin can remove users
            if role_id not in ADMIN_ROLES:
                raise ForbiddenError(
                    "Only company admins can remove users",
                    additional_info={"required_role": "admin or super admin"}
                )
        
        # Get company info for later checks
        try:
            company_response = (
                supabase.table("companies")
                .select("name")
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching company information: {str(e)}")
        
        # Prevent removing yourself (the last admin)
        if str(user_id_to_remove) == user_id:
            # Get your role in the company
            try:
                your_role_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("company_id", str(company_id))
                    .eq("user_id", user_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking user role: {str(e)}")
            
            if your_role_response.data:
                your_role_id = your_role_response.data[0]["role_id"]
                
                # Check if there are other admins with the same role
                try:
                    other_admins_response = (
                        supabase.table("user_companies")
                        .select("user_id")
                        .eq("company_id", str(company_id))
                        .eq("role_id", your_role_id)
                        .neq("user_id", user_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error checking other admins: {str(e)}")
                
                if not other_admins_response.data:
                    raise BadRequestError(
                        "Cannot remove yourself as you are the last admin of the company",
                        additional_info={"user_id": str(user_id), "company_id": str(company_id)}
                    )
        
        # Delete the user-company relationship
        try:
            response = (
                supabase.table("user_companies")
                .delete()
                .eq("user_id", str(user_id_to_remove))
                .eq("company_id", str(company_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error removing user from company: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"User with ID '{user_id_to_remove}' not found in company",
                additional_info={"user_id": str(user_id_to_remove), "company_id": str(company_id)}
            )
        
        return {"message": "User removed from company successfully"}
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")