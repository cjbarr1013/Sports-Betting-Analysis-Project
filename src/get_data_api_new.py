import requests
import json


class APIClient:
    def __init__(self):
        pass

    def get_request(self, url, params):
        """"""

        r = requests.get(url, headers=self.headers, params=params)
        
        if r.status_code == 200:
            return r.json()

        print('Request failed with status:', r.status_code)
        return {}
    
    def get_params(self, keys, values):
        """"""
        
        query_string = {}
        for key, value in zip(keys, values):
            if value is not None:
                query_string[key] = value
        
        return query_string


class NBAStatsAPIClient(APIClient):
    def __init__(self):
        self.base_url = 'https://api-nba-v1.p.rapidapi.com'
        self.key = '5d4e021604msh02b622d72706cd8p1ea776jsnb23e50a563d2'
        self.host = 'api-nba-v1.p.rapidapi.com'
        self.headers = {
                        'X-RapidAPI-Key': self.key,
                        'X-RapidAPI-Host': self.host
                        }
    
    def get_players(self, id: int=None, name: str=None, team: int=None, 
                    season: int=None, country: str=None, search: str=None):
        """Return JSON containing data about players given one, or
        a combination of parameters."""

        url = self.base_url + '/players'
        parameter_keys = ['id', 'name', 'team', 'season', 'country', 'search']
        parameter_values = [id, name, team, season, country, search]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_games(self, id: int=None, live: str=None, date: str=None, league: str=None, 
                  season: int=None, team: int=None, h2h: str=None):
        """Return JSON containing data about games given one, or
        a combination of parameters."""
        
        url = self.base_url + '/games'
        parameter_keys = ['id', 'live', 'date', 'league', 'season', 'team', 'h2h']
        parameter_values = [id, live, date, league, season, team, h2h]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)

    def get_teams(self, id: int=None, name: str=None, code: str=None, league: str=None, 
                  conference: str=None, division: str=None, search: str=None):
        """Return JSON containing data about teams given one, or
        a combination of parameters."""

        url = self.base_url + '/teams'
        parameter_keys = ['id', 'name', 'code', 'league', 'conference', 'division', 'search']
        parameter_values = [id, name, code, league, conference, division, search]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_player_stats(self, id: int=None, game: int=None, 
                         team: int=None, season: int=None):
        """Return JSON containing data about teams given one, or
        a combination of parameters."""

        url = self.base_url + '/players/statistics'
        parameter_keys = ['id', 'game', 'team', 'season']
        parameter_values = [id, game, team, season]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_game_stats(self, id: int):
        """"""

        url = self.base_url + '/games/statistics'
        query_string = {'id': id}
        
        return self.get_request(url, query_string)
    
    def get_team_stats(self, id: int, season: int):
        """"""

        url = self.base_url + '/teams/statistics'
        query_string = {'id': id, 'season': season}
        
        return self.get_request(url, query_string)
    

class NFLStatsAPIClient:
    pass


class NHLStatsAPIClient:
    pass


class MLBStatsAPIClient:
    pass


if __name__ == "__main__":
    api = NBAStatsAPIClient()
    json_file = api.get_player_stats(team=1, season=2023)
    with open('player_stats_test_1_2023.json', 'w') as f:
            json.dump(json_file, f, indent=4)

