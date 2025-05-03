"""
Base singleton implementation for reuse across the application.
"""
from typing import Any, Dict, Type, TypeVar

# Type variable for the class that implements the Singleton pattern
T = TypeVar("T", bound=type)


class Singleton(type):
    """
    Metaclass for implementing the Singleton pattern.
    This ensures only one instance of a class exists.
    """

    _instances: Dict[Type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """
        Override the __call__ method to implement the singleton pattern.
        Returns the existing instance if already created, otherwise creates a new one.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear_instance(mcs, cls: Type) -> None:
        """
        Clear a specific singleton instance from the registry.
        This can be useful in testing or when you need to recreate an instance.

        Args:
            cls: The class whose instance should be cleared
        """
        if cls in mcs._instances:
            del mcs._instances[cls]

    @classmethod
    def clear_all_instances(mcs) -> None:
        """
        Clear all singleton instances from the registry.
        This can be useful during application shutdown or for testing purposes.
        """
        mcs._instances.clear()
