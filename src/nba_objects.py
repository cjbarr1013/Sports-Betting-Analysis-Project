import pandas as pd
pd.set_option('display.max_columns', None)

from file_handler import FileHandler


class NBATeam:
    def __init__(self, team: dict):
        self.id = team['id']
        self.name = team['name']
        self.city = team['city']
        self.nickname = team['nickname']
        self.code = team['code']
        self.conference = team['conference']
        self.division = team['division']
        self.logo = team['logo']
        self.players = []
        self.gamelog = []
        self.defense = None


class NBADefense:
    def __init__(self):
        pass


class NBAGame:
    def __init__(self, game: dict):
        # Game info
        self.id = game['id']
        self.season = game['season']
        self.date = game['date']
        self.time = game['time']
        self.playoffs = game['playoffs']
        
        # Location
        self.arena_name = game['arena']['name']
        self.arena_city = game['arena']['city']
        self.arena_state = game['arena']['state']
        self.arena_country = game['arena']['country']

        # Away team info
        self.away_id = game['away']['id']
        self.away_code = game['away']['code']
        self.away_q1 = game['away']['score']['q1']
        self.away_q2 = game['away']['score']['q2']
        self.away_q3 = game['away']['score']['q3']
        self.away_q4 = game['away']['score']['q4']
        self.away_total = game['away']['score']['total']
        self.away_players = []
        
        # Home team info
        self.home_id = game['home']['id']
        self.home_code = game['home']['code']
        self.home_q1 = game['home']['score']['q1']
        self.home_q2 = game['home']['score']['q2']
        self.home_q3 = game['home']['score']['q3']
        self.home_q4 = game['home']['score']['q4']
        self.home_total = game['home']['score']['total']
        self.home_players = []


class NBAPlayer:
    def __init__(self, player: dict):
        # Basic player info
        self.id = player['id']
        self.first_name = player['first_name']
        self.last_name = player['last_name']
        self.position = player['position']
        self.team_id = player['team_id']
        self.jersey = player['jersey']
        self.height = player['height']
        self.weight = player['weight']
        self.injury_status = None
        
        # Player data
        self.props = []
        self.stats = NBAPlayerStats(self.id)
        self.gp_season = None
        self.gp_all = None


class NBAPlayerStats:
    def __init__(self, id: int):
        pass


class NBAPlayerProp:
    def __init__(self, prop: dict):
        self.prop = prop['prop']
        self.prop_name = prop['prop_name']
        self.sportsbook = prop['sportsbook']
        self.name = prop['name']
        self.line = prop['line']
        self.odds = prop['odds']
        self.over_under = prop['over_under']