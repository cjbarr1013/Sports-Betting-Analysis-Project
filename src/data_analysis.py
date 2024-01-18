import pandas as pd
import xlsxwriter
from datetime import datetime
import numpy as np
pd.set_option('display.max_columns', None)

from nfl_objects import NFLPlayer, NFLTeam, NFLGame, NFLDefense, NFLPlayerProp
from file_handler import FileHandler
import get_data
import get_data_api as api


class NFLDataAnalysis:
    def __init__(self):
        self.teams = []
        self.players = []
        self.games = []
        self.__init_teams()
        self.__init_players()
        self.__init_odds()
        self.__init_games()

        self.season = self.games[-1].season
        self.week = self.__init_week()

        self.game_split = [3, 6, 9]

    def __init_teams(self):
        team_handler = FileHandler('nfl_teams.json', get_data.team_path)
        team_dicts = team_handler.load_file()
        
        for team in team_dicts:
            self.teams.append(NFLTeam(team))

    def __init_players(self):
        player_handler = FileHandler('nfl_players.json', get_data.player_path)
        player_dicts = player_handler.load_file()
        
        for player in player_dicts:
            try:
                player = NFLPlayer(player)
            except FileNotFoundError:
                continue
            
            self.players.append(player)
            
            for team in self.teams:
                if team.team_id == player.team_id:
                    team.players.append(player)
                    break
    
    def __init_odds(self):
        for prop in api.markets['nfl']:
            prefix = prop['prefix']
            odds_handler = FileHandler(f'{prefix}_odds.json', get_data.line_path)
            odds_dicts = odds_handler.load_file()

            for item in odds_dicts:
                prop = NFLPlayerProp(item)
                for player in self.players:
                    player_name = player.name.lower()
                    prop_name = prop.name.lower()
                    for ch in ['.', '-', "'", '*', '+']:
                        player_name = player_name.replace(ch, '')
                        prop_name = prop_name.replace(ch, '')
                    if player_name == prop_name and prop.sportsbook in api.sportsbooks:
                        player.props.append(prop)
     
    def __init_games(self):
        game_handler = FileHandler('nfl_games.json', get_data.game_path)
        game_dicts = game_handler.load_file()
        
        for game in game_dicts:
            game = NFLGame(game)
            self.games.append(game)
            for team in self.teams:
                if team.team_id == game.home_team_id or team.team_id == game.away_team_id:
                    team.gamelog.append(game)
    
    def __init_week(self):
        for game in self.games:
            if game.home_score == "":
                return game.week

    def player_stats_table(self, stat_type: str, stat='', pos=['QB', 'RB', 'WR', 'TE', 'K']):
        """Given values outlined below, the function returns a sorted Dataframe with columns 
        representing the player, position, their team, next opponent, last 5 gamelog (right being the 
        most recent), current line and odds, average this season, and average the last 1, 3, 6, 9 
        games. All stats are per game.\n
        stat_type = 'pa' -> stat = 'cmps', 'atts', 'yds', 'tds', 'ints'\n
        stat_type = 'ru' -> stat = 'atts', 'yds'\n
        stat_type = 're' -> stat = 'recs', 'yds'\n
        stat_type = 'fg' -> stat = 'made', 'points'\n
        stat_type = 'attd' -> stat = ''\n
        pos == 'QB', 'RB', 'WR', 'TE', 'K', or all by default. Must be list and can contain multiple."""
        
        columns = ['Player', 'Position', 'Team', 'Opp', 'L5 Log', 'Line', 'Odds', 'Season', 'Last', 
                   f'L{self.game_split[0]}', f'L{self.game_split[1]}', f'L{self.game_split[2]}']
        
        info = []
        for team in self.teams:
            opp_obj = self.get_team_object(team.get_opp(self.season, self.week))
            for player in team.players:
                if player.position in pos and opp_obj is not None and len(player.props) > 0:
                    # Check if stat exists in the player's gamelog, skip if not.
                    try:
                        log = player.get_player_stats_log(stat_type, stat)
                    except:
                        continue
                    
                    # Get line and odds for prop if it exists for player, skip if not.
                    line, odds = None, None
                    for item in player.props:
                        if item.prop == stat_type + '_' + stat or item.prop == stat_type:
                            line = item.line
                            odds = item.odds
                            break
                    if line is None:
                        continue
                    
                    # Get no. of games played for current season, and calculate season avg.
                    gp = player.get_gp_by_season(self.season)
                    if gp == 0:
                        current_avg = 0
                    else:
                        current_avg = sum(log[-gp:]) / gp

                    # Build row for player info
                    row = [player.name, player.position, team.initials, opp_obj.initials,
                           log[-5:], line, odds, round(current_avg, 2), log[-1]]
                    for games in self.game_split:
                        stat_total = sum(log[-games:])
                        row.append(round(stat_total/games, 2))
                    info.append(row)
        
        # Create table, sort by Season avg, then L3 avg, and return
        table = pd.DataFrame(info, columns=columns)
        return table.sort_values(['Season', 'L3'], ascending=False).reset_index(drop=True)

    def stats_against_table(self, stat_type: str, stat='', sort_param='Season'):
        """Given values outlined below, the function returns a sorted Dataframe with columns 
        representing the team, next opp, last 5 gamelog (right being the most recent), average allowed 
        this season, and average allowed the last 1, 3, 6, 9 games. All stats are per game.\n
        stat_type = 'pa' -> stat = 'cmps', 'atts', 'yds', 'tds', 'ints'\n
        stat_type = 'ru' -> stat = 'atts', 'yds', 'tds'\n
        stat_type = 're' -> stat = 'recs', 'yds', 'tds'\n
        stat_type = 'fg' -> stat = 'made', 'atts', 'points'\n
        stat_type = 'attd' -> stat = ''"""

        columns = ['Team', 'Opp', 'L5 Log', 'Season', 'Last Game', 
                   f'L{self.game_split[0]}', f'L{self.game_split[1]}', 
                   f'L{self.game_split[2]}']
        
        info = []
        for team in self.teams:
            log = team.defense.get_stats_against_log(stat_type, stat)
            
            # Get no. of games played for current season, and calculate season avg.
            gp = team.defense.get_gp_by_season(self.season)
            if gp == 0:
                current_avg = 0
            else:
                current_avg = round(sum(log[-gp:]) / gp, 2)
            
            # Get display initials for opponent, or 'Bye' if bye week
            opp = team.get_opp(self.season, self.week)
            if opp != 'Bye':
                opp = self.get_team_object(opp).initials

            # Build row for team defense info
            row = [team.initials, opp, log[-5:], current_avg, log[-1]]
            for games in self.game_split:
                stat_total = sum(log[-games:])
                row.append(round(stat_total/games, 2))
            info.append(row)
        
        # Create table, sort based on sort_param, add rank column, and return
        table = pd.DataFrame(info, columns=columns)
        table = table.sort_values([sort_param, 'Season', 'L3'], ascending=True).reset_index(drop=True)
        table = self.add_rank_index(table, sort_param)
        return table

    def stats_against_by_pos_table(self, stat_type: str, stat: str, sort_param='sum'):
        """Returns a Dataframe with columns representing the team, next opp, and given stat allowed 
        this season to QB, RB, WR and TE.\n
        stat_type = 'ru' -> stat = 'atts', 'yds', 'tds' -> returns table with QB, RB\n
        stat_type = 're' -> stat = 'recs', 'yds', 'tds' -> returns table with RB, WR, TE\n
        sort_param = 'sum', 'QB', 'RB', 'WR', 'TE'"""

        if stat_type == 're':
            positions = ['RB', 'WR', 'TE']
        elif stat_type == 'ru':
            positions = ['QB', 'RB']
        elif stat_type == 'attd':
            positions = ['QB', 'RB', 'WR', 'TE']
        columns = ['Team', 'Opp'] + positions
        
        info = []
        for team in self.teams:
            # Get display initials for opponent, or 'Bye' if bye week
            opp = team.get_opp(self.season, self.week)
            if opp != 'Bye':
                opp = self.get_team_object(opp).initials

            # Build row for team defense info
            row = [team.initials, opp]
            gp = team.defense.get_gp_by_season(self.season)
            for pos in positions:
                stat_total = team.defense.get_stats_against_by_pos(pos, stat_type, stat)
                row.append(round(stat_total/gp, 2))
            info.append(row)
        
        # Create table, sort based on sort_param, and return
        table = pd.DataFrame(info, columns=columns)
        if sort_param == 'sum':
            table.sort_index(key=table.sum(1, numeric_only=True).get, ascending=True, inplace=True)
        else:
            table.sort_values(by=sort_param, ascending=True, inplace=True)
            table = self.add_rank_index(table, sort_param)
        
        return table.reset_index(drop=True)

    def add_rank_index(self, table: pd, sort_param: str) -> pd:
        ranks = []
        prev_value = 0
        i, j = 1, 1
        for value in table[sort_param]:
            if value == prev_value:
                ranks.append(i)
            else:
                ranks.append(j)
                i = j
            j += 1
            prev_value = value

        table.insert(0, "Rank", ranks)
        return table
            
    def display_prop_analysis(self, market: dict):
        """Given a market dict from get_data_api.py, return a Panda Dataframe displaying 
        Player Info, Past Performance, Opponent's Defensive Performance, and Prop Analysis values."""
        
        # Defining column names for data table
        log_games = 10
        log_stat_strings = [f'stat_{i+1}' for i in range(log_games)]
        log_opp_strings = [f'opp_{i+1}' for i in range(log_games)]

        matchup_games = 5
        matchup_stat_strings = [f'stat_{i+1}' for i in range(matchup_games)]
        matchup_opp_strings = [f'opp_{i+1}' for i in range(matchup_games)]

        player_info_cols = ['Player', 'Position', 'Team', 'Injury']

        matchup_cols = ['Next Opp.'] + matchup_stat_strings + matchup_opp_strings

        player_perf_cols = ['Season Avg.', 
                            f'L{self.game_split[0]} Avg.', 
                            f'L{self.game_split[1]} Avg.', 
                            f'L{self.game_split[2]} Avg.'] + log_stat_strings + log_opp_strings
                            
        def_perf_cols = ['Season Avg.', 'Season Avg. vs. Pos.', 
                         f'L{self.game_split[0]} Avg.',
                         f'L{self.game_split[1]} Avg.', 
                         f'L{self.game_split[2]} Avg.'] + log_stat_strings + log_opp_strings
        
        prop_info_cols = ['Prop', 'fd_line', 'fd_over', 'fd_under',
                          'dk_line', 'dk_over', 'dk_under',
                          'espn_line', 'espn_over', 'espn_under']

        analysis_cols = ['analysis_pl', 'analysis_def', 'analysis_tot']

        columns = player_info_cols + matchup_cols + player_perf_cols
        columns += def_perf_cols + prop_info_cols + analysis_cols

        # Main loop for going through players on each team to find matching props
        info = []
        for team in self.teams:
            for player in team.players:
                for prop in player.props:
                    if prop.prop == market['prefix']:
                        
                        # Get all info for player and prop
                        opp_obj = self.get_team_object(team.get_opp(self.season, self.week))
                        player_info = self.get_player_info_data(player, team)
                        matchup_info = self.get_matchup_data(opp_obj, player, market, matchup_games)
                        player_perf_info = self.get_player_perf_data(player, market, log_games)
                        def_perf_info = self.get_def_perf_data(opp_obj, market, log_games, player.position)
                        
                        # Get list of prop objects only if they pertain to called upon market
                        props = [obj for obj in player.props if obj.prop == market['prefix']]
                        prop_info = self.get_prop_info_data(props, prop.prop)
                        
                        # If no min line for analysis, go to next prop
                        if prop_info[0] is None:
                            continue
                        
                        analysis_info = self.get_analysis_data(player, opp_obj, market, prop_info[0])
                        
                        # Construct row, then break prop loop to move onto next player
                        row = player_info + matchup_info + player_perf_info
                        row += def_perf_info + prop_info[1] + analysis_info
                        info.append(row)
                        break
        
        # Build table and sort by total of prop analysis values
        table = pd.DataFrame(info, columns=columns)
        return table.sort_values(['analysis_tot', 'analysis_pl'], ascending=False).reset_index(drop=True)

    def get_player_info_data(self, player: NFLPlayer, team: NFLTeam):
        """"""
        
        # Assign info to variables
        name = player.name
        pos = player.position
        tm = team.initials
        inj = self.get_display_injury(player)

        # Assemble row and return
        row = [name, pos, tm, inj]
        return row

    def get_matchup_data(self, opp: NFLTeam, player: NFLPlayer, 
                         market: dict, n_games: int):
        """"""

        # Get nicely displayed opponent info
        opp_info = self.get_display_next_opp(opp)
        
        # Get full stat log to use in rest of function
        stat_type, stat = market['stat_type'], market['stat']
        full_stat_log = player.get_player_stats_log(stat_type, stat, opp.initials)
        
        # Get stat log and opponent log. Add None to make length == n_games
        stat_log = full_stat_log[-n_games:]
        opp_log = self.get_display_opp_log(n_games, player=player, opp_inits=opp.initials)
        while len(stat_log) < n_games:
            stat_log.append(None)
            opp_log.append(None)

        # Assemble row and return
        row = [opp_info] + stat_log + opp_log
        return row

    def get_player_perf_data(self, player: NFLPlayer, 
                             market: dict, n_games: int):
        """"""

        # Get full stat log to use in rest of function
        stat_type, stat = market['stat_type'], market['stat']
        full_stat_log = player.get_player_stats_log(stat_type, stat)
        
        # Calculate season average
        gp = player.get_gp_by_season(self.season)
        if gp == 0:
            season_avg = None
        else:
            season_avg = round(sum(full_stat_log[-gp:]) / gp, 2)
        
        # Get average for each value in self.game_split
        splits = []
        for games in self.game_split:
            if player.gp_all_time >= games:
                splits.append(round(sum(full_stat_log[-games:]) / games, 2))
            else:
                splits.append(None)
        
        # Get stat log and opponent log. Add None to make length == n_games
        stat_log = full_stat_log[-n_games:]
        opp_log = self.get_display_opp_log(n_games, player=player)
        while len(stat_log) < n_games:
            stat_log.append(None)
            opp_log.append(None)

        # Assemble row and return
        row = [season_avg] + splits + stat_log + opp_log
        return row

    def get_def_perf_data(self, team: NFLTeam, market: dict, 
                          n_games: int, pos: str):
        """"""

        # Get full stat log to use in rest of function
        stat_type, stat = market['stat_type'], market['stat']
        full_stat_log = team.defense.get_stats_against_log(stat_type, stat)

        # Calculate season average
        gp = team.defense.get_gp_by_season(self.season)
        if gp == 0:
            season_avg = None
        else:
            season_avg = round(sum(full_stat_log[-gp:]) / gp, 2)
            rank = self.get_def_rank(team, stat_type, stat, games=gp)
            season_avg = f'{season_avg} ({rank})'

        # Calculate season average vs player's position, and get rank
        # If passing or kicking stat, it will be the same as previous step
        if gp == 0:
            season_avg_vs_pos = None
        else:
            if stat_type in ['pa', 'fg']:
                season_avg_vs_pos = season_avg
            elif team.defense.get_stats_against_by_pos(pos, stat_type, stat) is None:
                season_avg_vs_pos = None
            else:
                season_tot_vs_pos = team.defense.get_stats_against_by_pos(pos, stat_type, stat)
                season_avg_vs_pos = round(season_tot_vs_pos / gp, 2)
                rank = self.get_def_rank(team, stat_type, stat, pos=pos)
                season_avg_vs_pos = f'{season_avg_vs_pos} ({rank})'

        # Get average and rank for each value in self.game_split
        splits = []
        for games in self.game_split:
            avg = round(sum(full_stat_log[-games:]) / games, 2)
            rank = self.get_def_rank(team, stat_type, stat, games=games)
            splits.append(f'{avg} ({rank})')

        # Get stat log and opponent log
        stat_log = full_stat_log[-n_games:]
        opp_log = self.get_display_opp_log(n_games, team=team)
        while len(stat_log) < n_games:
            stat_log.append(None)
            opp_log.append(None)

        # Assemble row and return
        row = [season_avg] + [season_avg_vs_pos] + splits + stat_log + opp_log
        return row
    
    def get_prop_info_data(self, props: list, prop_id):
        """Given list of NFL player props (with related prop_id) and prop 
        name ('attd', 'pa_cmps', etc.), get lines/odds for FD, DK, and ESPN. 
        Also get smallest line and return in a tuple with line/odds list."""

        # Initialize line/odds variables as None
        fd_line, fd_over, fd_under = None, None, None
        dk_line, dk_over, dk_under = None, None, None
        espn_line, espn_over, espn_under = None, None, None

        # Divide prop objects into lists
        fd_props = [prop for prop in props if prop.sportsbook == 'fanduel']
        dk_props = [prop for prop in props if prop.sportsbook == 'draftkings']
        espn_props = [prop for prop in props if prop.sportsbook == 'barstool']

        # Get Fanduel line/odds
        # Assuming 2 prop objects (1 over, 1 under) w/ same line
        if len(fd_props) > 0:
            fd_line = fd_props[0].line
            fd_over = fd_props[0].odds
            if prop_id != 'attd':
                fd_under = fd_props[1].odds
        
        # Get Draftkings line/odds
        # Assuming 2 prop objects (1 over, 1 under) w/ same line
        if len(dk_props) > 0:
            dk_line = dk_props[0].line
            dk_over = dk_props[0].odds
            if prop_id != 'attd':
                dk_under = dk_props[1].odds
        
        # Get ESPNBet line/odds
        if len(espn_props) > 0:
            # Assuming 2 prop objects (1 over, 1 under) w/ same line
            if prop_id in ['attd', 'pa_yds']:
                espn_line = espn_props[0].line
                espn_over = espn_props[0].odds
                espn_under = espn_props[1].odds

            # Assuming 6 prop objects (3 over, 3 under) w/ 3 different lines
            # Take the middle line/odds
            elif prop_id in ['pa_atts', 'pa_cmps', 'ru_yds', 're_yds']:
                try:
                    espn_line = espn_props[1].line
                    espn_over = espn_props[1].odds
                    espn_under = espn_props[4].odds
                except IndexError:
                    pass

            # Assuming 6 prop objects (3 over, 3 under) w/ 3 different lines
            # Take line that matches smallest of FD/DK lines
            elif prop_id in ['pa_tds', 'ru_atts', 
                             're_recs', 'fg_made', 'fg_points']:
                lines = [i for i in [fd_line, dk_line] if i is not None]
                try:
                    for prop in espn_props:
                        if prop.line == min(lines):
                            espn_line = prop.line
                            if prop.over_under == 'over':
                                espn_over = prop.odds
                            else:
                                espn_under = prop.odds
                # Take the middle line/odds if no FD/DK line available
                except ValueError:
                    try:
                        espn_line = espn_props[1].line
                        espn_over = espn_props[1].odds
                        espn_under = espn_props[4].odds
                    except IndexError:
                        pass
            
            # Assuming 6 prop objects (3 over, 3 under) w/ 3 different lines
            # Take line the smallest line (should always be 0.5)
            elif prop_id == 'pa_ints':
                espn_line = espn_props[0].line
                espn_over = espn_props[0].odds
                espn_under = espn_props[3].odds

        # Find the smallest line for analysis, will be None if no lines
        # There will be no lines if number of dicts doesn't match typical number of dicts
        try:
            min_line = min([i for i in [fd_line, dk_line, espn_line] if i is not None])
        except ValueError:
            min_line = None

        # Assemble row and return in tuple
        row = [props[0].prop_name, fd_line, fd_over, fd_under]
        row += [dk_line, dk_over, dk_under]
        row += [espn_line, espn_over, espn_under]
        return (min_line, row)
    
    def get_analysis_data(self, player: NFLPlayer, opp: NFLTeam, 
                          market: dict, line):
        """Get player and defensive performance values, apply final weights, add together,
        and return in a list."""

        # Weights for player and defensive performance metrics
        w_player = 0.6
        w_def = 0.4
        
        # Get performance values
        player_score = self.player_performance_analysis(player, market, line)
        defense_score = self.def_performance_analysis(player, opp, market, line)
        
        # Check if player_score == None (player has played 6 or less career games)
        try:
            total = (player_score * w_player) + (defense_score * w_def)
        except TypeError:
            return [None, round(defense_score, 2), None]

        return [round(player_score, 2), round(defense_score, 2), round(total, 2)]

    def get_display_injury(self, player: NFLPlayer) -> str:
        """Given NFLPlayer object, return injury status in following format:\n
        '{status[0]} ({inj})' --> D (Ankle) or 'None' if no injury designation."""
        
        if player.injury['game status'] in ['n/a', '']:
            return 'Active'
        else:
            status = player.injury['game status']
            inj = player.injury['comment']
            return f'{status[0]} ({inj})'
        
    def get_display_next_opp(self, opp: NFLTeam):
        """Given NFLTeam obj of the opponent, return next opp info in following format:\n
        '{opp.initials} {game_obj.day} {game_obj.time}' --> DEN Sun 4:30PM"""
        
        game_obj = opp.get_next_game_obj()
        if game_obj.home_team_id == opp.team_id:
            return f'at {opp.initials} {game_obj.day} {game_obj.time}'
        else:
            return f'vs {opp.initials} {game_obj.day} {game_obj.time}'

    def get_display_opp_log(self, games: int, player=None, team=None, opp_inits='all') -> list:
        """Given NFLPlayer or NFLTeam object and n games, return list of n opponents in the format:\n
        '{opp} ({date})' --> 'DAL (10/17/2023)'"""
        
        if player is not None:
            locs = player.get_player_loc_log(opp=opp_inits)[-games:]
            opps = player.get_player_opp_log(opp=opp_inits)[-games:]
            dates = player.get_player_date_log(opp=opp_inits)[-games:]
        elif team is not None:
            locs = team.get_game_loc_log()[-games:]
            opps = team.get_game_opp_log()[-games:]
            opps = [self.get_team_object(opp).initials for opp in opps]
            dates = team.get_game_date_log()[-games:]
        
        opp_log = []
        for loc, opp, date in zip(locs, opps, dates):
            # Convert str date to datetime object, then convert back to desired str format
            d = datetime.strptime(date, '%Y-%m-%d').strftime('%m/%d/%y')
            if loc in ['H', 'N']:
                opp_log.append(f'{opp} ({d})')
            else:
                opp_log.append(f'@{opp} ({d})')
        return opp_log

    def get_team_object(self, value: str):
        """Given an team_id, inits or name, get NFLTeam object."""

        for team in self.teams:
            if value == team.team_id or value == team.name or value == team.initials:
                return team
        return None
    
    def get_def_rank(self, team: NFLTeam, stat_type: str, stat: str, games=0, pos=''):
        """Given stat_type, stat, and # of games OR position, return int value of
        rank for either all pos for last n games, or for pos this season."""

        if pos != '':
            table = self.stats_against_by_pos_table(stat_type, stat, pos)
        elif games in self.game_split:
            table = self.stats_against_table(stat_type, stat, f'L{games}')
        elif games > 0:
            table = self.stats_against_table(stat_type, stat, 'Season')
        else:
            return 0
        
        return table.loc[table['Team'] == team.initials, 'Rank'].iloc[0]

    def player_performance_analysis(self, player: NFLPlayer, market: dict, line):
        """Used in display_performance_analysis, return value representing player 
        performance vs the given stat"""

        stat_type, stat = market['stat_type'], market['stat']
        metrics = self.get_player_metrics(player)

        # Metrics var will be empty dict if player.gp_all_time < certain value
        if len(metrics) == 0:
            return None
        
        # Get average over number of games provided by metrics variable
        # Then use player_avg_vs_line to get performance value
        m_player = []
        player_stat_log = player.get_player_stats_log(stat_type, stat)
        for games in metrics['splits']:
            avg = sum(player_stat_log[-games:]) / games
            m_avl = self.player_avg_vs_line(avg, line)
            m_player.append(m_avl)

        # Use log_vs_line to get performance value based on 
        # number of times line has been covered
        for n in metrics['n_cover']:
            m_p_cover = self.log_vs_line(player_stat_log[-n:], line)
            m_player.append(m_p_cover)

        # Apply weights and return score
        score = 0
        for m, w in zip(m_player, metrics['weights']):
            score += m * w
        return score

    def def_performance_analysis(self, player: NFLPlayer, opp: NFLTeam, 
                                 market: dict, line):
        """Used in display_performance_analysis, return value representing defensive 
        performance vs the given stat"""

        stat_type, stat = market['stat_type'], market['stat']
        metrics = self.get_def_metrics(opp, stat_type)

        # Get performace value based on def rank vs stat
        m_def = []
        for games in metrics['splits']:
            m_rvs = self.def_rank_vs_stat(opp, stat_type, stat, games=games)
            m_def.append(m_rvs)
        
        # Get performance value based on def rank vs stat vs position
        # If passing or kicking stat, then value is based on def rank vs stat 
        # this season because these stats are usually only one player.
        # No data for rushing yards vs WRs, so will treat that situation
        # same as passing or kicking prop for now
        if stat_type in ['pa', 'fg'] or opp.defense.get_stats_against_by_pos(player.position, stat_type, stat) is None:
            gp = opp.defense.get_gp_by_season(self.season)
            m_rvsvp = self.def_rank_vs_stat(opp, stat_type, stat, games=gp)
        else:
            m_rvsvp = self.def_rank_vs_stat(opp, stat_type, stat, pos=player.position)
        
        m_def.append(m_rvsvp)

        # Use log_vs_line to get performance value based on number of times line has been covered
        # Will be TypeError if n_cover == None, and n_cover will be None 
        # if stat_type in [ru, re] because these stats are accumulated by
        # multiple players, not just one like 'pa' and 'fg'
        try:
            for n in metrics['n_cover']:
                def_stat_log = opp.defense.get_stats_against_log(stat_type, stat)[-n:]
                m_d_cover = self.log_vs_line(def_stat_log, line)
                m_def.append(m_d_cover)
        except TypeError:
            m_def.extend([0, 0, 0])

        # Apply weights and return score
        score = 0
        for m, w in zip(m_def, metrics['weights']):
            score += m * w
        return score

    def player_avg_vs_line(self, avg: float, line: float):
        """Take an average stat value and prop line to determine performance value.\n"""

        ratio = avg / line
        ratio = 0.5 if ratio < 0.5 else 2 if ratio > 2 else ratio
        return np.interp(ratio, [0.5, 1, 2], [0, 0.5, 1])

    def log_vs_line(self, log: list, line: float):
        """Take stat log and prop line to see how often the line has been covered 
        and return a performance value."""

        count = 0
        for stat in log:
            if stat > line:
                count += 1
        return count / len(log)

    def def_rank_vs_stat(self, team: NFLTeam, stat_type: str, stat: str, games=0, pos=''):
        """Return performance value based on the defense's rank vs given stat."""

        rank = self.get_def_rank(team, stat_type, stat, games, pos)
        return rank / 32
    
    def get_player_metrics(self, player: NFLPlayer):
        """Given NFLPlayer object, return metrics used to analyze player performance.\n
        Returns a dictionary with the following:\n
        'splits': list of 3 ints representing # of games to include in avg vs line analysis\n
        'n_cover': int representing # of games to include in log vs line analysis\n
        'weights': weights to apply to each metric"""
        
        gp = player.gp_all_time
        g1, g2, g3 = self.game_split[0], self.game_split[1], self.game_split[2]
        
        # Weight splits for main metrics
        avg_v_line = 1/2
        cover_num = 1/2
        
        # If the player has < 6 career gp, not enough data for analysis
        if gp < 6:
            return {}
        elif 6 <= gp < 9:
            return {'splits': [g1, gp-g1, gp],
                    'n_cover': [g1, gp-g1, gp],
                    'weights': [avg_v_line*(5.5/10), avg_v_line*(4.5/10), 0,
                                cover_num*(5.5/10), cover_num*(4.5/10), 0]}
        elif 9 <= gp < 12:
            return {'splits': [g1, g2, gp-g1],
                    'n_cover': [g1, g2, gp-g1],
                    'weights': [avg_v_line*(4/10), avg_v_line*(3/10), avg_v_line*(3/10),
                                cover_num*(4/10), cover_num*(3/10), cover_num*(3/10)]}
        elif gp >= 12:
            return {'splits': [g1, g2, g3],
                    'n_cover': [g1, g2, g3],
                    'weights': [avg_v_line*(4/10), avg_v_line*(3/10), avg_v_line*(3/10),
                                cover_num*(4/10), cover_num*(3/10), cover_num*(3/10)]}

    def get_def_metrics(self, team: NFLTeam, stat_type: str):
        """Given NFLTeam object and stat_type == 'pa', 'ru', 're', 'fg', 
        return metrics used to analyze defensive performance.\n
        Returns a dictionary with the following:\n
        'splits': list of 3 ints representing # of games to include in rank vs line analysis\n
        'n_cover': int representing # of games to include in log vs line analysis (if applicable)\n
        'weights': weights to apply to each metric"""
        
        gp = team.defense.get_gp_by_season(self.season)
        g1, g2, g3 = self.game_split[0], self.game_split[1], self.game_split[2]

        if stat_type in ['pa', 'fg']:
            # Weight splits for main metrics
            cover = 1/4
            rvs = 1/2
            rvsvp = 1/4
            
            if gp < g1:
                return {'splits':  [g1, g2, g3],
                        'n_cover': [g1, g2, g3],
                        'weights': [(rvs * (5/10)) + (rvsvp * (1/6)), (rvs * (3/10)) + (rvsvp * (1/6)), 
                                    (rvs * (2/10)) + (rvsvp * (1/6)), 
                                    0, 
                                    (cover * (5/10)) + (rvsvp * (1/6)), (cover * (3/10)) + (rvsvp * (1/6)), 
                                    (cover * (2/10)) + (rvsvp * (1/6))]}

            else:
                return {'splits': [g1, g2, g3],
                        'n_cover': [g1, g2, g3],
                        'weights': [(rvs * (4/10)), (rvs * (3/10)), 
                                    (rvs * (3/10)),
                                    rvsvp, 
                                    (cover * (4/10)), (cover * (3/10)), 
                                    (cover * (3/10))]}
            
        else:
            # Weight splits for main metrics
            # Cover metric weight is split between other two because rushing and
            # receiving stats are accumulated by multiple players.
            # This is also why n_cover is None, and it's weight is 0
            cover = 1/4
            rvs = (1/2) + (cover * (3/4))
            rvsvp = (1/4) + (cover * (1/4))

            if gp < g1:
                return {'splits': [g1, g2, g3],
                        'n_cover': [None, None, None],
                        'weights': [(rvs * (5/10)) + (rvsvp * (1/3)), (rvs * (3/10)) + (rvsvp * (1/3)), 
                                    (rvs * (2/10)) + (rvsvp * (1/3)), 
                                    0, 
                                    0, 0, 0]}
            else:
                return {'splits': [g1, g2, g3],
                        'n_cover': [None, None, None],
                        'weights': [(rvs * (4/10)), (rvs * (3/10)), 
                                    (rvs * (3/10)), 
                                    rvsvp, 
                                    0, 0, 0]}

    def tables_to_excel(self, file_name: str, tables: list):
        """Given a file name and a list of Pandas Dataframes, create an Excel Workbook 
        with a sheet for each table. Tables in list must be tuples with format (pd, sheet_name)"""
        
        path = 'excel/nfl/' + file_name
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        
        for table in tables:
            table[0].to_excel(writer, sheet_name=table[1])

        writer.close()


if __name__ == "__main__":
    analysis = NFLDataAnalysis()
    for player in analysis.players:
        if len(player.props) > 0:
            print()
            print(player.name)
            for prop in player.props:
                if prop.prop in ['pa_tds', 'ru_atts', 
                                    're_recs', 'fg_made', 'fg_points']:
                    if prop.sportsbook == 'barstool':
                        print(prop.prop_name)
                        print(prop.line)
                        print(prop.odds)
                        print(prop.over_under)
    

    



        
        