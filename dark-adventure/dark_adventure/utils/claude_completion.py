""" generates episode text... you probably want to modify some things, like prompt and options, for your case """
import anthropic
from typing import Optional


def get_claude_completion(
        prompt: str,
        api_key: str,
        max_tokens: Optional[int] = 30000,      # 15000
        temperature: Optional[float] = 1.0,     # 0.7
        # model: str = "claude-haiku-4-5-20251001"
        model: str = "claude-opus-4-5-20251101"
        # model: str = "claude-3-7-sonnet-20250219"
        # model: str = "claude-3-5-haiku-20241022"
) -> str:
    """
    Get a completion from Claude using the Anthropic API.

    Args:
        prompt (str): The input prompt to send to Claude
        api_key (str): Your Anthropic API key
        max_tokens (int, optional): Maximum number of tokens in the response. Defaults to 1000
        temperature (float): higher = more creative, try range 0.2..1.0
        model (str, optional): The Claude model to use.

    Returns:
        str: Claude's response text

    Raises:
        anthropic.APIError: If there's an error communicating with the API
    """
    # Initialize the Anthropic client
    client = anthropic.Client(api_key=api_key)

    try:
        # Create a streaming message with the prompt
        with client.messages.stream(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system="You are a script generator that delivers complete responses without interrupting to ask if the user wants you to continue. Always provide the entire requested content without breaking for confirmation.",
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            response = stream.get_final_message()

        # Return the response text
        return response.content[0].text

    except anthropic.APIError as e:
        print(f"Error calling Claude API: {str(e)}")
        raise