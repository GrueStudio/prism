"""
Signal system for the Prism CLI.

Godot-like signals with decorator-based declaration and callback validation.

Usage:
    class MyClass:
        @signal
        def request_load(self) -> None:
            '''Emitted when load is requested.'''
            pass
        
        @signal
        def data_loaded(self, data: dict, count: int) -> None:
            '''Emitted when data is loaded.'''
            pass
    
    obj = MyClass()
    obj.request_load.connect(lambda: print("loaded"))
    obj.request_load()  # or obj.request_load.emit()
    
    obj.data_loaded.connect(lambda d, c: print(f"{c} items"))
    obj.data_loaded({"key": "value"}, 5)
"""
import inspect
from typing import Any, Callable, List


class SignalError(Exception):
    """Exception raised for signal-related errors."""
    pass


class Signal:
    """
    A signal that can have callbacks connected to it.

    Signals are callable - calling the signal emits it.
    Validates callback signatures against the signal's signature.
    """

    def __init__(self, name: str = "", signature: Any = None) -> None:
        """
        Initialize the signal.

        Args:
            name: Signal name (for error messages).
            signature: The signal method's signature for validation.
        """
        self.name = name
        self.signature = signature
        self._callbacks: List[Callable] = []
        self._expected_params: List[inspect.Parameter] = []

        # Extract expected parameters from signature (excluding 'self')
        if signature:
            sig = inspect.signature(signature)
            self._expected_params = [
                p for name, p in sig.parameters.items() if name != 'self'
            ]

    def connect(self, callback: Callable) -> None:
        """
        Connect a callback to this signal.

        Validates callback signature against signal signature.

        Args:
            callback: Function to call when signal is emitted.

        Raises:
            SignalError: If callback signature doesn't match signal signature.
        """
        if callback in self._callbacks:
            return

        # Validate callback signature if we have a signal signature
        if self._expected_params:
            self._validate_callback(callback)

        self._callbacks.append(callback)

    def _validate_callback(self, callback: Callable) -> None:
        """
        Validate that callback signature matches signal signature.

        Args:
            callback: Callback function to validate.

        Raises:
            SignalError: If signatures don't match.
        """
        try:
            callback_sig = inspect.signature(callback)
        except (ValueError, TypeError):
            # Can't inspect signature (e.g., built-in), skip validation
            return

        callback_params = list(callback_sig.parameters.values())

        # Check parameter count
        if len(callback_params) != len(self._expected_params):
            raise SignalError(
                f"Callback for signal '{self.name}' has {len(callback_params)} "
                f"parameters, but signal expects {len(self._expected_params)}. "
                f"Signal signature: {self._format_signature(self._expected_params)}. "
                f"Callback signature: {self._format_signature(callback_params)}"
            )

        # Check parameter types (if annotated)
        for i, (expected, actual) in enumerate(zip(self._expected_params, callback_params)):
            expected_type = expected.annotation
            actual_type = actual.annotation

            # Skip if either is not annotated
            if expected_type == inspect.Parameter.empty or actual_type == inspect.Parameter.empty:
                continue

            # Check type compatibility
            if expected_type != actual_type:
                # Check if actual is a subclass of expected
                try:
                    if not (isinstance(actual_type, type) and 
                            isinstance(expected_type, type) and 
                            issubclass(actual_type, expected_type)):
                        raise SignalError(
                            f"Callback parameter {i} for signal '{self.name}' has type "
                            f"'{actual_type.__name__}', but signal expects '{expected_type.__name__}'"
                        )
                except TypeError:
                    # Generic types (List, Dict, etc.) - just warn for now
                    pass

    def _format_signature(self, params: List[inspect.Parameter]) -> str:
        """Format parameter list for error messages."""
        parts = []
        for p in params:
            if p.annotation != inspect.Parameter.empty:
                parts.append(f"{p.name}: {p.annotation.__name__}")
            else:
                parts.append(p.name)
        return f"({', '.join(parts)})"

    def disconnect(self, callback: Callable) -> None:
        """
        Disconnect a callback from this signal.

        Args:
            callback: Function to disconnect.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def disconnect_all(self) -> None:
        """Disconnect all callbacks from this signal."""
        self._callbacks.clear()

    def emit(self, *args, **kwargs) -> None:
        """
        Emit the signal, calling all connected callbacks.

        Args:
            *args: Positional arguments to pass to callbacks.
            **kwargs: Keyword arguments to pass to callbacks.
        """
        for callback in list(self._callbacks):
            callback(*args, **kwargs)

    def __call__(self, *args, **kwargs) -> None:
        """
        Emit the signal (shorthand for emit()).

        Args:
            *args: Positional arguments to pass to callbacks.
            **kwargs: Keyword arguments to pass to callbacks.
        """
        self.emit(*args, **kwargs)

    def is_connected(self, callback: Callable) -> bool:
        """
        Check if a callback is connected to this signal.

        Args:
            callback: Function to check.

        Returns:
            True if callback is connected, False otherwise.
        """
        return callback in self._callbacks

    def get_connections(self) -> List[Callable]:
        """
        Get list of connected callbacks.

        Returns:
            List of connected callback functions.
        """
        return list(self._callbacks)


class SignalDescriptor:
    """
    Descriptor that provides per-instance Signal objects.

    When you declare `my_signal = Signal()` on a class, this descriptor
    ensures each instance gets its own Signal object.
    """

    def __init__(self, name: str, signature: Any = None) -> None:
        """
        Initialize the descriptor.

        Args:
            name: Name of the signal.
            signature: The signal method's signature for validation.
        """
        self.name = name
        self.signature = signature
        self.instance_signals: dict = {}

    def __get__(self, obj, objtype=None):
        """
        Get the Signal instance for the object.

        Args:
            obj: The instance object.
            objtype: The class type (unused).

        Returns:
            Signal instance for this object.
        """
        if obj is None:
            return self

        if obj not in self.instance_signals:
            self.instance_signals[obj] = Signal(
                name=self.name,
                signature=self.signature
            )

        return self.instance_signals[obj]

    def __set__(self, obj, value) -> None:
        """
        Prevent assignment to signal.

        Args:
            obj: The instance object.
            value: The value being assigned (ignored).

        Raises:
            SignalError: Always raised - signals cannot be reassigned.
        """
        raise SignalError(f"Cannot reassign signal '{self.name}'")


def signal(func=None):
    """
    Decorator to declare a method as a signal.

    The decorated method's signature is used to validate connected callbacks.
    The method body is optional - it can be just documentation (pass) or
    contain logic that runs when the signal is emitted.

    Usage:
        class MyClass:
            @signal
            def request_load(self) -> None:
                '''Emitted when load is requested.'''
                pass

            @signal
            def data_loaded(self, data: dict) -> None:
                '''Emitted when data is loaded.'''
                # Optional: run this logic when signal emits
                print(f"Loaded: {data}")

    Args:
        func: The method being decorated.

    Returns:
        SignalDescriptor that creates per-instance Signal objects.
    """
    if func is None:
        # Called as @signal() with parentheses
        def decorator(f):
            return signal(f)
        return decorator

    # Get the function's signature for validation
    signal_name = func.__name__

    # Return descriptor with signature info
    return SignalDescriptor(name=signal_name, signature=func)
