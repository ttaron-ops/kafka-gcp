import sys
import os
import typer
from rich.console import Console
from getpass import getpass
from pathlib import Path

console = Console()

def is_interactive():
    """
    Check if the current environment is interactive.
    Tests multiple conditions to ensure we don't try to use interactive prompts
    in environments that don't support them.
    """
    # Check if stdin is a TTY device
    if not sys.stdin.isatty():
        return False
    
    # Check if we're in a test environment or CI pipeline
    if 'CI' in os.environ or 'PYTEST_CURRENT_TEST' in os.environ:
        return False
    
    # Check for no-interaction flags
    if '--no-interaction' in sys.argv or '-n' in sys.argv:
        return False
    
    return True

def non_interactive_fallback():
    """Display warning about non-interactive environment and exit."""
    console.print("[bold red]Error:[/bold red] This command requires an interactive terminal.")
    console.print("Please run this command in a terminal where you can provide input.")
    console.print("\nFor automation purposes, consider using command-line options instead of the interactive wizard.")
    raise typer.Exit(code=1)

def safe_text(message, default=None, multiline=False, **kwargs):
    """
    Safely prompt for text input using basic input(), without questionary.
    
    Args:
        message: Message to display to the user
        default: Default value if user doesn't provide input
        multiline: Whether to support multiline input (terminated by empty line)
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Display the prompt with default value if provided
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "
        
        if not multiline:
            console.print(prompt, end="")
            value = input().strip()
            
            # Use default if no input provided
            if not value and default is not None:
                return default
            
            return value
        else:
            # Multiline input mode
            console.print(f"{message} (enter blank line to finish):")
            lines = []
            while True:
                line = input()
                if not line and not lines:  # First line is empty, use default
                    return default if default is not None else ""
                if not line:  # Empty line terminates input
                    break
                lines.append(line)
            return "\n".join(lines)
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_select(message, choices, default=None, help_text=None, **kwargs):
    """
    Safely prompt for selection using basic input(), without questionary.
    
    Args:
        message: Message to display to the user
        choices: List of choices to select from
        default: Default choice if user doesn't select anything
        help_text: Optional help text to display before choices
    """
    if not is_interactive():
        non_interactive_fallback()
    
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
        selected = None
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
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_confirm(message, default=False, **kwargs):
    """
    Safely prompt for confirmation using basic input(), without questionary.
    """
    if not is_interactive():
        non_interactive_fallback()
    
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
            if value in ['y', 'yes']:
                return True
            elif value in ['n', 'no']:
                return False
            
            console.print("[red]Please enter 'y' or 'n'.[/red]")
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_checkbox(message, choices, default=None, **kwargs):
    """
    Safely prompt for multiple selections using basic input(), without questionary.
    """
    if not is_interactive():
        non_interactive_fallback()
    
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
        
        # Prompt for selection
        console.print("Enter numbers separated by spaces (or press Enter for defaults): ", end="")
        value = input().strip()
        
        # Handle default
        if not value and default:
            return default
        if not value and not default:
            return []
        
        # Handle numeric selections
        selected = []
        try:
            for num in value.split():
                selection = int(num)
                if 1 <= selection <= len(choices):
                    selected.append(choices[selection - 1])
            return selected
        except ValueError:
            console.print("[red]Invalid input. Using default selection.[/red]")
            return default if default else []
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_multiselect(message, choices, default=None, min_selections=0, **kwargs):
    """
    Enhanced version of safe_checkbox with better handling of defaults and minimum selections.
    
    Args:
        message: Message to display to the user
        choices: List of choices to select from
        default: Default selections if user doesn't select anything
        min_selections: Minimum number of selections required
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Display the message
        console.print(f"{message}")
        console.print("(Select multiple options by entering their numbers separated by spaces)")
        
        # Display choices with numbers
        for i, choice in enumerate(choices):
            # Mark default choices
            if default and choice in default:
                console.print(f"  {i+1}. [bold cyan]{choice}[/bold cyan] (selected by default)")
            else:
                console.print(f"  {i+1}. {choice}")
        
        # Keep prompting until we get valid input
        while True:
            # Prompt for selection
            if default:
                console.print("Enter numbers separated by spaces (or press Enter for defaults): ", end="")
            else:
                console.print("Enter numbers separated by spaces: ", end="")
                
            value = input().strip()
            
            # Handle default
            if not value and default:
                if len(default) >= min_selections:
                    return default
                else:
                    console.print(f"[red]Please select at least {min_selections} options.[/red]")
                    continue
            
            # Handle numeric selections
            selected = []
            try:
                if value:
                    for num in value.split():
                        selection = int(num)
                        if 1 <= selection <= len(choices):
                            selected.append(choices[selection - 1])
                
                # Check minimum selections
                if len(selected) < min_selections:
                    console.print(f"[red]Please select at least {min_selections} options.[/red]")
                    continue
                    
                return selected
            except ValueError:
                console.print("[red]Invalid input. Please enter numbers separated by spaces.[/red]")
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_number(message, min_value=None, max_value=None, default=None, **kwargs):
    """
    Safely prompt for numeric input with validation.
    
    Args:
        message: Message to display to the user
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if user doesn't provide input
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Build constraints text
        constraints = []
        if min_value is not None:
            constraints.append(f"min: {min_value}")
        if max_value is not None:
            constraints.append(f"max: {max_value}")
        
        constraints_text = f" ({', '.join(constraints)})" if constraints else ""
        
        # Display the prompt with default value if provided
        if default is not None:
            prompt = f"{message}{constraints_text} [{default}]: "
        else:
            prompt = f"{message}{constraints_text}: "
        
        while True:
            console.print(prompt, end="")
            value = input().strip()
            
            # Use default if no input provided
            if not value and default is not None:
                return default
            
            # Validate input
            try:
                num_value = int(value)
                
                # Check constraints
                if min_value is not None and num_value < min_value:
                    console.print(f"[red]Value must be at least {min_value}.[/red]")
                    continue
                    
                if max_value is not None and num_value > max_value:
                    console.print(f"[red]Value must be at most {max_value}.[/red]")
                    continue
                
                return num_value
            except ValueError:
                console.print("[red]Please enter a valid number.[/red]")
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_password(message, default=None, confirm=False, **kwargs):
    """
    Safely prompt for password input (masked).
    
    Args:
        message: Message to display to the user
        default: Default value if user doesn't provide input
        confirm: Whether to ask for confirmation
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Display the prompt
        console.print(f"{message}", end="")
        
        # Handle password input
        value = getpass("")
        
        # Use default if no input provided
        if not value and default is not None:
            return default
        
        # Handle confirmation if requested
        if confirm and value:
            console.print("Confirm password: ", end="")
            confirm_value = getpass("")
            
            if value != confirm_value:
                console.print("[red]Passwords do not match. Please try again.[/red]")
                return safe_password(message, default, confirm)
        
        return value
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_path(message, default=None, must_exist=False, file_okay=True, dir_okay=True, **kwargs):
    """
    Safely prompt for file or directory path with validation.
    
    Args:
        message: Message to display to the user
        default: Default value if user doesn't provide input
        must_exist: Whether the path must exist
        file_okay: Whether files are acceptable
        dir_okay: Whether directories are acceptable
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Build type text
        type_text = []
        if file_okay:
            type_text.append("file")
        if dir_okay:
            type_text.append("directory")
        
        type_str = f" ({' or '.join(type_text)})"
        
        # Display the prompt with default value if provided
        if default is not None:
            prompt = f"{message}{type_str} [{default}]: "
        else:
            prompt = f"{message}{type_str}: "
        
        while True:
            console.print(prompt, end="")
            value = input().strip()
            
            # Use default if no input provided
            if not value and default is not None:
                value = default
            
            # Validate path
            path = Path(value).expanduser()
            
            if must_exist and not path.exists():
                console.print(f"[red]Path '{value}' does not exist.[/red]")
                continue
                
            if not dir_okay and path.is_dir():
                console.print(f"[red]'{value}' is a directory, not a file.[/red]")
                continue
                
            if not file_okay and path.is_file():
                console.print(f"[red]'{value}' is a file, not a directory.[/red]")
                continue
            
            return str(path)
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_typer_confirm(message, default=False, abort=False):
    """
    Safely prompt for confirmation without using typer's internals.
    This is a drop-in replacement for typer.confirm().
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        result = safe_confirm(message, default)
        if abort and not result:
            raise typer.Abort()
        return result
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def check_interactive_or_exit():
    """Check if environment is interactive, exit with message if not."""
    if not is_interactive():
        non_interactive_fallback()
