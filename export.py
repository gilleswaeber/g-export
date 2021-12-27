import json
import sqlite3
import sys
import time
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from multiprocessing.pool import ThreadPool
from pathlib import Path
from sys import stderr
from typing import Iterable, Mapping, Dict, Tuple, Optional

import pandas
import requests
from pandas import DataFrame
from steam.client import SteamClient  # noqa
from steam.steamid import SteamID
from steam.webapi import WebAPI
from tqdm import tqdm

from helpers import TmpFile, one_way_sync, read_json_gz_file, write_json_gz_file, split_chunks
from steam_info import Category

SCRIPT_DIR = Path(__file__).parent
DIST_DIR = SCRIPT_DIR / 'dist'
DIST_RES_DIR = DIST_DIR / 'res'
DIST_IMG_DIR = DIST_DIR / 'img'
CACHE_DIR = SCRIPT_DIR / 'cache'
RES_DIR = SCRIPT_DIR / 'res'
STEAM_DB_CACHE = CACHE_DIR / 'steamdb.json.gz'
REPORT_FILE = DIST_DIR / 'index.html'
DATA_DUMP_FILE = DIST_DIR / 'data.json.gz'
REPO_URL = 'https://git.romlig.ch/gilles/g-export'
KNOWN_PLATFORMS = {  # svg icon in res folder
    'epic', 'xboxone', 'steam', 'gog', 'uplay', 'origin', 'rockstar', 'battlenet', 'generic'
}


class ImageCache:
    def __init__(self):
        self._locations: Dict[str, Path] = {}

    def path(self, url: str) -> Path:
        if url not in self._locations:
            digest = sha256(url.encode("utf-8")).hexdigest()
            self._locations[url] = CACHE_DIR / digest[0] / digest[:2] / f'{digest}.webp'
        return self._locations[url]

    def rel_path(self, url: str) -> Path:
        return self.path(url).relative_to(CACHE_DIR)


def download_image(url: str):
    dest = IMAGE_CACHE.path(url)
    with TmpFile(dest) as dest_tmp:
        dest_tmp.write_bytes(requests.get(url).content)


IMAGE_CACHE = ImageCache()


def steam_ids(steam_id):
    s = SteamID(steam_id)
    return [
        s.as_32,
        s.as_64,
        s.as_steam2_zero,
        s.as_steam2,
        s.as_steam3
    ]


def create_parent_dirs(missing_images: Iterable[Path]):
    for f in set(p.parent for p in missing_images):
        f.mkdir(exist_ok=True, parents=True)


def run(*, gog_db, steam_id=None, steam_api_key=None, all_friends=False, friends=None):
    export_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    CACHE_DIR.mkdir(exist_ok=True)

    df = read_gog_database(gog_db)
    steam_db = get_steam_metadata(df)

    def get_steam_id(ids):
        for game_id in sorted(ids, key=lambda x: int(x)):
            if game_id in steam_db and steam_db[game_id] and not steam_db[game_id]['_missing_token']:
                return game_id
        return None

    def get_game_info(row):
        if row.steam_id:
            return steam_db[row.steam_id]
        return None

    unknown_categories = set()

    def get_categories(info):
        categories = set()
        if info is not None and 'category' in info['common']:
            for c in info['common']['category'].keys():
                try:
                    categories.add(Category(int(c.replace('category_', ''))))
                except:
                    if c not in unknown_categories:
                        print('Unknown Steam category', c.replace('category_', ''), file=stderr)
                        unknown_categories.add(c)
        return categories

    friends_info, game_friends = get_friends_info(all_friends, friends, steam_api_key, steam_id)

    df['steam_id'] = df['steam_ids'].apply(get_steam_id)
    df['info'] = df.apply(get_game_info, axis=1)
    df['categories'] = df['info'].apply(get_categories)
    df['icon_rel'] = df['icon'].apply(lambda x: IMAGE_CACHE.rel_path(x) if x else None)
    df['cover_rel'] = df['cover'].apply(lambda x: IMAGE_CACHE.rel_path(x) if x else None)

    friends_info['icon_rel'] = friends_info['icon'].apply(lambda x: IMAGE_CACHE.rel_path(x) if x else None)
    images = [*df['icon'].dropna(), *df['cover'].dropna(), *friends_info['icon'].dropna()]

    download_missing_images(images)

    DIST_DIR.mkdir(exist_ok=True)
    DIST_RES_DIR.mkdir(exist_ok=True)
    DIST_IMG_DIR.mkdir(exist_ok=True)
    one_way_sync(CACHE_DIR, DIST_IMG_DIR, (IMAGE_CACHE.rel_path(i) for i in images))
    one_way_sync(RES_DIR, DIST_RES_DIR, (f.relative_to(RES_DIR) for f in RES_DIR.iterdir() if f.is_file()))
    games_dump = [dict(
        title=row.title,
        icon=str('img' / row.icon_rel).replace('\\', '/') if row.icon else None,
        cover=str('img' / row.cover_rel).replace('\\', '/') if row.cover else None,
        platforms=row.platforms,
        categories=dict(
            single=Category.SINGLEPLAYER in row.categories,
            multi=Category.MULTIPLAYER in row.categories,
            coop=Category.COOP in row.categories or Category.ONLINE_COOP in row.categories,
            pvp=Category.PVP in row.categories or Category.ONLINE_PVP in row.categories
        ) if row.info else False,
        gameTime=row.game_time,
        lastPlayed=row.last_played,
        rating=row.rating,
        summary=row.summary,
        friends=list(sorted(set(f for r in row.all_releases for f in game_friends[r]))),
        steamId=row.steam_id,
        allReleases=row.all_releases,
    ) for row in df.itertuples()]
    friends_dump = {row.Index: dict(
        name=row.name,
        icon=str('img' / row.icon_rel).replace('\\', '/') if row.icon else None
    ) for row in friends_info.itertuples()}
    with TmpFile(REPORT_FILE) as r, r.open('wt', encoding='utf-8') as report:
        report.write(
            '<!DOCTYPE html>\n'
            '<html><head>\n'
            '<meta charset="utf-8"/>\n'
            '<meta rel="shortcut icon" href="res/p-generic.svg"/>\n'
            '<title>My Games</title>\n'
            '<script src="res/ag-grid-community.min.noStyle.js"></script>\n'
            '<script src="res/luxon.min.js"></script>\n'
            '<script>const data = '
        )
        write_json_gz_file(DATA_DUMP_FILE, dict(games=games_dump, friends=friends_dump))
        json.dump(games_dump, report)
        report.write(f';\n')
        report.write(f'const showFriends = {"true" if friends or all_friends else "false"};\n')
        report.write(f'const friendsInfo = ')
        json.dump(friends_dump, report)
        report.write(';')
        report.write(
            '</script>\n'
            '<script src="res/script.js"></script>\n'
            '<link rel="stylesheet" href="res/style.css">\n'
            '<link rel="stylesheet" href="res/ag-grid.css">\n'
            '<link rel="stylesheet" href="res/ag-theme-balham-dark.css">\n'
            '</head><body>\n'
            '<div id="gridContainer"><div id="myGrid" class="ag-theme-balham-dark"></div>\n'

            f'<div id="exportInfo">{df.shape[0]} games – '
            f'game list exported from GOG Galaxy using <a href="{REPO_URL}">g-export</a> – '
            f'{export_time}</div></div>\n'

            '<div id="details"><div id="background"><img width=48 height=48 alt=""/></div>'
            '<img id="cover" height=482 width=342/>'
            '<h1>My Games</h1><div id="summary"></div></div>\n'

            '</body>\n'
        )


def read_gog_database(path):
    print("Reading GOG database… ", end="")
    with sqlite3.connect(path) as con:
        query = '''
WITH l AS (SELECT releaseKey, "type" t, "value" v
FROM ProductPurchaseDates links
JOIN GamePieces gp ON links.gameReleaseKey = gp.releaseKey
JOIN GamePieceTypes gpt ON gp.gamePieceTypeId = gpt.id),
r AS (SELECT releaseKey,
SUBSTR(releaseKey, 0, INSTR(releaseKey, '_')) platform,
MIN(CASE WHEN t = 'title' THEN json_extract(v, '$.title') END) AS title,
MAX(CASE WHEN t = 'myRating' THEN json_extract(v, '$.myRating') END) AS rating,
MIN(CASE WHEN t = 'allGameReleases' THEN v END) AS allGameReleases,
MAX(CASE WHEN t = 'originalImages' THEN v END) AS images,
MAX(CASE WHEN t = 'meta' THEN v END) AS meta,
MAX(CASE WHEN t = 'summary' THEN json_extract(v, '$.summary') END) AS summary
FROM l
GROUP BY releaseKey),
steam_releases AS (SELECT allGameReleases, NULLIF(CAST(SUBSTR(json_each.value, 7) AS INTEGER), 0) steamRelease FROM
r, json_each(r.allGameReleases, '$.releases')
WHERE json_each.value LIKE 'steam%')
SELECT
title,
SUM(times.minutesInGame) game_time,
MAX(lastPlayedDate) last_played,
IFNULL(MAX(rating), 0) rating,
MAX(summary) summary,
GROUP_CONCAT(DISTINCT platform) platforms,
json_extract(MAX(images), '$.squareIcon') icon,
json_extract(MAX(images), '$.verticalCover') cover,
GROUP_CONCAT(DISTINCT steamRelease) steam_ids,
json_extract(allGameReleases, '$.releases') all_releases
FROM r
LEFT JOIN steam_releases USING (allGameReleases)
LEFT JOIN GameTimes times USING (releaseKey)
LEFT JOIN LastPlayedDates lastPlayed ON releaseKey = lastPlayed.gameReleaseKey
LEFT JOIN ReleaseProperties prop USING (releaseKey)
LEFT JOIN ProductPurchaseDates purchase ON releaseKey = purchase.gameReleaseKey
LEFT JOIN UserReleaseProperties userProps USING (releaseKey)
GROUP BY allGameReleases
HAVING IFNULL(MAX(prop.isVisibleInLibrary), 1) > 0 AND IFNULL(MAX(prop.isDlc), 0) < 1 AND IFNULL(MAX(userProps.isHidden), 0) < 1
-- AND NOT (Platforms = 'xboxone' AND game_time = 0 AND last_played IS NULL)  -- Xbox Game Pass
ORDER BY title
'''
        df = pandas.read_sql_query(query, con)
        df['steam_ids'] = df['steam_ids'].apply(lambda x: x.split(',') if x else [])
        df['all_releases'] = df['all_releases'].apply(lambda x: json.loads(x))
    print("done")
    return df


def get_steam_metadata(games_df):
    # Retrieve missing Steam metadata
    if STEAM_DB_CACHE.is_file():
        steam_db = read_json_gz_file(STEAM_DB_CACHE)
    else:
        steam_db = {}
    if 'apps' not in steam_db:
        steam_db['apps'] = {}
    missing_apps = [int(a) for ids in games_df['steam_ids']
                    for a in ids if a not in steam_db]
    if len(missing_apps):
        print(f"Downloading Steam metadata for {len(missing_apps)} apps… ", end='')
        client = SteamClient()
        client.anonymous_login()
        steam_data = client.get_product_info(apps=missing_apps)
        retrieve_stamp = int(time.time())
        for a in missing_apps:
            if a not in steam_data['apps']:
                steam_data['apps'][str(a)] = False  # invalid app number
            else:
                steam_data['apps'][a]['retrieved'] = retrieve_stamp
        steam_db.update((str(k), v) for k, v in steam_data['apps'].items())
        write_json_gz_file(STEAM_DB_CACHE, steam_db)
        print("done")
    return steam_db


def get_friends_info(all_friends: bool, friends: Optional[Iterable[str]],
                     steam_api_key: Optional[str], steam_id: Optional[str]) -> Tuple[DataFrame, Mapping[str, list]]:
    game_friends = defaultdict(list)
    friends_info = {}
    if friends or all_friends:
        my_id = SteamID(steam_id)
        if not my_id.is_valid():
            my_id = SteamID.from_url(f'https://steamcommunity.com/id/{steam_id}')
        if my_id is None or not my_id.is_valid():
            raise ValueError('Failed to retrieve info for steam id', steam_id)

        print("Retrieve Steam friends list…", end=" ")
        api = WebAPI(steam_api_key)
        steam_friends = api.ISteamUser.GetFriendList_v1(steamid=my_id, relationship='friend')['friendslist']['friends']
        steam_friends_info = {}
        for chunk in split_chunks(steam_friends, 100):
            players = api.ISteamUser.GetPlayerSummaries_v2(
                steamids=','.join(f['steamid'] for f in chunk)
            )['response']['players']
            for p in players:
                steam_friends_info[p['steamid']] = p
        if all_friends:
            my_friends = steam_friends
        else:
            friends_filter = set(friends)
            my_friends = [f for f in steam_friends
                          if f.steamid in friends_filter
                          or steam_friends_info[f.steamid]['personaname'] in friends_filter
                          or any(p in friends_filter for p in steam_ids(f['steamid']))
                          or steam_friends_info[f['steamid']].profileurl
                              .replace('https://steamcommunity.com/id/', '')
                              .rtrim('/') in friends_filter]
        print("done")
        for f in tqdm(my_friends, desc="Retrieve friends' game lists"):
            resp = api.IPlayerService.GetOwnedGames(
                steamid=f['steamid'], include_played_free_games=True, include_appinfo=False, appids_filter=[],
                include_free_sub=True)['response']
            if 'games' in resp:
                for a in resp['games']:
                    game_friends[f'steam_{a["appid"]}'].append(f'steam_{f["steamid"]}')
            else:
                tqdm.write(steam_friends_info[f['steamid']]['personaname'], 'does not share their game collection')
                steam_friends_info.pop(f['steamid'])
        friends_info.update((f'steam_{k}', dict(name=info['personaname'], icon=info['avatar'], platform='steam'))
                            for k, info in steam_friends_info.items())
    friends_info = DataFrame.from_dict(friends_info, 'index')
    return friends_info, game_friends


def download_missing_images(images: Iterable[str]):
    # Download missing images
    missing_images = [i for i in set(images) if not IMAGE_CACHE.path(i).exists()]
    if len(missing_images):
        print("Downloading missing images…")
        create_parent_dirs(IMAGE_CACHE.path(url) for url in missing_images)
        with ThreadPool(4) as pool:
            list(tqdm(pool.imap(download_image, missing_images),
                      desc='Downloading images', total=len(missing_images)))


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Export a game list from GOG Galaxy as an HTML page.\n'
                    'The HTML page is located in the dist folder as well as all resources (e.g. game covers).',
        epilog='When using --friends or --all-friends, both --steam-id and --steam-api-key must be set. '
               'Only Steam friends are supported, their game collections must be public.')
    parser.add_argument(
        '--steam-id', help='Steam ID or vanity URL name (appears in the url of the profile page)')
    parser.add_argument('--steam-api-key',
                        help='Steam Web API key, get one here: https://steamcommunity.com/dev/apikey')
    parser.add_argument('--all-friends', action='store_true',
                        help='Show games owned by all friends')
    parser.add_argument('--friends', nargs='+',
                        help='Show games owned by listed friends, Steam ID or vanity URL name or pseudonym')
    parser.add_argument('--gog-db', default=r'C:\ProgramData\GOG.com\Galaxy\storage\galaxy-2.0.db',
                        help='Location of the GOG Galaxy database file galaxy-2.0.db')
    arg = parser.parse_args()
    if arg.friends and arg.all_friends:
        print('--friends cannot be used with --all-friends', file=stderr)
        sys.exit(1)
    if (arg.friends or arg.all_friends) and not (arg.steam_id and arg.steam_api_key):
        print('When using --friends or --all-friends, both --steam-id and --steam-api-key must be set', file=stderr)
        sys.exit(1)
    run(**vars(arg))
