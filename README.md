# SousChef

Recipe management, meal planning, and grocery lists — all through Claude. Save recipes by dictating them or importing from a URL, plan meals for the week, and let Claude auto-generate the shopping list. Your data lives locally in `~/.souschef/souschef.db`.

There's no separate app. Claude is the interface.

---

## Install (Claude Desktop, macOS)

Two clicks total. No terminal, no Python install, no git.

> **Heads up:** Claude Desktop's extensions and skills are managed in two different places, so SousChef ships as **two files**. Both are needed for the full experience. If you only install the first one, the tools will work but Claude won't follow SousChef's recipe-planning workflow as smoothly.

### Step 1 — Install the SousChef extension (`.mcpb`)

This gives Claude the tools to read and write your recipes, plans, and grocery lists.

1. Download **`souschef.mcpb`** from the [latest release](https://github.com/AcceleratedIndustries/SousChef/releases/latest).
2. Double-click the file. Claude Desktop opens an install prompt.
3. Click **Install**.

**Verify it worked:**

- **UI check.** Open Claude Desktop → **Settings → Extensions**. You should see *SousChef* listed and toggled on.
- **Functional check.** Open a new chat and say:
  > *What SousChef tools are available?*

  Claude should list tools like `recipe_add`, `plan_create`, `grocery_generate`, etc. If Claude says it doesn't see SousChef tools, the extension didn't load — check that it's enabled in Settings → Extensions.

- **End-to-end smoke test:**
  > *Save a test recipe called "Hello World" with one ingredient: water, 1 cup.*

  Claude should call `recipe_add` and report success with a recipe ID.

### Step 2 — Install the SousChef skill (`.zip`)

This teaches Claude *how* to use SousChef well — when to render visuals, how to tag recipes, how to suggest meals.

1. Download **`souschef-skill.zip`** from the same release.
2. In Claude Desktop, open **Customize → Skills**.
3. Click **+** (or **+ Create skill**).
4. Upload `souschef-skill.zip`.

**Verify it worked:**

- **UI check.** The *souschef* skill appears in your Skills list, toggled on.
- **Functional check.** Open a new chat and say:
  > *I want to plan meals for next week.*

  Claude should proactively reach for SousChef — calling `plan_suggest` to find candidate recipes, asking about dietary preferences, and creating a plan with `plan_create`. Without the skill, Claude will likely ask generic clarifying questions instead.

If the skill upload says "invalid skill" or similar, make sure the ZIP has the **`souschef/` folder as its root**, not a nested subfolder. The file structure inside the ZIP should be:

```
souschef/
└── SKILL.md
```

---

## Updating SousChef

Claude Desktop manages extension updates automatically when a new `souschef.mcpb` is published. To update the skill, download the latest `souschef-skill.zip` and re-upload it through Customize → Skills (the new version replaces the old).

---

## Where your data lives

| What | Where |
|---|---|
| Recipes, plans, grocery lists, chat history | `~/.souschef/souschef.db` (SQLite) |
| Recipe images downloaded from URLs | `~/.souschef/images/` |
| Rendered HTML views | `~/.souschef/output/` |

Override the directory with the `SOUSCHEF_DB_DIR` environment variable. Everything is local — no cloud sync, no telemetry.

---

## What you can do

Once installed, just ask Claude in natural language. A few examples:

- *Save my mom's lasagna recipe — it's two pounds of ground beef, ...*
- *Import this recipe: https://example.com/some-soup*
- *What can I make with chicken thighs and rice?*
- *Plan dinners for next week — keep it vegetarian.*
- *Generate a grocery list for that plan, doubled.*
- *Show me a printable view of the lasagna recipe.*
- *Mark olive oil and eggs as bought.*

---

## Troubleshooting

**"I can't see SousChef tools in this chat."**
Check Settings → Extensions and confirm SousChef is toggled on. Close and reopen the chat tab if you just installed it.

**"Claude calls the tools but doesn't tag recipes / render visuals / suggest meals."**
The skill probably isn't installed. See Step 2 above.

**"Where did my data go after I uninstalled?"**
Uninstalling the extension does not delete `~/.souschef/`. Reinstall and your recipes and plans come right back.

**"Can I use this with Claude Code instead of Claude Desktop?"**
Yes. The `.mcpb` is Desktop-specific, but the underlying MCP server can be configured manually in any MCP-aware client. See `CLAUDE.md` for developer setup.

---

## For developers

See [`CLAUDE.md`](CLAUDE.md) for project layout, build instructions, and how to run the CLI locally without packaging an `.mcpb`.

## License

MIT
