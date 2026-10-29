import argparse
import json
import os
from pathlib import Path
from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
FAQ_PATH = Path(__file__).with_name("campus_faq.json")
INSTRUCTIONS = (
    "You are Orange Desk, an assistant for a FICTIONAL campus. "
    "For campus facts, use lookup_campus_faq and only state information from its output. "
    "If the tool has no answer, say so. Keep answers brief."
)
FAQ_TOOL = {
    "type": "function",
    "name": "lookup_campus_faq",
    "description": "Look up a topic in the fictional campus FAQ.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "enum": ["library", "it_support", "tutoring", "parking"],
            }
        },
        "required": ["topic"],
        "additionalProperties": False,
    },
}


def lookup_campus_faq(topic):
    data = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    return {
        "topic": topic,
        "found": topic in data,
        "answer": data.get(topic, "No FAQ entry found."),
    }


def basic_text(client, question):
    # TODO 1: basic generation
    response = client.responses.create(
        model=MODEL,
        instructions="You are a concise, helpful assistant.",
        input=question,
    )
    return response.output_text


def ask_with_tool(client, question, previous_response_id=None):
    request = {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "input": question,
        "tools": [FAQ_TOOL],
        "tool_choice": "required",
        "store": True,
    }
    # TODO 3: link this question to the earlier conversation turn
    if previous_response_id:
        request["previous_response_id"] = previous_response_id

    first = client.responses.create(**request)
    tool_results = []
    for item in first.output:
        if item.type == "function_call" and item.name == "lookup_campus_faq":
            # TODO 2a: run the tool locally and package its result
            args = json.loads(item.arguments)
            result = lookup_campus_faq(args["topic"])
            tool_results.append({
                "type": "function_call_output",
                "call_id": item.call_id,  # links the output to the model's request
                "output": json.dumps(result),
            })

    if not tool_results:
        raise RuntimeError("No tool results. Did you complete TODO 2a?")

    # TODO 2b: send the tool results back so the model can write the final answer
    second = client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=tool_results,
        previous_response_id=first.id,
        tool_choice="none",
        store=True,
    )
    return second.output_text, second.id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["basic", "tool", "followup"], default="tool")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY. See student handout or run offline_trace.py.")
    client = OpenAI()
    if args.mode == "basic":
        print(basic_text(client, "Explain an API in two sentences."))
    elif args.mode == "tool":
        answer, _ = ask_with_tool(client, "Where do I get IT support?")
        print(answer)
    else:
        answer, last_id = ask_with_tool(client, "Where do I get IT support?")
        print("Answer 1:", answer)
        answer_2, _ = ask_with_tool(client, "Which room was that again?", last_id)
        print("Answer 2:", answer_2)


if __name__ == "__main__":
    main()
 
