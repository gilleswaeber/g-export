g-export
========
Export a game list from GOG Galaxy as an HTML page.
The HTML page is located in the dist folder as well as all resources (e.g. game covers).

Example: https://srv.romlig.ch/games/

Requirements: Python 3.7+, Python packages: pandas requests steam tqdm:
```sh
python -m pip install pandas requests steam[client] tqdm
```

Example usage:
```sh
python ./export.py  # when GOG is installed, no friend games
python ./export.py --steam-id name --steam-api-key XXXXXXXXXXXXXXXXXXXXXXXX --all-friends
```

Usage: `python export.py [-h] [--steam-id STEAM_ID] [--steam-api-key STEAM_API_KEY] [--all-friends] [--friends FRIENDS]
[--gog-db GOG_DB]`

Optional arguments:
```
-h, --help            show the help message and exit
--steam-id STEAM_ID   Steam ID or vanity URL name (appears in the url of the profile page)
--steam-api-key STEAM_API_KEY
                      Steam Web API key, get one here: https://steamcommunity.com/dev/apikey
--all-friends         Show games owned by all friends
--friends FRIENDS     Show games owned by listed friends, comma-separated, Steam ID or vanity URL name or pseudonym
--gog-db GOG_DB       Location of the GOG Galaxy database file galaxy-2.0.db

When using --friends or --all-friends, both --steam-id and --steam-api-key must be set. Only Steam friends are
supported, their game collections must be public.
```

© Gilles Waeber 2022
