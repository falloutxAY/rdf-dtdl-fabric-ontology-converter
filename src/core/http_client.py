"""
HTTP request helpers for Fabric API client.

This module provides HTTP request utilities for the Fabric API client,
with consistent error handling and retry support.

Classes:
    RequestHandler: Centralized HTTP request handling with error handling
    ResponseHandler: Response parsing and error handling
"""

import json
import logging
from typing import Dict, Any, Optional, Union, Literal

import requests

logger = logging.getLogger(__name__)

# Type aliases
HttpMethod = Literal["GET", "POST", "PATCH", "DELETE", "PUT"]


class TransientAPIError(Exception):
    """Exception for transient API errors (429, 503) that should be retried.
    
    Microsoft Fabric uses HTTP 429 with a Retry-After header to indicate
    when the client should retry. This exception captures that information
    for use by retry logic.
    
    See: https://learn.microsoft.com/en-us/rest/api/fabric/articles/throttling
    """
    
    def __init__(self, status_code: int, retry_after: int = 5, message: str = ""):
        self.status_code = status_code
        self.retry_after = retry_after
        self.message = message
        super().__init__(f"Transient error (HTTP {status_code}): {message}")


class FabricAPIError(Exception):
    """Exception raised for Fabric API errors.
    
    Attributes:
        status_code: HTTP status code
        error_code: Fabric-specific error code
        message: Human-readable error message
    """
    
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message} (HTTP {status_code})")


def is_transient_error(exception: BaseException) -> bool:
    """Check if exception is a transient error that should be retried.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception is transient and should be retried
    """
    if isinstance(exception, TransientAPIError):
        return True
    if isinstance(exception, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    return False


def get_retry_wait_time(retry_state: Any) -> float:
    """Custom wait function that respects the Retry-After header from Fabric API.
    
    Microsoft Fabric returns a Retry-After header in 429 responses indicating
    how many seconds to wait before retrying. This function extracts that value
    and uses it, falling back to exponential backoff for other errors.
    
    Args:
        retry_state: The tenacity retry state object
        
    Returns:
        Number of seconds to wait before retrying
    """
    exception = retry_state.outcome.exception()
    
    # Honor Retry-After from TransientAPIError (429/503 responses)
    if isinstance(exception, TransientAPIError) and exception.retry_after:
        wait_time = float(exception.retry_after)
        logger.debug(f"Using Retry-After header value: {wait_time}s")
        return wait_time
    
    # Fall back to exponential backoff for other transient errors
    # Base: 2s, multiplier: 2x, max: 60s
    attempt = retry_state.attempt_number
    wait_time = min(2 * (2 ** (attempt - 1)), 60)
    logger.debug(f"Using exponential backoff: {wait_time}s (attempt {attempt})")
    return wait_time


class RequestHandler:
    """Centralized HTTP request handling with error handling.
    
    Handles common request patterns including:
    - Timeout handling
    - Connection error handling
    - Consistent logging format
    - Error message structure
    
    Example:
        >>> handler = RequestHandler(rate_limiter)
        >>> response = handler.execute(
        ...     "GET", url, "List ontologies",
        ...     headers=headers
        ... )
    """
    
    def __init__(
        self,
        rate_limiter: Optional[Any] = None,
        default_timeout: int = 30,
    ):
        """Initialize the request handler.
        
        Args:
            rate_limiter: Optional rate limiter instance
            default_timeout: Default request timeout in seconds
        """
        self._rate_limiter = rate_limiter
        self._default_timeout = default_timeout
    
    def execute(
        self,
        method: HttpMethod,
        url: str,
        operation_name: str,
        timeout: Optional[int] = None,
        **kwargs: Any
    ) -> requests.Response:
        """Execute an HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            url: URL to request
            operation_name: Description of operation (for logging)
            timeout: Request timeout in seconds (uses default if not specified)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
            
        Raises:
            FabricAPIError: On any request failure with consistent error codes
        """
        timeout = timeout or self._default_timeout
        
        # Acquire rate limit token before making request
        if self._rate_limiter:
            wait_time = self._rate_limiter.get_wait_time()
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s before {operation_name}")
            self._rate_limiter.acquire()
        
        try:
            logger.debug(f"{operation_name}: {method} {url}")
            response = requests.request(method, url, timeout=timeout, **kwargs)
            return response
        
        except requests.exceptions.Timeout:
            logger.error(f"{operation_name}: Request timeout after {timeout}s")
            raise FabricAPIError(
                status_code=408,
                error_code='RequestTimeout',
                message=f'{operation_name} timed out after {timeout} seconds'
            )
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"{operation_name}: Connection error: {e}")
            raise FabricAPIError(
                status_code=503,
                error_code='ConnectionError',
                message=f'{operation_name} failed to connect to Fabric API: {e}'
            )
        
        except requests.exceptions.RequestException as e:
            logger.error(f"{operation_name}: Request error: {e}")
            raise FabricAPIError(
                status_code=500,
                error_code='RequestError',
                message=f'{operation_name} request failed: {e}'
            )


class ResponseHandler:
    """Handles API response parsing and error handling.
    
    Provides consistent response handling including:
    - JSON parsing with error handling
    - HTTP status code handling
    - Transient error detection (429, 503)
    - Long-running operation detection
    
    Example:
        >>> handler = ResponseHandler()
        >>> result = handler.handle(response)
    """
    
    @staticmethod
    def handle(response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors.
        
        Args:
            response: The HTTP response to handle
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            FabricAPIError: On error responses
            TransientAPIError: On retryable errors (429, 503)
        """
        if response.status_code in (200, 201):
            if response.text:
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response text: {response.text[:500]}")
                    raise FabricAPIError(
                        status_code=response.status_code,
                        error_code='InvalidResponse',
                        message=f'Server returned invalid JSON: {e}'
                    )
            return {}
        
        if response.status_code == 202:
            # Long-running operation
            location = response.headers.get('Location')
            operation_id = response.headers.get('x-ms-operation-id')
            retry_after = int(response.headers.get('Retry-After', 30))
            
            return {
                '_lro': True,
                'location': location,
                'operation_id': operation_id,
                'retry_after': retry_after,
            }
        
        # Handle transient errors (429, 503) - raise special exception for retry
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 30))
            logger.warning(f"Rate limited (429). Retry after {retry_after}s")
            raise TransientAPIError(429, retry_after, "Rate limit exceeded")
        
        if response.status_code == 503:
            retry_after = int(response.headers.get('Retry-After', 10))
            logger.warning(f"Service unavailable (503). Retry after {retry_after}s")
            raise TransientAPIError(503, retry_after, "Service temporarily unavailable")
        
        # Error response
        try:
            error_data = response.json()
            error_message = error_data.get('message', response.text)
            error_code = error_data.get('errorCode', 'Unknown')
        except json.JSONDecodeError:
            error_message = response.text
            error_code = 'Unknown'
        
        raise FabricAPIError(
            status_code=response.status_code,
            error_code=error_code,
            message=error_message,
        )


def sanitize_display_name(name: str) -> str:
    """Sanitize names to meet Fabric item constraints.
    
    Fabric item names must:
    - Contain only letters, numbers, and underscores
    - Start with a letter
    - Be less than 90 characters
    
    Args:
        name: The original name
        
    Returns:
        Sanitized name that meets Fabric constraints
    """
    if not name:
        return "Ontology"
    cleaned = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    if not cleaned[0].isalpha():
        cleaned = 'O_' + cleaned
    # Fabric error message mentions < 90 chars
    return cleaned[:90]
