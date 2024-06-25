from bs4 import BeautifulSoup
import pandas as pd
import time
import asyncio
import aiohttp
from members_scraper import fetch_html


async def scrape_films_page(page, session):
    # print(f'Scraping film page #{page}. . .')

    film_num = (72 * (page-1))

    url = f'https://letterboxd.com/films/ajax/popular/page/{page}/'
    html = await fetch_html(url, session)
    data = []

    # print(html)

    try:
        soup = BeautifulSoup(html, 'lxml')

        films = soup.find_all("li", class_="listitem poster-container")

        if not films:
            attempts = 0

            # If server response error, wait 5 seconds and try again
            while not soup.find('div', class_='pagination') and attempts < 5:
                time.sleep(5)
                html = await fetch_html(url, session)
                soup = BeautifulSoup(html, 'lxml')
                films = soup.find_all("li", class_="listitem poster-container")
                attempts += 1

            if attempts == 5:
                print(f"Server response error while scraping film page #{page}")

        for film in films:
            film_num += 1

            item = {}
            film_info = film.find('div')
            # print(f'{film_info}\n')
            item['Film Name'] = film_info.find('img').attrs['alt']
            item['Film Link'] = film_info.attrs['data-target-link']
            item['Ranking'] = film_num

            data.append(item)

        print(f'Scraped film page #{page}. . .')

    except Exception as err:
        print(f'Error scraping page film page #{page}: {err}')

    finally:
        return data


async def main():
    data = []

    open("data/films.csv", "w").close()

    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []
        page = 1
        all_films_scraped = False

        while not all_films_scraped:
            # print(page-1)
            # Dump data every 1000 pages scraped
            if page != 1 and (page - 1) % 1000 == 0:
                # print('hi')
                df = pd.DataFrame(data)
                df.to_csv("data/films.csv", mode='a')
                data = []

            for p in range(page, page+50):
                # print(f'Scraping film page #{p}. . .')
                tasks.append(scrape_films_page(p, session))

            responses = await asyncio.gather(*tasks)
            page += 50
            tasks = []

            for response in responses:
                if not response:
                    all_films_scraped = True
                else:
                    data += response

            # time.sleep(.25)

    if len(data) > 0:
        df = pd.DataFrame(data)
        df.to_csv("data/films.csv", mode='a')

    t1 = time.time()

    print(f'Scraped {page-1} pages in {(t1-t0)/60} minutes. That\'s {1/((page-1)/((t1-t0)/60))} mins/pg.')

    print("Films finished scraping")

if __name__ == '__main__':
    asyncio.run(main())