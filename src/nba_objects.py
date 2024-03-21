import pandas as pd
pd.set_option('display.max_columns', None)
import timeit
from datetime import datetime

from file_handler import FileHandler


class NBAGame:
    def __init__(self, key: str, game: dict):
        # Game info
        self.id = key
        self.season = game['season']
        self.datetime = datetime.fromisoformat(game['datetime'])
        self.date = game['date']
        self.time = game['time']
        self.finished = game['finished']
        self.overtime = game['overtime']
        self.playoffs = game['playoffs']
        self.arena = game['arena']['name']
        self.city = game['arena']['city']
        self.state = game['arena']['state']
        self.country = game['arena']['country']
        self.home = NBATeamGamelog(game['home'])
        self.away = NBATeamGamelog(game['away'])


class NBATeamGamelog:
    def __init__(self, team_stats: dict):
        # One instance should represent stats from one team, for one game
        self.id = team_stats['id']
        self.outcome = team_stats['outcome']
        self.team = None # NBATeam object
        self.player_gamelogs = [] # NBAPlayerGamelog objects for team
        self.q1 = team_stats['score']['q1']
        self.q2 = team_stats['score']['q2']
        self.q3 = team_stats['score']['q3']
        self.q4 = team_stats['score']['q4']
        self.ot = team_stats['score']['ot']
        self.points = team_stats['score']['total']
        self.margin = team_stats['margin']


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
        
        self.players = [] # List of NBAPlayer objects
        self.finished_games = [] # List of NBAGame objects
        self.scheduled_games = [] # List of NBAGame objects

    def get_tot_stats_against(self, stats: list, pos: str='all', 
                              n_games: int=100):
        """
        Return list with sums of team total stats for previous n_games. If 
        multiple items in stats list, return tuple of lists with specified stat 
        info. Non-string stats requested will be sums.\n
        ex.) if stats = ['date', 'opponent', 'points'], return ([dates], [opps],
        [point sums matching indexes to those dates and opps])\n
        pos = 'all', 'G', 'F', or 'C'
        """

        # Put positions in list to check in main loop
        if pos == 'all':
            pos = ['G', 'F', 'C']
        else:
            pos = [pos]

        all_opp_gamelogs = self.__get_opp_gamelogs(n_games)
        all_stats = []
        for stat in stats:
            stat_list = []
            if type(all_opp_gamelogs[0][0].string_to_stat(stat)) is str:
                for gamelogs in all_opp_gamelogs:
                    stat_list.append(gamelogs[0].string_to_stat(stat))
            else:
                for gamelogs in all_opp_gamelogs:
                    stat_total = 0
                    for gamelog in gamelogs:
                        if gamelog.base_position in pos:
                            stat_total += gamelog.string_to_stat(stat)
                    stat_list.append(stat_total)
            all_stats.append(stat_list)
        
        if len(all_stats) > 1:
            return tuple(all_stats)
        else:
            return all_stats[0]
    
    def get_ind_stats_against(self, stats: list, pos: str='all', 
                              n_games: int=100):
        """
        Return individual stats in the format outlined below.\n
        One over-arching list, containing lists representing each game, where
        these lists contain lists with stat info\n
        ex.) if stats = ['position', 'first_name', 'last_name', 'points',
        'opponent', 'date'], return [[[pos, first, last, stat, opp, date],
        [pos, first, last,...]], [[pos, first, last,...],[pos, fir...],...],...]\n
        stats = list of str_to_stat strings\n
        pos = 'all', 'G', 'F', or 'C'
        """

        # Put positions in list to check in main loop
        if pos == 'all':
            pos = ['G', 'F', 'C']
        else:
            pos = [pos]

        all_opp_gamelogs = self.__get_opp_gamelogs(n_games)
        all_stats = []
        for gamelogs in all_opp_gamelogs:
            game_stat_list = []
            for gamelog in gamelogs:
                pl_stat_list = []
                for stat in stats:
                    if gamelog.base_position in pos:
                        pl_stat_list.append(gamelog.string_to_stat(stat))
                game_stat_list.append(pl_stat_list)
            all_stats.append(game_stat_list)
        return all_stats

    def __get_opp_gamelogs(self, n: int):
        """
        Return list of n lists of player gamelogs for team's most recent
        opponents.
        """

        player_gamelogs = []
        for game in self.finished_games[-n:]:
            if game.home.id == self.id:
                player_gamelogs.append(game.away.player_gamelogs)
            else:
                player_gamelogs.append(game.home.player_gamelogs)
        return player_gamelogs

    def get_no_of_gp(self, seasons=[], loc='all', opps=[]):
        """Return int representing number of games played meeting parameters"""

        gamelog_list = self.finished_games.copy()
        # Delete games not in seasons
        if len(seasons) > 0:
            gamelog_list = self.__check_season(seasons, gamelog_list)
        # Delete games not matching location
        if loc != 'all':
            gamelog_list = self.__check_loc(loc, gamelog_list)
        # Delete games not in seasons
        if len(opps) > 0:
            gamelog_list = self.__check_opp(opps, gamelog_list)

        return len(gamelog_list)
    
    def __check_season(self, seasons: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if gamelog_list[i].season not in seasons:
                del gamelog_list[i]
        return gamelog_list

    def __check_loc(self, loc: str, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if loc == 'home':
                if gamelog_list[i].home.id != self.id:
                    del gamelog_list[i]
            elif loc == 'away':
                if gamelog_list[i].away.id != self.id:
                    del gamelog_list[i]
        return gamelog_list
    
    def __check_opp(self, opps: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if gamelog_list[i].home.id == self.id:
                if gamelog_list[i].away.id not in opps:
                    del gamelog_list[i]
            if gamelog_list[i].away.id == self.id:
                if gamelog_list[i].home.id not in opps:
                    del gamelog_list[i]
        return gamelog_list


class NBAPlayer:
    def __init__(self, player: dict):
        self.id = player['id']
        self.first_name = player['firstname']
        self.last_name = player['lastname']
        self.full_name = self.first_name + ' ' + self.last_name
        self.alt_names = []
        self.height_ft = player['height']['feet']
        self.height_in = player['height']['inches']
        self.weight = player['weight']
        self.jersey = player['jersey']
        self.position = player['position']
        self.base_position = player['position']
        self.all_positions = []
        self.injury_status = None
        self.gamelog = []
        self.team = None
        self.props = []
        self.gp_all = len(self.gamelog)

    def get_stats(self, stats: list, loc: str='all', opps: list=[], 
                  seasons: list=[], without_player: list=[], 
                  with_player: list=[], n_games: int=2000):
        """
        Return tuple of stats for provided arguments. Stats will be in
        lists where each item represents an individual game.\n

        stats = string stat value(s) representing stats needed. Ex.) 
        ['minutes', 'points', 'date', 'opponent']\n
        loc = 'home' or 'away' (default 'all')\n
        opp = team ID of opponent (default 'all')\n
        without_player = player ID. If not present in game, include game 
        (default 'none')\n
        with_player = player ID. If present in game, include game 
        (default 'all')\n
        n_games = number if games to include (default 20)\n
        form = 'avg' or 'list' (default 'list')
        """

        # Make copy of player's gamelogs, then check each parameter
        gamelog_list = self.gamelog.copy()
        if len(gamelog_list) > 0:
            # Delete games not matching location
            if loc != 'all':
                gamelog_list = self.__check_loc(loc, gamelog_list)
            # Delete games not matching opponent
            if len(opps) > 0:
                gamelog_list = self.__check_opp(opps, gamelog_list)
            # Delete games not matching season
            if len(seasons) > 0:
                gamelog_list = self.__check_season(seasons, gamelog_list)
            # Delete games matching without_player value
            if len(without_player) > 0:
                gamelog_list = self.__check_without_player(without_player, 
                                                           gamelog_list)
            # Delete games not matching with_player value 
            if len(with_player) > 0:
                gamelog_list = self.__check_with_player(with_player, 
                                                        gamelog_list)

        # Get stats from gamelog into list
        all_stats = self.__get_stats_from_gamelogs(stats, n_games, 
                                                   gamelog_list)
        # Return stat list in tuple
        return all_stats

    def get_no_of_gp(self, seasons=[], loc='all', opps=[]):
        """Return int representing number of games played meeting parameters"""

        gamelog_list = self.gamelog.copy()
        # Delete games not in seasons
        if len(seasons) > 0:
            gamelog_list = self.__check_season(seasons, gamelog_list)
        # Delete games not matching location
        if loc != 'all':
            gamelog_list = self.__check_loc(loc, gamelog_list)
        # Delete games not in seasons
        if len(opps) > 0:
            gamelog_list = self.__check_opp(opps, gamelog_list)

        return len(gamelog_list)

    def __check_loc(self, loc: str, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if gamelog_list[i].loc != loc:
                del gamelog_list[i]
        return gamelog_list
    
    def __check_opp(self, opps: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if gamelog_list[i].loc == 'home':
                if gamelog_list[i].game.away.id not in opps:
                    del gamelog_list[i]
            elif gamelog_list[i].loc == 'away':
                if gamelog_list[i].game.home.id not in opps:
                    del gamelog_list[i]
        return gamelog_list
    
    def __check_season(self, seasons: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            if gamelog_list[i].game.season not in seasons:
                del gamelog_list[i]
        return gamelog_list

    def __check_without_player(self, without_player: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            gamelogs = gamelog_list[i].game.home.player_gamelogs + \
                        gamelog_list[i].game.away.player_gamelogs
            for gamelog in gamelogs:
                if gamelog.player_id in without_player:
                    del gamelog_list[i]
                    break
        return gamelog_list

    def __check_with_player(self, with_player: list, gamelog_list: list):
        for i in range(len(gamelog_list) -1, -1, -1):
            gamelogs = gamelog_list[i].game.home.player_gamelogs + \
                        gamelog_list[i].game.away.player_gamelogs
            count = 0
            for gamelog in gamelogs:
                if gamelog.player_id in with_player:
                    break
                count += 1
            if count == len(gamelogs):
                del gamelog_list[i]
        return gamelog_list
    
    def __get_stats_from_gamelogs(self, stats: list, n_games: int,
                                   gamelog_list: list):
        all_stats = []
        for stat in stats:
            stat_list = []
            for game in gamelog_list:
                stat_list.append(game.string_to_stat(stat))
            all_stats.append(stat_list[-n_games:])
        # Want tuple of lists if more than one stat, else want one list
        if len(all_stats) > 1:
            return tuple(all_stats)
        else:
            return all_stats[0]

    def get_props(self, market_key, bookmaker_keys=[], price_range=()):
        """
        Return list of NBAPlayerProp objects for provided arguments.\n

        market_key = key used for API calls\n
        bookmaker_keys = list of bookies to include (default 'all')\n
        price_range = range of odds to include (tuple) (default = 'all')
        """

        props_list = self.props.copy()
        if len(self.props) > 0:
            # Delete items not matching market_key
            for i in range(len(props_list) -1, -1, -1):
                if props_list[i].market_key != market_key:
                    del props_list[i]
            # Delete items not matching bookmaker_keys
            if len(bookmaker_keys) != 0:
                for i in range(len(props_list) -1, -1, -1):
                    if props_list[i].bookmaker_key not in bookmaker_keys:
                        del props_list[i]
            # Delete items not in price_range
            if len(price_range) != 0:
                for i in range(len(props_list) -1, -1, -1):
                    if (price_range[0] > props_list[i].price or 
                        price_range[1] < props_list[i].price):
                        del props_list[i]
        return props_list
    

class NBAPlayerGamelog:
    def __init__(self, player_stats: dict):
        self.game_id = player_stats['game_id']
        self.loc = player_stats['loc']
        self.team_id = player_stats['team_id']
        self.player_id = player_stats['player_id']
        self.first_name = player_stats['firstname']
        self.last_name = player_stats['lastname']
        self.position = player_stats['pos']
        self.base_position = (self.position[-1] if self.position is not None 
                              else None)
        self.minutes = int(player_stats['min'].split(':')[0])
        self.points = player_stats['points']
        self.fgm = player_stats['fgm']
        self.fga = player_stats['fga']
        self.fgp = float(player_stats['fgp'])
        self.ftm = player_stats['ftm']
        self.fta = player_stats['fta']
        self.ftp = float(player_stats['ftp'])
        self.tpm = player_stats['tpm']
        self.tpa = player_stats['tpa']
        self.tpp = float(player_stats['tpp'])
        self.off_reb = player_stats['off_reb']
        self.def_reb = player_stats['def_reb']
        self.tot_reb = player_stats['tot_reb']
        self.assists = player_stats['assists']
        self.fouls = player_stats['fouls']
        self.steals = player_stats['steals']
        self.turnovers = player_stats['turnovers']
        self.blocks = player_stats['blocks']
        self.double_double = 0
        self.triple_double = 0
        self.plus_minus = player_stats['plus_minus']
        self.comment = player_stats['comment']
        self.game = None # NBAGame object
        
        self.__dd_td_check()

    def string_to_stat(self, stat_str: str):
        """Return variable associated with given string."""
        if stat_str == 'location':
            return self.loc
        if stat_str == 'minutes':
            return self.minutes
        if stat_str == 'points':
            return self.points
        if stat_str == 'rebounds':
            return self.tot_reb
        if stat_str == 'assists':
            return self.assists
        if stat_str == 'threes':
            return self.tpm
        if stat_str == 'blocks':
            return self.blocks
        if stat_str == 'steals':
            return self.steals
        if stat_str == 'blocks_steals':
            return self.blocks + self.steals
        if stat_str == 'turnovers':
            return self.turnovers
        if stat_str == 'points_rebounds_assists':
            return self.points + self.tot_reb + self.assists
        if stat_str == 'points_rebounds':
            return self.points + self.tot_reb
        if stat_str == 'points_assists':
            return self.points + self.assists
        if stat_str == 'rebounds_assists':
            return self.tot_reb + self.assists
        if stat_str == 'double_double':
            return self.double_double
        if stat_str == 'triple_double':
            return self.triple_double
        if stat_str == 'position':
            return self.position
        if stat_str == 'first_name':
            return self.first_name
        if stat_str == 'last_name':
            return self.last_name
        if stat_str == 'datetime':
            return self.game.datetime
        if stat_str == 'date':
            dt = datetime.strptime(self.game.date, '%m/%d/%y')
            return dt.strftime('%-m/%-d/%y')
        if stat_str == 'opponent':
            if self.loc == 'home':
                return self.game.away.team.code
            else:
                return self.game.home.team.code

    def __dd_td_check(self):
        count = 0
        for i in [self.points, self.assists, self.tot_reb, 
                  self.steals, self.blocks]:
            if i >= 10:
                count += 1
        if count >= 2:
            self.double_double = 1
        if count >= 3:
            self.triple_double = 1

class NBAPlayerProp:
    def __init__(self, prop: dict):
        self.bookmaker_key = prop['bookmaker_key']
        self.bookmaker_name = prop['bookmaker_name']
        self.market_key = prop['market_key']
        self.market_name = prop['market_name']
        self.market_abv = prop['market_abv']
        self.last_update = datetime.fromisoformat(prop['last_update'])
        self.player_name = prop['player_name']
        self.name = prop['name']
        self.price = prop['price']
        self.line = prop['line']


class NBAGameProp:
    def __init__(self, prop: dict):
        pass


if __name__ == "__main__":
    game = {
        "season": 2023,
        "datetime": "2023-12-04T22:00:00-05:00",
        "date": "12/04/23",
        "time": "10:00PM",
        "finished": True,
        "overtime": False,
        "playoffs": False,
        "arena": {
            "name": "Golden 1 Center",
            "city": "Sacramento",
            "state": "CA",
            "country": None
        },
        "away": {
            "id": 23,
            "code": "NOP",
            "score": {
                "q1": "35",
                "q2": "34",
                "q3": "31",
                "q4": "27",
                "ot": 0,
                "total": 127
            },
            "outcome": "W",
            "margin": 10
        },
        "home": {
            "id": 30,
            "code": "SAC",
            "score": {
                "q1": "36",
                "q2": "25",
                "q3": "30",
                "q4": "26",
                "ot": 0,
                "total": 117
            },
            "outcome": "L",
            "margin": -10
        }
    }

    team = NBAGame('123', game)
    print(team.datetime)




    