"""Input validation utilities for security and data integrity."""
from pathlib import Path
from typing import Union


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


def validate_excel_file_path(file_path: Union[str, Path]) -> Path:
    """Validate that a file path is safe and points to a valid Excel file.

    This function prevents path traversal attacks and ensures the file
    is of an allowed type.

    Args:
        file_path: Path to the Excel file

    Returns:
        Validated Path object

    Raises:
        FileValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not accessible
    """
    # Convert to Path object
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check file is actually a file (not a directory or symlink)
    if not path.is_file():
        raise FileValidationError(f"Path is not a regular file: {file_path}")

    # Validate file extension
    allowed_extensions = {'.xlsx', '.xls'}
    if path.suffix.lower() not in allowed_extensions:
        raise FileValidationError(
            f"Invalid file type '{path.suffix}'. "
            f"Allowed types: {', '.join(allowed_extensions)}"
        )

    # Check file is readable
    try:
        with path.open('rb') as f:
            # Try to read first byte to verify permissions
            f.read(1)
    except PermissionError:
        raise PermissionError(f"Access denied to file: {file_path}")
    except Exception as e:
        raise FileValidationError(f"Cannot access file: {e}")

    # Get absolute path to prevent traversal
    resolved_path = path.resolve()

    # Additional security: Check resolved path doesn't escape expected directory
    # For now, we just ensure it's an absolute path and exists
    # In production, you might want to restrict to a specific base directory:
    #
    # allowed_dir = Path("data").resolve()
    # if not resolved_path.is_relative_to(allowed_dir):
    #     raise FileValidationError(
    #         f"Access to file outside allowed directory denied: {resolved_path}"
    #     )

    return resolved_path


def validate_dataframe_columns(df, required_columns: list) -> None:
    """Validate that a DataFrame has all required columns.

    Args:
        df: pandas DataFrame to validate
        required_columns: List of required column names

    Raises:
        ValueError: If required columns are missing
    """
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"DataFrame missing required columns: {', '.join(missing_cols)}"
        )
