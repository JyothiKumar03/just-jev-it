"""Toy support-ticket agent for smoke-testing just-jev-it."""

from typesafe_sdk import Choice, TypeSafeClient


def classify_priority(ticket_text, client: TypeSafeClient):
    """Classify a ticket's priority as low/medium/high using Jev."""
    response = client.system_one(
        state={"ticket": ticket_text},
        questions={
            "priority": Choice(
                instructions="What priority should this support ticket be assigned?",
                criteria={
                    "low": "Minor issue, no urgency",
                    "medium": "Normal issue, standard turnaround",
                    "high": "Urgent, blocking, or high-impact issue",
                },
            ),
        },
    )
    return response.choices["priority"].choice


def draft_reply(ticket_text, llm):
    """Draft a free-text reply to the customer. Not a classification task."""
    prompt = f"Write a helpful, empathetic reply to this support ticket:\n{ticket_text}"
    return llm.complete(prompt)
