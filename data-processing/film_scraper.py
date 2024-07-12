'''
    For scraping films listed at https://letterboxd.com/films/
'''

from members_scraper import fetch_html
from bs4 import BeautifulSoup
import pandas as pd
import asyncio
import aiohttp
import time


async def scrape_films_page(page, session):
    '''
        Takes in integer representing page number and aiohttp.ClientSession object and scrapes said page number on Letterboxd's popular film list.
        Returns list of dicts representing film info including film name, href link, and it's popularity ranking.
    '''

    # Calculating film ranking, since there's 72 films listed on a single Letterboxd films page
    film_num = (72 * (page-1))

    url = f'https://letterboxd.com/films/ajax/popular/page/{page}/'
    _, html = await fetch_html(url, session)
    data = []

    try:
        # Getting list of all films on film page using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        films = soup.find_all("li", class_="listitem poster-container")

        if not films:
            attempts = 1

            # If server response error, wait 5 seconds and try again
            while not soup.find('div', class_='pagination') and attempts < 10:
                time.sleep(5)
                _, html = await fetch_html(url, session)
                soup = BeautifulSoup(html, 'lxml')
                films = soup.find_all("li", class_="listitem poster-container")
                attempts += 1

            if attempts == 10:
                print(f"Server response error while scraping film page #{page}")

        for film in films:
            film_num += 1

            item = {}
            film_info = film.find('div')
            item['Film Name'] = film_info.find('img').attrs['alt']
            item['Film Link'] = film_info.attrs['data-target-link']
            item['Ranking'] = film_num

            data.append(item)

        print(f'Scraped film page #{page}')

    except Exception as err:
        print(f'Error scraping page film page #{page}: {err}')

    finally:
        return data


async def main():
    data = []

    open("data/films.csv", "w").close()

    t0 = time.time()

    # Asynchronously scraping all film data (appx. 950k films as of 7/11/24) and saving to data/films.csv
    async with aiohttp.ClientSession() as session:
        tasks = []
        page = 1
        all_films_scraped = False

        while not all_films_scraped:
            # Dump data to csv every 1000 pages scraped
            if page != 1 and (page - 1) % 1000 == 0:
                df = pd.DataFrame(data)
                df.to_csv("data/films.csv", mode='a')
                data = []

            # Sending 50 requests at a time
            for p in range(page, page+50):
                tasks.append(scrape_films_page(p, session))

            responses = await asyncio.gather(*tasks)
            page += 50
            tasks = []

            # Once a response is empty, no more film data to be scraped
            for response in responses:
                if not response:
                    all_films_scraped = True
                else:
                    data += response

    # Cleaning up data that hasn't been dumped to csv and dumping it
    if len(data) > 0:
        df = pd.DataFrame(data)
        df.to_csv("data/films.csv", mode='a')

    t1 = time.time()

    print(f'Scraped {page-1} pages in {(t1-t0)/60} minutes. That\'s {1/((page-1)/((t1-t0)/60))} mins/pg.')
    print("Films finished scraping")

if __name__ == '__main__':
    asyncio.run(main())