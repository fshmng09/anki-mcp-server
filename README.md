# anki-mcp-server

Anki に直接カードを追加できる MCP サーバー。AnkiConnect 経由で動作する。

## セットアップ

### 1. AnkiConnect アドオンをインストール

Anki を開き、`ツール` → `アドオン` → `新たにアドオンを取得` でコード `2055492159` を入力してインストール。Anki を再起動する。

### 2. Claude Desktop に設定

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anki": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/anki-mcp-server", "anki-mcp-server"]
    }
  }
}
```

### 3. Claude Code に設定

```bash
claude mcp add anki -- uv run --directory /path/to/anki-mcp-server anki-mcp-server
```

## 使用可能なツール

| ツール | 説明 |
|---|---|
| `add_card` | Basic（表/裏）カードを追加 |
| `add_cloze` | 穴埋め（Cloze）カードを追加 |
| `list_decks` | デッキ一覧を取得 |
| `create_deck` | デッキを作成 |
| `search_cards` | カードを検索 |

## 使用例

> 「民法177条の背信的悪意者排除論の規範、Ankiに入れて」

→ `add_cloze` で `予備試験::民法` に登録:

```
{{c1::背信的悪意者}}は民法177条の「第三者」から{{c2::除外}}される
```

> 「"hallucination" の意味をAnkiに追加して」

→ `add_card` で `English::Applied AI Engineer` に登録

## 前提条件

- Anki が起動していること（AnkiConnect は Anki のプロセス内で動作する）
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
