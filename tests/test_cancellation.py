"""
Tests for the cancellation module.

Tests cover the CancellationToken class, CancellationTokenSource,
signal handling, and integration with the Fabric client.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import signal

import sys
sys.path.insert(0, 'src')

from cancellation import (
    CancellationToken,
    CancellationTokenSource,
    OperationCancelledException,
    setup_cancellation_handler,
    restore_default_handler,
    get_global_token,
)


class TestOperationCancelledException:
    """Tests for OperationCancelledException."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = OperationCancelledException()
        assert str(exc) == "Operation was cancelled"
        assert exc.message == "Operation was cancelled"
        assert exc.operation is None
    
    def test_exception_with_custom_message(self):
        """Test exception with custom message."""
        exc = OperationCancelledException("Custom cancellation message")
        assert "Custom cancellation message" in str(exc)
        assert exc.message == "Custom cancellation message"
    
    def test_exception_with_operation(self):
        """Test exception with operation name."""
        exc = OperationCancelledException("Cancelled", operation="upload")
        assert "upload" in str(exc)
        assert exc.operation == "upload"
    
    def test_exception_is_raisable(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(OperationCancelledException) as exc_info:
            raise OperationCancelledException("Test cancel")
        
        assert exc_info.value.message == "Test cancel"


class TestCancellationToken:
    """Tests for CancellationToken class."""
    
    def test_initial_state(self):
        """Test that token starts in non-cancelled state."""
        token = CancellationToken()
        assert token.is_cancelled() is False
        assert token.cancel_reason is None
    
    def test_cancel_changes_state(self):
        """Test that cancel() changes the state."""
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled() is True
    
    def test_cancel_with_reason(self):
        """Test cancellation with reason."""
        token = CancellationToken()
        token.cancel(reason="User pressed Ctrl+C")
        assert token.is_cancelled() is True
        assert token.cancel_reason == "User pressed Ctrl+C"
    
    def test_cancel_idempotent(self):
        """Test that multiple cancel() calls are safe."""
        token = CancellationToken()
        token.cancel("First")
        token.cancel("Second")  # Should not override
        assert token.is_cancelled() is True
        # First reason should be kept
        assert token.cancel_reason == "First"
    
    def test_throw_if_cancelled_when_not_cancelled(self):
        """Test throw_if_cancelled() does nothing when not cancelled."""
        token = CancellationToken()
        # Should not raise
        token.throw_if_cancelled()
        token.throw_if_cancelled("some operation")
    
    def test_throw_if_cancelled_when_cancelled(self):
        """Test throw_if_cancelled() raises when cancelled."""
        token = CancellationToken()
        token.cancel()
        
        with pytest.raises(OperationCancelledException):
            token.throw_if_cancelled()
    
    def test_throw_if_cancelled_with_operation(self):
        """Test throw_if_cancelled() includes operation name."""
        token = CancellationToken()
        token.cancel()
        
        with pytest.raises(OperationCancelledException) as exc_info:
            token.throw_if_cancelled("upload ontology")
        
        assert exc_info.value.operation == "upload ontology"
    
    def test_callback_executed_on_cancel(self):
        """Test that registered callbacks are called on cancel."""
        token = CancellationToken()
        callback_called = [False]
        
        def on_cancel():
            callback_called[0] = True
        
        token.register_callback(on_cancel)
        token.cancel()
        
        assert callback_called[0] is True
    
    def test_multiple_callbacks_executed(self):
        """Test that all callbacks are executed in order."""
        token = CancellationToken()
        call_order = []
        
        token.register_callback(lambda: call_order.append(1))
        token.register_callback(lambda: call_order.append(2))
        token.register_callback(lambda: call_order.append(3))
        
        token.cancel()
        
        assert call_order == [1, 2, 3]
    
    def test_callback_exception_does_not_prevent_others(self):
        """Test that callback exceptions don't prevent other callbacks."""
        token = CancellationToken()
        results = []
        
        def callback_ok():
            results.append("ok")
        
        def callback_error():
            raise RuntimeError("Callback failed")
        
        token.register_callback(callback_ok)
        token.register_callback(callback_error)
        token.register_callback(callback_ok)
        
        token.cancel()  # Should not raise
        
        assert results == ["ok", "ok"]
    
    def test_unregister_callback(self):
        """Test callback unregistration."""
        token = CancellationToken()
        callback_called = [False]
        
        def on_cancel():
            callback_called[0] = True
        
        token.register_callback(on_cancel)
        result = token.unregister_callback(on_cancel)
        
        assert result is True
        token.cancel()
        assert callback_called[0] is False
    
    def test_unregister_nonexistent_callback(self):
        """Test unregistering callback that was never registered."""
        token = CancellationToken()
        
        def some_callback():
            pass
        
        result = token.unregister_callback(some_callback)
        assert result is False
    
    def test_wait_returns_true_when_cancelled(self):
        """Test wait() returns True when cancelled."""
        token = CancellationToken()
        
        # Cancel in another thread
        def cancel_later():
            time.sleep(0.05)
            token.cancel()
        
        thread = threading.Thread(target=cancel_later)
        thread.start()
        
        result = token.wait(timeout=1.0)
        thread.join()
        
        assert result is True
    
    def test_wait_returns_false_on_timeout(self):
        """Test wait() returns False on timeout."""
        token = CancellationToken()
        
        result = token.wait(timeout=0.05)
        
        assert result is False
        assert token.is_cancelled() is False
    
    def test_reset_clears_cancelled_state(self):
        """Test reset() clears the cancelled state."""
        token = CancellationToken()
        token.cancel("some reason")
        
        assert token.is_cancelled() is True
        assert token.cancel_reason == "some reason"
        
        token.reset()
        
        assert token.is_cancelled() is False
        assert token.cancel_reason is None
    
    def test_thread_safety(self):
        """Test thread safety of cancel and is_cancelled."""
        token = CancellationToken()
        results = []
        
        def checker():
            for _ in range(100):
                results.append(token.is_cancelled())
                time.sleep(0.001)
        
        def canceller():
            time.sleep(0.05)
            token.cancel()
        
        threads = [
            threading.Thread(target=checker),
            threading.Thread(target=checker),
            threading.Thread(target=canceller),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have False then True values
        assert False in results
        assert True in results


class TestCancellationTokenSource:
    """Tests for CancellationTokenSource class."""
    
    def test_source_has_token(self):
        """Test that source provides a token."""
        source = CancellationTokenSource()
        assert source.token is not None
        assert isinstance(source.token, CancellationToken)
    
    def test_source_cancel_cancels_token(self):
        """Test that cancelling source cancels its token."""
        source = CancellationTokenSource()
        
        assert source.is_cancelled() is False
        assert source.token.is_cancelled() is False
        
        source.cancel()
        
        assert source.is_cancelled() is True
        assert source.token.is_cancelled() is True
    
    def test_linked_token_cancelled_with_parent(self):
        """Test that linked tokens are cancelled with parent."""
        source = CancellationTokenSource()
        child = source.create_linked_token()
        
        assert child.is_cancelled() is False
        
        source.cancel("parent cancelled")
        
        assert child.is_cancelled() is True
        assert child.cancel_reason == "parent cancelled"
    
    def test_multiple_linked_tokens(self):
        """Test multiple linked tokens."""
        source = CancellationTokenSource()
        children = [source.create_linked_token() for _ in range(5)]
        
        source.cancel()
        
        for child in children:
            assert child.is_cancelled() is True


class TestSignalHandler:
    """Tests for signal handler setup."""
    
    def test_setup_returns_token(self):
        """Test that setup returns a cancellation token."""
        try:
            token = setup_cancellation_handler(show_message=False)
            assert isinstance(token, CancellationToken)
            assert token.is_cancelled() is False
        finally:
            restore_default_handler()
    
    def test_get_global_token(self):
        """Test get_global_token returns the setup token."""
        try:
            token = setup_cancellation_handler(show_message=False)
            global_token = get_global_token()
            assert global_token is token
        finally:
            restore_default_handler()
    
    def test_restore_handler(self):
        """Test that restore_default_handler works."""
        original_handler = signal.getsignal(signal.SIGINT)
        
        try:
            setup_cancellation_handler(show_message=False)
            # Handler should be different now
            assert signal.getsignal(signal.SIGINT) != original_handler
            
            restore_default_handler()
            # Handler should be restored
            assert signal.getsignal(signal.SIGINT) == original_handler
        finally:
            # Ensure cleanup
            signal.signal(signal.SIGINT, original_handler)


class TestFabricClientCancellation:
    """Tests for cancellation integration with FabricOntologyClient."""
    
    def test_create_ontology_checks_cancellation(self):
        """Test that create_ontology checks cancellation token."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id="12345678-1234-1234-1234-123456789012",
            tenant_id="test-tenant",
            use_interactive_auth=False
        )
        
        # Create client without actually authenticating
        with patch('fabric_client.DefaultAzureCredential'):
            client = FabricOntologyClient(config)
            client._access_token = "mock-token"
            client._token_expires = time.time() + 3600
        
        token = CancellationToken()
        token.cancel()
        
        # Cancellation check happens before any API call
        with pytest.raises(OperationCancelledException):
            client.create_ontology(
                display_name="TestOntology",
                definition={"parts": []},
                cancellation_token=token
            )
    
    def test_update_ontology_definition_checks_cancellation(self):
        """Test that update_ontology_definition checks cancellation token."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id="12345678-1234-1234-1234-123456789012",
            tenant_id="test-tenant",
            use_interactive_auth=False
        )
        
        with patch('fabric_client.DefaultAzureCredential'):
            client = FabricOntologyClient(config)
            client._access_token = "mock-token"
            client._token_expires = time.time() + 3600
        
        token = CancellationToken()
        token.cancel()
        
        # Cancellation check happens before any API call
        with pytest.raises(OperationCancelledException):
            client.update_ontology_definition(
                ontology_id="test-id",
                definition={"parts": []},
                cancellation_token=token
            )
    
    def test_create_or_update_checks_cancellation(self):
        """Test that create_or_update_ontology checks cancellation token."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id="12345678-1234-1234-1234-123456789012",
            tenant_id="test-tenant",
            use_interactive_auth=False
        )
        
        with patch('fabric_client.DefaultAzureCredential'):
            client = FabricOntologyClient(config)
            client._access_token = "mock-token"
            client._token_expires = time.time() + 3600
        
        token = CancellationToken()
        token.cancel()
        
        # Cancellation check happens before any API call
        with pytest.raises(OperationCancelledException):
            client.create_or_update_ontology(
                display_name="TestOntology",
                definition={"parts": []},
                cancellation_token=token
            )
    
    def test_wait_for_operation_checks_cancellation_immediately(self):
        """Test that _wait_for_operation checks cancellation immediately."""
        from fabric_client import FabricConfig, FabricOntologyClient
        
        config = FabricConfig(
            workspace_id="12345678-1234-1234-1234-123456789012",
            tenant_id="test-tenant",
            use_interactive_auth=False
        )
        
        with patch('fabric_client.DefaultAzureCredential'):
            client = FabricOntologyClient(config)
            client._access_token = "mock-token"
            client._token_expires = time.time() + 3600
        
        # Pre-cancelled token
        token = CancellationToken()
        token.cancel()
        
        # Should raise immediately without making any API calls
        with pytest.raises(OperationCancelledException):
            client._wait_for_operation(
                "https://api.fabric.microsoft.com/operations/test",
                retry_after=1,
                max_retries=10,
                cancellation_token=token
            )


class TestCancellationScenarios:
    """Integration tests for common cancellation scenarios."""
    
    def test_interruptible_loop(self):
        """Test cancelling an interruptible processing loop."""
        token = CancellationToken()
        processed = []
        
        def process_items(items, token):
            for item in items:
                token.throw_if_cancelled()
                processed.append(item)
                time.sleep(0.01)
        
        items = list(range(100))
        
        # Cancel after some processing
        def cancel_later():
            time.sleep(0.05)
            token.cancel()
        
        cancel_thread = threading.Thread(target=cancel_later)
        cancel_thread.start()
        
        with pytest.raises(OperationCancelledException):
            process_items(items, token)
        
        cancel_thread.join()
        
        # Should have processed some but not all items
        assert len(processed) > 0
        assert len(processed) < len(items)
    
    def test_cleanup_callback_executed(self):
        """Test that cleanup callbacks are executed on cancellation."""
        token = CancellationToken()
        cleanup_performed = [False]
        resource_id = ["resource-123"]
        
        def cleanup():
            cleanup_performed[0] = True
            resource_id[0] = None  # Simulate cleanup
        
        token.register_callback(cleanup)
        
        # Simulate cancellation during operation
        token.cancel()
        
        assert cleanup_performed[0] is True
        assert resource_id[0] is None
    
    def test_nested_operations_with_linked_tokens(self):
        """Test nested operations using linked tokens."""
        source = CancellationTokenSource()
        
        outer_cancelled = [False]
        inner_cancelled = [False]
        
        def outer_operation(token):
            token.register_callback(lambda: outer_cancelled.__setitem__(0, True))
            
            # Create linked token for inner operation
            child = CancellationTokenSource()
            child.token.register_callback(lambda: inner_cancelled.__setitem__(0, True))
            
            # Link to parent
            token.register_callback(lambda: child.cancel())
            
            return child.token
        
        inner_token = outer_operation(source.token)
        
        # Cancel parent
        source.cancel()
        
        # Both should be cancelled
        assert outer_cancelled[0] is True
        assert inner_cancelled[0] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
