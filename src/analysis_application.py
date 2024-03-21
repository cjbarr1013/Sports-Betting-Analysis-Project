import sys
from datetime import datetime
import pandas as pd

import get_data
import get_data_api as api
from file_handler import FileHandler
from data_analysis import NBADataAnalysis


class AnalysisApplication:
    def __init__(self):
        self.sport = None
        self.analysis = None

    def initialize_objects(self):
        if self.sport == 'nba':
            get_data.get_player_injuries(self.sport)
            self.analysis = NBADataAnalysis()
        elif self.sport == 'nfl':
            pass
        elif self.sport == 'nhl':
            pass
        elif self.sport == 'mlb':
            pass

    def complete_data_reload(self):
        """Completely reload all team, game, player, and player stats data for 
        all seasons.\n
        311/100 API calls, cost $0.0311, 31.1 min."""
        
        # Get list of all seasons
        seasons = get_data.get_seasons(self.sport)
        
        # Get team data, then load into teams variable
        get_data.get_team_data(self.sport)
        json_handler = FileHandler(f'{self.sport}_teams.json', f'data/{self.sport}/teams')
        teams = json_handler.load_file()
        
        # Get only player data for current season
        # Player objects in data_analysis are only needed for active players
        get_data.get_player_data(self.sport, seasons[-1])

        # Go through all seasosn and get game data and player stats
        for season in seasons:
            get_data.get_game_data(self.sport, season)
            for team in teams:
                get_data.get_player_stats_data(f'{self.sport}', team['id'], season)

    def refresh_data(self):
        """Refresh all team, game, player, and player stats data for current season.
        Can use if last update occured during the current season.\n
        63/100 API calls, cost $0.00, 6.3 min."""
        
        # Get current season
        season = get_data.get_seasons(self.sport)[-1]
        
        # Get team data, then load into teams variable
        get_data.get_team_data(self.sport)
        json_handler = FileHandler(f'{self.sport}_teams.json', f'data/{self.sport}/teams')
        teams = json_handler.load_file()
        
        # For current season, get game and player data, and player stats
        get_data.get_game_data(self.sport, season)
        get_data.get_player_data(self.sport, season)
        for team in teams:
            get_data.get_player_stats_data(self.sport, team['id'], season)

    def refresh_core_lines(self, date_str: str):
        """Use market keys and date string to get odds for featured markets.\n
        Will result in (3 x n_events)/20,000 API calls."""

        markets_handler = FileHandler('api_keys_core_markets.json', 'src')
        markets = markets_handler.load_file()
        for market in markets:
            get_data.get_core_market_odds(self.sport, market, date_str)

    def refresh_player_prop_lines(self, date_str: str):
        """Update events.json, then use market keys and date string to get odds
        for all markets other than the featured markets.\n
        Will results in (n_markets x n_events)/20,000 API calls."""

        get_data.get_events(self.sport, date_str)
        markets_handler = FileHandler('api_keys_player_prop_markets.json', 
                                      f'data/{self.sport}/odds')
        markets = markets_handler.load_file()
        for market in markets:
            get_data.get_additional_market_odds(self.sport, market)

    def update_core_analysis_workbook(self):
        pass

    def update_player_prop_analysis_workbook(self, date_str: str):
        """"""

        markets_handler = FileHandler('api_keys_player_prop_markets.json', 
                                      f'data/{self.sport}/odds')
        markets = markets_handler.load_file()
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        tables = []
        # Loop through prop dicts to create separate tables and add to tables
        for market in markets:
            table = self.analysis.create_player_prop_tables(date_obj, market)
            tables.append((table, market['abv_name']))

        table_name = f'{self.sport}_prop_analysis_tables_data.xlsx'
        self.analysis.tables_to_excel(table_name, tables=tables)

    def input_date(self):
        dt = input('Please input date in format yyyy-mm-dd: ')
        return dt

    def exit(self):
        sys.exit()

    def main_menu(self):
        print()
        print('Please select a sport:')
        print('1: NBA')
        print('2: NFL')
        print('3: NHL')
        print('4: MLB')
        print()
        print('exit: Exit program')
   
    def main_execute(self):
        self.main_menu()
        while True:
            print()
            command = input('Command: ')
            if command == '1':
                self.sport = 'nba'
                self.sport_execute()
            elif command == '2':
                self.sport = 'nfl'
                self.sport_execute()
            elif command == '3':
                self.sport = 'nhl'
                self.sport_execute()
            elif command == '4':
                self.sport = 'mlb'
                self.sport_execute()
            elif command == 'exit':
                self.exit()
            else:
                self.main_menu()

    def sport_menu(self):
        print()
        print('What would you like to do?')
        print('--------------------------')
        print('00: Complete Reload of Game, Player, and Team Data')
        print()
        print('auto: Toggle Auto')
        print()
        print('1: Refresh Data')
        print('2: Refresh Core Lines')
        print('3: Refresh Player Prop Lines')
        print()
        print('4: Update Core Analysis Workbook')
        print('5: Update Player Prop Analysis Workbook')
        print()
        print('6: Refresh Data and Core Lines + Update Core Analysis Workbook')
        print('7: Refresh Data and Player Prop Lines + Update Player Prop Analysis Workbooks')
        print('8: Refresh All Data and Lines + Update All Analysis Workbooks')
        print()
        print('main: Return to Main Menu')
        print('exit: Exit Program')
        print('--------------------------')

    def sport_execute(self):
        self.sport_menu()
        while True:
            print()
            command = input('Command: ')
            if command == '00':
                self.complete_data_reload()
            elif command == 'auto':
                pass
            elif command == '1':
                self.refresh_data()
            elif command == '2':
                dt = self.input_date()
                self.refresh_core_lines(dt)
            elif command == '3':
                dt = self.input_date()
                self.refresh_player_prop_lines(dt)
            elif command == '4':
                self.initialize_objects()
                self.update_core_analysis_workbook()
            elif command == '5':
                dt = self.input_date()
                self.initialize_objects()
                self.update_player_prop_analysis_workbook(dt)
            elif command == '6':
                dt = self.input_date()
                self.refresh_data()
                self.refresh_core_lines(dt)
                self.initialize_objects()
                self.update_core_analysis_workbook()
            elif command == '7':
                dt = self.input_date()
                self.refresh_data()
                self.refresh_player_prop_lines(dt)
                self.initialize_objects()
                self.update_player_prop_analysis_workbook(dt)
            elif command == '8':
                dt = self.input_date()
                self.refresh_data()
                self.refresh_core_lines(dt)
                self.refresh_player_prop_lines(dt)
                self.initialize_objects()
                self.update_core_analysis_workbook()
                self.update_player_prop_analysis_workbook(dt)
            elif command == 'main':
                self.main_menu()
                break
            elif command == 'exit':
                self.exit()
            else:
                self.sport_menu()


if __name__ == "__main__":
    app = AnalysisApplication()
    app.main_execute()