# Finder Enrichment AI Client

A lightweight Python package for managing AI API calls to various providers. Currently supports Google Gemini AI with more providers coming soon.

## Features

- **Lightweight**: No heavy dependencies, just HTTP requests
- **Simple**: Easy-to-use interface for AI API calls
- **Extensible**: Designed to support multiple AI providers
- **Configurable**: Support for both environment variables and direct API key passing

## Installation

```bash
pip install finder-enrichment-ai-client
```

## Quick Start

### Google Gemini AI

```python
from finder_enrichment_ai_client import GoogleAIClient

# Initialize with environment variable
client = GoogleAIClient()

# Or initialize with direct API key
client = GoogleAIClient(api_key="your-api-key-here")

# Generate text
response = client.generate_content("Hello! How are you?")
if response['success']:
    print(response['text'])
else:
    print(f"Error: {response['error']}")

# Analyze image
response = client.analyze_image(
    image_url="https://example.com/image.jpg",
    prompt="Describe this image"
)
if response['success']:
    print(response['text'])
```

## Environment Variables

Set `GOOGLE_GEMINI_API_KEY` in your environment:

```bash
export GOOGLE_GEMINI_API_KEY="your-api-key-here"
```

## API Reference

### GoogleAIClient

#### Methods

- `generate_content(prompt, model=None, temperature=0.7, max_tokens=1000)`: Generate text content
- `analyze_image(image_url, prompt, model=None)`: Analyze images with text prompts
- `set_model(model)`: Change the default model
- `set_temperature(temperature)`: Set the default temperature (0.0 to 1.0)
- `get_available_models()`: Get list of available models

#### Response Format

All methods return a dictionary with:
- `success`: Boolean indicating if the call was successful
- `text`: Generated text (if successful)
- `raw_response`: Full API response
- `error`: Error message (if not successful)

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Format code
black .
isort .
```

## License

MIT License
