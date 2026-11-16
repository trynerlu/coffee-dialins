# coffee-dialins
Web app for easy coffee dial-in listing

## How to run

- **Live:** https://trynerlu.github.io/coffee-dialins/
- **Locally:** open `index.html` in a browser. There's nothing to install or build. It loads React and Babel from cdnjs, so it needs internet. In the app, go to **Settings → GitHub** and enter the owner, repo and a personal access token.
- **Data script:** `tools/dialin_api.py` adds and updates entries through the GitHub API (standard Python only):
  ```
  export GITHUB_TOKEN=...
  python tools/dialin_api.py list
  python tools/dialin_api.py add entries.json --dry-run
  ```
