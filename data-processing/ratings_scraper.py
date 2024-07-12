'''
    For scraping Letterboxd user pages.
'''

from members_scraper import fetch_html
from bs4 import BeautifulSoup
import pandas as pd
import asyncio
import aiohttp
import time   


async def get_num_film_pages(member, session):
    '''
        Takes in string representing Letterboxd user href and aiohttp.ClientSession object.
        Returns integer representing number of pages necessary to scrape to collect all user ratings.
    '''

    url = f'https://letterboxd.com{member}films/'
    (resp_code, html) = await fetch_html(url, session)

    attempts = 1
    while resp_code != 200 and attempts < 100:
        (resp_code, html) = await fetch_html(url, session)
        attempts += 1

    try:
        if resp_code != 200:
            raise Exception(f"Response code {resp_code}")
        
        # Parsing page using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        paginate_pages = soup.find_all("li", class_="paginate-page")

        return int(paginate_pages[-1].find('a').text) if paginate_pages else 1
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for member {member}: {err}")


async def scrape_member_ratings(member, page, session):
    '''
        Takes in string representing Letterboxd user href, int representing page number, and aiohttp.ClientSession object.  
        Returns tuple of list of dicts representing user rated data and list of dict representings user unrated data respectively.
    '''

    url = f'https://letterboxd.com{member}films/page/{page}/'
    (resp_code, html) = await (fetch_html(url, session))

    attempts = 1
    while resp_code != 200 and attempts < 100:
        (resp_code, html) = await (fetch_html(url, session))
        attempts += 1

    rated_data = []
    unrated_data = []

    try:
        # Parsing data using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        films = soup.find_all("li", class_="poster-container")   

        for film in films:
            rating_span = film.find('p').find('span')

            if rating_span: 
                rating = rating_span.attrs['class'][-1].split('-')[1]
                if rating != "16": # Adding to rated data
                    item = {}
                    item['User'] = member
                    film_info = film.find('div')
                    item['Film'] = film_info.find('img').attrs['alt']
                    item['Film Link'] = film_info.attrs['data-target-link']
                    item['Rating'] = rating

                    rated_data.append(item)

                else: # If got rating of 16, it means the user liked the film but didn't rate it. Add to unrated data.
                    item = {}
                    item['User'] = member
                    film_info = film.find('div')
                    item['Film'] = film_info.find('img').attrs['alt']
                    item['Film Link'] = film_info.attrs['data-target-link']

                    unrated_data.append(item)                    

            # If user doesn't have rating for film, add to unrated data
            else: 
                item = {}
                item['User'] = member
                film_info = film.find('div')
                item['Film'] = film_info.find('img').attrs['alt']
                item['Film Link'] = film_info.attrs['data-target-link']

                unrated_data.append(item)

    except Exception as err:
        print(f"Error scraping member {member}, film page #{page}: {err}")

    finally: 
        return (rated_data, unrated_data)
    

async def main():
    pages_scraped = 0

    # Scraping member pages listed in data/members.csv
    with open("data/members.csv") as fh:
        fh.readline()
        members_lines = fh.readlines()

    open("data/ratings.csv", "w").close()

    t0 = time.time()

    # Scraping all films logged by members in data/members.csv
    async with aiohttp.ClientSession() as session:
        users_scraped = 0
        data = []

        for line in members_lines:
            # After every 100 members' ratings are scraped, dump data to data/ratings.csv
            if users_scraped != 0 and users_scraped % 100 == 0:
                df = pd.DataFrame(data)
                df.to_csv("data/ratings.csv", mode='a')
                data = []
                users_scraped = 0

            tasks = []
            member = line.split(',')[1].strip()

            try:
                # Get number of pages user has filled in ratings
                tasks.append(get_num_film_pages(member, session))
                pages = (await asyncio.gather(*tasks))[0]
                pages_scraped += 1
                
                # Scraping every page user has filled in ratings
                tasks = []
                for page in range(1, pages + 1):
                    print(f'Scraping member {member}, page {page}. . .')
                    tasks.append(scrape_member_ratings(member, page, session))
                responses = await asyncio.gather(*tasks)

                rating_sum = sum(len(rated_data) for rated_data, _ in responses)
                if rating_sum: # Only store data if user rated any films
                    mean_rating = round(sum(int(data['Rating']) for rated_data, _ in responses for data in rated_data ) / rating_sum, 2)
                    for rated_data, unrated_data in responses:
                        data += rated_data

                        if unrated_data:
                            for i in range(len(unrated_data)):
                                unrated_data[i]['Rating'] = mean_rating

                            data += unrated_data

                pages_scraped += pages
                print(f'Finished scraping {member}. {pages_scraped} pages scraped so far. . .')

            except Exception as err:
                print(f'Error caught member {member}: {err}')

            finally:
                users_scraped += 1

    t1=time.time()

    print(f"{(t1-t0)/60} minutes to scrape {pages_scraped} member film pages")

    # Cleaning up data that hasn't been dumped to csv and dumping it
    if len(data) > 0:
        df = pd.DataFrame(data)
        df.to_csv("data/ratings.csv", mode='a')

    print("Ratings finished scraping.")


if __name__ == '__main__':
    asyncio.run(main())
