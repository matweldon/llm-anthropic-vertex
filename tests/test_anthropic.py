import json
import llm
import os
import pytest
from pydantic import BaseModel

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\xa6\x00\x00\x01\x1a"
    b"\x02\x03\x00\x00\x00\xe6\x99\xc4^\x00\x00\x00\tPLTE\xff\xff\xff"
    b"\x00\xff\x00\xfe\x01\x00\x12t\x01J\x00\x00\x00GIDATx\xda\xed\xd81\x11"
    b"\x000\x08\xc0\xc0.]\xea\xaf&Q\x89\x04V\xe0>\xf3+\xc8\x91Z\xf4\xa2\x08EQ\x14E"
    b"Q\x14EQ\x14EQ\xd4B\x91$I3\xbb\xbf\x08EQ\x14EQ\x14EQ\x14E\xd1\xa5"
    b"\xd4\x17\x91\xc6\x95\x05\x15\x0f\x9f\xc5\t\x9f\xa4\x00\x00\x00\x00IEND\xaeB`"
    b"\x82"
)

PROJECT_ID = 'dummy-project'
REGION = 'europe-west1'

@pytest.mark.vcr
def test_prompt():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    response = model.prompt("Two names for a pet pelican, be brief")
    assert str(response) == "1. **Petro**\n2. **Captain Beak**"
    response_dict = dict(response.response_json)
    response_dict.pop("id")  # differs between requests
    assert response_dict == {
        "content": [{"citations": None, "text": "1. **Petro**\n2. **Captain Beak**", "type": "text"}],
        "model": "claude-haiku-4-5-20251001",
        "role": "assistant",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "type": "message",
    }
    assert response.input_tokens == 17
    assert response.output_tokens == 20
    assert response.token_details is None


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_async_prompt():
    model = llm.get_async_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    conversation = model.conversation()
    response = await conversation.prompt("Two names for a pet pelican, be brief")
    assert await response.text() == "1. **Pouch**\n2. **Captain**"
    response_dict = dict(response.response_json)
    response_dict.pop("id")  # differs between requests
    assert response_dict == {
        "content": [{"citations": None, "text": "1. **Pouch**\n2. **Captain**", "type": "text"}],
        "model": "claude-haiku-4-5-20251001",
        "role": "assistant",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "type": "message",
    }
    assert response.input_tokens == 17
    assert response.output_tokens == 17
    assert response.token_details is None


EXPECTED_IMAGE_TEXT = (
    "# Red and Green\n\nThree words describing this image:\n"
    "\n1. **Red** - top rectangle\n2. **Green** - bottom rectangle\n3. **Rectangles** - shape/form"
)


@pytest.mark.vcr
def test_image_prompt():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    response = model.prompt(
        "Describe image in three words",
        attachments=[llm.Attachment(content=TINY_PNG)],
    )
    assert str(response) == EXPECTED_IMAGE_TEXT
    response_dict = response.response_json
    response_dict.pop("id")  # differs between requests
    assert response_dict == {
        "content": [{"citations": None, "text": EXPECTED_IMAGE_TEXT, "type": "text"}],
        "model": 'claude-haiku-4-5-20251001',
        "role": "assistant",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "type": "message",
    }

    assert response.input_tokens == 83
    assert response.token_details is None


@pytest.mark.vcr
def test_image_with_no_prompt():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    response = model.prompt(
        prompt=None,
        attachments=[llm.Attachment(content=TINY_PNG)],
    )
    assert str(response) == (
        "# Color Analysis\n\nThis image shows two colored rectangles:\n"
        "\n1. **Top rectangle**: Red (#FF0000)"
        "\n2. **Bottom rectangle**: Bright Green/Lime Green (#00FF00)\n"
        "\nThese are primary colors in the RGB color model, displayed as solid blocks with white space between them."
    )



class Dog(BaseModel):
    name: str
    age: int
    bio: str


@pytest.mark.vcr
def test_schema_prompt():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION

    response = model.prompt("Invent a good dog", schema=Dog)
    dog = json.loads(response.text())
    assert dog == {
        "name": "Max",
        "age": 4,
        "bio": ("Max is a charming Golden Retriever with a heart of pure gold."
        " Known for his boundless energy, he loves long hikes, swimming in lakes, and playing fetch with an enthusiasm that never seems to fade."
        " Max has an incredible ability to sense when someone needs comfort and is always ready with a wagging tail and a gentle nudge."
        " He's got a silly sense of humor and loves to make his human family laugh with his goofy antics."
        " Despite his playful nature, Max is incredibly well-behaved, obedient, and has completed advanced obedience training."
        " He's the kind of dog who greets every person and other dog he meets as a best friend."
        " Max thrives on companionship and adventures, and his loyalty is unwavering."),
    }



@pytest.mark.vcr
def test_prompt_with_prefill_and_stop_sequences():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    response = model.prompt(
        "Very short function describing a pelican",
        prefill="```python",
        stop_sequences=["```"],
        hide_prefill=True,
    )
    text = response.text()
    assert text == (
        """
def pelican():
    \"\"\"A large water bird with a distinctive expandable throat pouch.\"\"\"
    return {
        "body": "Large, heavy-bodied",
        "beak": "Long and straight",
        "pouch": "Expandable throat for catching fish",
        "habitat": "Coastal and inland waters",
        "diet": "Fish"
    }
"""
    )


@pytest.mark.vcr
def test_thinking_prompt():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id = PROJECT_ID
    model.region = REGION
    conversation = model.conversation()
    response = conversation.prompt(
        "Two names for a pet pelican, be brief", thinking=True,
    )
    assert response.text() ==   "1. **Pouch** — references their iconic bill pouch\n2. **Captain** — nautical and playful for a water-loving bird"
    response_dict = dict(response.response_json)
    assert response_dict['model'] == "claude-haiku-4-5-20251001"
    assert response_dict['stop_reason'] == 'end_turn'
    assert response_dict['stop_sequence'] is None
    content_types = [turn['type'] for turn in response_dict['content']]
    assert content_types == ['thinking','text']
    assert response.input_tokens == 45
    assert response.token_details is None


@pytest.mark.vcr
def test_tools():
    model = llm.get_model("vertex-4.5-haiku")
    model.project_id=PROJECT_ID
    model.region=REGION
    names = ["Charles", "Sammy"]
    chain_response = model.chain(
        "Two names for a pet pelican",
        tools=[
            llm.Tool.function(lambda: names.pop(0), name="pelican_name_generator"),
        ],
    )
    text = chain_response.text()
    assert text == (
        " Here are two great names for a pet pelican:\n"
        "\n1. **Charles** - A distinguished and charming name for your feathered friend"
        "\n2. **Sammy** - A friendly and approachable name with a fun, casual feel\n"
        "\nBoth would make wonderful names for a pelican! "
        "Choose whichever feels like the best fit for your pet's personality. 🦆"
    )
    tool_calls = chain_response._responses[0].tool_calls()
    assert len(tool_calls) == 2
    assert all(call.name == "pelican_name_generator" for call in tool_calls)
    assert [
        result.output for result in chain_response._responses[1].prompt.tool_results
    ] == ["Charles", "Sammy"]
