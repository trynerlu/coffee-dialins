# coffee-dialins
Web app for easy coffee dial-in listing

## How to run

- **Live:** https://trynerlu.github.io/coffee-dialins/
- **Locally:** open `index.html` in a browser. There's nothing to install or build. It loads React and Babel from cdnjs, so it needs internet. In the app, go to **Settings → GitHub** and enter the owner, repo and a personal access token.
- **Data script:** `tools/dialin_api.py` adds and updates entries through the GitHub API (standard Python only):
  ```
  export GITHUB_TOKEN=$(gh auth token)   # uses your gh login, no token to paste
  python tools/dialin_api.py list
  python tools/dialin_api.py add entries.json --dry-run
  ```

## Logging coffees with Claude Code

Open a Claude Code session on this repo (terminal, desktop app, or your phone via Remote Control to the Mac session) and:

1. Send a bag photo plus your verdict, typed or dictated.
2. Claude reads the label, looks up the roaster's product page and shows a **draft card** with only the open questions.
3. Confirm, and Claude dry-runs, writes the entry with `tools/dialin_api.py`, and verifies the logbook with `check`.
4. The app picks it up on its next sync.

No token setup is needed: the script uses the logged-in GitHub CLI (`gh auth token`). Logbook entries go straight to `main`; any other change is discussed first and goes through a pull request. The full rules live in `CLAUDE.md`, and `schema.json` is the data contract.
