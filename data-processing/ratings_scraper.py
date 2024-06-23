from bs4 import BeautifulSoup
import pandas as pd
import time
import asyncio
import aiohttp
from members_scraper import fetch_html

# async def fetch_html(url, session):
#     async with session.get(url) as response:
#         return await response.text()
    

async def get_num_pages(member, session):
    url = f'https://letterboxd.com{member}films/'
    html = await fetch_html(url, session)

    try:
        soup = BeautifulSoup(html, 'lxml')
        paginate_pages = soup.find_all("li", class_="paginate-page")
        return int(paginate_pages[-1].find('a').text)
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for member {member}: {err}")


async def scrape_member_ratings(member, page, session):
    url = f'https://letterboxd.com{member}films/page/{page}/'
    html = await fetch_html(url, session)
    data = []

    try:
        soup = BeautifulSoup(html, 'lxml')
        
        films = soup.find_all("li", class_="poster-container")   

        for film in films:
            rating_span = film.find('p').find('span')

            # If user doesn't have rating for film, ignore it
            if rating_span:
                rating = rating_span.attrs['class'][-1].split('-')[1]
                if rating != "16": # If got rating of 16, it means the user liked the film but didn't rate it
                    item = {}
                    item['User'] = member
                    film_info = film.find('div')
                    item['Film'] = film_info.find('img').attrs['alt']
                    item['Film Link'] = film_info.attrs['data-target-link']
                    item['Rating'] = rating

                    data.append(item)

        print(f"Member {member}, film page #{page} successfully scraped")

    except Exception as err:
        print(f"Error scraping member {member}, film page #{page}: {err}")

    finally: 
        return data
    

async def main():
    pages_scraped = 0

    with open("data/less-members.csv") as fh:
        fh.readline()
        members_lines = fh.readlines()

    open("data/ratings.csv", "w").close()

    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        count = 0
        data = []

        for line in members_lines:
            # After every 100 members' ratings are scraped, save progress
            if count == 100:
                df = pd.DataFrame(data)
                df.to_csv("data/ratings.csv", mode='a')
                data = []
                count = 0

            tasks = []
            member = line.split(',')[1].strip()

            # Get number of pages user has filled in ratings
            tasks.append(get_num_pages(member, session))
            pages = (await asyncio.gather(*tasks))[0]
            pages_scraped += 1
            
            # Scraping every page user has filled in ratings
            tasks = []
            for page in range(1, pages + 1):
                tasks.append(scrape_member_ratings(member, page, session))
            responses = await asyncio.gather(*tasks)

            for response in responses:
                data += response

            pages_scraped += pages

    t1=time.time()

    print(f"{(t1-t0)/60} minutes to scrape {pages_scraped} member film pages")

    if len(data) > 0:
        df = pd.DataFrame(data)
        df.to_csv("data/ratings.csv", mode='a')

    print("Process finished")


if __name__ == '__main__':
    asyncio.run(main())
