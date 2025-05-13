"""
Command pattern implementation for the CLI interface.
Provides a standard structure for all commands and reduces duplication.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, cast

import typer
from rich.console import Console

from kafka_cli.core.config_manager import ConfigManager
from kafka_cli.core.errors import CommandError, ErrorHandler

console = Console()
T = TypeVar("T")


class Command(ABC):
    """Base Command interface"""

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the command with the given arguments"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Get the name of the command"""
        pass

    @abstractmethod
    def description(self) -> str:
        """Get the description of the command"""
        pass


class ProfileAwareCommand(Command, ABC):
    """Base class for commands that need access to profile configuration"""

    def __init__(self) -> None:
        self.config_manager = ConfigManager()

    def get_profile(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """Get the profile configuration"""
        profile_data = self.config_manager.load_profile(profile_name)
        if profile_data is None:
            return {}
        return profile_data

    def save_profile(self, profile_data: Dict[str, Any], profile_name: Optional[str] = None) -> bool:
        """Save the profile configuration"""
        return self.config_manager.save_profile(profile_data, profile_name)

    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        return self.config_manager.list_profiles()


class CommandGroup:
    """Group of related commands"""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.commands: Dict[str, Command] = {}

    def add_command(self, command: Command) -> "CommandGroup":
        """Add a command to the group"""
        self.commands[command.name()] = command
        return self

    def register_with_typer(self, app: typer.Typer) -> None:
        """Register all commands with a Typer app"""
        for cmd_name, command in self.commands.items():
            # Create a wrapper function to execute the command
            def create_command_wrapper(cmd: Command) -> Callable[..., Any]:
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    try:
                        result = cmd.execute(*args, **kwargs)
                        return result
                    except Exception as e:
                        ErrorHandler().handle_exception(e)
                        raise typer.Exit(code=1) from e

                # Set the name and help text to match the command
                wrapper.__name__ = cmd.name()
                wrapper.__doc__ = cmd.description()
                return wrapper

            # Register the wrapper with Typer
            app.command(cmd_name)(create_command_wrapper(command))


class CommandResult(Generic[T]):
    """Encapsulates the result of a command execution"""

    def __init__(self, success: bool, value: Optional[T] = None, error: Optional[str] = None) -> None:
        self.success = success
        self.value = value
        self.error = error

    @staticmethod
    def ok(value: Optional[T] = None) -> "CommandResult[T]":
        """Create a successful result"""
        return CommandResult(True, value)

    @staticmethod
    def error(error_message: str) -> "CommandResult[T]":
        """Create an error result"""
        return CommandResult(False, error=error_message)

    def on_success(self, callback: Callable[[T], None]) -> "CommandResult[T]":
        """Execute callback if the result is successful"""
        if self.success and self.value is not None:
            callback(self.value)
        return self

    def on_error(self, callback: Callable[[str], None]) -> "CommandResult[T]":
        """Execute callback if the result is an error"""
        if not self.success and self.error is not None:
            callback(self.error)
        return self

    def unwrap(self) -> T:
        """Get the value or raise an exception if it's an error"""
        if not self.success:
            raise CommandError(self.error or "Unknown error")
        if self.value is None:
            raise CommandError("Result value is None")
        return cast(T, self.value)

    def unwrap_or(self, default: T) -> T:
        """Get the value or return the default if it's an error"""
        if not self.success or self.value is None:
            return default
        return cast(T, self.value)

    def map(self, func: Callable[[T], Any]) -> "CommandResult[Any]":
        """Apply a function to the value if successful"""
        if self.success and self.value is not None:
            try:
                return CommandResult.ok(func(self.value))
            except Exception as e:
                return CommandResult.error(str(e))
        return CommandResult(self.success, error=self.error)


# Factory for creating commands
class CommandFactory:
    """Factory for creating command instances"""

    _commands: Dict[str, type] = {}

    @classmethod
    def register(cls, command_type: str) -> Callable[[type], type]:
        """Decorator to register a command class"""

        def wrapper(command_class: type) -> type:
            cls._commands[command_type] = command_class
            return command_class

        return wrapper

    @classmethod
    def create(cls, command_type: str, *args: Any, **kwargs: Any) -> Command:
        """Create a command of the specified type"""
        if command_type not in cls._commands:
            raise ValueError(f"No command registered with type: {command_type}")

        try:
            command_class = cls._commands[command_type]
            return command_class(*args, **kwargs)
        except Exception as e:
            ErrorHandler().handle_exception(e)
            raise ValueError(f"Failed to create command of type {command_type}: {str(e)}") from e
