"""
Interactive prompt handling with Strategy pattern implementation.
Consolidates duplicated input handling code and provides a consistent interface.
"""
import os
import sys
from abc import ABC, abstractmethod
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, cast

import typer
from rich.console import Console

from kafka_cli.core.errors import CommandError

console = Console()

T = TypeVar("T")


def is_interactive() -> bool:
    """
    Check if the current environment is interactive.
    Tests multiple conditions to ensure we don't try to use interactive prompts
    in environments that don't support them.
    """
    # Check if stdin is a TTY device
    if not sys.stdin.isatty():
        return False

    # Check if we're in a test environment or CI pipeline
    if "CI" in os.environ or "PYTEST_CURRENT_TEST" in os.environ:
        return False

    # Check for no-interaction flags
    if "--no-interaction" in sys.argv or "-n" in sys.argv:
        return False

    return True


def check_interactive_or_exit() -> None:
    """Check if environment is interactive, exit with message if not."""
    if not is_interactive():
        console.print("[bold red]Error:[/bold red] This command requires an interactive terminal.")
        console.print("Please run this command in a terminal where you can provide input.")
        console.print("\nFor automation purposes, consider using command-line options instead of the interactive wizard.")
        raise typer.Exit(code=1)


# Strategy pattern for different types of prompts
class PromptStrategy(Generic[T], ABC):
    """Base abstract strategy for interactive prompts"""

    @abstractmethod
    def prompt(self, message: str, **kwargs: Any) -> T:
        """Prompt the user for input using the strategy"""
        pass


class TextPromptStrategy(PromptStrategy[str]):
    """Strategy for text input prompts"""

    def prompt(self, message: str, **kwargs: Any) -> str:
        """Prompt for text input"""
        default: Optional[str] = kwargs.get("default")
        multiline: bool = kwargs.get("multiline", False)

        if not is_interactive():
            if default is not None:
                return default
            raise typer.Exit(code=1)

        try:
            if not multiline:
                # Display the prompt with default value if provided
                if default:
                    prompt = f"{message} [{default}]: "
                else:
                    prompt = f"{message}: "

                console.print(prompt, end="")
                value = input().strip()

                # Use default if no input provided
                if not value and default is not None:
                    return default

                return value
            else:
                # Multiline input mode
                console.print(f"{message} (enter blank line to finish):")
                lines: List[str] = []
                while True:
                    line = input()
                    if not line and not lines:  # First line is empty, use default
                        return default if default is not None else ""
                    if not line:  # Empty line terminates input
                        break
                    lines.append(line)
                return "\n".join(lines)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default is not None:
                return default
            raise typer.Exit(code=1) from e


class SelectPromptStrategy(PromptStrategy[str]):
    """Strategy for selection prompts"""

    def prompt(self, message: str, **kwargs: Any) -> str:
        """Prompt for selection from a list of choices"""
        choices: List[str] = kwargs.get("choices", [])
        default: Optional[str] = kwargs.get("default")
        help_text: Optional[str] = kwargs.get("help_text")

        if not choices:
            raise CommandError("No choices provided for select prompt")

        if not is_interactive():
            if default is not None:
                return default
            if choices:
                return choices[0]
            raise typer.Exit(code=1)

        try:
            # Display the message
            console.print(f"{message}")

            # Display help text if provided
            if help_text:
                console.print(f"[italic]{help_text}[/italic]")

            # Display choices with numbers
            for i, choice in enumerate(choices):
                # Highlight the default choice
                if default and choice == default:
                    console.print(f"  {i+1}. [bold cyan]{choice}[/bold cyan] (default)")
                else:
                    console.print(f"  {i+1}. {choice}")

            # Prompt for selection
            selected: Optional[str] = None
            while selected is None:
                prompt = "Enter number (or press Enter for default): " if default else "Enter number: "
                console.print(prompt, end="")
                value = input().strip()

                # Handle default
                if not value and default:
                    return default

                # Handle numeric selection
                try:
                    selection = int(value)
                    if 1 <= selection <= len(choices):
                        selected = choices[selection - 1]
                    else:
                        console.print("[red]Invalid selection. Please try again.[/red]")
                except ValueError:
                    console.print("[red]Please enter a number.[/red]")

            return selected
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default is not None:
                return default
            if choices:
                return choices[0]
            raise typer.Exit(code=1) from e


class ConfirmPromptStrategy(PromptStrategy[bool]):
    """Strategy for confirmation prompts"""

    def prompt(self, message: str, **kwargs: Any) -> bool:
        """Prompt for confirmation"""
        default: bool = kwargs.get("default", False)

        if not is_interactive():
            return default

        try:
            # Create yes/no prompt with appropriate default
            yes_label = "Y" if default else "y"
            no_label = "n" if default else "N"
            prompt = f"{message} [{yes_label}/{no_label}]: "

            while True:
                console.print(prompt, end="")
                value = input().strip().lower()

                # Handle empty input (use default)
                if not value:
                    return default

                # Handle y/n input
                if value in ["y", "yes"]:
                    return True
                elif value in ["n", "no"]:
                    return False

                console.print("[red]Please enter 'y' or 'n'.[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            return default


class MultiSelectPromptStrategy(PromptStrategy[List[str]]):
    """Strategy for multi-selection prompts"""

    def prompt(self, message: str, **kwargs: Any) -> List[str]:
        """Prompt for multiple selections"""
        choices: List[str] = kwargs.get("choices", [])
        default: List[str] = kwargs.get("default", [])
        min_selections: int = kwargs.get("min_selections", 0)

        if not choices:
            raise CommandError("No choices provided for multiselect prompt")

        if not is_interactive():
            if default:
                return default
            # Return minimum required selections
            if min_selections > 0:
                return choices[:min_selections]
            return []

        try:
            # Display the message
            console.print(f"{message}")
            console.print("(You can select multiple options by entering their numbers separated by spaces)")

            # Display choices with numbers
            for i, choice in enumerate(choices):
                # Mark default choices
                if default and choice in default:
                    console.print(f"  {i+1}. [bold cyan]{choice}[/bold cyan] (selected by default)")
                else:
                    console.print(f"  {i+1}. {choice}")

            valid_selections = False
            selected_items: List[str] = []

            while not valid_selections:
                # Prompt for selection
                console.print("Enter numbers separated by spaces (or press Enter for defaults): ", end="")
                value = input().strip()

                # Handle default
                if not value:
                    selected_items = default if default else []
                else:
                    # Parse input
                    try:
                        selected_indices = [int(x) for x in value.split()]
                        selected_items = []

                        for idx in selected_indices:
                            if 1 <= idx <= len(choices):
                                selected_items.append(choices[idx - 1])
                            else:
                                console.print(f"[red]Invalid selection {idx}. Ignoring.[/red]")
                    except ValueError:
                        console.print("[red]Please enter numbers separated by spaces.[/red]")
                        continue

                # Check minimum selections
                if min_selections > 0 and len(selected_items) < min_selections:
                    console.print(f"[red]You must select at least {min_selections} options.[/red]")
                    continue

                valid_selections = True

            return selected_items
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default:
                return default
            # Return minimum required selections
            if min_selections > 0:
                return choices[:min_selections]
            return []


class NumberPromptStrategy(PromptStrategy[int]):
    """Strategy for numeric input prompts"""

    def prompt(self, message: str, **kwargs: Any) -> int:
        """Prompt for numeric input"""
        default: Optional[int] = kwargs.get("default")
        min_value: Optional[int] = kwargs.get("min_value")
        max_value: Optional[int] = kwargs.get("max_value")

        if not is_interactive():
            if default is not None:
                return default
            if min_value is not None:
                return min_value
            return 0

        try:
            # Build range constraint info
            range_info = ""
            if min_value is not None and max_value is not None:
                range_info = f" ({min_value}-{max_value})"
            elif min_value is not None:
                range_info = f" (min: {min_value})"
            elif max_value is not None:
                range_info = f" (max: {max_value})"

            valid_number = False
            value: Optional[int] = None

            while not valid_number:
                # Display prompt
                if default is not None:
                    prompt = f"{message}{range_info} [{default}]: "
                else:
                    prompt = f"{message}{range_info}: "

                console.print(prompt, end="")
                input_value = input().strip()

                # Handle default
                if not input_value and default is not None:
                    return default

                # Parse and validate input
                try:
                    value = int(input_value)

                    # Validate range
                    if min_value is not None and value < min_value:
                        console.print(f"[red]Value must be at least {min_value}.[/red]")
                        continue

                    if max_value is not None and value > max_value:
                        console.print(f"[red]Value must be at most {max_value}.[/red]")
                        continue

                    valid_number = True

                except ValueError:
                    console.print("[red]Please enter a valid number.[/red]")

            return cast(int, value)  # We know it's not None at this point
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default is not None:
                return default
            if min_value is not None:
                return min_value
            return 0


class PasswordPromptStrategy(PromptStrategy[str]):
    """Strategy for password input prompts"""

    def prompt(self, message: str, **kwargs: Any) -> str:
        """Prompt for password input (masked)"""
        default: Optional[str] = kwargs.get("default")
        confirm: bool = kwargs.get("confirm", False)

        if not is_interactive():
            if default is not None:
                return default
            raise typer.Exit(code=1)

        try:
            # First password attempt
            console.print(f"{message}: ", end="")
            password = getpass("")

            # Use default if no input provided
            if not password and default is not None:
                return default

            # If confirmation is required
            if confirm and password:
                console.print("Confirm password: ", end="")
                confirm_password = getpass("")

                if password != confirm_password:
                    console.print("[red]Passwords don't match. Please try again.[/red]")
                    return self.prompt(message, **kwargs)

            return password
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default is not None:
                return default
            raise typer.Exit(code=1) from e


class PathPromptStrategy(PromptStrategy[str]):
    """Strategy for file/directory path input prompts"""

    def prompt(self, message: str, **kwargs: Any) -> str:
        """Prompt for file or directory path"""
        default: Optional[str] = kwargs.get("default")
        must_exist: bool = kwargs.get("must_exist", False)
        file_okay: bool = kwargs.get("file_okay", True)
        dir_okay: bool = kwargs.get("dir_okay", True)

        if not is_interactive():
            if default is not None:
                return default
            raise typer.Exit(code=1)

        try:
            valid_path = False
            path_value: Optional[str] = None

            while not valid_path:
                # Display prompt
                if default:
                    prompt = f"{message} [{default}]: "
                else:
                    prompt = f"{message}: "

                console.print(prompt, end="")
                input_value = input().strip()

                # Handle default
                if not input_value and default is not None:
                    path_value = default
                else:
                    path_value = input_value

                # Skip validation for empty paths
                if not path_value:
                    if default is not None:
                        return default
                    console.print("[red]Path cannot be empty.[/red]")
                    continue

                # Resolve and validate path
                path_obj = Path(os.path.expanduser(path_value))

                # Check existence if required
                if must_exist and not path_obj.exists():
                    console.print(f"[red]Path does not exist: {path_value}[/red]")
                    continue

                # Check if path is a file
                if path_obj.exists() and path_obj.is_file() and not file_okay:
                    console.print(f"[red]Expected a directory, got a file: {path_value}[/red]")
                    continue

                # Check if path is a directory
                if path_obj.exists() and path_obj.is_dir() and not dir_okay:
                    console.print(f"[red]Expected a file, got a directory: {path_value}[/red]")
                    continue

                valid_path = True

            return cast(str, path_value)  # We know it's not None at this point
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
            if default is not None:
                return default
            raise typer.Exit(code=1) from e


# Prompt factory for creating the appropriate strategy
class PromptFactory:
    """Factory for creating prompt strategies"""

    _strategies: Dict[str, Type[PromptStrategy]] = {
        "text": TextPromptStrategy,
        "select": SelectPromptStrategy,
        "confirm": ConfirmPromptStrategy,
        "multiselect": MultiSelectPromptStrategy,
        "number": NumberPromptStrategy,
        "password": PasswordPromptStrategy,
        "path": PathPromptStrategy,
    }

    @classmethod
    def create_strategy(cls, strategy_type: str) -> PromptStrategy:
        """Create a strategy of the specified type"""
        strategy_class = cls._strategies.get(strategy_type)
        if not strategy_class:
            raise CommandError(f"Unknown prompt strategy type: {strategy_type}")
        return strategy_class()


# Main prompt interface
class Prompt:
    """Unified interface for all prompt types"""

    @staticmethod
    def text(message: str, **kwargs: Any) -> str:
        """Prompt for text input"""
        strategy = PromptFactory.create_strategy("text")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def select(message: str, **kwargs: Any) -> str:
        """Prompt for selection from a list of choices"""
        strategy = PromptFactory.create_strategy("select")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def confirm(message: str, **kwargs: Any) -> bool:
        """Prompt for confirmation"""
        strategy = PromptFactory.create_strategy("confirm")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def multiselect(message: str, **kwargs: Any) -> List[str]:
        """Prompt for multiple selections"""
        strategy = PromptFactory.create_strategy("multiselect")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def number(message: str, **kwargs: Any) -> int:
        """Prompt for numeric input"""
        strategy = PromptFactory.create_strategy("number")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def password(message: str, **kwargs: Any) -> str:
        """Prompt for password input (masked)"""
        strategy = PromptFactory.create_strategy("password")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def path(message: str, **kwargs: Any) -> str:
        """Prompt for file or directory path"""
        strategy = PromptFactory.create_strategy("path")
        return strategy.prompt(message, **kwargs)

    @staticmethod
    def typer_confirm(message: str, default: bool = False, abort: bool = False) -> bool:
        """Compatibility method for typer.confirm replacement"""
        result = Prompt.confirm(message, default=default)
        if abort and not result:
            raise typer.Abort()
        return result
