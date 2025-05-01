from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Optional, List


class LLMMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")


class LLMClient:
    def __init__(self, api_key: str, api_url: str, model: str):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_url)

    async def invoke(
        self, messages: List[LLMMessage], model_name: Optional[str] = None, **kwargs
    ) -> str:
        """
        Send a request to the LLM API and get a response

        Args:
            messages: List of LLMMessage objects representing the conversation
            model_name: Optional model name to override the default
            **kwargs: Additional parameters to pass to the API call

        Returns:
            The content of the assistant's response
        """
        # Use the default model if no model_name is provided
        model = model_name or self.model

        # Convert LLMMessage objects to dictionaries
        message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]

        # Send the request to the API
        response = await self.client.chat.completions.create(
            model=model, messages=message_dicts, **kwargs
        )

        # Return the content of the response
        return response.choices[0].message.content
