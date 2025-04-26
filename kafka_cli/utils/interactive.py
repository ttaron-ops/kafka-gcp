import sys
import os
import typer
from rich.console import Console

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

def safe_text(message, default=None, **kwargs):
    """
    Safely prompt for text input using basic input(), without questionary.
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
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
    except Exception as e:
        console.print(f"[bold red]Error with prompt:[/bold red] {str(e)}")
        non_interactive_fallback()

def safe_select(message, choices, default=None, **kwargs):
    """
    Safely prompt for selection using basic input(), without questionary.
    """
    if not is_interactive():
        non_interactive_fallback()
    
    try:
        # Display the message
        console.print(f"{message}")
        
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
