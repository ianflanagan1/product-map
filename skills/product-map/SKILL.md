---
name: product-map
description: Build or update an app's product map, the guide to its pages and messages that colleagues' problem reports are written against. product-map reads the code; Claude only writes a short plain-words description of each page or action that's new or changed since the last build.
disable-model-invocation: true
allowed-tools: Bash(command -v product-map), Bash(echo "exit $?"), Bash(product-map pending:*), Bash(product-map describe:*), Bash(product-map build:*), Bash(grep *), Bash(ls *), Read, Grep, Glob
---

# Product map

Build the product map of the app in the folder named after the skill's name, or the current folder, with the `product-map` command. The command reads everything from the code; your only part is describing what's waiting for a description.

Output of `command -v product-map`, captured when this skill loaded:

```
!`command -v product-map; echo "exit $?"`
```

If the block above still shows the command rather than its output, run `command -v product-map` yourself. If it isn't found, reply `⚠️ product-map isn't installed.`, then that it's set up as product-map's README describes, and stop.

## What's waiting

Run `product-map pending <dir>`. When it ends `➖ Every page and action is described.`, go on to Build. Otherwise it prints each one waiting as JSON: its key, and its facts as read from the code.

## Describe

For each one waiting, write a description for a colleague who uses the app every day but has never seen its code, reading it to report a problem:

- A few sentences, at most 500 characters: what it's for, how people get to it, and what happens when they use it. Use the words on its screens, from its facts.
- Name no code: no files, classes, functions, variables, database tables or `/api/` addresses. The facts' notes are what developers wrote in the code: use them to understand it, never quote them.
- An action, such as `action:DELETE /account`, also needs a title naming what people do, as they'd say it: `Deleting your account`, not `DELETE /account`.
- A page with no address of its own is shown after something else happens: say what, if its facts or the code show it.
- When the facts don't make it clear, read the code they come from, with the Read tool, and the Grep and Glob tools or, where you don't have those, `grep` and `ls` commands; nothing else that runs in a shell. State only what the facts or the code show; when you can't tell, say less rather than guess.

Then give them all at once, each under a `## ` line with its key, an action's title on a `Title: ` line after it:

```sh
product-map describe <dir> <<'EOF'
## page:favs
Your saved favourites, page by page. ...

## action:DELETE /account
Title: Deleting your account
Pressing Delete Account on the Account page ...
EOF
```

Never put a line that is only `EOF` in a description.

When it stops with ⚠️ naming descriptions it didn't accept, fix those and give them all again.

## Build

Run `product-map build <dir>`.

## Output

Reply with `product-map build`'s output as it is: `✅ Built the product map.` and its path, or `➖ The product map is up to date.` After ✅, one line naming how many pages and actions you described, if any. After a ⚠️ or ❌ from any `product-map` command you can't resolve as above, pass it on, then one short line on the cause and the fix you propose.
