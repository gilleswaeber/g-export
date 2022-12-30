class Platform:
    def __init__(self, key, name):
        self.key = key
        self.name = name


PLATFORMS = {p.key: p for p in [
    # svg icon in res folder
    Platform('epic', 'Epic'),
    Platform('xboxone', 'Xbox'),
    Platform('steam', 'Steam'),
    Platform('gog', 'GOG.com'),
    Platform('uplay', 'Ubisoft Connect'),
    Platform('origin', 'Origin'),
    Platform('rockstar', 'Rockstar'),
    Platform('battlenet', 'Battle.net'),
    Platform('generic', 'Other'),
]}
