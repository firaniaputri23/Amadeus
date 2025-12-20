# Development Guidelines for Swarm AI Boilerplate Agent

This document outlines the development guidelines and best practices for contributing to the Combined Agent API with Microservices Architecture project.

## Table of Contents

1. [Architectural Principles](#architectural-principles)
2. [Code Structure](#code-structure)
3. [Coding Standards](#coding-standards)
4. [API Design](#api-design)
5. [Testing](#testing)
6. [Environment Management](#environment-management)
7. [Documentation](#documentation)
8. [Microservice Development](#microservice-development)
9. [Git Workflow](#git-workflow)
10. [Pre-Commit Guidelines](#pre-commit-guidelines)
11. [Deployment](#deployment)

## Architectural Principles

- **Microservice Independence**: Each microservice should be self-contained with its own routes, utilities, and business logic.
- **Separation of Concerns**: Keep different functionalities separated into appropriate microservices.
- **Single Responsibility**: Each module, class, or function should have a single, well-defined responsibility.
- **DRY (Don't Repeat Yourself)**: Avoid code duplication across microservices; create shared libraries when needed.
- **Loose Coupling**: Minimize dependencies between microservices to ensure they can evolve independently.
- **Clean Interfaces**: Define clear interfaces between components and microservices.
- **Statelessness**: Design services to be stateless where possible for better scalability.

## Code Structure

- Organize code in a logical directory structure following the established pattern:
  ```
  microservice/
  ├── service_name/
  │   ├── routes/           # API routes for the service
  │   ├── utils/            # Utility functions
  │   ├── models.py         # Data models
  │   ├── README.md         # Service documentation
  │   └── __init__.py
  ```
- Place shared code in appropriate utility modules to avoid duplication.
- Prefer composition over inheritance when designing class hierarchies.

## Coding Standards

- Follow PEP 8 style guidelines for Python code.
- Use meaningful variable and function names that clearly indicate their purpose.
- Include type hints for function parameters and return values.
- Write docstrings for all modules, classes, and functions using the Google docstring format:
  ```python
  def function_name(param1: str, param2: int) -> bool:
      """Short description of function.
      
      More detailed description if needed.
      
      Args:
          param1: Description of param1
          param2: Description of param2
          
      Returns:
          Description of return value
          
      Raises:
          ExceptionType: Description of when this exception is raised
      """
  ``` 

- Use proper error handling from `microservice\agent_boilerplate\boilerplate\errors.py`
- Avoid global variables and state where possible.
- Use environment variables for configuration rather than hard-coded values.

## API Design

- Follow RESTful principles for API endpoints.
- Use appropriate HTTP methods (GET, POST, PUT, DELETE) for their intended purposes.
- Return consistent JSON response formats with status codes:
  ```json
  {
    "success": true,
    "data": {}, 
    "message": "Optional message"
  }
  ```
- Include validation for all API inputs.
- Version APIs appropriately when making breaking changes.
- Document all API endpoints with:
  - Expected input parameters
  - Response format
  - Possible error codes
  - Authentication requirements

## Testing

- Write unit tests for all new functions and methods.
- Include integration tests for API endpoints.
- Mock external dependencies in tests.
- Test for both success and failure cases.
- Run tests before submitting pull requests.
- Maintain at least 80% code coverage.

## Environment Management

- Always use environment variables for configuration settings.
- Never commit sensitive information (API keys, credentials) to the repository.
- Include a sample `.env.example` file with required environment variables.
- Provide clear documentation for all required environment variables.
- Support different environments (development, testing, production) with appropriate configurations.

## Documentation

- Maintain up-to-date documentation for all microservices in their respective README.md files.
- Document all API endpoints and their usage.
- Include setup instructions and prerequisites in the main README.md.
- Add comments for complex logic, but prioritize making the code self-documenting.
- Document known limitations and constraints.

## Microservice Development

### Adding a New Microservice

1. Create a new directory under `microservice/` with an appropriate name.
2. Create a `routes/` directory for API routes.
3. Create necessary utility modules and models.
4. Include the service's routes in the main `app.py` file.
5. Add comprehensive documentation in a README.md file.

### Modifying Existing Microservices

- Respect the existing architecture and patterns.
- Make changes that are backward compatible when possible.
- Update tests and documentation to reflect changes.
- Consider the impact on other microservices before making changes.

## Git Workflow

- Use feature branches for all new development.
- Branch naming convention: `feature/feature-name`, `bugfix/issue-name`, `hotfix/urgent-fix`.
- Write clear, descriptive commit messages explaining the purpose of the change.
- Keep commits focused on a single logical change.
- Create pull requests for review before merging to the main branch.
- Ensure all tests pass before submitting a pull request.
- Address code review comments promptly.

## Pre-Commit Guidelines

Before committing your code, ensure the following:

1. **Code Review**: Run a self-review of your code against this document's guidelines.
2. **LLM Review**: Utilize an LLM (e.g., Claude, GPT) to review your changes and verify compliance with these guidelines:
   ```
   Please review my code changes and check if they follow these guidelines:
   1. Adherence to architectural principles (separation of concerns, single responsibility)
   2. Proper documentation (docstrings, comments, README updates)
   3. Code structure and organization
   4. Proper error handling
   5. API design best practices
   6. No duplication of existing code
   7. Add new item in Document Version History
   8. Make sure the development value is ALWAYS set to `True` in `auth_middleware.py`
   9. Update the version on the ## Document Version History in this md file
   ```

3. **Diff Review**: Check your git diff to ensure no sensitive information, debug code, or unneeded comments are included.
4. **Documentation Updates**: Verify that all relevant documentation is updated to reflect your changes.


## Deployment

- Make sure the development value is set to `True` in `auth_middleware.py` for development environments.
- Test all changes in a staging environment before deploying to production.
- Use Docker containers for consistent deployment across environments.
- Automate deployment processes where possible.
- Document deployment procedures for each microservice.
- Include rollback procedures in case of deployment failures.

## Best Practices

- Avoid duplicating code; look for existing implementations first.
- Consider different environments (dev, test, prod) when making changes.
- Only make requested changes or changes you fully understand.
- Keep clean separation between microservices.
- Avoid writing single-use scripts directly in the codebase.
- Never mock data in production code; only use mocking for tests.
- Always validate and sanitize user inputs.
- Handle errors gracefully with appropriate error messages.
- Log important events and errors for debugging purposes.
- Consider performance implications of changes, especially for API endpoints. 

## Document Version History

| Version | Date       | Author      | Description |
|---------|------------|-------------|-------------|
| 1.0.0   | 2024-05-02 | Initial Team | Initial version of development guidelines |# astroid-swarm-vanilla
