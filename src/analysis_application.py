import sys
import pandas as pd

import get_data
import get_data_api as api
from data_analysis import NFLDataAnalysis


class AnalysisApplication:
    def __init__(self):
        pass

    def main_menu(self):
        print()
        print('Please select a sport:')
        print('1: NFL')
        print('2: NBA')
        print('3: NHL')
        print('4: MLB')
        print()
        print('exit: Exit program')

    def exit(self):
        sys.exit()
   
    def main_execute(self):
        self.main_menu()
        while True:
            print()
            command = input('Command: ')
            if command == '1':
                nfl_app = NFLAnalysisApplication()
                nfl_app.nfl_main_execute()
            if command == '2':
                pass
            if command == '3':
                pass
            if command == '4':
                pass
            elif command == 'exit':
                self.exit()
            else:
                self.main_menu()


class NFLAnalysisApplication:
    def __init__(self):
        self.update_dynamic_data()
        self.analysis = NFLDataAnalysis()

    def update_dynamic_data(self):
        # Update data that changes throughout week (i.e. injuries, weather, lines)
        
        get_data.scrape_all_injuries()
        # Function call for updating weather
        # Function call for updating gambling lines

    def initialize_objects(self):
        self.analysis = NFLDataAnalysis()

    def reload_all_data(self):
        get_data.scrape_all_player_info()
        get_data.scrape_all_player_gamelogs()
        get_data.scrape_all_injuries()
        get_data.scrape_all_team_info()
        get_data.scrape_all_def_gamelogs()
        get_data.scrape_def_season_stats()
        get_data.scrape_def_vs_position()
        get_data.scrape_all_gamelog_schedule()

    def reload_lines(self):
        get_data.get_upcoming_games('nfl')
        get_data.get_lines('nfl')

    def update_weekly_data(self):
        # Update data that changes each NFL week (i.e. gamelogs, player info,
        # def season stats, def vs pos, gamelog/schedule)
        pass

    def update_player_stats_workbook(self):
        tables = []
        for prop in api.markets['nfl']:
            stat_type = prop['stat_type']
            stat = prop['stat']
            name = prop['display_name']
            tables.append((self.analysis.player_stats_table(stat_type, stat), name))

        self.analysis.tables_to_excel('Player_Stat_Tables.xlsx', tables=tables)

    def update_def_vs_stats_workbook(self):
        tables = []
        for prop in api.markets['nfl']:
            # Don't include receiving stats, they are the same as passing
            if prop['stat_type'] == 're':
                continue
            stat_type = prop['stat_type']
            stat = prop['stat']
            name = prop['display_name']
            tables.append((self.analysis.stats_against_table(stat_type, stat), name))

        # Insert Rushing TDs table after Rushing Yds
        tables.insert(8, (self.analysis.stats_against_table('ru', 'tds'), 'Rushing TDs'))
        self.analysis.tables_to_excel('Def_vs_Stat_Tables.xlsx', tables=tables)

    def update_def_vs_pos_vs_stats_workbook(self):
        tables = []
        for prop in api.markets['nfl']:
            # Don't include passing or kicking, those are only done by QB and K (typically)
            if prop['stat_type'] not in ['attd', 'ru', 're']:
                continue
            stat_type = prop['stat_type']
            stat = prop['stat']
            name = prop['display_name']
            tables.append((self.analysis.stats_against_by_pos_table(stat_type, stat), name))

        # Insert Rushing TDs and Receiving TDs after ATTD
        tables.insert(1, (self.analysis.stats_against_by_pos_table('ru', 'tds'), 'Rushing TDs'))
        tables.insert(2, (self.analysis.stats_against_by_pos_table('re', 'tds'), 'Receiving TDs'))
        self.analysis.tables_to_excel('Def_vs_Pos_vs_Stat_Tables.xlsx', tables=tables)

    def update_prop_analysis_workbook(self):
        tables = []
        first = True
        all_props = pd.DataFrame()
        
        # Loop through prop dicts to create separate tables and 'All Props' table
        for prop in api.markets['nfl']:
            name = prop['display_name']
            table = self.analysis.display_prop_analysis(prop)
            tables.append((table, name))
            
            # Build 'All Props' table, skipping 'Anytime TDs'
            if first:
                first = False
                continue
            else:
                all_props = pd.concat([all_props, table])

        # Sort 'All Props' and insert after 'Anytime TDs' tab
        all_props = all_props.sort_values(['analysis_tot', 'analysis_pl'], ascending=False).reset_index(drop=True)
        tables.insert(1, (all_props, 'All Props'))
        
        self.analysis.tables_to_excel('NFL_Prop_Analysis_Tables_Data.xlsx', tables=tables)

    def exit(self):
        sys.exit()

    def nfl_main_menu(self):
        print()
        print('What would you like to do?')
        print('--------------------------')
        print('1: Reload All Data')
        print('2: Reload All Lines')
        print()
        print('3: Update Player Stats Tables')
        print('4: Update Defensive Stats Tables')
        print('5: Update Prop Analysis Tables')
        print()
        print('6: Return to Main Menu')
        print('7: Exit Program')
        print('--------------------------')

    def nfl_main_execute(self):
        self.nfl_main_menu()
        while True:
            print()
            command = input('Command: ')
            if command == '1':
                self.reload_all_data()
                self.initialize_objects()
            elif command == '2':
                self.reload_lines()
                self.initialize_objects()
            elif command == '3':
                self.update_player_stats_workbook()
            elif command == '4':
                self.update_def_vs_stats_workbook()
                self.update_def_vs_pos_vs_stats_workbook()
            elif command == '5':
                self.update_prop_analysis_workbook()
            elif command == '6':
                break
            elif command == '7':
                self.exit()
            else:
                self.nfl_main_menu()


if __name__ == "__main__":
    app = AnalysisApplication()
    app.main_execute()