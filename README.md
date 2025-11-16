# llm-anthropic-vertex

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/matweldon/llm-anthropic-vertex/blob/main/LICENSE)

LLM access to Anthropic Claude models via Google Vertex AI

This is a fork of [llm-anthropic](https://github.com/simonw/llm-anthropic) adapted to work with Google Vertex AI's Anthropic integration. It provides access to all Claude models (3, 3.5, 3.7, 4, and 4.5) through Google Cloud.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

### From source
```bash
cd llm-anthropic-vertex
llm install -e .
```



## Prerequisites

1. A Google Cloud project with the Vertex AI API enabled
2. Appropriate IAM roles on your user account (or a Service Account with appropriate IAM roles, see below)
3. Each Anthropic model to be used must be individually enabled in your project's Vertex AI model garden console
4. Install the `gcloud` SDK

### Set up utility
This plugin includes a setup utility to help you configure your Google Cloud project and region. After installing the plugin, run it like this:
```bash
llm-anthropic-vertex-setup
```
This will guide you through selecting a Google Cloud project and region, and set the appropriate environment variables. Note that the utility does not modify your shell profile, so you will need to add the environment variables it suggests to your shell profile manually.

## Authentication

This plugin uses Google Cloud credentials instead of API keys. Set up authentication using one of these methods:

### Method 1: Application Default Credentials (Recommended for local development)
```bash
gcloud auth application-default login
```

### Method 2: Service Account
1. Create a service account with Vertex AI permissions
2. Download the service account JSON key file
3. Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## Configuration

Set your Google Cloud project ID and region using environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_REGION="europe-west1"  # default
```

Alternatively, you can use:
```bash
export GCP_PROJECT="your-project-id"
export GCP_REGION="europe-west1"
```



## Usage from the command line

Run `llm models list` to list the models, and `llm models --options` to include a list of their options.

Run prompts like this:
```bash
llm -m vertex-sonnet-4.5 'Fun facts about Newport, Wales'
llm -m anthropic-vertex/claude-opus-4-1@20250805 'Fun facts about national statistics'
```
Image attachments are supported too:
```bash
llm -m vertex-sonnet-4.5 'describe this image' -a https://static.simonwillison.net/static/2024/pelicans.jpg
llm -m vertex-haiku-4.5 'extract text' -a page.png
```
The Claude 3.5 and 4 models can handle PDF files:
```bash
llm -m vertex-sonnet-4.5 'extract text' -a page.pdf
```
Anthropic's models support [schemas](https://llm.datasette.io/en/stable/schemas.html). Here's how to use Claude 4 Sonnet to invent a dog:

```bash
llm -m vertex-sonnet-4.5 --schema 'name,age int,bio: one sentence' 'invent a surprising dog'
```
Example output:
```json
{
  "name": "Whiskers the Mathematical Mastiff",
  "age": 7,
  "bio": "Whiskers is a mastiff who can solve complex calculus problems by barking in binary code and has won three international mathematics competitions against human competitors."
}
```

## Usage from Python

Python code can access the models like this:
```python
import llm

model = llm.get_model("vertex-haiku-4.5")
model.project_id = 'your-project-id'
model.region = 'europe-west1'
print(model.prompt("Fun facts about chipmunks"))
```
Consult [LLM's Python API documentation](https://llm.datasette.io/en/stable/python-api.html) for more details.


## Extended reasoning with Claude 3.7 Sonnet and higher

Claude 3.7 introduced [extended thinking](https://www.anthropic.com/news/visible-extended-thinking) mode, where Claude can expend extra effort thinking through the prompt before producing a response.

Use the `-o thinking 1` option to enable this feature:

```bash
llm -m vertex-4.5-sonnet -o thinking 1 'Write a convincing speech to a high school about the importance of official statistics'
```
The chain of thought is not currently visible while using LLM, but it is logged to the database and can be viewed using this command:
```bash
llm logs -c --json
```
Or in combination with `jq`:
```bash
llm logs --json -c | jq '.[0].response_json.content[0].thinking' -r
```
By default up to 1024 tokens can be used for thinking. You can increase this budget with the `thinking_budget` option:
```bash
llm -m vertex-4.5-sonnet -o thinking_budget 32000 'Write a long speech about pelicans in French'
```

## Model options

The following options can be passed using `-o name value` on the CLI or as `keyword=value` arguments to the Python `model.prompt()` method:

- **max_tokens**: `int`

    The maximum number of tokens to generate before stopping

- **temperature**: `float`

    Amount of randomness injected into the response. Defaults to 1.0. Ranges from 0.0 to 1.0. Use temperature closer to 0.0 for analytical / multiple choice, and closer to 1.0 for creative and generative tasks. Note that even with temperature of 0.0, the results will not be fully deterministic.

- **top_p**: `float`

    Use nucleus sampling. In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by top_p. You should either alter temperature or top_p, but not both. Recommended for advanced use cases only. You usually only need to use temperature.

- **top_k**: `int`

    Only sample from the top K options for each subsequent token. Used to remove 'long tail' low probability responses. Recommended for advanced use cases only. You usually only need to use temperature.

- **user_id**: `str`

    An external identifier for the user who is associated with the request

- **prefill**: `str`

    A prefill to use for the response

- **hide_prefill**: `boolean`

    Do not repeat the prefill value at the start of the response

- **stop_sequences**: `array, str`

    Custom text sequences that will cause the model to stop generating - pass either a list of strings or a single string

- **cache**: `boolean`

    Use Anthropic prompt cache for any attachments or fragments

- **thinking**: `boolean`

    Enable thinking mode

- **thinking_budget**: `int`

    Number of tokens to budget for thinking

The `prefill` option can be used to set the first part of the response. To increase the chance of returning JSON, set that to `{`:

```bash
llm -m vertex-sonnet-4.5 'Fun data about pelicans' \
  -o prefill '{'
```
If you do not want the prefill token to be echoed in the response, set `hide_prefill` to `true`:

```bash
llm -m vertex-4.5-haiku 'Short python function describing a pelican' \
  -o prefill '```python' \
  -o hide_prefill true \
  -o stop_sequences '```'
```
This example sets `` ``` `` as the stop sequence, so the response will be a Python function without the wrapping Markdown code block.

To pass a single stop sequence, send a string:
```bash
llm -m vertex-sonnet-4.5 'Fun facts about pelicans' \
  -o stop-sequences "beak"
```
For multiple stop sequences, pass a JSON array:

```bash
llm -m vertex-sonnet-4.5 'Fun facts about pelicans' \
  -o stop-sequences '["beak", "feathers"]'
```

When using the Python API, pass a string or an array of strings:

```python
response = llm.query(
    model="vertex-sonnet-4.5",
    query="Fun facts about pelicans",
    stop_sequences=["beak", "feathers"],
)
```

## Regional Availability

Claude models are available in different Vertex AI regions. Not all models are available in all regions. If in doubt, try setting the region to 'global'.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment and install dependencies using uv:
```bash
cd llm-anthropic-vertex
uv venv
source .venv/bin/activate
uv sync --extra test
```

Alternatively, if you have an existing virtual environment:
```bash
cd llm-anthropic-vertex
llm install -e '.[test]'
```

Make sure you have Google Cloud credentials configured as described in the Authentication section above.

To run the tests:
```bash
pytest
```

This project uses [pytest-recording](https://github.com/kiwicom/pytest-recording) to record Vertex AI API responses for the tests. Updating the stored responses is not recommended unless you're very patient because the API calls contain sensitive credentials. Please log an issue for advice.



## Credits

This plugin is a fork of [llm-anthropic](https://github.com/simonw/llm-anthropic) by Simon Willison, adapted to work with Google Vertex AI by Mat Weldon. All credit for the original architecture and implementation goes to Simon Willison.

The module was initially updated by [Claude Code](https://www.claude.com/product/claude-code). All of the changes were checked by me, and the tests were validated, updated and rerun by me.
