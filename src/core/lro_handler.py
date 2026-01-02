"""
Long-running operation (LRO) handler for Fabric API.

This module provides utilities for handling long-running operations
with progress reporting and cancellation support.

Classes:
    LROHandler: Handles polling and status tracking for LRO operations
"""

import time
import logging
from typing import Dict, Any, Optional, Callable

import requests
from tqdm import tqdm

from .http_client import FabricAPIError, TransientAPIError

# Try to import CancellationToken
try:
    from .cancellation import CancellationToken, OperationCancelledException
except ImportError:
    try:
        from ..cancellation import CancellationToken, OperationCancelledException
    except ImportError:
        CancellationToken = None  # type: ignore
        OperationCancelledException = Exception  # type: ignore

logger = logging.getLogger(__name__)


class LROHandler:
    """Handler for long-running operations in Fabric API.
    
    Provides polling and status tracking for asynchronous operations
    with progress reporting and cancellation support.
    
    Example:
        >>> handler = LROHandler(get_headers_func)
        >>> result = handler.wait_for_operation(
        ...     operation_url,
        ...     retry_after=30
        ... )
    """
    
    def __init__(
        self,
        get_headers: Callable[[], Dict[str, str]],
        timeout: int = 30,
    ):
        """Initialize the LRO handler.
        
        Args:
            get_headers: Callable that returns auth headers
            timeout: Timeout for polling requests in seconds
        """
        self._get_headers = get_headers
        self._timeout = timeout
    
    def wait_for_operation(
        self,
        operation_url: str,
        retry_after: int = 30,
        max_retries: int = 60,
        cancellation_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Wait for a long-running operation to complete with progress reporting.
        
        Args:
            operation_url: URL to poll for operation status
            retry_after: Initial delay between polls in seconds
            max_retries: Maximum number of poll attempts
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Operation result dictionary
            
        Raises:
            FabricAPIError: If operation fails or times out
            OperationCancelledException: If cancellation is requested
        """
        logger.info(f"Waiting for operation to complete... (polling every {retry_after}s)")
        
        with tqdm(
            total=100,
            desc="Operation progress",
            unit="%",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        ) as pbar:
            last_progress = 0
            
            for attempt in range(max_retries):
                # Check for cancellation before sleeping
                if cancellation_token and hasattr(cancellation_token, 'throw_if_cancelled'):
                    cancellation_token.throw_if_cancelled("waiting for operation")
                
                # Use interruptible sleep if cancellation token provided
                self._interruptible_sleep(retry_after, cancellation_token)
                
                try:
                    response = requests.get(
                        operation_url,
                        headers=self._get_headers(),
                        timeout=self._timeout
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Operation polling request failed (attempt {attempt+1}/{max_retries}): {e}"
                    )
                    continue
                
                if response.status_code == 200:
                    result = self._parse_status_response(response, pbar, last_progress)
                    if result is not None:
                        return result
                    last_progress = pbar.n
                else:
                    logger.warning(f"Failed to check operation status: {response.status_code}")
        
        raise FabricAPIError(
            status_code=504,
            error_code='OperationTimeout',
            message='Operation timed out',
        )
    
    def wait_for_operation_and_get_result(
        self,
        operation_url: str,
        retry_after: int = 20,
        max_retries: int = 60,
        cancellation_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Wait for operation and fetch the result from result URL.
        
        After the operation succeeds, fetches the actual result from the result URL
        which is provided in the Location header of the success response.
        
        Args:
            operation_url: URL to poll for operation status
            retry_after: Initial delay between polls in seconds
            max_retries: Maximum number of poll attempts
            cancellation_token: Optional token for cancellation support
            
        Returns:
            Operation result dictionary
            
        Raises:
            FabricAPIError: If operation fails or times out
            OperationCancelledException: If cancellation is requested
        """
        logger.info(f"Waiting for operation to complete... (polling every {retry_after}s)")
        
        with tqdm(
            total=100,
            desc="Operation progress",
            unit="%",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        ) as pbar:
            last_progress = 0
            
            for attempt in range(max_retries):
                # Check for cancellation before sleeping
                if cancellation_token and hasattr(cancellation_token, 'throw_if_cancelled'):
                    cancellation_token.throw_if_cancelled("waiting for operation")
                
                self._interruptible_sleep(retry_after, cancellation_token)
                
                try:
                    response = requests.get(
                        operation_url,
                        headers=self._get_headers(),
                        timeout=self._timeout
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Operation polling request failed (attempt {attempt+1}/{max_retries}): {e}"
                    )
                    continue
                
                if response.status_code == 200:
                    result = self._handle_success_response_with_result(
                        response, operation_url, pbar, last_progress
                    )
                    if result is not None:
                        return result
                    last_progress = pbar.n
                else:
                    logger.warning(f"Failed to check operation status: {response.status_code}")
        
        raise FabricAPIError(
            status_code=504,
            error_code='OperationTimeout',
            message='Operation timed out',
        )
    
    def _interruptible_sleep(
        self,
        seconds: int,
        cancellation_token: Optional[Any] = None,
    ) -> None:
        """Sleep in small intervals to allow cancellation checks.
        
        Args:
            seconds: Total seconds to sleep
            cancellation_token: Optional cancellation token to check
        """
        if cancellation_token and hasattr(cancellation_token, 'is_cancelled'):
            for _ in range(seconds):
                if cancellation_token.is_cancelled():
                    cancellation_token.throw_if_cancelled("waiting for operation")
                time.sleep(1)
        else:
            time.sleep(seconds)
    
    def _parse_status_response(
        self,
        response: requests.Response,
        pbar: tqdm,
        last_progress: int,
    ) -> Optional[Dict[str, Any]]:
        """Parse operation status response and update progress.
        
        Args:
            response: The HTTP response
            pbar: Progress bar to update
            last_progress: Last recorded progress value
            
        Returns:
            Operation result if completed, None if still running
            
        Raises:
            FabricAPIError: If operation failed
        """
        try:
            result = response.json()
        except ValueError as e:
            logger.warning(f"Failed to parse operation status: {e}")
            return None
        
        status = result.get('status', 'Unknown')
        percent_complete = result.get('percentComplete', 0) or 0
        
        # Update progress bar
        if percent_complete > last_progress:
            pbar.update(percent_complete - last_progress)
        
        pbar.set_postfix_str(f"Status: {status}")
        logger.info(f"Operation status: {status} ({percent_complete}% complete)")
        
        if status == 'Succeeded':
            pbar.update(100 - pbar.n)  # Complete the bar
            return result
        elif status == 'Failed':
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            raise FabricAPIError(
                status_code=500,
                error_code='OperationFailed',
                message=f"Operation failed: {error_msg}",
            )
        
        return None  # Still running
    
    def _handle_success_response_with_result(
        self,
        response: requests.Response,
        operation_url: str,
        pbar: tqdm,
        last_progress: int,
    ) -> Optional[Dict[str, Any]]:
        """Handle success response and fetch result from result URL.
        
        Args:
            response: The HTTP response
            operation_url: Original operation URL
            pbar: Progress bar to update
            last_progress: Last recorded progress value
            
        Returns:
            Operation result if completed, None if still running
        """
        try:
            result = response.json()
        except ValueError as e:
            logger.warning(f"Failed to parse operation status: {e}")
            return None
        
        status = result.get('status', 'Unknown')
        percent_complete = result.get('percentComplete', 0) or 0
        
        # Update progress bar
        if percent_complete > last_progress:
            pbar.update(percent_complete - last_progress)
        
        pbar.set_postfix_str(f"Status: {status}")
        logger.info(f"Operation status: {status} ({percent_complete}% complete)")
        
        if status == 'Succeeded':
            pbar.update(100 - pbar.n)  # Complete the bar
            return self._fetch_result(response, operation_url, result)
        elif status == 'Failed':
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            raise FabricAPIError(
                status_code=500,
                error_code='OperationFailed',
                message=f"Operation failed: {error_msg}",
            )
        
        return None  # Still running
    
    def _fetch_result(
        self,
        response: requests.Response,
        operation_url: str,
        fallback_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch result from result URL.
        
        Args:
            response: The success response containing Location header
            operation_url: Original operation URL for fallback
            fallback_result: Result to return if fetch fails
            
        Returns:
            The fetched result or fallback
        """
        # Get the result URL from the Location header
        result_url = response.headers.get('Location')
        if result_url:
            logger.info(f"Fetching result from: {result_url}")
            try:
                result_response = requests.get(
                    result_url,
                    headers=self._get_headers(),
                    timeout=self._timeout
                )
                if result_response.status_code == 200:
                    return result_response.json()
                else:
                    logger.warning(
                        f"Failed to fetch result from {result_url}: {result_response.status_code}"
                    )
            except Exception as e:
                logger.warning(f"Error fetching result: {e}")
        
        # Fallback: try appending /result to operation URL
        result_url = f"{operation_url}/result"
        logger.info(f"Trying fallback result URL: {result_url}")
        try:
            result_response = requests.get(
                result_url,
                headers=self._get_headers(),
                timeout=self._timeout
            )
            if result_response.status_code == 200:
                return result_response.json()
        except Exception as e:
            logger.warning(f"Error fetching fallback result: {e}")
        
        # Return the status response if no result URL found
        return fallback_result
