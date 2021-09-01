from steam.client import SteamClient  # noqa

import json
import sqlite3
import sys
from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha256
from itertools import chain
from multiprocessing.pool import ThreadPool
from collections import defaultdict
from pathlib import Path
from sys import stderr

import pandas
import requests
from steam.steamid import SteamID
from steam.webapi import WebAPI
from tqdm import tqdm

from helpers import TmpFile, one_way_sync, read_json_gz_file, write_json_gz_file, split_chunks
from steam_info import Category

SCRIPT_DIR = Path(__file__).parent
DIST_DIR = SCRIPT_DIR / 'dist'
CACHE_DIR = SCRIPT_DIR / 'cache'
RES_DIR = SCRIPT_DIR / 'res'
STEAM_DB_CACHE = CACHE_DIR / 'steamdb.json.gz'
REPORT_FILE = DIST_DIR / 'index.html'


def steam_ids(steam_id):
    s = SteamID(steam_id)
    return [
        s.as_32,
        s.as_64,
        s.as_steam2_zero,
        s.as_steam2,
        s.as_steam3
    ]


def run(*, gog_db, steam_id=None, steam_api_key=None, all_friends=False, friends=None):
    with sqlite3.connect(gog_db) as con:
        query = '''
WITH l AS (SELECT releaseKey, "type" t, "value" v
FROM GameLinks
JOIN GamePieces gp USING (releaseKey)
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

    df['steam_ids'] = df['steam_ids'].apply(
        lambda x: x.split(',') if x else [])
    df['all_releases'] = df['all_releases'].apply(lambda x: json.loads(x))

    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir()
    images = []
    images.extend(df['icon'].dropna())
    images.extend(df['cover'].dropna())

    # Download missing images
    missing_images = [
        i for i in images if not image_cache_location(i).exists()]
    if len(missing_images):
        print("Downloading missing images…")
        with ThreadPool(4) as pool:
            list(tqdm(pool.imap(download_image, missing_images),
                      desc='Downloading images', total=len(missing_images)))

    # Retrieve missing Steam metadata
    if STEAM_DB_CACHE.is_file():
        steam_db = read_json_gz_file(STEAM_DB_CACHE)
    else:
        steam_db = {}
    missing_apps = [int(a) for ids in df['steam_ids']
                    for a in ids if a not in steam_db]
    if len(missing_apps):
        print(f"Downloading metadata from Steam for {len(missing_apps)} apps…")
        client = SteamClient()
        client.anonymous_login()
        steam_data = client.get_product_info(apps=missing_apps)
        for a in missing_apps:
            if a not in steam_data['apps']:
                steam_db['apps'][a] = False  # invalid app number
        steam_db.update(**{str(k): v for k, v in steam_data['apps'].items()})
        write_json_gz_file(STEAM_DB_CACHE, steam_db)

    def get_steam_info(row):
        for steam_id in sorted(row.steam_ids, key=lambda x: int(x)):
            if steam_id in steam_db and steam_db[steam_id] and not steam_db[steam_id]['_missing_token']:
                return steam_db[steam_id]
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
                        print('Unknown Steam category', c.replace(
                            'category_', ''), file=stderr)
                        unknown_categories.add(c)
        return categories

    game_friends = defaultdict(list)
    friends_info = {}
    if friends or all_friends:
        my_id = SteamID(steam_id)
        if not my_id.is_valid():
            my_id = SteamID.from_url(
                f'https://steamcommunity.com/id/{steam_id}')
        if my_id is None or not my_id.is_valid():
            raise ValueError('Failed to retrieve info for steam id', steam_id)

        api = WebAPI(steam_api_key)
        my_friends = api.ISteamUser.GetFriendList_v1(
            steamid=my_id, relationship='friend')['friendslist']['friends']
        steam_friends_info = {}
        for chunk in split_chunks(my_friends, 100):
            players = api.ISteamUser.GetPlayerSummaries_v2(steamids=','.join(f['steamid'] for f in chunk))['response'][
                'players']
            for p in players:
                steam_friends_info[p['steamid']] = p
        if not all_friends:
            friends_filter = set(friends.split(','))
            my_friends = [f for f in friends
                          if f.steamid in friends_filter
                          or any(p in friends_filter for p in steam_friends_info[f.steamid]['personaname'].split(','))
                          or any(p in friends_filter for p in steam_ids(f['steamid']))
                          or steam_friends_info[f['steamid']].profileurl.replace('https://steamcommunity.com/id/',
                                                                                 '').rtrim('/') in friends_filter]
        for f in my_friends:
            resp = api.IPlayerService.GetOwnedGames(
                steamid=f['steamid'], include_played_free_games=True, include_appinfo=False, appids_filter=[],
                include_free_sub=True)
            resp = resp['response']
            if 'games' in resp:
                for a in resp['games']:
                    game_friends[f'steam_{a["appid"]}'].append(
                        f'steam_{f["steamid"]}')
            else:
                print(steam_friends_info[f['steamid']]['personaname'],
                      ' does not share their game collection')
                steam_friends_info.pop(f['steamid'])
        friends_info.update((f'steam_{k}', dict(
            name=info['personaname'], icon=info['avatar'])) for k, info in steam_friends_info.items())

    df['info'] = df.apply(get_steam_info, axis=1)
    df['categories'] = df['info'].apply(get_categories)
    df['icon_rel'] = df['icon'].apply(lambda x: image_cache_location(
        x).relative_to(CACHE_DIR) if x else None)
    df['cover_rel'] = df['cover'].apply(
        lambda x: image_cache_location(x).relative_to(CACHE_DIR) if x else None)

    DIST_RES_DIR = DIST_DIR / 'res'
    DIST_IMG_DIR = DIST_DIR / 'img'
    DIST_DIR.mkdir(exist_ok=True)
    DIST_RES_DIR.mkdir(exist_ok=True)
    DIST_IMG_DIR.mkdir(exist_ok=True)
    one_way_sync(CACHE_DIR, DIST_IMG_DIR, chain(
        df['icon_rel'].dropna(), df['cover_rel'].dropna()))
    one_way_sync(RES_DIR, DIST_RES_DIR, (f.relative_to(RES_DIR)
                                         for f in RES_DIR.iterdir() if f.is_file()))

    with TmpFile(REPORT_FILE) as r, r.open('wt', encoding='utf-8') as report:
        report.write(
            '<!DOCTYPE html>\n<html><head>\n<meta charset="utf-8"/>\n')
        report.write(f'<meta rel="shortcut icon" href="res/p-generic.svg"/>\n')
        report.write(f'<title>My Games</title>\n')
        report.write(
            f'<script src="res/ag-grid-community.min.noStyle.js"></script>\n')
        report.write(f'<script src="res/luxon.min.js"></script>\n')
        report.write(f'<script>const data = ')
        json.dump([dict(
            title=row.title,
            icon=str('img' / row.icon_rel) if row.icon else None,
            cover=str('img' / row.cover_rel) if row.cover else None,
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
            friends=list(
                sorted(set(f for r in row.all_releases for f in game_friends[r])))
        ) for row in df.itertuples()], report)
        report.write(f';')
        if friends or all_friends:
            report.write('const showFriends = true; const friendsInfo = ')
            json.dump(friends_info, report)
            report.write(';')
        else:
            report.write('const showFriends = false;')
        report.write('</script>\n')
        report.write(f'<script src="res/script.js"></script>\n')
        report.write(f'<link rel="stylesheet" href="res/style.css">\n')
        report.write(f'<link rel="stylesheet" href="res/ag-grid.css">\n')
        report.write(
            f'<link rel="stylesheet" href="res/ag-theme-balham-dark.css">\n')
        report.write('</head><body>\n')
        report.write(
            '<div id="gridContainer"><div id="myGrid" class="ag-theme-balham-dark"></div>')
        report.write(
            f'<div id="exportInfo">{df.shape[0]} games – game list exported from GOG Galaxy using <a href="https://git.romlig.ch/gilles/g-export">g-export</a> – {datetime.now().strftime("%d.%m.%Y %H:%M")}</div></div>\n')
        report.write(
            '<div id="details"><div id="background"><img/></div><img id="cover" height=482 width=342/><h1>My Games</h1><div id="summary"></div></div>\n')
        report.write('</body>\n')


KNOWN_PLATFORMS = {'epic', 'xboxone', 'steam', 'gog',
                   'uplay', 'origin', 'rockstar', 'battlenet', 'generic'}


def download_image(url):
    dest = image_cache_location(url)
    with TmpFile(dest) as dest_tmp:
        dest_tmp.write_bytes(requests.get(url).content)


IMAGE_CACHE_LOCATIONS = {}


def image_cache_location(url: str) -> Path:
    if url not in IMAGE_CACHE_LOCATIONS:
        digest = sha256(url.encode("utf-8")).hexdigest()
        IMAGE_CACHE_LOCATIONS[url] = CACHE_DIR / f'{digest}.webp'
    return IMAGE_CACHE_LOCATIONS[url]


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
    parser.add_argument('--friends',
                        help='Show games owned by listed friends, comma-separated, Steam ID or vanity URL name or pseudonym')
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
