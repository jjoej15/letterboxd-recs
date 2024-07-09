import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
# from use_model import genres

genres = [
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Music",
    "Mystery",
    "Romance",
    "Science Fiction",
    "Thriller",
    "TV Movie",
    "War",
    "Western"
]


async def fetch_html(url, session):
    '''
    Takes in url and ClientSession object and returns tuple of response status and response text/html
    '''
    async with session.get(url) as response:
        return (response.status, await response.text())
    

async def get_num_film_pages(member, session):
    url = f'https://letterboxd.com{member}films/'
    (resp_code, html) = await fetch_html(url, session)

    attempts = 0
    while resp_code != 200 and attempts < 100:
        (resp_code, html) = await fetch_html(url, session)
        attempts += 1

    # if resp_code != 200:
    #     raise Exception(f"Response code {resp_code}")

    try:
        if resp_code != 200:
            raise Exception(f"Response code {resp_code}")

        soup = BeautifulSoup(html, 'lxml')
        paginate_pages = soup.find_all("li", class_="paginate-page")
        return int(paginate_pages[-1].find('a').text) if paginate_pages else 1
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for member {member}: {err}")


async def scrape_member_ratings(member, page, session):
    url = f'https://letterboxd.com{member}films/page/{page}/'
    (resp_code, html) = await (fetch_html(url, session))

    attempts = 0
    while resp_code != 200 and attempts < 100:
        (resp_code, html) = await (fetch_html(url, session))
        attempts += 1

    rated_data = []
    unrated_data = []

    try:
        soup = BeautifulSoup(html, 'lxml')
        
        films = soup.find_all("li", class_="poster-container")   

        for film in films:
            rating_span = film.find('p').find('span')

            if rating_span: 
                rating = rating_span.attrs['class'][-1].split('-')[1]
                if rating != "16": # If got rating of 16, it means the user liked the film but didn't rate it. Add to rated data.
                    item = {}
                    item['User'] = member
                    film_info = film.find('div')
                    item['Film'] = film_info.find('img').attrs['alt']
                    item['Film Link'] = film_info.attrs['data-target-link']
                    item['Rating'] = rating

                    rated_data.append(item)

                else: # Add to unrated data
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

        # print(f"Member {member}, film page #{page} successfully scraped")

    except Exception as err:
        print(f"Error scraping member {member}, film page #{page}: {err}")

    finally: 
        return (rated_data, unrated_data)


async def get_num_watchlist_pages(user, session):
    url = f'https://letterboxd.com{user}watchlist/'
    (resp_code, html) = await fetch_html(url, session)

    if resp_code in (204, 403): # If this happens, user likely has watchlist privated
        return None
    elif resp_code != 200:
        while resp_code != 200:
            (resp_code, html) = await fetch_html(url, session)

    try:
        soup = BeautifulSoup(html, 'lxml')
        paginate_pages = soup.find_all("li", class_="paginate-page")
        return int(paginate_pages[-1].find('a').text) if paginate_pages else 1
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for user watchlist: {err}")


async def scrape_watchlist(user, page, session):
    url = f'https://letterboxd.com{user}watchlist/page/{page}/'
    (resp_code, html) = await fetch_html(url, session)

    while resp_code != 200:
        (resp_code, html) = await fetch_html(url, session)

    film_links = []

    try:
        soup = BeautifulSoup(html, 'lxml')

        films = soup.find_all('li', class_='poster-container')
        for film in films:
            film_links.append(film.find('div').attrs['data-target-link'])

    except Exception as err:
        print(f"Error scraping {user} watchlist page #{page}: {err}")

    finally:
        return film_links
    

async def scrape_user_data(user, exclude_watchlist):
    user_ratings = []
    user_watchlist = []

    async with aiohttp.ClientSession() as session:
        print(f'Scraping data for {user}. . .')
        tasks = []
        tasks.append(get_num_film_pages(user, session))
        pages = (await asyncio.gather(*tasks))[0]

        tasks = [] 
        for page in range(1, pages + 1):
            tasks.append(scrape_member_ratings(user, page, session))
        responses = await asyncio.gather(*tasks)

        rating_sum = sum(len(rated_data) for rated_data, _ in responses)
        if rating_sum: # Only store data if user rated any films
            mean_rating = round(sum(int(data['Rating']) for rated_data, _ in responses for data in rated_data ) / rating_sum, 2)
            for rated_data, unrated_data in responses:
                user_ratings += rated_data

                if unrated_data:
                    for i in range(len(unrated_data)):
                        unrated_data[i]['Rating'] = mean_rating

                    user_ratings += unrated_data

        else:
            for _, unrated_data in responses:
                for i in range(len(unrated_data)):
                    unrated_data[i]['Ratings'] = 10

                user_ratings += unrated_data

        if exclude_watchlist:
            tasks = []
            tasks.append(get_num_watchlist_pages(user, session))
            pages = (await asyncio.gather(*tasks))[0]
            if not pages:
                print("Couldn't scrape user watchlist. Please try unprivating watchlist.")
                return (user_ratings, [])

            tasks = [] 
            for page in range(1, pages + 1):
                tasks.append(scrape_watchlist(user, page, session))
            responses = await asyncio.gather(*tasks)

            for response in responses:
                user_watchlist += response

    return (user_ratings, user_watchlist)


async def scrape_pred_data(film_link, idx, filters, session):
    film_info = {'idx': idx}

    try:
        # Getting number of viewers film has gotten
        if 'Popularity' in filters:
            url = f'https://letterboxd.com{film_link}members/'
            (resp_code, html) = await fetch_html(url, session)

            while resp_code != 200:
                (resp_code, html) = await fetch_html(url, session)

            soup = BeautifulSoup(html, 'lxml')
            num_viewers = int(soup.find('li', class_='js-route-watches').find('a').attrs['title'].split()[0].replace(',', ''))
            film_info['viewers'] = num_viewers

        # Getting genre of film
        if 'Genre' in filters:
            url = f'https://letterboxd.com{film_link}genres/'
            (resp_code, html) = await fetch_html(url, session)

            while resp_code != 200:
                (resp_code, html) = await fetch_html(url, session)

            soup = BeautifulSoup(html, 'lxml')
            film_genres = [genre.text for genre in soup.find('div', id="tab-genres").find_all('a') if genre.text in genres]
            film_info['genres'] = film_genres
            
    finally:
        return film_info