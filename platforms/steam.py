from enum import IntEnum

from steam.webapi import WebAPI

from helpers import split_chunks


class Category(IntEnum):
    MULTIPLAYER = 1
    SINGLEPLAYER = 2
    HL2_MODS = 6
    HL1_MODS = 7
    VAC_ENABLED = 8
    COOP = 9
    DEMO = 10
    HDR = 12
    CAPTIONS = 13
    COMMENTARY = 14
    STATS = 15
    SOURCE_SDK = 16
    LEVEL_EDITOR = 17
    CONTROLLER_PARTIAL = 18
    MODS = 19
    MMO = 20
    DOWNLOADABLE_CONTENT = 21
    ACHIEVEMENTS = 22
    STEAM_CLOUD = 23
    SPLIT_SCREEN = 24
    LEADERBOARDS = 25
    CROSS_PLATFORM_MULTI = 27
    CONTROLLER = 28
    TRADING_CARDS = 29
    WORKSHOP = 30
    TURN_NOTIFICATIONS = 32
    IN_APP_PURCHASES = 35
    ONLINE_PVP = 36
    SPLIT_SCREEN_PVP = 37
    ONLINE_COOP = 38
    SPLIT_SCREEN_COOP = 39
    STEAMVR_COLLECTIBLES = 40
    REMOTEPLAY_PHONE = 41
    REMOTEPLAY_TABLET = 42
    REMOTEPLAY_TV = 43
    REMOTEPLAY_TOGETHER = 44
    CLOUD_GAMING = 45
    CLOUD_GAMING_NVIDIA = 46
    LAN_PVP = 47
    LAN_COOP = 48
    PVP = 49
    HD_AUDIO = 50
    WORKSHOP_CHINA = 51
    VR_HTC = 101
    VR_OCULUS = 102
    VR_WINDOWS = 104
    VR_VALVE = 105
    VR_TRACKED_MOTION = 201
    VR_GAMEPAD = 202
    VR_KB_MOUSE = 203
    VR_SEATED = 301
    VR_STANDING = 302
    VR_ROOM_SCALE = 303
    VR_ONLY = 401
    VR_SUPPORTED = 402
    EARLY_ACCESS = 666
    PROFILE_FEATURES_LIMITED = 776
    LOW_CONFIDENCE_METRIC = 777
    ADULT_ONLY = 888


CATEGORY_NAMES = {
    Category.MULTIPLAYER: "Multi-player",
    Category.SINGLEPLAYER: "Single-player",
    Category.HL2_MODS: "Mods (require HL2)",
    Category.HL1_MODS: "Mods (require HL1)",
    Category.VAC_ENABLED: "Valve Anti-Cheat enabled",
    Category.COOP: "Co-op",
    Category.DEMO: "Game demo",
    Category.HDR: "HDR available",
    Category.CAPTIONS: "Captions available",
    Category.COMMENTARY: "Commentary available",
    Category.STATS: "Stats",
    Category.SOURCE_SDK: "Includes Source SDK",
    Category.LEVEL_EDITOR: "Includes level editor",
    Category.CONTROLLER_PARTIAL: "Partial Controller Support",
    Category.MODS: "Mods",
    Category.MMO: "MMO",
    Category.DOWNLOADABLE_CONTENT: "Downloadable Content",
    Category.ACHIEVEMENTS: "Steam Achievements",
    Category.STEAM_CLOUD: "Steam Cloud",
    Category.SPLIT_SCREEN: "Shared/Split Screen",
    Category.LEADERBOARDS: "Steam Leaderboards",
    Category.CROSS_PLATFORM_MULTI: "Cross-Platform Multiplayer",
    Category.CONTROLLER: "Full controller support",
    Category.TRADING_CARDS: "Steam Trading Cards",
    Category.WORKSHOP: "Steam Workshop",
    Category.TURN_NOTIFICATIONS: "Steam Turn Notifications",
    Category.IN_APP_PURCHASES: "In-App Purchases",
    Category.ONLINE_PVP: "Online PvP",
    Category.SPLIT_SCREEN_PVP: "Shared/Split Screen PvP",
    Category.ONLINE_COOP: "Online Co-op",
    Category.SPLIT_SCREEN_COOP: "Shared/Split Screen Co-op",
    Category.STEAMVR_COLLECTIBLES: "SteamVR Collectibles",
    Category.REMOTEPLAY_PHONE: "Remote Play on Phone",
    Category.REMOTEPLAY_TABLET: "Remote Play on Tablet",
    Category.REMOTEPLAY_TV: "Remote Play on TV",
    Category.REMOTEPLAY_TOGETHER: "Remote Play Together",
    Category.CLOUD_GAMING: "Cloud Gaming",
    Category.CLOUD_GAMING_NVIDIA: "Cloud Gaming (NVIDIA)",
    Category.LAN_PVP: "LAN PvP",
    Category.LAN_COOP: "LAN Co-op",
    Category.PVP: "PvP",
    Category.HD_AUDIO: "Additional High-Quality Audio",
    Category.WORKSHOP_CHINA: "Steam China Workshop",
    Category.VR_HTC: "HTC Vive",
    Category.VR_OCULUS: "Oculus Rift",
    Category.VR_WINDOWS: "Windows Mixed Reality",
    Category.VR_VALVE: "Valve Index",
    Category.VR_TRACKED_MOTION: "VR: Tracked Motion Controllers",
    Category.VR_GAMEPAD: "VR: Gamepad",
    Category.VR_KB_MOUSE: "VR: Keyboard / Mouse",
    Category.VR_SEATED: "VR: Seated",
    Category.VR_STANDING: "VR: Standing",
    Category.VR_ROOM_SCALE: "VR: Room-Scale",
    Category.VR_ONLY: "VR Only",
    Category.VR_SUPPORTED: "VR Supported",
    Category.EARLY_ACCESS: "Early Access",
    Category.PROFILE_FEATURES_LIMITED: "Profile Features Limited",
    Category.LOW_CONFIDENCE_METRIC: "Low Confidence Metric",
    Category.ADULT_ONLY: "Adult Only"
}


class Genre(IntEnum):
    ACTION = 1
    STRATEGY = 2
    RPG = 3
    CASUAL = 4
    RACING = 9
    SPORTS = 18
    INDIE = 23
    ADVENTURE = 25
    SIMULATION = 28
    MMO = 29
    F2P = 37
    ACCOUNTING = 50
    ANIMATION_MODELING = 51
    AUDIO_PRODUCTION = 52
    DESIGN_ILLUSTRATION = 53
    EDUCATION = 54
    PHOTO_EDITING = 55
    SOFTWARE_TRAINING = 56
    UTILITIES = 57
    VIDEO_PRODUCTION = 58
    WEB_PUBLISHING = 59
    GAME_DEVELOPMENT = 60
    EARLY_ACCESS = 70
    SEXUAL = 71
    NUDITY = 72
    VIOLENT = 73
    GORE = 74
    DOCUMENTARY = 81
    TUTORIAL = 84


GENRE_NAMES = {
    Genre.ACTION: "Action",
    Genre.STRATEGY: "Strategy",
    Genre.RPG: "RPG",
    Genre.CASUAL: "Casual",
    Genre.RACING: "Racing",
    Genre.SPORTS: "Sports",
    Genre.INDIE: "Indie",
    Genre.ADVENTURE: "Adventure",
    Genre.SIMULATION: "Simulation",
    Genre.MMO: "Massively Multiplayer",
    Genre.F2P: "Free to Play",
    Genre.ACCOUNTING: "Accounting",
    Genre.ANIMATION_MODELING: "Animation & Modeling",
    Genre.AUDIO_PRODUCTION: "Audio Production",
    Genre.DESIGN_ILLUSTRATION: "Design & Illustration",
    Genre.EDUCATION: "Education",
    Genre.PHOTO_EDITING: "Photo Editing",
    Genre.SOFTWARE_TRAINING: "Software Training",
    Genre.UTILITIES: "Utilities",
    Genre.VIDEO_PRODUCTION: "Video Production",
    Genre.WEB_PUBLISHING: "Web Publishing",
    Genre.GAME_DEVELOPMENT: "Game Development",
    Genre.EARLY_ACCESS: "Early Access",
    Genre.SEXUAL: "Sexual Content",
    Genre.NUDITY: "Nudity",
    Genre.VIOLENT: "Violent",
    Genre.GORE: "Gore",
    Genre.DOCUMENTARY: "Documentary",
    Genre.TUTORIAL: "Tutorial",
}


class SteamAPI:
    def __init__(self, steam_api_key):
        self._api = WebAPI(steam_api_key)

    def get_friends(self, steam_id):
        return self._api.ISteamUser.GetFriendList_v1(steamid=steam_id, relationship='friend')['friendslist']['friends']

    def get_player_summaries(self, steam_ids):
        players_info = {}
        for chunk in split_chunks(steam_ids, 100):
            players = self._api.ISteamUser.GetPlayerSummaries_v2(
                steamids=','.join(chunk)
            )['response']['players']
            for p in players:
                players_info[p['steamid']] = p
        return players_info

    def get_owned_games(self, steam_id):
        return self._api.IPlayerService.GetOwnedGames(
            steamid=steam_id, include_played_free_games=True, include_appinfo=False, appids_filter=[],
            include_free_sub=True, language='english', include_extended_appinfo=False)['response']
