import requests
import json
from datetime import datetime, timezone, timedelta
from file_handler import FileHandler


class APIClient:
    def __init__(self):
        pass

    def get_request(self, url, params):
        """Return JSON given API url and appropriate parameters."""

        r = requests.get(url, headers=self.headers, params=params)
        
        if r.status_code == 200:
            return r.json()

        print('Request failed with status:', r.status_code)
        return {}
    
    def get_params(self, keys, values):
        """
        Provided parameter keys and values, create dictionary to
        be passed to get_request function as params.
        """
        
        query_string = {}
        for key, value in zip(keys, values):
            if value is not None or value != []:
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
    
    def get_seasons(self):
        """Return JSON with callable seasons."""

        url = self.base_url + '/seasons'
        parameter_keys = []  # No parameters needed
        parameter_values = []  # No parameters needed

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)

    def get_players(self, id: int=None, name: str=None, team: int=None, 
                    season: int=None, country: str=None, search: str=None):
        """
        Return JSON containing data about players given one, or
        a combination of parameters.\n
        Ex.) Given team and season parameters, return JSON with info of 
        every player that has played for that team this year.
        """

        url = self.base_url + '/players'
        parameter_keys = ['id', 'name', 'team', 'season', 'country', 'search']
        parameter_values = [id, name, team, season, country, search]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_games(self, id: int=None, live: str=None, date: str=None, league: str=None, 
                  season: int=None, team: int=None, h2h: str=None):
        """
        Return JSON containing data about games given one, or
        a combination of parameters.\n
        Ex.) Given season parameter, return JSON with info on every game that
        season, pre/reg/post season, both completed and scheduled.
        """
        
        url = self.base_url + '/games'
        parameter_keys = ['id', 'live', 'date', 'league', 'season', 'team', 'h2h']
        parameter_values = [id, live, date, league, season, team, h2h]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)

    def get_teams(self, id: int=None, name: str=None, code: str=None, league: str=None, 
                  conference: str=None, division: str=None, search: str=None):
        """
        Return JSON containing data about teams given one, or
        a combination of parameters.\n
        Ex.) Call with no parameters to return JSON with info on all teams.
        """

        url = self.base_url + '/teams'
        parameter_keys = ['id', 'name', 'code', 'league', 'conference', 'division', 'search']
        parameter_values = [id, name, code, league, conference, division, search]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_player_stats(self, id: int=None, game: int=None, 
                         team: int=None, season: int=None):
        """
        Return JSON containing player stats data given one, or
        a combination of parameters.\n
        Ex.) Given team and season parameters, return JSON with individual player
        stats for the given team for every individual game that season.
        """

        url = self.base_url + '/players/statistics'
        parameter_keys = ['id', 'game', 'team', 'season']
        parameter_values = [id, game, team, season]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def get_game_stats(self, id: int):
        """
        Return JSON containing total game stats for each team
        given the game id.
        """

        url = self.base_url + '/games/statistics'
        query_string = {'id': id}
        
        return self.get_request(url, query_string)
    
    def get_team_stats(self, id: int, season: int):
        """
        Return JSON containing a teams total season stats given team id 
        and season.
        """

        url = self.base_url + '/teams/statistics'
        query_string = {'id': id, 'season': season}
        
        return self.get_request(url, query_string)
    

class NFLStatsAPIClient:
    pass


class NHLStatsAPIClient:
    pass


class MLBStatsAPIClient:
    pass


class OddsAPIClient(APIClient):
    def __init__(self):
        self.base_url = 'https://api.the-odds-api.com/v4/sports'
        self.key = 'cb1d0f43e31783f0a89fe53481df9e9c'
        self.headers = None

    def get_sports(self, all: str='false'):
        """
        Return a json containing info on in-season sports. Set all = 'true' (str) 
        to return info on all available sports.
        """

        url = self.base_url
        query_string = {'apiKey': self.key, 'all': all}
        
        return self.get_request(url, query_string)

    def get_events(self, sport: str, date_str: str=None):
        """
        Given sport and date in format yyyy-mm-dd, return json inclduing
        event_ids and other related info for that day's games. Get sport values
        from get-sports API call.
        """

        start, end = self.__get_iso_date_range(date_str)

        url = self.base_url + f'/{sport}/events'
        parameter_keys = ['apiKey', 'commenceTimeFrom', 'commenceTimeTo']
        parameter_values = [self.key, start, end]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)

    def get_odds(self, sport: str, markets: list, regions: list=['us'], 
                 event_ids: list=[], bookmakers: list=[], date_str: str=None, 
                 odds_format: str='american'):
        """
        Given required variables sport and market, return json with bookmaker odds.\n
        Use keys in Featured Betting Markets at 
        the-odds-api.com/sports-odds-data/betting-markets.html\n
        Probably will be used given sport, markets, bookmakers, and date.\n

        sport = from get_sports API call\n
        markets = 'h2h', 'totals', 'spreads', 'outrights'\n
        bookmakers = from custom list of bookmakers\n
        date_str = yyyy-mm-dd
        """

        # Join lists into comma separated strings
        markets = ','.join(markets)
        regions = ','.join(regions)
        event_ids = ','.join(event_ids)
        bookmakers = ','.join(bookmakers)
        start, end = self.__get_iso_date_range(date_str)

        url = self.base_url + f'/{sport}/odds'
        parameter_keys = ['apiKey', 'regions', 'markets', 'oddsFormat', 'eventIds',
                          'bookmakers', 'commenceTimeFrom', 'commenceTimeTo']
        parameter_values = [self.key, regions, markets, odds_format, event_ids,
                            bookmakers, start, end]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)

    def get_event_odds(self, sport: str, event_id: str, markets: list, 
                       regions: list=['us'], bookmakers: list=[], 
                       odds_format: str='american'):
        """
        Given required variables sport, eventID and market, return json with 
        bookmaker odds. Must call with eventID, one eventID at a time.\n
        Use keys in Additional, Game Period, and Player Prop Markets at 
        the-odds-api.com/sports-odds-data/betting-markets.html\n
        Probably will be used given sport, event_id, market and bookmakers.\n
        
        sport = from get_sports API call\n
        event_id = from get_events API call\n
        markets = 'player_points', 'player_assists_alternate', 'btts', etc.\n
        bookmakers = from custom list of bookmakers
        """

        markets = ','.join(markets)
        regions = ','.join(regions)
        bookmakers = ','.join(bookmakers)

        url = self.base_url + f'/{sport}/events/{event_id}/odds'
        parameter_keys = ['apiKey', 'regions', 'markets', 'bookmakers', 'oddsFormat']
        parameter_values = [self.key, regions, markets, bookmakers, odds_format]

        query_string = self.get_params(parameter_keys, parameter_values)
        return self.get_request(url, query_string)
    
    def __get_iso_date_range(self, date_str: str):
        """
        Given date in format yyyy-mm-dd, return commenceTimeFrom and commenceTimeTo 
        values for The Odds API call. Both will be strings in iso format, commenceTimeTo
        will be a day later. Timezone is UTC.
        """
        try:
            start = datetime.strptime(date_str, '%Y-%m-%d')
            start = start.astimezone(tz=timezone.utc).replace(tzinfo=None)
            end = start + timedelta(days=1)
            return start.isoformat()+'Z', end.isoformat()+'Z'
        except TypeError:
            return None, None


if __name__ == "__main__":
    #api = NBAStatsAPIClient()
    #print(api.get_seasons())

    #api = OddsAPIClient()
    #print(api.get_sports())
    #print(api.get_events('basketball_nba', '2024-01-31'))
    #odds = api.get_events('basketball_nba', '2024-01-31')
    
    #odds = api.get_odds('basketball_nba', ['h2h'], 
                        #event_ids = ['bdd9f81bd5b9358f9dd0480895196b45', 'a1ce4e385dafe59342d13a82dff13f45'], 
                        #bookmakers=['fanduel', 'draftkings', 'espnbet'])
    pass
