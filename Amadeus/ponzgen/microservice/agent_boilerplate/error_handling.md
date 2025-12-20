# Error Handling Guidelines

This document outlines the standardized error handling approach used throughout the application.

## 1. Backend Error Handling

### 1.1 Error Response Format

All API endpoints return errors in a consistent format:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "additional_info": {
            // Context-specific error details as key-value pairs
        }
    }
}
```

### 1.2 Error Classes

The following error classes are available in `microservice/agent_boilerplate/boilerplate/errors.py`:

| Error Class | HTTP Status | Description |
|-------------|-------------|-------------|
| `BadRequestError` | 400 | Invalid request parameters |
| `UnauthorizedError` | 401 | Authentication required |
| `ForbiddenError` | 403 | Permission denied |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflict |
| `ValidationError` | 422 | Input validation failed |
| `InternalServerError` | 500 | Generic server error |
| `ServiceUnavailableError` | 503 | Service temporarily unavailable |

### 1.3 Usage in Route Handlers

Here's an example of how to use the error handling in route handlers:

```python
@router.get("/{item_id}")
async def get_item(item_id: str, request: Request):
    try:
        # Get item from database
        item = await get_item_from_db(item_id)
        
        if not item:
            raise NotFoundError(
                detail=f"Item with ID '{item_id}' not found",
                additional_info={
                    "item_id": item_id
                }
            )
            
        # Check permissions
        if not has_permission(request.user, item):
            raise ForbiddenError(
                detail="You don't have permission to access this item",
                additional_info={
                    "required_role": "admin",
                    "user_role": "user"
                }
            )
            
        return item
        
    except (NotFoundError, ForbiddenError) as e:
        # Let these errors propagate as is
        raise e
    except ValidationError as e:
        # Handle validation errors
        raise e
    except Exception as e:
        # Catch any other exceptions and wrap them
        raise InternalServerError(
            detail="Failed to get item",
            additional_info={
                "error_message": str(e),
                "item_id": item_id
            }
        )
```

## 2. Frontend Error Handling

### 2.1 Error Processing Functions

The frontend includes helpers for handling API errors:

1. `handleApiError`: Parses API error responses in a consistent way
2. `displayErrorMessage`: Displays error messages in the UI
3. `Utils.displayError`: Utility method to display errors in containers
4. `Utils.loadWithErrorHandling`: Helper for loading data with error handling

### 2.2 Usage in JavaScript

```javascript
// Example using error handling functions
async function fetchData() {
    try {
        const response = await API.get('/some-endpoint');
        return response;
    } catch (error) {
        const parsedError = handleApiError(error);
        displayErrorMessage('container-id', parsedError);
        return null;
    }
}

// Example using Utils helper
Utils.loadWithErrorHandling('container-id', 
    async () => {
        return await API.get('/some-endpoint');
    },
    (result) => {
        // Handle successful result
        displayResults(result);
    }
);
```

### 2.3 Error Display

Errors are displayed in a consistent UI format:

- Error title with error code
- Error message
- Detailed information in a collapsible section

## 3. Common Error Scenarios

### 3.1 Input Validation

Use `ValidationError` for invalid input:

```python
if not item_data.get("name"):
    raise ValidationError(
        detail="Missing required field",
        additional_info={
            "field": "name"
        }
    )
```

### 3.2 Authentication Errors

Use `UnauthorizedError` for auth issues:

```python
if not request.state.user_id:
    raise UnauthorizedError(
        detail="Authentication required to access this resource"
    )
```

### 3.3 Permission Errors

Use `ForbiddenError` for permission issues:

```python
if user_role != "admin":
    raise ForbiddenError(
        detail="Administrator access required",
        additional_info={
            "required_role": "admin",
            "current_role": user_role
        }
    )
```

### 3.4 Resource Not Found

Use `NotFoundError` when resources don't exist:

```python
if not agent_response.data:
    raise NotFoundError(
        detail=f"Agent with ID '{agent_id}' not found",
        additional_info={
            "agent_id": agent_id
        }
    )
```

## 4. OpenAPI Documentation

The error responses are documented in OpenAPI (Swagger) for each router:

```python
router = APIRouter(
    prefix="/some-endpoint",
    tags=["some-tag"],
    responses={
        **ERROR_RESPONSES,  # Include all standard error responses
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        # Success response example
                    }
                }
            }
        }
    }
)
```

## 5. Error Handling Best Practices

1. **Be specific**: Use the most specific error class for each situation
2. **Provide context**: Include relevant context in `additional_info`
3. **Propagate known errors**: Don't rewrap known errors like `NotFoundError`
4. **Wrap unknown errors**: Wrap unexpected exceptions in `InternalServerError`
5. **Graceful degradation**: Frontend should handle errors gracefully
6. **Consistent formatting**: Follow the standard error format
7. **User-friendly messages**: Error messages should be clear and helpful
8. **Log errors**: Log all 500-level errors for debugging
9. **Security**: Don't leak sensitive information in error messages
10. **Validation**: Validate inputs before processing

## 6. Error Code Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `BAD_REQUEST` | 400 | Invalid request parameters |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `INTERNAL_SERVER_ERROR` | 500 | Generic server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

You can also use custom error codes by passing the `error_code` parameter to any error class. 