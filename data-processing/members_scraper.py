'''
    For scraping https://letterboxd.com/members/popular/
'''

from bs4 import BeautifulSoup
import pandas as pd
import asyncio
import aiohttp
import time


async def fetch_html(url, session):
    '''
        Takes in string representing url and aiohttp.ClientSession object.
        Returns tuple of response status and response text/html respectively.
    '''

    async with session.get(url) as response:
        return (response.status, await response.text())


async def scrape_popular_members(page, session):
    '''
        Takes in int representing page number for Letterboxd popular members page and aiohttp.ClientSession object.
        Returns list of strings representing user hrefs for members on page.
    '''

    url = f"https://letterboxd.com/members/popular/page/{page}/"
    resp_code, html = await fetch_html(url, session)
    data = []

    attempts = 1
    while resp_code != 200 and attempts < 100:
        resp_code, html = await fetch_html(url, session)
        attempts += 1

    try:
        # Parsing page using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        if soup.title.text != "Letterboxd - Not Found":
            members = soup.find_all("div", class_="person-summary")

            for member in members:
                item = {}
                item['userHref'] = member.find('a').attrs['href']
                data.append(item)

            # Removing featured popular reviewers on right side of screen on webpage
            data = data[:-5]
            print(f'Member page #{page} successfully scraped')   

        else:
            print(f"Member page #{page} not found")

    except Exception as err:
        print(f"Error scraping member page #{page}: {err}")

    finally:
        return data
    

async def main():
    # Scraping 167 pages of https://letterboxd.com/members/popular/ (appx. 5000 members) and storing data in data/members.csv
    num_pages = 167
    data = []

    t0 = time.time()
    
    # Scraping popular member pages 1 through 167
    async with aiohttp.ClientSession() as session:
        tasks = []
        for page in range(1, num_pages+1):
            tasks.append(scrape_popular_members(page, session))
        responses = await asyncio.gather(*tasks)

    for response in responses:
        data += response
        
    t1=time.time()

    print(f"{(t1-t0)/60} minutes to scrape {num_pages} member pages")

    df = pd.DataFrame(data)
    df.to_csv("data/members.csv")

    print("Members finished scraping")


if __name__ == '__main__':
    asyncio.run(main())