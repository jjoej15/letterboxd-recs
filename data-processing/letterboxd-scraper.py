from bs4 import BeautifulSoup
import pandas as pd
import time
import asyncio
import aiohttp

async def fetch_html(url, session):
    async with session.get(url) as response:
        return await response.text()

async def scrape_popular_members(page, session):
    url = "https://letterboxd.com/members/popular/" if page == 1 else f"https://letterboxd.com/members/popular/page/{page}/"
    html = await fetch_html(url, session)
    data = []

    try:
        soup = BeautifulSoup(html, 'lxml')
        if soup.title.text != "Letterboxd - Not Found":
            members = soup.find_all("div", class_="person-summary")

            for member in members:
                item = {}
                item['userHref'] = member.find('a').attrs['href']
                data.append(item)

            # Removing featured popular reviewers on right side of screen on webpage
            data = data[:-5]
            print(f'Page #{page} successfully scraped')   
        else:
            print(f"Page #{page} not found")

    except Exception as err:
        print(f"Error scraping page #{page}: {err}")

    finally:
        return data
    

async def main():
    num_pages = 167
    data = []

    t0 = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for page in range(1, num_pages+1):
            tasks.append(scrape_popular_members(page, session))
        responses = await asyncio.gather(*tasks)

    for response in responses:
        data += response
        
    t1=time.time()

    print(f"{(t1-t0)/60} minutes to scrape {num_pages} pages")

    df = pd.DataFrame(data)
    df.to_csv("members.csv")

    print("Process finished")


if __name__ == '__main__':
    asyncio.run(main())