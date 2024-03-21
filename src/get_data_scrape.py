import requests
from bs4 import BeautifulSoup

import time
from random import randint

# Request webpage and use .text to return the content of the response in Unicode, not bytes like .content would
# then remove comments so we can access all tables. Give to BeautifulSoup to create our soup object.
# Pause for a few moments so we don't go beyond website access limit
def get_soup(url: str) -> BeautifulSoup:
    headers = requests.utils.default_headers()
    headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
    })

    r = requests.get(url, headers=headers).text.replace("<!--","").replace("-->","")
    time.sleep(randint(4, 6))
    return BeautifulSoup(r, "html.parser")

# Get a list of dictionaries of player injuries, including player id, game status, practice status, and comments from PFR
# only includes QB, RB, WR, TE, and K
def get_player_injuries(sport: str):
    injuries = []
    soup = get_soup(f'https://www.espn.com/{sport}/injuries')
    for table in soup.find_all('table'):
        for row in table.find('tbody').find_all('tr'):
            injury = {}
            
            td = row.find_all('td')
            injury['name'] = td[0].get_text()
            injury['status'] = td[3].find('span').get_text()
            injury['comment'] = td[4].get_text()
            
            injuries.append(injury)

    return injuries


## Testing ##
if __name__ == "__main__":

    print(get_player_injuries('nba'))
    