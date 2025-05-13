"""
Centralized error handling system for the Kafka CLI.
Provides consistent error reporting, logging, and user feedback.
"""
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

import typer
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_rich_traceback

# Install rich traceback handler for better error visualization
install_rich_traceback()

console = Console()

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class ErrorSeverity(Enum):
    """Enum defining the severity levels for errors"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class KafkaCliError(Exception):
    """Base exception class for all Kafka CLI errors"""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        help_text: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.code = code
        self.details = details or {}
        self.help_text = help_text
        self.exit_code = exit_code


class ConfigurationError(KafkaCliError):
    """Error related to configuration handling"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class AuthenticationError(KafkaCliError):
    """Error related to cloud provider authentication"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ValidationError(KafkaCliError):
    """Error related to input validation"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.field = field
        if field:
            self.details["field"] = field


class NetworkError(KafkaCliError):
    """Error related to network operations"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ResourceError(KafkaCliError):
    """Error related to cloud resources"""

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        if resource_type:
            self.details["resource_type"] = resource_type
        if resource_id:
            self.details["resource_id"] = resource_id


class CommandError(KafkaCliError):
    """Error related to command execution"""

    def __init__(self, message: str, command: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        if command:
            self.details["command"] = command


class ErrorHandler:
    """
    Centralized error handler for the application.
    Uses the Observer pattern to allow different parts of the app to subscribe to error events.
    """

    _instance: Optional["ErrorHandler"] = None

    def __new__(cls) -> "ErrorHandler":
        if cls._instance is None:
            cls._instance = super(ErrorHandler, cls).__new__(cls)
            cls._instance._observers: Dict[ErrorSeverity, List[Callable[[KafkaCliError], None]]] = {
                severity: [] for severity in ErrorSeverity
            }
            cls._instance._error_counts: Dict[ErrorSeverity, int] = {severity: 0 for severity in ErrorSeverity}
        return cls._instance

    def register(self, observer: Callable[[KafkaCliError], None], severity: Optional[ErrorSeverity] = None) -> None:
        """Register an observer for error notifications"""
        if severity:
            self._observers[severity].append(observer)
        else:
            # Register for all severities if none specified
            for sev in ErrorSeverity:
                self._observers[sev].append(observer)

    def unregister(self, observer: Callable[[KafkaCliError], None], severity: Optional[ErrorSeverity] = None) -> None:
        """Unregister an observer"""
        if severity:
            if observer in self._observers[severity]:
                self._observers[severity].remove(observer)
        else:
            # Unregister from all severities
            for sev in ErrorSeverity:
                if observer in self._observers[sev]:
                    self._observers[sev].remove(observer)

    def handle(self, error: KafkaCliError) -> None:
        """Handle an error by notifying all registered observers"""
        # Update error counts
        self._error_counts[error.severity] += 1

        # Notify observers
        for observer in self._observers[error.severity]:
            observer(error)

        # Handle based on severity
        if error.severity == ErrorSeverity.INFO:
            self._handle_info(error)
        elif error.severity == ErrorSeverity.WARNING:
            self._handle_warning(error)
        elif error.severity == ErrorSeverity.ERROR:
            self._handle_error(error)
        elif error.severity == ErrorSeverity.CRITICAL:
            self._handle_critical(error)

    def handle_exception(self, exc: Exception) -> None:
        """Handle a general exception by converting it to appropriate KafkaCliError"""
        if isinstance(exc, KafkaCliError):
            self.handle(exc)
        else:
            # Wrap other exceptions in CommandError
            error = CommandError(
                str(exc) or f"An unexpected {exc.__class__.__name__} occurred",
                severity=ErrorSeverity.ERROR,
                details={"exception_type": exc.__class__.__name__},
            )
            self.handle(error)

    def _handle_info(self, error: KafkaCliError) -> None:
        """Handle informational messages"""
        console.print(f"[blue]INFO:[/blue] {error.message}")
        if error.help_text:
            console.print(f"[blue]INFO:[/blue] {error.help_text}")

    def _handle_warning(self, error: KafkaCliError) -> None:
        """Handle warning messages"""
        console.print(f"[yellow]WARNING:[/yellow] {error.message}")
        if error.help_text:
            console.print(f"[yellow]HELP:[/yellow] {error.help_text}")

    def _handle_error(self, error: KafkaCliError) -> None:
        """Handle error messages"""
        console.print(Panel(f"[bold red]ERROR:[/bold red] {error.message}", title="Error", border_style="red"))

        if error.details:
            console.print("[red]Details:[/red]")
            for key, value in error.details.items():
                console.print(f"  [red]{key}:[/red] {value}")

        if error.help_text:
            console.print(f"[green]HELP:[/green] {error.help_text}")

        # Exit if exit code is specified
        if error.exit_code is not None:
            raise typer.Exit(code=error.exit_code)

    def _handle_critical(self, error: KafkaCliError) -> None:
        """Handle critical errors"""
        console.print(
            Panel(
                f"[bold white on red]CRITICAL ERROR:[/bold white on red] {error.message}", title="Critical Error", border_style="red"
            )
        )

        if error.details:
            console.print("[red]Details:[/red]")
            for key, value in error.details.items():
                console.print(f"  [red]{key}:[/red] {value}")

        if error.help_text:
            console.print(f"[green]HELP:[/green] {error.help_text}")

        # Always exit on critical errors
        exit_code = error.exit_code if error.exit_code is not None else 1
        raise typer.Exit(code=exit_code)

    def get_error_counts(self) -> Dict[ErrorSeverity, int]:
        """Get the count of errors by severity"""
        return self._error_counts.copy()


# Decorators for error handling
def error_handler(func: F) -> F:
    """
    Decorator that wraps a function in a try-except block
    and handles exceptions using the ErrorHandler.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[Any]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler().handle_exception(e)
            return None

    return cast(F, wrapper)


def validation_required(*fields: str) -> Callable[[F], F]:
    """
    Decorator that validates the presence of required fields in a dictionary.
    Expects the first argument to be a dictionary.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not args or not isinstance(args[0], dict):
                raise ValidationError(
                    "Validation decorator requires first argument to be a dictionary", severity=ErrorSeverity.ERROR
                )

            data = args[0]
            missing_fields = [field for field in fields if field not in data or data[field] is None]

            if missing_fields:
                raise ValidationError(
                    f"Required fields are missing: {', '.join(missing_fields)}",
                    severity=ErrorSeverity.ERROR,
                    help_text="Please provide values for all required fields and try again.",
                )

            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


# Global functions for error handling
def raise_error(
    message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, error_type: Type[KafkaCliError] = KafkaCliError, **kwargs: Any
) -> None:
    """Raise an error of the specified type and severity"""
    if not issubclass(error_type, KafkaCliError):
        raise TypeError("error_type must be a subclass of KafkaCliError")

    error = error_type(message, severity=severity, **kwargs)
    ErrorHandler().handle(error)


def log_info(message: str, **kwargs: Any) -> None:
    """Log an informational message"""
    raise_error(message, severity=ErrorSeverity.INFO, **kwargs)


def log_warning(message: str, **kwargs: Any) -> None:
    """Log a warning message"""
    raise_error(message, severity=ErrorSeverity.WARNING, **kwargs)


def log_error(message: str, **kwargs: Any) -> None:
    """Log an error message"""
    raise_error(message, severity=ErrorSeverity.ERROR, **kwargs)


def log_critical(message: str, **kwargs: Any) -> None:
    """Log a critical error message"""
    raise_error(message, severity=ErrorSeverity.CRITICAL, **kwargs)
