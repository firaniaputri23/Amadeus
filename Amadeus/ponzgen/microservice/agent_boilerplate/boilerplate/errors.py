"""
Error Response Module

This module provides standardized error handling for the API routes.

Usage:
    from boilerplate.errors import BadRequestError, NotFoundError

    @router.get("/items/{item_id}", responses={**ERROR_RESPONSES})
    def get_item(item_id: str):
        try:
            item = find_item(item_id)
            if not item:
                raise NotFoundError(f"Item with ID {item_id} not found")
            return item
        except Exception as e:
            # Log the exception
            raise InternalServerError(f"Failed to retrieve item: {str(e)}")
"""

from typing import Optional, Dict, Any, List, Union
from fastapi import HTTPException, status
from pydantic import ValidationError as PydanticValidationError

class APIError(HTTPException):
    """Base class for API errors with standardized error response format."""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code or str(status_code),
                    "message": detail,
                    "additional_info": additional_info or {}
                }
            }
        )

# 4xx Client Errors
class BadRequestError(APIError):
    """400 Bad Request - Client sent an invalid request."""
    def __init__(self, detail: str, error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code or "BAD_REQUEST",
            additional_info=additional_info
        )

class UnauthorizedError(APIError):
    """401 Unauthorized - Authentication is required or has failed."""
    def __init__(self, detail: str = "Authentication required", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code or "UNAUTHORIZED",
            additional_info=additional_info
        )

class ForbiddenError(APIError):
    """403 Forbidden - User does not have permission to access the resource."""
    def __init__(self, detail: str = "Access forbidden", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code or "FORBIDDEN",
            additional_info=additional_info
        )

class NotFoundError(APIError):
    """404 Not Found - Requested resource was not found."""
    def __init__(self, detail: str, error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code or "NOT_FOUND",
            additional_info=additional_info
        )

class ConflictError(APIError):
    """409 Conflict - Request conflicts with current state of the server."""
    def __init__(self, detail: str, error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code or "CONFLICT",
            additional_info=additional_info
        )

class TooManyRequestsError(APIError):
    """429 Too Many Requests - Rate limit exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code=error_code or "TOO_MANY_REQUESTS",
            additional_info=additional_info
        )

class ValidationError(APIError):
    """422 Unprocessable Entity - Request validation failed."""
    def __init__(self, detail: str, error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code or "VALIDATION_ERROR",
            additional_info=additional_info
        )

# 5xx Server Errors
class InternalServerError(APIError):
    """500 Internal Server Error - Generic server error."""
    def __init__(self, detail: str = "Internal server error", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code or "INTERNAL_SERVER_ERROR",
            additional_info=additional_info
        )

class ServiceUnavailableError(APIError):
    """503 Service Unavailable - Server is temporarily unable to handle the request."""
    def __init__(self, detail: str = "Service temporarily unavailable", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code or "SERVICE_UNAVAILABLE",
            additional_info=additional_info
        )

class GatewayTimeoutError(APIError):
    """504 Gateway Timeout - Upstream service did not respond in time."""
    def __init__(self, detail: str = "Gateway timeout", error_code: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=detail,
            error_code=error_code or "GATEWAY_TIMEOUT",
            additional_info=additional_info
        )

def handle_pydantic_validation_error(exc: PydanticValidationError) -> ValidationError:
    """
    Convert a Pydantic ValidationError into our standardized ValidationError format.
    
    Args:
        exc: The original Pydantic validation error
        
    Returns:
        A ValidationError instance with structured error information
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join([str(loc) for loc in error["loc"]]),
            "error": error["msg"]
        })
    
    return ValidationError(
        detail="Invalid input data",
        additional_info={"validation_errors": errors}
    )

# Error Response Examples
ERROR_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Invalid request parameters",
                        "additional_info": {
                            "invalid_fields": ["field1", "field2"]
                        }
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                        "additional_info": {}
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Access forbidden",
                        "additional_info": {
                            "required_role": "admin"
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Resource not found",
                        "additional_info": {
                            "resource_type": "agent",
                            "resource_id": "123"
                        }
                    }
                }
            }
        }
    },
    409: {
        "description": "Conflict",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "CONFLICT",
                        "message": "Resource already exists",
                        "additional_info": {
                            "conflicting_field": "email"
                        }
                    }
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid input data",
                        "additional_info": {
                            "validation_errors": [
                                {
                                    "field": "email",
                                    "error": "Invalid email format"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "TOO_MANY_REQUESTS",
                        "message": "Rate limit exceeded",
                        "additional_info": {
                            "retry_after": 60
                        }
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Internal server error",
                        "additional_info": {
                            "error_id": "abc123"
                        }
                    }
                }
            }
        }
    },
    503: {
        "description": "Service Unavailable",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "Service temporarily unavailable",
                        "additional_info": {
                            "retry_after": 300
                        }
                    }
                }
            }
        }
    },
    504: {
        "description": "Gateway Timeout",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "GATEWAY_TIMEOUT",
                        "message": "Gateway timeout",
                        "additional_info": {
                            "service": "upstream_api"
                        }
                    }
                }
            }
        }
    }
} 