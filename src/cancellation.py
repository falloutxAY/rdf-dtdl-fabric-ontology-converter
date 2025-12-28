"""
Cancellation support for long-running operations.

This module provides thread-safe cancellation tokens and signal handlers
for graceful cancellation of operations like ontology uploads.

Example:
    ```python
    from cancellation import setup_cancellation_handler, OperationCancelledException
    
    # Setup Ctrl+C handler
    token = setup_cancellation_handler()
    
    # Register cleanup callback
    token.register_callback(lambda: print("Cleaning up..."))
    
    # Check for cancellation in long-running loop
    for item in items:
        token.throw_if_cancelled()
        process(item)
    ```
"""

import signal
import threading
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class OperationCancelledException(Exception):
    """
    Raised when an operation is cancelled by the user.
    
    This exception should be caught at the top level to perform
    cleanup and exit gracefully.
    
    Attributes:
        message: Human-readable description of the cancellation.
        operation: Optional name of the operation that was cancelled.
    """
    
    def __init__(
        self, 
        message: str = "Operation was cancelled",
        operation: Optional[str] = None
    ):
        self.message = message
        self.operation = operation
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.operation:
            return f"{self.message} (operation: {self.operation})"
        return self.message


class CancellationToken:
    """
    Thread-safe cancellation token for cooperative cancellation.
    
    Use this class to implement graceful cancellation of long-running
    operations. The token can be checked periodically or used to
    throw an exception when cancellation is requested.
    
    Attributes:
        is_cancelled: Whether cancellation has been requested.
    
    Example:
        ```python
        token = CancellationToken()
        
        # In main code
        def long_operation(token):
            for i in range(1000):
                token.throw_if_cancelled()
                do_work(i)
        
        # When user presses Ctrl+C
        token.cancel()
        ```
    """
    
    def __init__(self):
        """Initialize a new cancellation token."""
        self._cancelled = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()
        self._cancel_reason: Optional[str] = None
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Mark the token as cancelled and notify all callbacks.
        
        This method is thread-safe and can be called from any thread,
        including signal handlers.
        
        Args:
            reason: Optional reason for the cancellation.
        """
        with self._lock:
            if self._cancelled.is_set():
                return  # Already cancelled
            
            self._cancel_reason = reason
            self._cancelled.set()
            
            logger.info(f"Cancellation requested: {reason or 'user initiated'}")
            
            # Execute callbacks in registration order
            for callback in self._callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Cancellation callback failed: {e}")
    
    def is_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.
        
        This method is thread-safe and can be called frequently
        without significant performance impact.
        
        Returns:
            True if cancel() has been called, False otherwise.
        """
        return self._cancelled.is_set()
    
    def throw_if_cancelled(self, operation: Optional[str] = None) -> None:
        """
        Raise OperationCancelledException if cancellation requested.
        
        Call this method at safe cancellation points in your code
        where it's okay to abort the operation.
        
        Args:
            operation: Optional name of the current operation for
                      better error messages.
        
        Raises:
            OperationCancelledException: If cancel() has been called.
        """
        if self.is_cancelled():
            message = "Operation was cancelled"
            if self._cancel_reason:
                message = f"Operation was cancelled: {self._cancel_reason}"
            raise OperationCancelledException(message, operation)
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a cleanup callback to run when cancelled.
        
        Callbacks are executed in registration order when cancel()
        is called. Exceptions in callbacks are logged but don't
        prevent other callbacks from running.
        
        Args:
            callback: A callable with no arguments to execute on cancellation.
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[], None]) -> bool:
        """
        Remove a previously registered callback.
        
        Args:
            callback: The callback to remove.
            
        Returns:
            True if the callback was found and removed, False otherwise.
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until cancellation is requested or timeout expires.
        
        This is useful for implementing interruptible sleep or
        waiting for cancellation in a background thread.
        
        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.
            
        Returns:
            True if cancelled, False if timeout expired.
        """
        return self._cancelled.wait(timeout)
    
    def reset(self) -> None:
        """
        Reset the token to non-cancelled state.
        
        Warning: Use with caution. This clears the cancelled state
        but does not unregister callbacks.
        """
        with self._lock:
            self._cancelled.clear()
            self._cancel_reason = None
    
    @property
    def cancel_reason(self) -> Optional[str]:
        """Get the reason for cancellation, if provided."""
        return self._cancel_reason


class CancellationTokenSource:
    """
    Factory for creating linked cancellation tokens.
    
    Use this class when you need to create child tokens that
    are automatically cancelled when the parent is cancelled.
    
    Example:
        ```python
        source = CancellationTokenSource()
        
        # Create child token for sub-operation
        child_token = source.create_linked_token()
        
        # Cancelling parent cancels all children
        source.cancel()
        assert child_token.is_cancelled()
        ```
    """
    
    def __init__(self):
        """Initialize a new cancellation token source."""
        self._token = CancellationToken()
        self._children: List[CancellationToken] = []
        self._lock = threading.Lock()
    
    @property
    def token(self) -> CancellationToken:
        """Get the main cancellation token."""
        return self._token
    
    def create_linked_token(self) -> CancellationToken:
        """
        Create a child token linked to this source.
        
        The child token will be automatically cancelled when
        the parent source is cancelled.
        
        Returns:
            A new CancellationToken linked to this source.
        """
        child = CancellationToken()
        
        with self._lock:
            self._children.append(child)
            
            # Link parent to child
            def cancel_child():
                child.cancel(self._token.cancel_reason)
            
            self._token.register_callback(cancel_child)
        
        return child
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel the source token and all linked tokens.
        
        Args:
            reason: Optional reason for the cancellation.
        """
        self._token.cancel(reason)
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._token.is_cancelled()


# Global token for signal handler
_global_token: Optional[CancellationToken] = None
_original_sigint_handler = None


def setup_cancellation_handler(
    show_message: bool = True,
    message: str = "\n⚠️  Cancellation requested. Cleaning up..."
) -> CancellationToken:
    """
    Setup SIGINT (Ctrl+C) handler for graceful cancellation.
    
    This function installs a signal handler that creates a cancellation
    token when the user presses Ctrl+C. The first Ctrl+C triggers
    graceful cancellation; a second Ctrl+C forces immediate exit.
    
    Args:
        show_message: Whether to print a message on cancellation.
        message: The message to print when cancelled.
    
    Returns:
        A CancellationToken that will be cancelled on SIGINT.
    
    Example:
        ```python
        token = setup_cancellation_handler()
        
        try:
            for item in items:
                token.throw_if_cancelled()
                process(item)
        except OperationCancelledException:
            print("Operation cancelled by user")
            sys.exit(130)
        ```
    """
    global _global_token, _original_sigint_handler
    
    token = CancellationToken()
    _global_token = token
    
    # Track if we're in graceful shutdown
    graceful_shutdown = [False]
    
    def signal_handler(sig: int, frame) -> None:
        """Handle SIGINT signal."""
        if graceful_shutdown[0]:
            # Second Ctrl+C - force exit
            print("\n⚠️  Forced exit. Some cleanup may be incomplete.")
            # Restore original handler and re-raise
            if _original_sigint_handler:
                signal.signal(signal.SIGINT, _original_sigint_handler)
            raise KeyboardInterrupt
        
        graceful_shutdown[0] = True
        
        if show_message:
            print(message)
        
        token.cancel("user interrupted (SIGINT)")
    
    # Save original handler
    _original_sigint_handler = signal.getsignal(signal.SIGINT)
    
    # Install our handler
    signal.signal(signal.SIGINT, signal_handler)
    
    return token


def restore_default_handler() -> None:
    """
    Restore the default SIGINT handler.
    
    Call this after your operation completes to restore normal
    Ctrl+C behavior.
    """
    global _original_sigint_handler
    
    if _original_sigint_handler:
        signal.signal(signal.SIGINT, _original_sigint_handler)
        _original_sigint_handler = None


def get_global_token() -> Optional[CancellationToken]:
    """
    Get the global cancellation token if one is set up.
    
    Returns:
        The global CancellationToken, or None if not set up.
    """
    return _global_token


# Type alias for type hints
CancellationCallback = Callable[[], None]
