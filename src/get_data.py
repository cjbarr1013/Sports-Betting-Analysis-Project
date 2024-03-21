from datetime import datetime, timezone
import time
import timeit
import os

import get_data_api as api
import get_data_scrape as scrape
from file_handler import FileHandler


def pause_api_calls():
    time.sleep(6)

def get_seasons(sport: str):
    """
    Given 'sport' == 'nba', 'nfl', 'mlb', or 'nhl', return list of 
    seasons with available data.
    """

    print(f'Getting {sport.upper()} season data...')

    if sport == 'nba':
        return api.NBAStatsAPIClient().get_seasons()['response']

    elif sport == 'nfl':
        pass

    elif sport == 'mlb':
        pass

    elif sport == 'nhl':
        pass

def get_team_data(sport: str):
    """
    Given 'sport' == 'nba', 'nfl', 'mlb', or 'nhl', return list of
    organized dictionaries containing team data in json format.
    """
    
    print(f'Getting {sport.upper()} team data...')
    
    new_teams = []
    if sport == 'nba':
        pause_api_calls()
        teams = api.NBAStatsAPIClient().get_teams()
        for team in teams['response']:
            # Skip ID 37, not an NBA Franchise
            if team['nbaFranchise'] and team['id'] != 37:
                new_teams.append(organize_nba_team_data(team))

    elif sport == 'nfl':
        pass

    elif sport == 'mlb':
        pass

    elif sport == 'nhl':
        pass

    file_name = f'{sport}_teams.json'
    file_path = f'data/{sport}/teams'
    json_handler = FileHandler(file_name, file_path)
    json_handler.write_file(new_teams)

def organize_nba_team_data(team: dict):
    return {
        'id': team['id'],
        'name': team['name'],
        'city': team['city'],
        'nickname': team['nickname'],
        'code': team['code'],
        'logo': team['logo'],
        'conference': team['leagues']['standard']['conference'],
        'division': team['leagues']['standard']['division']
    }

def organize_nfl_team_data(team: dict):
    return {}

def organize_mlb_team_data(team: dict):
    return {}

def organize_nhl_team_data(team: dict):
    return {}

def get_game_data(sport: str, season: int):
    """
    Given 'sport' == 'nba', 'nfl', 'mlb', or 'nhl', and season, 
    return list of organized dictionaries containing game data in json format.
    """

    print(f'Getting {season} {sport.upper()} game data...')

    new_games = {}
    if sport == 'nba':
        pause_api_calls()
        games = api.NBAStatsAPIClient().get_games(season=season, 
                                                  league='standard')
        for game in games['response']:
            # Include only regular and post season games
            if game['stage'] in [2, 4]:
                new_games[game['id']] = organize_nba_game_data(game)

    elif sport == 'nfl':
        pass

    elif sport == 'mlb':
        pass

    elif sport == 'nhl':
        pass

    file_name = f'{season}_{sport}_games.json'
    file_path = f'data/{sport}/games'
    json_handler = FileHandler(file_name, file_path)
    json_handler.write_file(new_games)

def organize_nba_game_data(game: dict):
    # Stage 2 is regular season, stage 4 is playoffs
    playoffs = False
    if game['stage'] == 4:
        playoffs = True

    # Get datetime str, convert to datetime obj, convert to EST
    new_dt = convert_utc_to_est(game['date']['start'])
    new_dt_iso = new_dt.isoformat()
    new_date = new_dt.date().strftime('%m/%d/%y')
    new_time = new_dt.time().strftime('%-I:%M%p')

    # If game is complete, get scores. If not, set items == None
    if game['status']['long'] == 'Finished':
        finished = True
        away_score = {
            'q1': game['scores']['visitors']['linescore'][0],
            'q2': game['scores']['visitors']['linescore'][1],
            'q3': game['scores']['visitors']['linescore'][2],
            'q4': game['scores']['visitors']['linescore'][3],
            'ot': 0,
            'total': game['scores']['visitors']['points']
        }
        home_score = {
            'q1': game['scores']['home']['linescore'][0],
            'q2': game['scores']['home']['linescore'][1],
            'q3': game['scores']['home']['linescore'][2],
            'q4': game['scores']['home']['linescore'][3],
            'ot': 0,
            'total': game['scores']['home']['points']
        }

    elif game['status']['long'] in ['Scheduled', 'In Play']:
        finished = False
        away_score = {
            'q1': None,
            'q2': None,
            'q3': None,
            'q4': None,
            'ot': None,
            'total': None
        }
        home_score = {
            'q1': None,
            'q2': None,
            'q3': None,
            'q4': None,
            'ot': None,
            'total': None
        }
    
    # Get overtime score (if applicable). Only 1st OT was included previously.
    try:
        away_reg_total = sum([int(away_score['q1']), int(away_score['q2']), 
                             int(away_score['q3']), int(away_score['q4'])])
        home_reg_total = sum([int(home_score['q1']), int(home_score['q2']), 
                             int(home_score['q3']), int(home_score['q4'])])
        away_score['ot'] = away_score['total'] - away_reg_total
        home_score['ot'] = home_score['total'] - home_reg_total
    # Exception if either away_score or home_score are None
    except (TypeError, ValueError):
        pass
    
    # Get bool value for overtime
    overtime = False
    try:
        if away_score['ot'] > 0 and home_score['ot'] > 0:
            overtime = True
    # Exception if either away_score or home_score are None
    except TypeError:
        pass

    # Get win or loss, also margin of win or loss.
    try:
        margin = away_score['total'] - home_score['total']
        home_margin, away_margin = -margin, margin
        if margin > 0:
            home_outcome, away_outcome = 'L', 'W'
        elif margin < 0:
            home_outcome, away_outcome = 'W', 'L'
    # Exception if either away_score or home_score are None
    except TypeError:
        home_outcome, away_outcome = None, None
        home_margin, away_margin = None, None

    return {
            'season': game['season'],
            'datetime': new_dt_iso,
            'date': new_date,
            'time': new_time,
            'finished': finished,
            'overtime': overtime,
            'playoffs': playoffs,
            'arena': game['arena'],
            'away': {
                     'id': game['teams']['visitors']['id'],
                     'code': game['teams']['visitors']['code'],
                     'score': away_score,
                     'outcome': away_outcome,
                     'margin': away_margin
                     },
            'home': {
                     'id': game['teams']['home']['id'],
                     'code': game['teams']['home']['code'],
                     'score': home_score,
                     'outcome': home_outcome,
                     'margin': home_margin
                     }
            }

def organize_nfl_game_data(team: dict):
    return {}

def organize_mlb_game_data(team: dict):
    return {}

def organize_nhl_game_data(team: dict):
    return {}

def get_player_data(sport: str, season: int):
    """"""

    print(f'Getting {sport.upper()} player data for {season} season...')

    new_players = []
    json_handler = FileHandler(f'{sport}_teams.json', f'data/{sport}/teams')
    teams = json_handler.load_file()

    if sport == 'nba':
        player_ids = []
        for team in teams:
            pause_api_calls()
            print(team['name'])
            players = api.NBAStatsAPIClient().get_players(team=team['id'], 
                                                          season=season)
            for player in players['response']:
                if player['id'] not in player_ids:
                    new_players.append(organize_nba_player_data(player))
                    player_ids.append(player['id'])

    elif sport == 'nfl':
        pass

    elif sport == 'mlb':
        pass

    elif sport == 'nhl':
        pass

    file_name = f'{sport}_players.json'
    file_path = f'data/{sport}/players'
    json_handler = FileHandler(file_name, file_path)
    json_handler.write_file(new_players)

def organize_nba_player_data(player: dict):
    # Check that the suffix is not in first name by mistake.
    # If it is, move to last name.
    first_name, last_name = fix_player_name(player['firstname'], 
                                            player['lastname'])

    return {
        'id': player['id'],
        'firstname': first_name,
        'lastname': last_name,
        'height': {
            'feet': player['height']['feets'],
            'inches': player['height']['inches']
        },
        'weight': player['weight']['pounds'],
        'jersey': player['leagues']['standard']['jersey'],
        'position': player['leagues']['standard']['pos']
    }

def organize_nfl_player_data(player: dict):
    return {}

def organize_mlb_player_data(player: dict):
    return {}

def organize_nhl_player_data(player: dict):
    return {}

def get_player_stats_data(sport: str, team: int=None, 
                          season: int=None):
    """
    Given sport, team and season, return list of dictionaries with 
    player gamelog info.
    """

    print(f'Getting {sport.upper()} player stats data for team {team} season {season}...')

    # Open games .json to get info for gamelogs
    json_handler = FileHandler(f'{season}_{sport}_games.json', f'data/{sport}/games')
    games = json_handler.load_file()
    new_player_stats = []

    if sport == 'nba':
        pause_api_calls()
        player_stats = api.NBAStatsAPIClient().get_player_stats(team=team, 
                                                                season=season)
        for player_stat in player_stats['response']:
            game_id = str(player_stat['game']['id'])
            # Skip if game not in games (Preseason)
            try:
                game = games[game_id]
            except KeyError:
                continue
            new_player_stat = organize_nba_player_stat_data(player_stat, game, game_id)
            # Check that the player actually played in the game
            if (new_player_stat['min'] is not None and 
                new_player_stat['min'] not in ['-', '--', '0:00']):
                new_player_stats.append(new_player_stat)

    elif sport == 'nfl':
        pass

    elif sport == 'mlb':
        pass

    elif sport == 'nhl':
        pass

    file_name = f'{season}_{team}_player_gamelogs.json'
    file_path = f'data/{sport}/players/gamelogs'
    json_handler = FileHandler(file_name, file_path)
    json_handler.write_file(new_player_stats)

def organize_nba_player_stat_data(player_stat: dict, game: dict, game_id: str):
    # Determine whether player was home or away
    if player_stat['team']['id'] == game['home']['id']:
        loc = 'home'
        opp_loc = 'away'
    else:
        loc = 'away'
        opp_loc = 'home'

    # Check that the suffix is not in first name by mistake.
    # If it is, move to last name.
    first_name, last_name = fix_player_name(player_stat['player']['firstname'], 
                                            player_stat['player']['lastname'])
    
    return {
            'game_id': game_id,
            'season': game['season'],
            'datetime': game['datetime'],
            'date': game['date'],
            'time': game['time'],
            'loc': loc,
            'team_id': game[loc]['id'],
            'team_code': game[loc]['code'],
            'team_score': game[loc]['score']['total'],
            'opp_id': game[opp_loc]['id'],
            'opp_code': game[opp_loc]['code'],
            'opp_score': game[opp_loc]['score']['total'],
            'playoffs': game['playoffs'],
            'player_id': player_stat['player']['id'],
            'firstname': first_name,
            'lastname': last_name,
            'pos': player_stat['pos'],
            'min': player_stat['min'],
            'points': player_stat['points'],
            'fgm': player_stat['fgm'],
            'fga': player_stat['fga'],
            'fgp': player_stat['fgp'],
            'ftm': player_stat['ftm'],
            'fta': player_stat['fta'],
            'ftp': player_stat['ftp'],
            'tpm': player_stat['tpm'],
            'tpa': player_stat['tpa'],
            'tpp': player_stat['tpp'],
            'off_reb': player_stat['offReb'],
            'def_reb': player_stat['defReb'],
            'tot_reb': player_stat['totReb'],
            'assists': player_stat['assists'],
            'fouls': player_stat['pFouls'],
            'steals': player_stat['steals'],
            'turnovers': player_stat['turnovers'],
            'blocks': player_stat['blocks'],
            'plus_minus': player_stat['plusMinus'],
            'comment': player_stat['comment']
    }

def organize_nfl_player_stat_data(player_stat: dict, game: dict, game_id: str):
    return {}

def organize_mlb_player_stat_data(player_stat: dict, game: dict, game_id: str):
    return {}

def organize_nhl_player_stat_data(player_stat: dict, game: dict, game_id: str):
    return {}

def get_player_injuries(sport: str):
    """
    Given sport ('nba', 'nfl', i.e.), save player injury data as 
    {sport}_player_injuries.json. Data is currently scraped from espn.com.
    """

    injuries = scrape.get_player_injuries(sport)
    injuries_handler = FileHandler(f'{sport}_player_injuries.json', f'data/{sport}/players')
    injuries_handler.write_file(injuries)

def get_events(sport: str, date_str: str):
    """
    Given sport ('nba', 'nfl', i.e.) and date_str in format yyyy-mm-dd, 
    save event info as events.json for the given date.
    """
    
    sports_handler = FileHandler('api_keys_sports.json', 'src')
    sports = sports_handler.load_file()
    
    events = api.OddsAPIClient().get_events(sports[sport]['key'], date_str)
    events_handler = FileHandler('events.json', f'data/{sport}/odds')
    events_handler.write_file(events)
    
def get_core_market_odds(sport: str, market: dict, date_str: str):
    """
    Given sport ('nba', 'nfl', i.e.), appropriate market dict from 
    api_keys_core_markets.json, and date_str in format yyyy-mm-dd, return 
    json with odds.
    """

    market_name = market['name']
    print(f'Getting {sport.upper()} {market_name} odds...')

    sports_handler = FileHandler('api_keys_sports.json', 'src')
    sports = sports_handler.load_file()

    bookies = []
    bookmakers_handler = FileHandler('api_keys_bookmakers.json', 'src')
    bookmakers = bookmakers_handler.load_file()
    for bookie in bookmakers:
        bookies.append(bookie['key'])

    market_key, market_group = market['key'], market['group']
    odds = api.OddsAPIClient().get_odds(sport=sports[sport]['key'],
                                        markets=[market_key],
                                        bookmakers=bookies,
                                        date_str=date_str)
    
    odds = organize_all_market_odds(odds, market)
    odds_handler = FileHandler(f'{market_key}.json', f'data/{sport}/odds/{market_group}')
    odds_handler.write_file(odds)

def get_additional_market_odds(sport: str, market: dict):
    """
    Given sport ('nba', 'nfl', i.e.) and appropriate market dict from 
    api_keys_player_props_markets.json, api_keys_alt_player_prop_markets.json, 
    and more to be added later, return json with odds.
    """

    market_name = market['ext_name']
    print(f'Getting {sport.upper()} {market_name} odds...')

    events_handler = FileHandler('events.json', f'data/{sport}/odds')
    events = events_handler.load_file()

    sports_handler = FileHandler('api_keys_sports.json', 'src')
    sports = sports_handler.load_file()

    bookies = []
    bookmakers_handler = FileHandler('api_keys_bookmakers.json', 'src')
    bookmakers = bookmakers_handler.load_file()
    for bookie in bookmakers:
        bookies.append(bookie['key'])

    market_key, market_group = market['key'], market['group']
    odds_list = []
    for event in events:
        odds = api.OddsAPIClient().get_event_odds(sport=sports[sport]['key'],
                                                  event_id=event['id'],
                                                  markets=[market_key],
                                                  bookmakers=bookies)
        odds_list.append(odds)
    
    odds_list = organize_all_market_odds(odds_list, market)
    odds_handler = FileHandler(f'{market_key}.json', f'data/{sport}/odds/{market_group}')
    odds_handler.write_file(odds_list)

def organize_all_market_odds(odds, market_dict):
    new_odds = []
    for event in odds:
        # For totals markets, there is another list structure around a single dict
        if type(event) is list:
            event = event[0]
        for bookmaker in event['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    # No line for h2h markets, double-double, or triple-double
                    try:
                        line = outcome['point']
                    except KeyError:
                        line = 0.5
                    # No player for h2h, totals, or spreads
                    try:
                        player_name = outcome['description']
                    except KeyError:
                        player_name = None
                    
                    last_update = convert_utc_to_est(market['last_update'])

                    prop = {
                        'event_id': event['id'],
                        'sport_key': event['sport_key'],
                        'sport_name': event['sport_title'],
                        'home_team': event['home_team'],
                        'away_team': event['away_team'],
                        'bookmaker_key': bookmaker['key'],
                        'bookmaker_name': bookmaker['title'],
                        'market_key': market['key'],
                        'market_name': market_dict['name'],
                        'market_abv': market_dict['abv_name'],
                        'last_update': last_update.isoformat(),
                        'name': outcome['name'],
                        'player_name': player_name,
                        'price': outcome['price'],
                        'line': line
                    }

                    new_odds.append(prop)
    
    return new_odds

def convert_utc_to_est(date_str: str):
    """
    Given iso date string in utc time zone, convert to datetime object 
    in est timezone.
    """

    # Convert to datetime obj, convert to EST and return
    dt = datetime.fromisoformat(date_str)
    return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def fix_player_name(first, last):
    # Exception for Attribute Error if either name in None
    try:
        suffix = first.split(' ')[-1]
        suffix_list = ['Jr.', 'Sr.', 'I', 'II', 'III', 'IV', 'V']
        if suffix in suffix_list:
            first = first.replace(f' {suffix}', '')
            last = last + ' ' + suffix
    except AttributeError:
        pass

    return first, last


if __name__ == "__main__":
    #get_team_data('nba')
    
    #for season in range(2015, 2024):
        #get_game_data('nba', season=season)
    
    #get_game_data('nba', season=2023)
    
    #get_player_data('nba', 2023)

    #json_handler = FileHandler('nba_teams.json', 'data/nba/teams')
    #teams = json_handler.load_file()
    #for team in teams:
        #get_player_stats_data('nba', team['id'], 2023)

    #get_events('nba', '2024-02-03')

    #markets_handler = FileHandler('api_keys_core_markets.json', 'src')
    #markets = markets_handler.load_file()
    #for market in markets:
        #get_core_market_odds('nba', market, '2024-02-03')
    
    #markets_handler = FileHandler('api_keys_player_prop_markets.json', 'data/nba/odds')
    #markets = markets_handler.load_file()
    #for market in markets[1:13]:
        #get_additional_market_odds('nba', market)

    get_player_injuries('nba')
