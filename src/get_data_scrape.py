import requests
from bs4 import BeautifulSoup
import pandas as pd
pd.set_option('display.max_columns', None)

import time
from random import randint
from functools import reduce

# Request webpage and use .text to return the content of the response in Unicode, not bytes like .content would
# then remove comments so we can access all tables. Give to BeautifulSoup to create our soup object.
# Pause for a few moments so we don't go beyond website access limit
def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url).text.replace("<!--","").replace("-->","")
    time.sleep(randint(4, 6))
    return BeautifulSoup(r, "html.parser")

# Getting both over headings (Passing, Rushing, Receiving, etc.), and subheadings (Yds, TDs, etc.) from each table.
# If there are no over headers, just return subheadings
def get_headers(table_html) -> list:
    over_headers = []
    if len(table_html.find('thead').find_all('tr')) == 2:
        for th in table_html.find('thead').find('tr').find_all('th'):
            if th.get('colspan') != None:
                over_headers.append({th.get_text(): int(th.get('colspan'))})
            else:
                over_headers.append({th.get_text(): 1})
        
        column_headers = [th.get_text() for th in table_html.find('thead').find_all('tr')[1].find_all('th')]
    else:
        column_headers = [th.get_text() for th in table_html.find('thead').find('tr').find_all('th')]

    if len(over_headers) > 0:
        return rename_headers(over_headers, column_headers)
    else:
        return column_headers

# Taking the first 2 letters from the over headers and adding them to the beginning of each subheading
# to distinguish subheadings with the same name
def rename_headers(over_headers, column_headers) -> list:
    headers = []
    col = 0
    for dict in over_headers:
        for key in dict:
            for span in range(dict[key]):
                try:
                    header = key[0:2] + column_headers[col]
                except:
                    header = column_headers[col]
                headers.append(header)
                col += 1
    return headers

# Go through table data and get all table data, including 'Rk' value so length matches header length.
# 'Row' list will == 1 if line is heading becuase it will find only 1 'th' value and no 'td' values
# but we have to find this 'th' value because this is where 'Rk' value is stored
def get_stats(table_html) -> list:
    stats = []
    for line in table_html.find('tbody').find_all('tr'):
        rk = line.find('th').get_text()
        row = [rk] + [td.get_text() for td in line.find_all('td')]
        if len(row) != 1:
            stats.append(row)
    
    return stats

# Main loop for gettings all tables, checking that they aren't == 'None', and combining them into one table
# (Option #1) put in a list of one table_id if yu want to make a simple table
# (Option #2) put in a list of two table_ids to make one table, if on same webpage, share headers, and want to concat vertical
# (Option #3) put in a list of four table_ids to make on table if situation is similar to making QB tables,
# as in, you have 2 sets of 2 table_ids, you'll concat each set vertically, then merge those concats horizontally
def table_maker(soup: BeautifulSoup, ids: list) -> pd:
    start = True
    table = None
    tables = []
    for i in range(len(ids)):
        table_html = soup.find('table', id=ids[i])
        
        if table_html == None:
            if i in [1, 3] and start == False:
                start = True
                tables.append(table)
            continue
        
        h, s = get_headers(table_html), get_stats(table_html)

        # If number of headers and number of columns of data are not same, then ignore table
        # For example, Tua Tagovailoa has one playoff game where he was not active
        try:
            temp_table = pd.DataFrame(s, columns=h)
        except ValueError:
            continue

        if start:
            table = temp_table
            keys = h[:10]
            start = False
        elif set(h).issubset(table.columns) or set(table.columns).issubset(h):
            table = pd.concat([table, temp_table])

        if i in [1, 3]:
            start = True
            tables.append(table)

    try:
        table = pd.merge(tables[0], tables[1], how='outer', on=keys)
    except IndexError:
        pass
    
    return table

# Adding data from normal gamelogs that is missing from advanced gamelogs to table for QBs
# Cmp%, TD, Int, Rate, Sk, Y/A,  and AY/A from normal gamelog and calculate rushing Y/A
def insert_missing_QB_data(soup: BeautifulSoup, table: pd) -> pd:
    # Must make table here because you cannot concat two tables with duplicate column names ('PaYds')
    temp = table_maker(soup, ['stats'])
    temp = remove_duplicate_cols(temp)
    temp2 = table_maker(soup, ['stats_playoffs'])
    if temp2 is not None:
        temp2 = remove_duplicate_cols(temp2)
        temp = pd.concat([temp, temp2])

    temp = remove_rows_by_values(temp, 'Year', [str(i) for i in list(range(2000, 2018))])
    temp = remove_rows_by_values(temp, 'GS', ['*', ''], reverse=True)
    temp = temp.reset_index(drop=True)

    try:
        pa_yds_index = table.columns.get_loc('PaYds')
        indices = ['PaAY/A', 'PaY/A', 'PaRate', 'PaInt', 'PaTD', 'PaCmp%']
        for i in indices:
            table.insert(pa_yds_index+1, i, temp[i])
    except KeyError:
        pass
    
    try:
        result_index = table.columns.get_loc('Result')
        table.insert(result_index+1, 'GS', temp['GS'])
    except KeyError:
        pass

    try:
        ru_yds_index = table.columns.get_loc('RuYds')
        table.insert(ru_yds_index+1, 'RuY/A', get_rush_ypa(table))
    except KeyError:
        pass

    return table

# Adding data from normal gamelogs that is missing from advanced gamelogs to table for RBs, WRs, and TEs
# rushing Y/A and recieving Y/R, Ctch%, and Y/Tgt
def insert_missing_RWT_data(table: pd) -> pd:
    try:
        ru_yds_index = table.columns.get_loc('RuYds')
        table.insert(ru_yds_index+1, 'RuY/A', get_rush_ypa(table))
    except KeyError:
        pass

    try:
        re_tds_index = table.columns.get_loc('ReTD')
        table.insert(re_tds_index+1, 'ReY/Tgt', get_rec_ypt(table))
        table.insert(re_tds_index+1, 'ReCtch%', get_rec_catch_pct(table))
        table.insert(re_tds_index+1, 'ReY/R', get_rec_ypr(table))
    except KeyError:
        pass
    
    return table

# Calculate rushing yards/att and return in a list given a table
def get_rush_ypa(table: pd) -> list:
    rush_ypa = []
    for y, a in zip(table['RuYds'], table['RuAtt']):
        try:
            rush_ypa.append(round(int(y)/int(a), 1))
        except (ZeroDivisionError, ValueError):
            rush_ypa.append(0.0)
    return rush_ypa

# Calculate yards/rec and return in a list given a table
def get_rec_ypr(table: pd) -> list:
    rec_ypr = []
    for y, r in zip(table['ReYds'], table['ReRec']):
        try:
            rec_ypr.append(round(int(y)/int(r), 1))
        except (ZeroDivisionError, ValueError):
            rec_ypr.append(0.0)
    return rec_ypr

# Calculate catch% and return in a list given a table
def get_rec_catch_pct(table: pd) -> list:
    catch_pct = []
    for r, t in zip(table['ReRec'], table['ReTgt']):
        try:
            catch_pct.append(round((int(r)/int(t))*100, 1))
        except (ZeroDivisionError, ValueError):
            catch_pct.append(0.0)
    return catch_pct

# Calculate yards/target and return in a list given a table
def get_rec_ypt(table: pd) -> list:
    rec_ypt = []
    for y, t in zip(table['ReYds'], table['ReTgt']):
        try:
            rec_ypt.append(round(int(y)/int(t), 1))
        except (ZeroDivisionError, ValueError):
            rec_ypt.append(0.0)
    return rec_ypt

# Providing a column name and list of values, if one of the values is in the given column, remove the row
# If reverse=True, then keep the rows containing the values in the given column
def remove_rows_by_values(table: pd, col: str, values: list, reverse=False) -> pd:
    if reverse:
        return table[table[col].isin(values)]
    else:
        return table[~table[col].isin(values)]

# Cleaning up table
# Removes duplicate columns, keeping the first occurence
def remove_duplicate_cols(table: pd) -> pd:
    return table.loc[:, ~table.columns.duplicated()]

# Separate Result into 2 separate columns ('W/L/T', 'Result')
def split_result(table: pd) -> pd:
    results = [item.split(" ") for item in table['Result']]
    opp_index = table.columns.get_loc('Opp') 
    table.insert(opp_index+1, 'W/L/T', [item[0] for item in results])
    table['Result'] = [item[1] for item in results]
    return table

# Sort data in table by date, then reset the index, dropping the original one
def sort_by_date(table: pd) -> pd:
    return table.sort_values(by=['Date']).reset_index(drop=True)

# Drops unwanted columns from table by name, first make new column list containing only values that are in table
# to avoid error
def drop_cols(table: pd, cols: list) -> pd:
    cols = [i for i in cols if i in table.columns]
    return table.drop(columns=cols)

# Rename specified columns
def rename_cols(table: pd, cols: dict) -> pd:
    return table.rename(columns=cols)

# Change items in loc from '@', '', 'N' to 'A', 'H', 'N' for clarity and to differentiate from
# missing data elsewhere in the table
def change_loc(table: pd) -> pd:
    table['Loc'].replace('@', 'A', inplace=True)
    table['Loc'].replace('', 'H', inplace=True)
    return table

# Create final table by concating our table to an empty table with columns that are consistent
# across all players sharing the same position. Used for player gamelogs
# Also replace 'NaN' and empty spaces with '0'
def finalize_table(table: pd, cols: list) -> pd:
    empty_table = pd.DataFrame(columns=cols)
    table = pd.concat([empty_table, table])
    table = zero_empty_spaces(table)
    return table

# Replace 'NaN' and empty spaces with '0'
def zero_empty_spaces(table: pd) -> pd:
    """Replace 'NaN' and empty spaces with '0'"""
    
    table.fillna(0, inplace=True)
    table.replace('', 0, inplace=True)
    return table

def rename_duplicate_headers(table: pd) -> pd:
    """Change names of headers that share the a name, so they can later
    be manipulated. i.e. (yds, rec, yds, rec) -> (yds1, rec2, yds3, rec4)"""

    headers = list(table.columns)
    new_headers = []
    count = 1
    for i in headers:
        if headers.count(i) > 1:
            new_headers.append(i + str(count))
            count += 1
        else:
            new_headers.append(i)
    table.columns = new_headers
    return table


## Define lists and dicts needed for functions
# QB IDs MUST BE IN THIS ORDER FOR TABLE MAKER TO WORK PROPERLY
qb_adv_table_ids = ['advanced_passing', 'advanced_passing_playoffs',
                'advanced_rushing_and_receiving', 'advanced_rushing_and_receiving_playoffs']

rwt_adv_table_ids = ['advanced_rushing_and_receiving', 'advanced_rushing_and_receiving_playoffs']

k_table_ids = ['stats', 'stats_playoffs']

qb_cols_to_drop = ['Rk', 'ReTgt', 'ReRec', 'ReYds', 'ReTD', 'Re1D', 'ReYBC',
                'ReYBC/R', 'ReYAC', 'ReYAC/R', 'ReADOT', 'ReBrkTkl', 'ReRec/Br',
                'ReDrop', 'ReDrop%', 'ReInt', 'ReRat']

rwt_cols_to_drop = ['Rk']

def_gl_cols_to_drop = ['Boxscore', 'Day']

k_cols_to_drop = ['Rk', 'GS', 'PaCmp', 'PaAtt', 'PaCmp%', 'PaYds1', 'PaTD', 'PaInt', 'PaRate',
                  'PaSk', 'PaYds2', 'PaY/A', 'PaAY/A', 'ScTD', 'Sk', 'TaSolo', 'TaAst', 'TaComb',
                  'TaTFL', 'TaQBHits', 'PuPnt', 'PuYds', 'PuY/P', 'PuRetYds', 'PuNet', 'PuNY/P', 
                  'PuTB', 'PuTB%', 'PuIn20', 'PuIn20%', 'PuBlck', 'OfNum', 'OfPct', 'DeNum', 
                  'DePct', 'STNum', 'STPct', 'Status']

qb_rwt_k_cols_to_rename = {'': 'Loc', 'Year': 'Season'}

qb_final_cols = ['Season', 'Date', 'G#', 'Week', 'Age', 'Tm', 'Loc', 'Opp', 'W/L/T', 'Result',
                 'GS', 'PaCmp', 'PaAtt', 'PaYds', 'PaCmp%', 'PaTD', 'PaInt', 'PaRate', 'PaY/A',
                 'PaAY/A', 'Pa1D', 'Pa1D%', 'PaIAY', 'PaIAY/PA', 'PaCAY', 'PaCAY/Cmp', 'PaCAY/PA',
                 'PaYAC', 'PaYAC/Cmp', 'PaDrops', 'PaDrop%', 'PaBadTh', 'PaBad%', 'PaSk', 'PaBltz',
                 'PaHrry', 'PaHits', 'PaPrss', 'PaPrss%', 'PaScrm', 'PaYds/Scr', 'RuAtt', 'RuYds',
                 'RuY/A', 'RuTD', 'Ru1D', 'RuYBC', 'RuYBC/Att', 'RuYAC', 'RuYAC/Att', 'RuBrkTkl',
                 'RuAtt/Br']

rwt_final_cols = ['Season', 'Date', 'G#', 'Week', 'Age', 'Tm', 'Loc', 'Opp', 'W/L/T', 'Result',
                  'RuAtt', 'RuYds', 'RuY/A', 'RuTD', 'Ru1D', 'RuYBC', 'RuYBC/Att', 'RuYAC', 
                  'RuYAC/Att', 'RuBrkTkl', 'RuAtt/Br', 'ReTgt', 'ReRec', 'ReYds', 'ReTD', 'ReY/R', 
                  'ReCtch%', 'ReY/Tgt', 'Re1D', 'ReYBC', 'ReYBC/R', 'ReYAC', 'ReYAC/R', 'ReADOT',
                  'ReBrkTkl', 'ReRec/Br', 'ReDrop', 'ReDrop%', 'ReInt', 'ReRat']

k_final_cols = ['Season', 'Date', 'G#', 'Week', 'Age', 'Tm', 'Loc', 'Opp', 'W/L/T', 'Result',
                'XPM', 'XPA', 'XP%', 'FGM', 'FGA', 'FG%', 'Pts']

# Not final, will drop 'Boxscore', but these are used to rename before concatenation (can't concat if cols have same names)
def_gl_cols = ['Week', 'Day', 'Date', 'Boxscore', 'W/L/T', 'OT', 'Loc', 'Opp', 'ScTm',
               'ScOpp', 'PaCmp', 'PaAtt', 'PaYds', 'PaTD', 'PaInt', 'PaSk', 'PaSkYds',
               'PaY/A', 'PaNY/A', 'PaCmp%', 'PaRate', 'RuAtt', 'RuYds', 'RuY/A', 'RuTD',
               'FGM', 'FGA', 'XPM', 'XPA', 'PuPnt', 'PuYds', '3DConv', '3DAtt', '4DConv',
               '4DAtt', 'ToP']


## Utilizing functions to scrape and format gamelog data into final tables
# Get QB's gamelog given PFR player_id. Will go back to 2018, or later if not active by that point.
def get_qb_gamelog(player_id: str) -> pd:
    adv_soup = get_soup(f'https://www.pro-football-reference.com/players/{player_id[0]}/{player_id}/gamelog/advanced/')
    gl_soup = get_soup(f'https://www.pro-football-reference.com/players/{player_id[0]}/{player_id}/gamelog/')
    table = table_maker(adv_soup, qb_adv_table_ids)
    if table is not None:
        table = insert_missing_QB_data(gl_soup, table)
        table = drop_cols(table, qb_cols_to_drop)
        table = rename_cols(table, qb_rwt_k_cols_to_rename)
        table = change_loc(table)
        table = split_result(table)
        table = sort_by_date(table)
        table = finalize_table(table, qb_final_cols)
    return table

# Get RB, WR, TE gamelog given PFR player_id. Will go back to 2018, or later if not active by that point.
def get_rwt_gamelog(player_id: str) -> pd:
    soup = get_soup(f'https://www.pro-football-reference.com/players/{player_id[0]}/{player_id}/gamelog/advanced/')
    table = table_maker(soup, rwt_adv_table_ids)
    if table is not None:
        table = insert_missing_RWT_data(table)
        table = drop_cols(table, rwt_cols_to_drop)
        table = rename_cols(table, qb_rwt_k_cols_to_rename)
        table = change_loc(table)
        table = split_result(table)
        table = sort_by_date(table)
        table = finalize_table(table, rwt_final_cols)
    return table

# Get kickers's gamelog given PFR player_id. Will go back to 2018, or later if not active by that point.
# Will build tables here instead of in table_maker() because of repeating column names
def get_k_gamelog(player_id: str) -> pd:
    soup = get_soup(f'https://www.pro-football-reference.com/players/{player_id[0]}/{player_id}/gamelog/')
    
    table_stats = table_maker(soup, ['stats'])
    table_playoffs = table_maker(soup, ['stats_playoffs'])
    if table_stats is not None or table_playoffs is not None:
        table_stats = rename_duplicate_headers(table_stats)
        table_stats = rename_duplicate_headers(table_stats)

        table = pd.concat([table_stats, table_playoffs])

        table = remove_rows_by_values(table, 'Year', [str(i) for i in list(range(1900, 2018))])
        table = remove_rows_by_values(table, 'GS', ['*', ''], reverse=True)
        table = drop_cols(table, k_cols_to_drop)
        table = rename_cols(table, qb_rwt_k_cols_to_rename)
        table.columns = [col[2:] if col[0:2] == 'Sc' else col for col in table.columns]
        table = change_loc(table)
        table = split_result(table)
        table = sort_by_date(table)
        table = finalize_table(table, k_final_cols)
        return table
    return table_stats

# Get Def gamelog going back to 2018 given PFR team_id.
# Has basic passing, rushing, kicking, punting, 3rd+4th down conv, and TOP
def get_def_gamelogs(team_id: str) -> pd:
    year = 2018
    start = True

    while True:
        tables = []
        url = f'https://www.pro-football-reference.com/teams/{team_id}/{str(year)}/gamelog/'
        soup = get_soup(url)
        temp_gl_table = table_maker(soup, [f'gamelog_opp{str(year)}'])
        temp_playoff_gl_table = table_maker(soup, [f'playoff_gamelog_opp{str(year)}'])
        tables.extend((temp_gl_table, temp_playoff_gl_table))
        for t in tables:    
            if t is not None:
                t.columns = def_gl_cols
                t.insert(0, 'Season', [year for i in range(len(t))])
                if start:
                    table = t
                    start = False
                else:
                    table = pd.concat([table, t])
        year += 1
        if tables[0] is None:
            break

    table = drop_cols(table, def_gl_cols_to_drop)
    table = change_loc(table)
    table = remove_rows_by_values(table, 'W/L/T', [''])
    table = table.reset_index(drop=True)
    return table

# Get tables for basic stats allowed to QB, RB, WR, TE for the given year
def get_def_vs_pos(year) -> pd:
    tables = []

    for i in ['QB', 'RB', 'WR', 'TE']:
        url = f'https://www.pro-football-reference.com/years/{year}/fantasy-points-against-{i}.htm'
        soup = get_soup(url)
        table = table_maker(soup, ['fantasy_def'])
        
        if table is not None:
            table = drop_cols(table, ['FaFantPt', 'FaDKPt', 'FaFDPt'])
            tables.append((table, i))
        else:
            break
        
    return tables

# Current table for current season stats 
# G, PA, Yds, ToPly, ToY/P, ToTO, FL, 1stD, Passing def, Rushing def, kicking ag, conversions ag
# Will build tables here instead of in table_maker() because of overlapping names
def get_def_season_stats(year) -> pd:
    url = f'https://www.pro-football-reference.com/years/{year}/opp.htm'
    soup = get_soup(url)

    table = None
    tables = []

    team_stats = table_maker(soup, ['team_stats'])
    if team_stats is not None:
        team_stats = drop_cols(team_stats, [col for col in team_stats.columns if col[0:2] in ['Rk', 'Pa', 'Ru', 'Pe']])
        team_stats = rename_cols(team_stats, {'PA': 'ToPA', 'Yds': 'ToYds', 'FL': 'ToFL', '1stD': 'To1stD', 'EXP': 'ToEXP'})

        adv_passing_stats = table_maker(soup, ['advanced_defense'])
        adv_passing_stats = drop_cols(adv_passing_stats, ['Att', 'Cmp', 'Yds', 'TD', 'Sk'])
        adv_passing_stats.columns = ['Pa' + col if col not in ['Tm', 'G', 'MTkl'] else col for col in adv_passing_stats.columns]

        passing_stats = table_maker(soup, ['passing'])
        passing_stats = rename_duplicate_headers(passing_stats)
        passing_stats = drop_cols(passing_stats, ['Rk'])
        passing_stats.columns = ['Pa' + col if col not in ['Tm', 'G'] else col for col in passing_stats.columns]
        passing_stats = rename_cols(passing_stats, {'PaYds1': 'PaYds', 'PaYds2': 'PaSkYds'})

        rushing_stats = table_maker(soup, ['rushing'])
        rushing_stats = drop_cols(rushing_stats, ['Rk'])
        rushing_stats.columns = ['Ru' + col if col not in ['Tm', 'G'] else col for col in rushing_stats.columns]

        kicking_stats = table_maker(soup, ['kicking'])
        kicking_stats = drop_cols(kicking_stats, ['Rk'])
        kicking_stats.columns = [col[2:] if col[0:2] == 'Sc' else col for col in kicking_stats.columns]

        conversion_stats = table_maker(soup, ['team_conversions'])
        conversion_stats = drop_cols(conversion_stats, ['Rk'])
        conversion_stats.columns = [col[2:] if col[0:2] in ['Do', 'Re'] else col for col in conversion_stats.columns]
        
        tables.extend((team_stats, adv_passing_stats, passing_stats, rushing_stats, kicking_stats, conversion_stats))

        table = reduce(lambda left, right: pd.merge(left, right, on=['Tm', 'G']), tables)
    
    return table

## Player and team info
# Get all player name, player_id, position, and team_id from fantasy and kicking pages for QB, RB, WR, TE, K
def get_basic_player_info(year) -> list:
    qb_rwt_soup = get_soup(f'https://www.pro-football-reference.com/years/{year}/fantasy.htm')
    k_soup = get_soup(f'https://www.pro-football-reference.com/years/{year}/kicking.htm')
    qb_rwt_html = qb_rwt_soup.find('table', id='fantasy')
    k_html = k_soup.find('table', id='kicking')

    players = []
    if qb_rwt_html is not None and k_html is not None:
        for table in [qb_rwt_html.find('tbody').find_all('tr'), k_html.find('tbody').find_all('tr')]:
            for row in table:
                player = {}
                td = row.find_all('td', limit=4)
                if len(td) == 0:
                    continue

                if td[2].get_text() in ['QB', 'RB', 'WR', 'TE']:
                    player['position'] = td[2].get_text()
                elif td[3].get_text() == 'K':
                    player['position'] = td[3].get_text()
                else:
                    continue
                
                player['name'] = td[0].get_text()
                player['player id'] = td[0].get('data-append-csv')
                
                if td[1].get_text() not in ['2TM', '3TM', '4TM']: # if == 2TM, 3TM, or 4TM, go to player page and get team id
                    player['team id'] = td[1].find('a').get('href').split('/')[2]
                else:
                    player['team id'] = get_team_id_for_player(player['player id'])
                
                players.append(player)
    
    return players

# Given the player_id, get the player's team_id from their PFR page
def get_team_id_for_player(player_id: str) -> str:
    soup = get_soup(f'https://www.pro-football-reference.com/players/{player_id[0]}/{player_id}.htm')
    div_html = soup.find(id='meta')
    return div_html.find_all('div', limit=2)[1].find_all('p', limit=4)[3].find('a').get('href').split('/')[2]

# Get team id, initials, and name for all 32 teams by parsing player fantasy page (best place initials are available)
def get_basic_team_info(year) -> list:
    teams = []
    soup = get_soup(f'https://www.pro-football-reference.com/years/{year}/fantasy.htm')
    table_html = soup.find('table', id='fantasy')

    if table_html is not None:
        for row in table_html.find('tbody').find_all('tr'):
            team = {}
            unique = True
            td = row.find_all('td', limit=3)
            if len(td) == 0:
                continue

            if td[1].get_text() not in ['2TM', '3TM', '4TM']:
                team['team initials'] = td[1].get_text()
                team['team name'] = td[1].find('a').get('title')
                team['team id'] = td[1].find('a').get('href').split('/')[2]
            else:
                continue
            
            for item in teams:
                if item['team id'] == team['team id']:
                    unique = False
                    break           
            if unique:
                teams.append(team)

            if len(teams) == 32:
                break
    
    return teams

# Get season, week #, date, time, home and away teams and scores for every game in the entire league in a given year
def get_all_gamelog_schedule(year) -> list:
    games = []
    soup = get_soup(f'https://www.pro-football-reference.com/years/{year}/games.htm')
    table_html = soup.find('table', id='games')

    if table_html is not None:
        for row in table_html.find('tbody').find_all('tr'):
            game = {}
            td = row.find_all('td')
            if len(td) == 0 or td[1].get_text() == 'Playoffs':
                continue

            game['game id'] = td[6].find('a').get('href').split('/')[2].replace('.htm', '')
            game['season'] = year
            game['week'] = row.find('th').get_text()
            game['day'] = td[0].get_text()
            game['date'] = td[1].get_text()
            game['time'] = td[2].get_text()
            
            if td[4].get_text() == '@':
                game['home team id'] = td[5].find('a').get('href').split('/')[2]
                game['home team name'] = td[5].find('a').get_text()
                game['away team id'] = td[3].find('a').get('href').split('/')[2]
                game['away team name'] = td[3].find('a').get_text()
                game['home points'] = td[8].get_text()
                game['away points'] = td[7].get_text()
            elif td[4].get_text() == '' or td[4].get_text() == 'N':
                game['home team id'] = td[3].find('a').get('href').split('/')[2]
                game['home team name'] = td[3].find('a').get_text()
                game['away team id'] = td[5].find('a').get('href').split('/')[2]
                game['away team name'] = td[5].find('a').get_text()
                game['home points'] = td[7].get_text()
                game['away points'] = td[8].get_text()
            else:
                continue

            games.append(game)
            
    return games

# Get a list of dictionaries of player injuries, including player id, game status, practice status, and comments from PFR
# only includes QB, RB, WR, TE, and K
def get_player_injuries() -> list:
    injuries = []
    soup = get_soup('https://www.pro-football-reference.com/players/injuries.htm')
    table_html = soup.find('table', id='injuries')

    for row in table_html.find('tbody').find_all('tr'):
        injury = {}
        td = row.find_all('td')
        if len(td) == 0:
            continue
        
        if td[1].get_text() in ['QB', 'RB', 'WR', 'TE', 'K']:
            injury['player id'] = row.find('th').get('data-append-csv')
            injury['game status'] = td[2].get_text()
            injury['practice status'] = td[4].get_text()
            injury['comment'] = td[3].get_text()
        else:
            continue

        injuries.append(injury)

    return injuries


## Testing ##
if __name__ == "__main__":
    #gamelogs = get_all_gamelog_schedule('2023')
    #for gamelog in gamelogs:
        #print(gamelog)

    print(get_qb_gamelog('MullNi00'))
    
    #tables = get_def_vs_pos('2023')
    #for table in tables:
        #print(table)


    # Saving HTML .txt files for testing to folder 'html_files'
    #soup = get_soup('https://www.pro-football-reference.com/years/2023/opp.htm')
    #table = table_maker(soup, ['returns'])
    #file_path = os.path.join('testing/html_files', 'team_def_stats.txt')
    #with open(file_path, 'w') as f:
        #f.write(soup.prettify())
    