# For game in todays NBA games
    # Analyze game props
        # Will need to access game logs for each team
    # For teams playing in game
        # For players on team

import os
import json
import timeit
import pandas as pd
import numpy as np
from datetime import datetime
import get_data
pd.set_option('display.max_columns', None)

from nba_objects import NBAGame, NBATeam, NBAPlayer, NBAPlayerGamelog, NBAPlayerProp
from file_handler import FileHandler


class NBADataAnalysis:
    def __init__(self):
        self.games = []
        self.teams = []
        self.players = []
        self.season = get_data.get_seasons('nba')[-1]
        
        self.__init_games()
        self.__init_teams()
        self.__init_players()
        self.__connect_gamelogs_with_games_and_players()
        self.__connect_games_and_teams()
        self.__sort_player_gamelogs()
        self.__connect_players_and_teams()
        self.__connect_props_and_players()
        self.__connect_injuries_and_players()
        self.__set_player_position()

    def __init_games(self):
        file_path = 'data/nba/games'
        game_files = sorted(os.listdir(file_path))
        for file in game_files:
            game_handler = FileHandler(file, file_path)
            games = game_handler.load_file()
            for key in games:
                self.games.append(NBAGame(key, games[key]))
        self.games.sort(key=lambda game: game.datetime)

    def __init_teams(self):
        team_handler = FileHandler('nba_teams.json', 
                                   'data/nba/teams')
        teams = team_handler.load_file()
        for team in teams:
            self.teams.append(NBATeam(team))

    def __init_players(self):
        player_handler = FileHandler('nba_players.json', 
                                     'data/nba/players')
        players = player_handler.load_file()
        alt_name_handler = FileHandler('alt_player_names.json', 
                                       'data/nba/players')
        alt_names = alt_name_handler.load_file()
        for player in players:
            player = NBAPlayer(player)
            # Add alternative names, if available
            try:
                player.alt_names = alt_names[str(player.id)]
            except KeyError:
                pass
            self.players.append(player)

    def __get_player_gamelogs(self):
        file_path = 'data/nba/players/gamelogs'
        gamelog_files = sorted(os.listdir(file_path))
        player_gamelogs = []
        for file in gamelog_files:
            gamelog_handler = FileHandler(file, file_path)
            gamelogs = gamelog_handler.load_file()
            for gamelog in gamelogs:
                player_gamelogs.append(NBAPlayerGamelog(gamelog))
        return player_gamelogs

    def __get_player_props(self):
        file_path = 'data/nba/odds/player_props'
        prop_files = sorted(os.listdir(file_path))
        player_props = []
        for file in prop_files:
            prop_handler = FileHandler(file, file_path)
            props = prop_handler.load_file()
            for prop in props:
                player_props.append(NBAPlayerProp(prop))
        return player_props
    
    def __get_player_injuries(self):
        injuries_handler = FileHandler('nba_player_injuries.json', 
                                       'data/nba/players')
        return injuries_handler.load_file()

    def __connect_gamelogs_with_games_and_players(self):
        player_gamelogs = self.__get_player_gamelogs()
        for gamelog in player_gamelogs:
            # Attach NBAPlayerGamelog to NBAGame object, and vise versa
            for game in self.games:
                if gamelog.game_id == game.id:
                    gamelog.game = game
                    if gamelog.team_id == game.home.id:
                        game.home.player_gamelogs.append(gamelog)
                    elif gamelog.team_id == game.away.id:
                        game.away.player_gamelogs.append(gamelog)
                    break
            # Attach NBAPlayerGamelog to NBAPlayer object
            for player in self.players:
                if gamelog.player_id == player.id:
                    player.gamelog.append(gamelog)
                    break
        del player_gamelogs

    def __sort_player_gamelogs(self):
        for player in self.players:
            player.gamelog.sort(key=lambda gamelog: gamelog.game.datetime)

    def __connect_games_and_teams(self):
        for team in self.teams:
            for game in self.games:
                if game.home.team is None:
                    if game.home.id == team.id:
                        game.home.team = team
                        if game.finished == True:
                            team.finished_games.append(game)
                        else:
                            team.scheduled_games.append(game)
                        continue
                if game.away.team is None:
                    if game.away.id == team.id:
                        game.away.team = team
                        if game.finished == True:
                            team.finished_games.append(game)
                        else:
                            team.scheduled_games.append(game)

    def __connect_players_and_teams(self):
        # Take last team_id in player's gamelog, make that their team
        # If a player switches teams, team won't update until a game is logged
        for player in self.players:
            for team in self.teams:
                try:
                    if player.gamelog[-1].team_id == team.id:
                        player.team = team
                        team.players.append(player)
                        break
                # Exception if player gamelog is empty
                except IndexError:
                    break
        
        # Sort player list in NBATeam objects by min/game
        def sort_by_minutes_played(player):
            mins = []
            for game in player.gamelog[-25:]:
                mins.append(game.minutes)
            return sum(mins) / len(mins)
        
        for team in self.teams:
            team.players.sort(key=sort_by_minutes_played, reverse=True)

    def __connect_props_and_players(self):
        props = self.__get_player_props()
        for player in self.players:
            for i in range(len(props) - 1, -1, -1):
                name = props[i].player_name
                if name == player.full_name or name in player.alt_names:
                    player.props.append(props.pop(i))
        # Temp while I figure out names that need added to alt_player_names.json
        unmatched_names = []
        for prop in props:
            if prop.player_name not in unmatched_names:
                unmatched_names.append(prop.player_name)
        print('Player prop unmatched names:')
        print(unmatched_names)

    def __connect_injuries_and_players(self):
        injuries = self.__get_player_injuries()
        for player in self.players:
            for injury in injuries:
                name = injury['name']
                if name == player.full_name or name in player.alt_names:
                    player.injury_status = injury
                    injuries.remove(injury)
                    break
        # Temp while I figure out names that need added to alt_player_names.json
        unmatched_names = []
        for injury in injuries:
            if injury['name'] not in unmatched_names:
                unmatched_names.append(injury['name'])
        print('Injuries unmatched names:')
        print(unmatched_names)

    def __set_player_position(self):
        for player in self.players:
            for game in player.gamelog:
                if game.position is not None:
                    player.all_positions.append(game.position)
            try:
                player.position = player.all_positions[-1]
                player.all_positions = set(player.all_positions)
                player.base_position = player.position[-1]
            # Exception if player.all_positions is empty
            except IndexError:
                continue

    def create_player_prop_tables(self, date_obj: datetime, prop_dict: dict):
        """
        Gather info for player prop analysis table and return in Pandas 
        DataFrame.
        """

        # Need defensive performance data for all teams vs stat
        def_ranks = self.__get_def_ranks_vs_stats(prop_dict['str_to_stat'])

        # Get games for given datetime object
        info = []
        games = self.__get_game_objects(date_obj)
        for game in games:
            # These dicts are used for all props within this game
            matchup_info = self.__get_matchup_info(game)
            inj_info = self.__get_injury_info(game)
            for team in [game.away.team, game.home.team]:
                # Get stats for all recent players vs opponent
                opp_obj = matchup_info[team.id]['raw']['opp']
                recent_players_vs = self.__get_recent_player_stats_vs(
                    opp_obj,
                    prop_dict['str_to_stat']
                )
                # Go through all players on both team for matching props
                # If props match dict key, gather player, def, analysis info
                for player in team.players:
                    props = player.get_props(prop_dict['key'])
                    if len(props) == 0:
                        continue
                    pl_info = self.__get_player_info(player)
                    prop_info = self.__get_player_prop_info(props)
                    pl_perf = self.__get_player_prop_performance_info(
                        player, 
                        prop_dict['str_to_stat'], 
                        prop_info['line'],
                        matchup_info[team.id]['raw']['loc'],
                        opp_obj,
                        inj_info['player_objs'][team.id]
                    )
                    def_perf = self.__get_def_vs_prop_performance_info(
                        player,
                        opp_obj, 
                        def_ranks,
                        recent_players_vs
                    )
                    perf_analysis = self.__get_performance_analysis_info(
                        player,
                        opp_obj,
                        prop_dict['str_to_stat'],
                        prop_info['line'],
                        matchup_info[team.id]['raw']['loc'],
                        def_ranks
                    )
                    # Will be None if gp threshold is not met
                    if perf_analysis is None:
                        continue
                    
                    row = (pl_info + matchup_info[team.id]['display'] 
                           + inj_info['display'] + prop_info['display'] 
                           + pl_perf + def_perf + perf_analysis)
                    info.append(row)

        # Build table and sort by total of prop analysis values
        table = pd.DataFrame(info)
        table = table.sort_values(table.columns[423], ascending=False)
        return table.reset_index(drop=True)
                    
    def create_alt_player_prop_tables(self):
        pass

    def create_core_tables(self):
        pass

    def tables_to_excel(self, file_name: str, tables: list):
        """
        Given a file name and a list of Pandas Dataframes, create an Excel 
        Workbook with a sheet for each table. Tables in list must be tuples 
        with format (pd, sheet_name)
        """
        
        path = 'excel/nba/' + file_name
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        
        for table in tables:
            table[0].to_excel(writer, sheet_name=table[1], header=False, 
                              index=False)

        writer.close()

    def __get_game_objects(self, date_obj: datetime):
        """Given datetime object, return game objects for that day"""

        games = []
        for game in reversed(self.games):
            if game.datetime.date() == date_obj.date():
                games.append(game)
                in_range = True
            elif 'in_range' in locals():
                break
        return games

    def __get_def_ranks_vs_stats(self, stat: str):
        """Given str_to_stat, return dict with defensive ranks."""

        # Initialize rank dict with team IDs
        def_ranks = {}
        for team in self.teams:
            def_ranks[team.id] = {}
        
        # Define columns and positions
        columns = ['Team', 'L5', 'L10', 'L20', 'Season']
        positions = ['all', 'G', 'F', 'C']

        # Make table for each pos with all team values for each split
        for pos in positions:
            info = []
            for team in self.teams:
                def_ranks[team.id][pos] = {}
                gp_season = team.get_no_of_gp(seasons=[self.season])
                n_games = max(20, gp_season)
                stats_against = team.get_tot_stats_against([stat], pos=pos, 
                                                           n_games=n_games)
                rank_splits = [5, 10, 20, gp_season]
                stat_splits = []
                for split in rank_splits:
                    stat_avg = round(sum(stats_against[-split:]) / split, 2)
                    stat_splits.append(stat_avg)
                row = [team] + stat_splits
                info.append(row)
            table = pd.DataFrame(info, columns=columns)
            
            # Loop through each rank split, sort by split, and add ranks
            for col in columns[-4:]:
                table = table.sort_values([col, 'Season'], ascending=True)
                table = table.reset_index(drop=True)
                table = self.__add_rank_index(table, col)
                # Go through each row, get rank and split value for dict
                for i in range(len(table)):
                    temp_dict = {
                        'rank': table.loc[i, 'Rank'],
                        'value': table.loc[i, col]
                        }
                    def_ranks[table.loc[i, 'Team'].id][pos][col] = temp_dict

        return def_ranks
    
    def __add_rank_index(self, table: pd, col: str):
        """
        Add column to provided Dataframe ranking values in col. Different from 
        index bc if values in col are equal, the rank will be same.
        """

        # Delete previous rank col, if it exists
        try:
            table.drop(columns='Rank', inplace=True)
        except KeyError:
            pass

        ranks = []
        prev_value = 0
        i, j = 1, 1
        for value in table[col]:
            if value == prev_value:
                ranks.append(i)
            else:
                ranks.append(j)
                i = j
            j += 1
            prev_value = value
        table.insert(0, 'Rank', ranks)
        return table
    
    def __get_matchup_info(self, game: NBAGame):
        """Given game object, return dict with matchup info"""

        home_matchup = 'vs ' + game.away.team.code
        away_matchup = 'at ' + game.home.team.code
        date_time = game.datetime.strftime('%A, %B %-d @ %-I:%M%p')

        return {
            game.home.id: {
                'display': [home_matchup, date_time],
                'raw': {
                    'opp': game.away.team,
                    'loc': 'home'
                    }
            },
            game.away.id: {
                'display': [away_matchup, date_time],
                'raw': {
                    'opp': game.home.team,
                    'loc': 'away'
                    }
            }
        }

    def __get_injury_info(self, game: NBAGame):
        """Given NBA Game obj, return dict with injury info."""
        
        inj_per_team = 5
        display_report = []
        player_objs = {}

        # Loop through all players on both teams to find injuries
        for team in [game.away.team, game.home.team]:
            team_report = [team.code]
            player_objs[team.id] = []
            for player in team.players:
                if player.injury_status is not None:
                    # Append items to team report
                    team_report.append(player.position)
                    team_report.append(player.first_name[0] + '. ' +
                                       player.last_name)
                    if player.injury_status['status'] == 'Out':
                        team_report.append('OUT')
                    elif player.injury_status['status'] == 'Day-To-Day':
                        team_report.append('GTD')
                    else:
                        team_report.append(None)

                    # Append IDs to dict
                    player_objs[team.id].append(player)

                if len(team_report) == (inj_per_team * 3) + 1:
                    break
            # If inj list not full, fill with None
            team_report = self.__fill_with_none(team_report, (inj_per_team*3)+1)
            display_report += team_report

        return {
            'display': display_report,
            'player_objs': player_objs
        }
    
    def __get_recent_player_stats_vs(self, opp: NBATeam, stat: str):
        """
        Return dict, where the player's pos points to recent related player
        stats vs the opp defense.
        """

        game_list = opp.get_ind_stats_against(['position', 'first_name',
                                               'last_name', stat, 'location',
                                               'opponent', 'date'], n_games=6)
        
        n_players = 2
        top_g, top_f, top_pf_c = [], [], []
        for game in game_list:
            temp_g, temp_f, temp_pf_c = [], [], []
            # Add players to appropriate list
            for log in game:
                if log[0][-1] == 'G':
                    temp_g.append(log)
                if log[0][-1] == 'F':
                    temp_f.append(log)
                if log[0] in ['PF', 'C']:
                    temp_pf_c.append(log)
            # Sort temp lists by stat value, then take top n_players
            temp_g = sorted(temp_g, key=lambda log: log[3], 
                            reverse=True)[:n_players]
            temp_f = sorted(temp_f, key=lambda log: log[3], 
                            reverse=True)[:n_players]
            temp_pf_c = sorted(temp_pf_c, key=lambda log: log[3],
                               reverse=True)[:n_players]
            # Append temp to macthing lists
            top_g.append(temp_g)
            top_f.append(temp_f)
            top_pf_c.append(temp_pf_c)

        # Make dict where key is position, and points to similar players
        recent_pl_vs = {}
        for pos in ['PG', 'SG', 'G']:
            recent_pl_vs[pos] = top_g
        for pos in ['SF', 'F']:
            recent_pl_vs[pos] = top_f
        for pos in ['PF', 'C']:
            recent_pl_vs[pos] = top_pf_c

        return recent_pl_vs
    
    def __get_player_info(self, player: NBAPlayer):
        """
        Given NBAPlayer obj, return list with basic player info for analysis 
        tables.
        """

        if player.jersey is not None:
            jersey = str(player.jersey)
        else:
            jersey = ''

        att = player.position + ' ● ' + player.team.code + ' ● #' + jersey
        return [player.first_name, player.last_name, player.team.code, att]

    def __get_player_prop_info(self, props: list):
        """
        Given list of NBAProp objects, return list with player prop info for 
        analysis tables, along with the consensus line that will be used for 
        analysis.
        """

        books = 4
        lines = []
        for prop in props:
            lines.append(prop.line)
        # Consensus line will be most common line. If theres a tie, first
        # to appear is chosen
        consensus = sorted(lines, key=lambda x: lines.count(x), reverse=True)[0]

        prop_info = {}
        for prop in props:
            # Create dict from bookmaker if it doesn't yet exist
            if prop.bookmaker_name not in prop_info:
                prop_info[prop.bookmaker_name] = {}
            # Add line and odds to dict
            prop_info[prop.bookmaker_name]['line'] = prop.line
            if prop.name in ['Over', 'Yes']:
                prop_info[prop.bookmaker_name]['over'] = prop.price
            elif prop.name in ['Under', 'No']:
                prop_info[prop.bookmaker_name]['under'] = prop.price
        
        # Take dict items and form into list
        prop_info_lst = [props[0].market_name, consensus]
        for book, item in prop_info.items():
            prop_info_lst.append(book)
            prop_info_lst.append(item.get('line', None))
            prop_info_lst.append(item.get('over', None))
            prop_info_lst.append(item.get('under', None))

        # If prop list not full, fill with None
        prop_info_lst = self.__fill_with_none(prop_info_lst, 2+(books*4))

        return {
            'display': prop_info_lst,
            'line': consensus
        }

    def __get_player_prop_performance_info(self, player: NBAPlayer, stat: str, 
                                           line: float, loc: str, opp: NBATeam, 
                                           inj: list):
        """
        Return list with player performance info for analysis tables.\n
        Includes overall, home/away, vs {opp}, w/o player 1, w/o player 2
        """

        # Splits and lengths for blocks and graphs
        avg_splits_all = [5, 10, 20, player.get_no_of_gp(seasons=[self.season])]
        avg_splits_loc = [5, 10, 20, player.get_no_of_gp(seasons=[self.season],
                                                         loc=loc)]
        avg_splits_opp = [3, 6, 9, player.get_no_of_gp(opps=[opp.id])]
        len_graph_all = 20
        len_graph_loc = 20
        len_graph_opp = 10

        # Get stats for overall averages and graph
        avg_all = self.__get_player_averages(player, stat, avg_splits_all, 1)
        graph_all = self.__get_graph_stats(player, stat, line, 
                                           n_games=len_graph_all)

        # Get stats for location based averages and graph
        avg_loc_title = [loc.capitalize()]
        avg_loc = self.__get_player_averages(player, stat, avg_splits_loc, 1, 
                                             loc=loc)
        avg_loc = avg_loc_title + avg_loc
        graph_loc = self.__get_graph_stats(player, stat, line, loc=loc, 
                                           n_games=len_graph_loc)

        # Get stats for opponent based averages and graph
        avg_opp_title = [f'vs {opp.code}']
        avg_opp = self.__get_player_averages(player, stat, avg_splits_opp, 1,
                                             opps=[opp.id])
        avg_opp = avg_opp_title + avg_opp
        graph_opp = self.__get_graph_stats(player, stat, line, opps=[opp.id], 
                                           n_games=len_graph_opp)

        # Get stats for without blocks
        wo_players = self.__find_similar_players(player, inj, 2)
        wo_blocks = []
        for pl in wo_players:
            wo_blocks.append(f'w/o  {pl.first_name[0]}. {pl.last_name}')
            wo_blocks += self.__get_with_without_block_stats(player, stat, 
                                                        without_player=[pl.id], 
                                                        n_games=6)
        wo_blocks = self.__fill_with_none(wo_blocks, 38)

        # Combine lists and return
        return avg_all + graph_all + avg_loc + graph_loc + avg_opp + \
            graph_opp + wo_blocks
    
    def __get_def_vs_prop_performance_info(self, player: NBAPlayer, 
                                           opp: NBATeam, def_ranks: dict,
                                           recent_pl_vs: list):
        """
        Return list with def vs prop performance info for analysis tables.
        Includes opp vs all, opp vs pos, and recent players vs blocks.
        """

        expand_pos = {'all': 'All', 'G': 'Guards', 
                      'F': 'Forwards', 'C': 'Centers'}
        splits = ['L5', 'L10', 'L20', 'Season']

        # Get stats and ranks for def vs all and vs pos blocks
        def_vs_blocks = []
        for pos in ['all', player.base_position]:
            def_vs_blocks += [f'{opp.code} vs {expand_pos[pos]}']
            for split in splits:
                value = def_ranks[opp.id][pos][split]['value']
                rank_value = def_ranks[opp.id][pos][split]['rank']
                rank_display = self.__make_ordinal(rank_value)
                def_vs_blocks += [value, rank_display]

        # Get stats for recent players vs blocks
        recent_vs_blocks = []
        games = recent_pl_vs[player.position]
        for game in reversed(games):
            game_block = []
            for log in game:
                pos = log[0]
                name = f'{log[1][0]}. {log[2]}'
                stat = log[3]
                matchup = self.__condense_matchup_info([log[4]], [log[5]], 
                                                       [log[6]])
                game_block += [pos, name, stat, matchup[0]]
            game_block = self.__fill_with_none(game_block, 8)
            # Add all but last item, don't need matchup twice
            recent_vs_blocks += game_block[:-1]
        
        return def_vs_blocks + recent_vs_blocks

    def __get_performance_analysis_info(self, player: NBAPlayer, opp: NBATeam, 
                                        stat: str, line: float, loc: str, 
                                        def_ranks: dict):
        """"""

        # Get performance analysis values
        s_pl_all = self.__analyze_player_prop_performance(player, stat, line, 
                                                          seasons=[self.season])
        s_pl_loc = self.__analyze_player_prop_performance(player, stat, line, 
                                                          seasons=[self.season],
                                                          loc=loc)
        s_pl_opp = self.__analyze_player_prop_performance(player, stat, line,
                                                          opp=[opp.id])
       
        def_vs_all_ranks = def_ranks[opp.id]['all']
        def_vs_pos_ranks = def_ranks[opp.id][player.base_position]
        s_def_all = self.__analyze_def_vs_stat_performance(opp, 
                                                           def_vs_all_ranks)
        s_def_pos = self.__analyze_def_vs_stat_performance(opp, 
                                                           def_vs_pos_ranks)

        # Define weight values
        w_pl_all = 0.4
        w_pl_loc = 0.2
        w_pl_opp = 0.2
        if s_pl_opp is None:
            w_pl_all = 0.5
            w_pl_loc = 0.3
            w_pl_opp = 0
        elif s_pl_opp is None and s_pl_loc is None:
            w_pl_all = 0.8
            w_pl_loc = 0
            w_pl_opp = 0
        elif s_pl_opp is None and s_pl_loc is None and s_pl_all is None:
            return None
        
        w_def_all = 0.1
        w_def_pos = 0.1

        # Calculate total performance value
        total = 0
        for s, w in zip([s_pl_all, s_pl_loc, s_pl_opp, s_def_all, s_def_pos],
                        [w_pl_all, w_pl_loc, w_pl_opp, w_def_all, w_def_pos]):
            if s is not None:
                total += s*w
        total = round(total*100, 2)

        # Round score values for display
        scores = []
        for s in [s_pl_all, s_pl_loc, s_pl_opp, s_def_all, s_def_pos]:
            if s is not None:
                scores.append(round(s*100))
            else:
                scores.append(None)

        return scores + [total]


    def __analyze_player_prop_performance(self, player: NBAPlayer, stat: str,
                                          line: float, seasons=[], loc='all', 
                                          opp=[]):
        """
        Return metric representing player performance vs. given stat.\n
        seasons = list of int\n
        loc = 'home', 'away' or 'all'\n
        opp = list of player id ints
        """
        
        # Get player metrics
        gp = player.get_no_of_gp(loc=loc, opps=opp)
        # Define 4th split based on performance analysis type (all, loc, or opp)
        if len(opp) == 0:
            spl_4 = player.get_no_of_gp(seasons=seasons, loc=loc)
        else:
            spl_4 = gp
        
        m = self.__get_player_metrics(gp, spl_4)
        # Length will be zero if gp threshold not met
        if len(m) == 0:
            return None
        
        # Calculate avg vs line metrics
        avgs = self.__get_player_averages(player, stat, m['splits']['avl'],
                                          loc=loc, opps=opp)
        m_avl = []
        for avg in avgs:
            m_avl.append(self.__calculate_avg_vs_line_metric(avg, line))

        # Calculate log vs line metrics
        log = player.get_stats([stat], loc=loc, opps=opp)
        m_cover = []
        for split in m['splits']['cover']:
            m_cover.append(self.__calculate_log_vs_line_metric(log[-split:], 
                                                               line))
              
        # Apply weights to metrics
        for i in range(len(m_avl)):
            m_avl[i] *= m['weights']['avl'][i]
            m_cover[i] *= m['weights']['cover'][i]
        
        return sum(m_avl) + sum (m_cover)

    def __analyze_def_vs_stat_performance(self, opp: NBATeam, def_ranks: dict):
        """
        Return metric representing defensive performance vs. given stat.\n
        def_ranks should be dict from def_ranks[opp.id][pos]
        """

        # Get defensive metrics
        m = self.__get_def_metrics(opp)

        # Calculate rank vs stat metrics
        m_rvs = []
        for split in def_ranks.values():
            m_rvs.append(self.__calculate_rank_vs_stat_metric(split['rank']))

        # Apply weights to metrics
        for i in range(len(m_rvs)):
            m_rvs[i] *= m['weights']['rvs'][i]

        return sum(m_rvs)

    def __calculate_avg_vs_line_metric(self, avg: float, line: float):
        """Use average stat value and line to determine performance value."""
        
        ratio = avg / line
        if ratio < 0.5:
            ratio = 0.5
        elif ratio > 2:
            ratio = 2
        return np.interp(ratio, [0.5, 1, 2], [0, 0.5, 1])

    def __calculate_log_vs_line_metric(self, log: list, line: float):
        """
        Take stat log and line to see how often the line has been covered 
        and return a performance value.
        """

        count = 0
        for stat in log:
            if stat > line:
                count += 1
        return count / len(log)

    def __calculate_rank_vs_stat_metric(self, rank: int):
        """Take rank value and divide by 30 to calc performance value"""
        
        return rank / 30
    
    def __get_player_metrics(self, gp: int, spl_4: int):
        """
        Return player splits and weights based on number of games played.\n 
        Split 4 will also need to be provided. Will either be gp this season
        if determining metrics for overall or home/away, or will be gp all time 
        if getting metrics for vs opponent.
        """

        # Determine split values based on games played
        if gp >= 40:
            spl_1 = 5
            spl_2 = 10
            spl_3 = 20
            spl_4 = spl_4
        elif 4 <= gp < 40:
            spl_1 = round(gp/7.99)
            spl_2 = round(gp/4)
            spl_3 = round(gp/2)
            spl_4 = spl_4
        else:
            return {}

        # Weights for main metrics
        avl = 0.3
        cover = 0.7

        # Weights for individual splits
        if spl_4 >= 4:
            avl_1 = avl*(7/20)
            avl_2 = avl*(5/20)
            avl_3 = avl*(4/20)
            avl_4 = avl*(4/20)
            cov_1 = cover*(7/20)
            cov_2 = cover*(5/20)
            cov_3 = cover*(4/20)
            cov_4 = cover*(4/20)
        # If spl_4 is less than 4, split 4th metric weight and set as zero
        else:
            avl_1 = avl*(9/20)
            avl_2 = avl*(6/20)
            avl_3 = avl*(5/20)
            avl_4 = 0
            cov_1 = cover*(9/20)
            cov_2 = cover*(6/20)
            cov_3 = cover*(5/20)
            cov_4 = 0

        return {
            'splits': {
                'avl': [spl_1, spl_2, spl_3, spl_4],
                'cover': [spl_1, spl_2, spl_3, spl_4]
            },
            'weights': {
                'avl': [avl_1, avl_2, avl_3, avl_4],
                'cover': [cov_1, cov_2, cov_3, cov_4]
            }
        }

    def __get_def_metrics(self, opp: NBATeam):
        """
        Return player weights based on number of games played. Same splits 
        that are used for display will be used in analysis.
        """

        # Weights for individual splits (only one)
        rvs = 1

        # Weights for individual splits
        gp_season = opp.get_no_of_gp(seasons=[self.season])
        if gp_season >= 3:
            rvs_1 = rvs*(4/20)
            rvs_2 = rvs*(5/20)
            rvs_3 = rvs*(5/20)
            rvs_4 = rvs*(6/20)
        # If gp_season is less than 3, split 4th metric weight and set as zero
        else:
            rvs_1 = rvs*(6/20)
            rvs_2 = rvs*(6/20)
            rvs_3 = rvs*(8/20)
            rvs_4 = 0

        return {
            'weights': {
                'rvs': [rvs_1, rvs_2, rvs_3, rvs_4]
            }
        }

    def __get_player_averages(self, player: NBAPlayer, stat: str, splits: list,
                              n_round: int=2, loc='all', opps: list=[]):
        """Return list with player stat averages."""

        stat_log = player.get_stats([stat], loc=loc, opps=opps)

        averages = []
        for split in splits:
            if len(stat_log) >= split and split != 0:
                avg = sum(stat_log[-split:]) / split
                averages.append(round(avg, n_round))
            else:
                averages.append(None)
        return averages

    def __get_graph_stats(self, player: NBAPlayer, stat: str, line: float, 
                          loc='all', opps: list=[], n_games=20):
        """Return list with stats ready for analysis graphs."""

        mins, stats, locs, opps_2, dates = player.get_stats(['minutes', stat, 
                                                     'location', 'opponent', 
                                                     'date'], loc=loc, 
                                                     opps=opps, 
                                                     n_games=n_games)

        stats_over = [stat if stat > line else None for stat in stats]
        stats_under = [stat if stat < line else None for stat in stats]
        matchups = self.__condense_matchup_info(locs, opps_2, dates)

        # Length of all variables should equal n_games
        mins = self.__fill_with_none(mins, n_games)
        stats = self.__fill_with_none(stats, n_games)
        stats_over = self.__fill_with_none(stats_over, n_games)
        stats_under = self.__fill_with_none(stats_under, n_games)
        matchups = self.__fill_with_none(matchups, n_games)

        return mins + stats + stats_over + stats_under + matchups
        
    def __get_with_without_block_stats(self, player: NBAPlayer, stat: str,  
                                 without_player: list=[], with_player: list=[],
                                 n_games=6):
        """
        Return list with stats ready for with/without analysis blocks.\n
        with/without_player inputs must be list of player IDs.
        """

        mins, stats, locs, opps, dates = player.get_stats(['minutes', stat, 
                                            'location', 'opponent', 'date'],
                                            without_player=without_player,
                                            with_player=with_player,
                                            n_games=n_games)
        matchups = self.__condense_matchup_info(locs, opps, dates)
        
        stat_list = []
        for i, j, k in zip(reversed(mins), reversed(stats), reversed(matchups)):
            stat_list += [i, j, k]
        stat_list = self.__fill_with_none(stat_list, n_games)
        return stat_list

    def __condense_matchup_info(self, locs: list, opps: list, dates: list):
        """Return list with condensed matchup info (vs. LAC 12/30/23)"""

        matchups = []
        for loc, opp, date in zip(locs, opps, dates):
            if loc == 'home':
                matchup = f'vs {opp} {date}'
            elif loc == 'away':
                matchup = f'at {opp} {date}'
            else:
                matchup = f'{opp} {date}'
            matchups.append(matchup)
        return matchups
    
    def __fill_with_none(self, lst: list, end_length: int):
        """Return list filled to end length with None type values."""

        while len(lst) < end_length:
            lst.append(None)
        return lst
    
    def __find_similar_players(self, main_player: NBAPlayer, player_list: list, 
                               n: int):
        """
        Return n NBAPlayer object(s) from player_list that are most comparable
        to player. player_list must be list of NBAPlayer objects.
        """
        
        similar_players = []
        for player in player_list:
            if (player.position == main_player.position 
                and player != main_player):
                similar_players.append(player)
        for player in player_list:
            if (player.base_position == main_player.base_position and 
                player not in similar_players + [main_player]):
                similar_players.append(player)
        for player in player_list:
            if player not in similar_players + [main_player]:
                similar_players.append(player)
        return similar_players[:n]
    
    def __make_ordinal(self, n: int):
        """Convert an integer into its ordinal representation i.e. 1 -> 1st"""
        n = int(n)
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        return str(n) + suffix
    

if __name__ == "__main__":
    analysis = NBADataAnalysis()
    prop_handler = FileHandler('api_keys_player_prop_markets.json', 'data/nba/odds')
    props = prop_handler.load_file()
    date_obj = datetime.fromisoformat("2024-02-03T20:30:00-05:00")
    for prop in props:
        analysis.create_player_prop_tables(date_obj, prop)

    #file_path = 'data/nba/odds/player_props'
    #files = sorted(os.listdir(file_path))
    #player_props = []
    #for file in files:
        #prop_handler = FileHandler(file, file_path)
        #props = prop_handler.load_file()
        #for i in range(len(props) -1, -1, -1):
            #if props[i]['bookmaker_key'] == 'espnbet':
                #del props[i]
        #prop_handler = FileHandler(file, file_path)
        #prop_handler.write_file(props)
        