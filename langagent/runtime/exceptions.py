"""Configuration-specific exceptions for the runtime layer.

Exit codes follow workflow.md specifications:
- 1: Stage capability violation
- 5: Required field missing
- 65: Malformed .env file
- 78: Validation error (type mismatch, placeholder detection, invalid enum)
"""


class RequiredFieldMissingError(Exception):
    """Raised when a required configuration field is missing after priority chain merging.
    
    Exit code: 5
    """
    
    def __init__(self, field: str, message: str = "") -> None:
        self.field = field
        self.exit_code = 5
        full_message = f"Required field missing: {field}"
        if message:
            full_message = f"{full_message} - {message}"
        super().__init__(full_message)


class ConfigPlaceholderError(Exception):
    """Raised when a configuration value contains placeholder text like <your-model-name>.
    
    Exit code: 78
    """
    
    def __init__(self, field: str, value: str) -> None:
        self.field = field
        self.value = value
        self.exit_code = 78
        super().__init__(
            f"Configuration field '{field}' contains placeholder value: {value}. "
            f"Please replace with actual configuration."
        )


class DotenvMalformedError(Exception):
    """Raised when a .env file contains malformed syntax.
    
    Exit code: 65
    """
    
    def __init__(self, file_path: str, message: str = "") -> None:
        self.file_path = file_path
        self.exit_code = 65
        full_message = f"Malformed .env file: {file_path}"
        if message:
            full_message = f"{full_message} - {message}"
        super().__init__(full_message)


class TypeMismatchError(Exception):
    """Raised when a configuration value has incorrect type.
    
    Exit code: 78
    """
    
    def __init__(self, field: str, expected_type: str, actual_value: object) -> None:
        self.field = field
        self.expected_type = expected_type
        self.actual_value = actual_value
        self.exit_code = 78
        super().__init__(
            f"Type mismatch for field '{field}': expected {expected_type}, "
            f"got {type(actual_value).__name__}"
        )
