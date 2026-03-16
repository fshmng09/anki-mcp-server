from __future__ import annotations

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("anki")

ANKI_CONNECT_URL = "http://localhost:8765"

# Model/field name mappings for EN and JA Anki
_BASIC_CANDIDATES = ["Basic", "基本"]
_CLOZE_CANDIDATES = ["Cloze", "穴埋め問題"]
_BASIC_FIELD_MAP = {
    "Basic": ("Front", "Back"),
    "基本": ("表面", "裏面"),
}
_CLOZE_FIELD_MAP = {
    "Cloze": ("Text", "Extra"),
    "穴埋め問題": ("Text", "裏面追記"),
}

_resolved: dict[str, str] = {}


async def _resolve_model(model_type: str) -> str:
    """Resolve the actual model name available in Anki."""
    if model_type in _resolved:
        return _resolved[model_type]
    models = await anki_request("modelNames")
    candidates = _BASIC_CANDIDATES if model_type == "basic" else _CLOZE_CANDIDATES
    for name in candidates:
        if name in models:
            _resolved[model_type] = name
            return name
    raise Exception(
        f"No suitable {model_type} model found. Available: {models}"
    )


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
    model = await _resolve_model("basic")
    front_field, back_field = _BASIC_FIELD_MAP[model]
    await anki_request("createDeck", deck=deck)
    note_id = await anki_request(
        "addNote",
        note={
            "deckName": deck,
            "modelName": model,
            "fields": {front_field: front, back_field: back},
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
    model = await _resolve_model("cloze")
    text_field, extra_field = _CLOZE_FIELD_MAP[model]
    await anki_request("createDeck", deck=deck)
    note_id = await anki_request(
        "addNote",
        note={
            "deckName": deck,
            "modelName": model,
            "fields": {text_field: text, extra_field: extra},
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
