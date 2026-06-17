class ToolError(Exception):
    """Base exception for tool execution failures."""

    def __init__(self, message: str, tool_name: str = "") -> None:
        self.tool_name = tool_name
        super().__init__(message)


class ToolForbidden(ToolError):
    """Raised when a tool cannot access the requested resource."""


class ToolTimeout(ToolError):
    """Raised when a tool execution exceeds the allowed time limit."""
