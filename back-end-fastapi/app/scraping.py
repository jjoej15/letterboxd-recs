'''
    Functions useful for scraping Letterboxd.
'''

import asyncio
import aiohttp
import cloudscraper
import re
from bs4 import BeautifulSoup


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


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}


def _normalize_user_path(user):
    user = (user or "").strip().strip('/')
    return f'/{user}/' if user else '/'


def _is_cloudflare_challenge(html):
    if not html:
        return False

    html = html.lower()
    return (
        "just a moment" in html
        or "cf_chl_opt" in html
        or "enable javascript and cookies to continue" in html
    )


def _fetch_html_cloudscraper(url):
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    response = scraper.get(url, headers=REQUEST_HEADERS, timeout=30)
    return (response.status_code, response.text)


def _extract_num_pages(soup):
    paginate_pages = soup.find_all("li", class_="paginate-page")
    if paginate_pages:
        return int(paginate_pages[-1].find('a').text)

    page_nums = []
    for link in soup.find_all('a', href=True):
        match = re.search(r'/page/(\d+)/', link['href'])
        if match:
            page_nums.append(int(match.group(1)))

    return max(page_nums) if page_nums else 1


def _extract_film_metadata(film):
    film_info = film.find('div', attrs={'data-target-link': True})
    if not film_info:
        film_info = film.find('div', attrs={'data-item-link': True})

    if not film_info:
        return None

    film_link = film_info.attrs.get('data-target-link') or film_info.attrs.get('data-item-link')

    film_title = None
    img = film_info.find('img')
    if img:
        film_title = img.attrs.get('alt')

    if not film_title:
        film_title = film_info.attrs.get('data-item-name') or film_info.attrs.get('data-item-full-display-name')

    if not film_title or not film_link:
        return None

    return {'Film': film_title, 'Film Link': film_link}


async def fetch_html(url, session):
    '''
        Takes in string representing url and aiohttp.ClientSession object.
        Returns tuple of response status and response text/html respectively.
    '''

    try:
        async with session.get(url, headers=REQUEST_HEADERS) as response:
            html = await response.text()

            # If Cloudflare challenge page is returned, switch to Cloudflare-aware client
            if response.status in (403, 429, 503) and _is_cloudflare_challenge(html):
                return await asyncio.to_thread(_fetch_html_cloudscraper, url)

            return (response.status, html)

    except Exception:
        # Fallback if aiohttp request fails due anti-bot/network behavior.
        return await asyncio.to_thread(_fetch_html_cloudscraper, url)
    

async def get_num_film_pages(member, session):
    '''
        Takes in string representing Letterboxd user href and aiohttp.ClientSession object.
        Returns integer representing number of pages necessary to scrape to collect all user ratings.
    '''    

    member = _normalize_user_path(member)
    url = f'https://letterboxd.com{member}films/'
    (resp_code, html) = await fetch_html(url, session)

    attempts = 1
    while resp_code != 200 and attempts < 100:
        (resp_code, html) = await fetch_html(url, session)
        attempts += 1

    try:
        if resp_code != 200:
            print(f"Error finding number of pages to scrape for member {member}: Response code {resp_code}")
            return 0

        # Parsing page using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        return _extract_num_pages(soup)
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for member {member}: {err}")
        return 0


async def scrape_member_ratings(member, page, session):
    '''
        Takes in string representing Letterboxd user href, int representing page number, and aiohttp.ClientSession object.  
        Returns tuple of list of dicts representing user rated data and list of dict representings user unrated data respectively.
    '''  

    member = _normalize_user_path(member)
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
        
        films = soup.select("li.griditem, li.poster-container")
        for film in films:
            film_data = _extract_film_metadata(film)
            if not film_data:
                continue

            rating_span = film.select_one('p.poster-viewingdata span.rating, p span.rating')

            if rating_span: 
                rated_class = next((class_name for class_name in rating_span.attrs.get('class', []) if class_name.startswith('rated-')), None)
                rating = rated_class.split('-')[1] if rated_class else None

                if not rating:
                    continue

                if rating != "16": # Add to rated data
                    item = {}
                    item['User'] = member
                    item['Film'] = film_data['Film']
                    item['Film Link'] = film_data['Film Link']
                    item['Rating'] = rating

                    rated_data.append(item)

                else: # If got rating of 16, it means the user liked the film but didn't rate it. Add to unrated data.
                    item = {}
                    item['User'] = member
                    item['Film'] = film_data['Film']
                    item['Film Link'] = film_data['Film Link']

                    unrated_data.append(item)                    

            # If user doesn't have rating for film, add to unrated data
            else: 
                item = {}
                item['User'] = member
                item['Film'] = film_data['Film']
                item['Film Link'] = film_data['Film Link']

                unrated_data.append(item)

    except Exception as err:
        print(f"Error scraping member {member}, film page #{page}: {err}")

    finally: 
        return (rated_data, unrated_data)


async def get_num_watchlist_pages(user, session):
    '''
        Takes in string representing Letterboxd user and aiohttp.ClientSession() object.
        Returns number of pages in user's watchlist.
    '''

    user = _normalize_user_path(user)
    url = f'https://letterboxd.com{user}watchlist/'
    (resp_code, html) = await fetch_html(url, session)

    if resp_code in (204, 403): # If this happens, user likely has watchlist privated
        return None
    
    # If some other server response error continue attempting to fetch html
    elif resp_code != 200:
        attempts = 1
        while resp_code != 200 and attempts < 100:
            (resp_code, html) = await fetch_html(url, session)
            attempts += 1

    try:
        # Parsing data using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        return _extract_num_pages(soup)
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for user watchlist: {err}")


async def scrape_watchlist(user, page, session):
    '''
        Takes in string representing Letterboxd user, integer representing page number, and aiohttp.ClientSession() object.
        Returns list of film hrefs from user's watchlist on given page.
    '''

    user = _normalize_user_path(user)
    url = f'https://letterboxd.com{user}watchlist/page/{page}/'
    (resp_code, html) = await fetch_html(url, session)

    while resp_code != 200:
        (resp_code, html) = await fetch_html(url, session)

    film_links = []

    try:
        # Getting film info using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        films = soup.select('li.griditem, li.poster-container')
        for film in films:
            film_data = _extract_film_metadata(film)
            if film_data:
                film_links.append(film_data['Film Link'])

    except Exception as err:
        print(f"Error scraping {user} watchlist page #{page}: {err}")

    finally:
        return film_links
    

async def scrape_user_data(user, exclude_watchlist):
    '''
        Takes in string representing Letterboxd user and boolean indicating whether to exclude films in user's watchlist.
        Returns tuple with list of dicts representing user ratings and list of film href's from user's watchlist respectively.
    '''

    user = _normalize_user_path(user)
    user_ratings = []
    user_watchlist = []

    # Asynchronously scraping user data
    async with aiohttp.ClientSession() as session:
        print(f'Scraping data for {user}. . .')
        tasks = []
        
        # Getting number of pages user has filled with ratings
        tasks.append(get_num_film_pages(user, session))
        pages = (await asyncio.gather(*tasks))[0]

        if not pages:
            print(f"Couldn't scrape ratings pages for {user}. Check username or try again shortly.")
            return ([], [])

        # Scraping user's ratings
        tasks = [] 
        for page in range(1, pages + 1):
            tasks.append(scrape_member_ratings(user, page, session))
        responses = await asyncio.gather(*tasks)

        rating_sum = sum(len(rated_data) for rated_data, _ in responses)
        if rating_sum: 
            mean_rating = round(sum(int(data['Rating']) for rated_data, _ in responses for data in rated_data ) / rating_sum, 2)
            for rated_data, unrated_data in responses:
                user_ratings += rated_data

                # Infering that user would rate films that they logged but didn't give a rating for to be the mean score of the ratings they did give
                if unrated_data:
                    for i in range(len(unrated_data)):
                        unrated_data[i]['Rating'] = mean_rating

                    user_ratings += unrated_data

        # If rating_sum is 0, user didn't rate any films, so give somewhat arbitrary rating of 10 to all films they logged.
        else:
            for _, unrated_data in responses:
                for i in range(len(unrated_data)):
                    unrated_data[i]['Rating'] = 10

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
    '''
        Takes in string representing href of film in some user's prediction, an integer representing the index in the prediction list
        it came from, a dictionary representing the filters that need to be applied, and an aiohttp.ClientSession object.
        Returns dict with data about film's number of viewers and it's genres, if the filters dict calls for them.
    '''

    film_info = {'idx': idx}

    try:
        # Getting number of viewers film has gotten
        if 'Popularity' in filters:
            url = f'https://letterboxd.com{film_link}members/'
            (resp_code, html) = await fetch_html(url, session)

            attempts = 1
            while resp_code != 200 and attempts < 100:
                (resp_code, html) = await fetch_html(url, session)
                attempts += 1

            soup = BeautifulSoup(html, 'lxml')
            num_viewers = int(soup.find('li', class_='js-route-watches').find('a').attrs['title'].split()[0].replace(',', ''))
            film_info['viewers'] = num_viewers

        # Getting genre of film
        if 'Genre' in filters:
            url = f'https://letterboxd.com{film_link}genres/'
            (resp_code, html) = await fetch_html(url, session)

            attempts = 1
            while resp_code != 200 and attempts < 100:
                (resp_code, html) = await fetch_html(url, session)
                attempts += 1

            soup = BeautifulSoup(html, 'lxml')
            film_genres = [genre.text for genre in soup.find('div', id="tab-genres").find_all('a') if genre.text in genres]
            film_info['genres'] = film_genres
            
    finally:
        return film_info