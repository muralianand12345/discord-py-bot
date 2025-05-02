import asyncio
import logging
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Any, Callable, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


class LLMMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="Content of the message"
    )


class LLMClient:
    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 10.0,
        request_timeout: float = 30.0,
    ):
        """
        Initialize LLM client with retry capabilities

        Args:
            api_key: API key for the LLM service
            api_url: Base URL for the API
            model: Default model to use
            max_retries: Maximum number of retry attempts
            retry_base_delay: Initial delay between retries (in seconds)
            retry_max_delay: Maximum delay between retries (in seconds)
            request_timeout: Timeout for API requests (in seconds)
        """
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=api_url, timeout=request_timeout
        )
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.request_timeout = request_timeout

    async def invoke(
        self,
        messages: List[LLMMessage],
        model_name: Optional[str] = None,
        retry_on_specific_errors: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """
        Send a request to the LLM API with automatic retries

        Args:
            messages: List of LLMMessage objects representing the conversation
            model_name: Optional model name to override the default
            retry_on_specific_errors: List of error message substrings to retry on
            **kwargs: Additional parameters to pass to the API call

        Returns:
            The content of the assistant's response
        """
        # Use the default model if no model_name is provided
        model = model_name or self.model

        # Convert LLMMessage objects to dictionaries
        message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]

        # Common error types to retry on
        default_retry_errors = [
            "rate_limit",
            "timeout",
            "connection",
            "server_error",
            "500",
            "502",
            "503",
            "504",
            "capacity",
            "overloaded",
        ]

        retry_errors = default_retry_errors
        if retry_on_specific_errors:
            retry_errors.extend(retry_on_specific_errors)

        # Initialize retry counter
        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                # Increment attempt counter
                attempt += 1

                # Log the attempt if it's a retry
                if attempt > 1:
                    logger.info(
                        f"LLM API retry attempt {attempt}/{self.max_retries + 1}"
                    )

                # Send the request to the API
                response = await self.client.chat.completions.create(
                    model=model, messages=message_dicts, **kwargs
                )

                # Return the content of the response on success
                return response.choices[0].message.content

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Check if error is in retryable errors list
                should_retry = False
                for retry_error in retry_errors:
                    if retry_error.lower() in error_msg:
                        should_retry = True
                        break

                # If reached max retries or error isn't retryable, raise the exception
                if attempt > self.max_retries or not should_retry:
                    logger.error(
                        f"LLM API request failed after {attempt} attempts: {str(e)}"
                    )
                    raise

                # Calculate backoff delay with exponential backoff and jitter
                delay = min(
                    self.retry_max_delay, self.retry_base_delay * (2 ** (attempt - 1))
                )
                # Add jitter (±20%)
                jitter = 0.2 * delay * (asyncio.random() * 2 - 1)
                delay = max(0.1, delay + jitter)

                logger.warning(
                    f"LLM API request failed (attempt {attempt}/{self.max_retries + 1}): {str(e)}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                # Wait before retrying
                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception

        # Fallback empty response if somehow we get here
        return ""

    async def with_fallback(
        self,
        messages: List[LLMMessage],
        fallback_fn: Callable[[], str],
        model_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Send a request to the LLM API with a fallback function if it fails

        Args:
            messages: List of LLMMessage objects representing the conversation
            fallback_fn: Function to call if the API request fails
            model_name: Optional model name to override the default
            **kwargs: Additional parameters to pass to the API call

        Returns:
            The content of the assistant's response or fallback value
        """
        try:
            return await self.invoke(messages, model_name, **kwargs)
        except Exception as e:
            logger.warning(f"LLM API request failed, using fallback: {str(e)}")
            return fallback_fn()

    def format_message_with_image(
        self, user_content: str, image_path: str
    ) -> List[Dict[str, Any]]:
        """
        Format user message content with an image for OpenAI API format

        Args:
            user_content: The text content from the user
            image_path: Path to the image file to include

        Returns:
            Formatted message content ready for the API
        """
        # Read and encode the image file
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")

        # Determine the image type
        image_bytes = base64.b64decode(base64_image)
        image_stream = BytesIO(image_bytes)
        image = Image.open(image_stream)
        image_type = image.format.lower()

        # Format according to OpenAI's content format
        return [
            {"type": "text", "text": user_content},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"},
            },
        ]

    def format_message_with_image_url(
        self, user_content: str, image_url: str
    ) -> List[Dict[str, Any]]:
        """
        Format user message content with an external image URL

        Args:
            user_content: The text content from the user
            image_url: URL of the image to include

        Returns:
            Formatted message content ready for the API
        """
        return [
            {"type": "text", "text": user_content},
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ]
