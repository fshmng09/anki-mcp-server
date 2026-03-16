from __future__ import annotations

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("anki")

ANKI_CONNECT_URL = "http://localhost:8765"


async def anki_request(action: str, **params):
    """Send a request to AnkiConnect."""
    try:
        async with httpx.AsyncClient() as client:
            payload: dict = {"action": action, "version": 6}
            if params:
                payload["params"] = params
            response = await client.post(
                ANKI_CONNECT_URL, json=payload, timeout=10.0
            )
            result = response.json()
            if result.get("error"):
                raise Exception(result["error"])
            return result.get("result")
    except httpx.ConnectError:
        raise Exception(
            "AnkiConnect に接続できません。"
            "Anki が起動していること、AnkiConnect アドオン (2055492159) が"
            "インストールされていることを確認してください。"
        )


@mcp.tool()
async def add_card(
    deck: str,
    front: str,
    back: str,
    tags: list[str] | None = None,
) -> str:
    """Add a basic (front/back) flashcard to Anki.

    Args:
        deck: Deck name (e.g. "予備試験::民法"). Created automatically if not exists.
        front: Front side of the card (question). Supports HTML.
        back: Back side of the card (answer). Supports HTML.
        tags: Optional tags (e.g. ["短答", "規範"]).
    """
    await anki_request("createDeck", deck=deck)
    note_id = await anki_request(
        "addNote",
        note={
            "deckName": deck,
            "modelName": "Basic",
            "fields": {"Front": front, "Back": back},
            "tags": tags or [],
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
            },
        },
    )
    return f"Card added to '{deck}' (note id: {note_id})"


@mcp.tool()
async def add_cloze(
    deck: str,
    text: str,
    extra: str = "",
    tags: list[str] | None = None,
) -> str:
    """Add a cloze (fill-in-the-blank) card to Anki.

    Use {{c1::word}} syntax to create blanks.
    Multiple clozes: {{c1::word1}} ... {{c2::word2}}.

    Example: "{{c1::背信的悪意者}}は民法177条の「第三者」から{{c2::除外}}される"

    Args:
        deck: Deck name (e.g. "予備試験::憲法"). Created automatically if not exists.
        text: Card text with cloze deletions.
        extra: Optional extra info shown on the back after answering.
        tags: Optional tags (e.g. ["論文", "規範"]).
    """
    await anki_request("createDeck", deck=deck)
    note_id = await anki_request(
        "addNote",
        note={
            "deckName": deck,
            "modelName": "Cloze",
            "fields": {"Text": text, "Extra": extra},
            "tags": tags or [],
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
            },
        },
    )
    return f"Cloze card added to '{deck}' (note id: {note_id})"


@mcp.tool()
async def list_decks() -> str:
    """List all Anki decks."""
    decks = await anki_request("deckNames")
    return "\n".join(sorted(decks))


@mcp.tool()
async def create_deck(name: str) -> str:
    """Create a new Anki deck.

    Args:
        name: Deck name. Use :: for hierarchy (e.g. "予備試験::民法").
    """
    deck_id = await anki_request("createDeck", deck=name)
    return f"Deck '{name}' created (id: {deck_id})"


@mcp.tool()
async def search_cards(query: str) -> str:
    """Search for cards in Anki.

    Args:
        query: AnkiConnect search query. Examples:
            - "deck:予備試験::民法" (cards in a deck)
            - "tag:規範" (cards with a tag)
            - "背信的悪意者" (cards containing text)
            - "deck:予備試験 tag:短答" (combine conditions)
    """
    note_ids = await anki_request("findNotes", query=query)
    if not note_ids:
        return "No cards found."

    notes_info = await anki_request("notesInfo", notes=note_ids[:20])
    results = []
    for note in notes_info:
        fields = {k: v["value"] for k, v in note["fields"].items()}
        tags = ", ".join(note["tags"]) if note["tags"] else ""
        field_str = " | ".join(
            f"{k}: {v[:100]}" for k, v in fields.items() if v
        )
        tag_part = f" [{tags}]" if tags else ""
        results.append(f"- {note['noteId']}{tag_part} {field_str}")

    total = len(note_ids)
    shown = min(total, 20)
    header = f"Found {total} cards"
    if total > shown:
        header += f" (showing first {shown})"
    return header + ":\n" + "\n".join(results)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
