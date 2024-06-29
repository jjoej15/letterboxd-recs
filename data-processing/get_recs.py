import asyncio
import aiohttp
from ratings_scraper import get_num_film_pages, scrape_member_ratings
from members_scraper import fetch_html
import pandas as pd
from bs4 import BeautifulSoup
from surprise import dump, accuracy
from colorama import Fore
import time
import functools



popularity_filter_map = {
    # Key represents user input. Value is tuple where first index is the min popularity ranking that
    # the film can be, second index is the max num. of users who've viewed the film can be. 
    '1': (1000, 800000),
    '2': (7200, 25000),
    '3': (17929, 7500)
}

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



async def get_num_watchlist_pages(user, session):
    url = f'https://letterboxd.com{user}watchlist/'
    (resp_code, html) = await fetch_html(url, session)

    if resp_code == 204: # If this happens, user likely has watchlist privated
        return None
    elif resp_code != 200:
        while resp_code != 200:
            (resp_code, html) = fetch_html(url, session)

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
        (resp_code, html) = fetch_html(url, session)

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

        for response in responses:
            user_ratings += response

        if exclude_watchlist:
            tasks = []
            tasks.append(get_num_watchlist_pages(user, session))
            pages = (await asyncio.gather(*tasks))[0]
            if not pages:
                print("Couldn't scrape user watchlist. Please try unprivating watchlist.")
                return []

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
    


async def apply_filters(pred_list, filters, n):
    if filters:
        filtered_list = []
        max_viewers = popularity_filter_map[filters['Popularity']][1] if 'Popularity' in filters else float('inf')
        genres_to_choose = [genres[int(genre_input)-1] for genre_input in filters['Genre']] if 'Genre' in filters else genres

        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 0
            while i < len(pred_list) and len(filtered_list) < n:
                tasks.append(scrape_pred_data(pred_list[i].iid, i, filters, session))

                if len(tasks) % 25 == 0:
                    responses = await asyncio.gather(*tasks)
                    tasks = []
                    for response in responses:
                        if ('viewers' in response and response['viewers'] > max_viewers) or ('genres' in response and not any(genre in genres_to_choose for genre in response['genres'])):
                            pass
                        else:
                            filtered_list.append(pred_list[response['idx']])

                i += 1

        return sorted(filtered_list, key=(lambda x : x.est), reverse=True)[:n]

    else:
        return pred_list[:n]
        


async def get_top_n_recs(user, n, df, algo, filters):
    min_rank = popularity_filter_map[filters['Popularity']][0] if 'Popularity' in filters else 0

    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
    rating_mean = df.loc[:, 'Rating'].mean()

    films_df = pd.read_csv('data/films.csv')

    user_films = set(df[df['User'] == user]['Film Link'].unique())
    all_films = set(df['Film Link'].unique())
    films_too_popular = set(films_df[films_df['Ranking'] < min_rank]['Film Link'].unique())
    films_in_watchlists = set(functools.reduce((lambda a, b : set(a).union(set(b))), filters['Watchlists'])) if filters['Watchlists'] else set()
    
    # Filtering out films user has seen, films that don't meet popularity filter criteria, 
    # and films in user watchlists (if user opted to ignore films in watchlists)
    films = list(all_films - user_films - films_too_popular - films_in_watchlists)

    user_film_pairs = [(user, film, rating_mean) for film in films]
    predictions = algo.test(user_film_pairs)
    accuracy.rmse(predictions)

    top_1000_recs = sorted(predictions, key=(lambda x : x.est), reverse=True)[:1000]

    # t0 = time.time()

    print('Applying filters. . .')

    filtered_recs = await apply_filters(top_1000_recs, filters, n)

    # t1 = time.time()

    # print(f'Scraped 600 pages in {(t1-t0)/60} minutes. That\'s {1/((600)/((t1-t0)/60))} mins/pg.')

    return [(pred.iid, pred.est) for pred in filtered_recs]



def get_blended_ratings(user_1_ratings, user_2_ratings, algo):
    # Find films user 1 has rated but user 2 hasnt
    # Predict what user 2 will rate those films
    # Find films user 2 has rated but user 1 hasn't
    # Predict what user 1 will rate those films
    # Return a list of dicts corresponding to the average of the ratings for each film
    user_1 = user_1_ratings[0]['User']
    user_2 = user_2_ratings[0]['User']

    to_predict = []
    combined_ratings = []
    films_in_common_dict = {}

    user_1_total_score = 0
    for user_1_rating in user_1_ratings:
        user_1_total_score += int(user_1_rating['Rating'])

        for user_2_rating in user_2_ratings:
            if user_1_rating['Film Link'] == user_2_rating['Film Link']:
                combined_ratings.append(user_1_rating)
                combined_ratings[-1]['Rating'] = str(round((int(user_1_rating['Rating']) + int(user_2_rating['Rating']))/2, 2))
                # combined_ratings[-1]['User'] = f'{user_1}, {user_2} blend'
                films_in_common_dict[user_1_rating['Film Link']] = True
                break

        # If user 2 hasn't seen film, add to testset
        if user_1_rating['Film Link'] not in films_in_common_dict:
            to_predict.append((user_2, user_1_rating['Film Link']))
    user_1_rating_mean = round(user_1_total_score / len(user_1_ratings), 2)

    user_2_total_score = 0
    for user_2_rating in user_2_ratings:
        user_2_total_score += int(user_2_rating['Rating'])

        # If user 1 hasn't seen film, add to testset
        if user_2_rating['Film Link'] not in films_in_common_dict:
            to_predict.append((user_1, user_2_rating['Film Link']))
    user_2_rating_mean = round(user_2_total_score / len(user_2_ratings), 2)

    user_film_pairs = [(user, film, user_1_rating_mean if user == user_1 else user_2_rating_mean) for (user, film) in to_predict]
    predictions = algo.test(user_film_pairs)

    for pred in predictions:
        combined_ratings.append({
                                    'User': user_1, 
                                    'Film Link': pred.iid,
                                    'Rating': round(pred.est, 2)
                                })
            
    return combined_ratings


async def main():
    ratings_df = pd.read_csv('data/ratings.csv')
    _, algo = dump.load('rec_model.pkl')
    blend_mode = input('Blend mode? (y/n): ') == 'y'

    user_1 = f'/{input("Enter Letterboxd username for film recommendations: ")}/'

    user_2 = f'/{input("Enter 2nd Letterboxd username for blend mode: ")}/' if blend_mode else None

    exclude_watchlist = input('Exclude films in watchlist? (y/n): ') == 'y'

    filter_dict = {}
    filters = input("""Would you like any filters (seperate filters by commas e.g. "g,p" if want genre and popularity filters)?
                        "n" - no
                        "p" - popularity filter
                        "g" - genre filter\n""").split(',')
    if 'p' in filters:
        filter_dict['Popularity'] = input("""What popularity filter (1/2/3)?
                                          "1" - less known films
                                          "2" - even lesser known films
                                          "3" - unknown films\n""")
    if 'g' in filters:
        filter_dict['Genre'] = input("""What genres (seperate by commas if want multiple)?
                                     "1" - Action
                                     "2" - Adventure
                                     "3" - Animation
                                     "4" - Comedy
                                     "5" - Crime
                                     "6" - Documentary
                                     "7" - Drama
                                     "8" - Family
                                     "9" - Fantasy
                                     "10" - History
                                     "11" - Horror
                                     "12" - Music
                                     "13" - Mystery
                                     "14" - Romance
                                     "15" - Science Fiction
                                     "16" - Thriller
                                     "17" - TV Movie
                                     "18" - War
                                     "19" - Western\n""").split(',')

    t0 = time.time()

    (ratings, user_1_watchlist) = await scrape_user_data(user_1, exclude_watchlist)
    watchlists = [user_1_watchlist] if user_1_watchlist else []
   
    if blend_mode:
        (user_2_ratings, user_2_watchlist) = await scrape_user_data(user_2, exclude_watchlist)
        watchlists.append(user_2_watchlist)

        ratings = get_blended_ratings(ratings, user_2_ratings, algo)

    filter_dict['Watchlists'] = watchlists

    print(f'Gathering recs. . .')
    
    user_df = pd.DataFrame(ratings)
    df = pd.concat([user_df, ratings_df])

    recs = await get_top_n_recs(user_1, 50, df, algo, filter_dict)

    for i, rec in enumerate(recs, 1):
        print(f'{Fore.CYAN}{i}. https://letterboxd.com{rec[0]} {Fore.GREEN}Predicted Rating: {round(rec[1])}{Fore.WHITE}')

    t1 = time.time()
    print(t1-t0)



async def main_v2():
    async with aiohttp.ClientSession() as session:
        # with open('output.txt', 'a') as file:
        #     lines = (await scrape_film_data('/film/inside-out-2-2024/', session)).split('\n')
        #     for line in lines:
        #         try:
        #             file.write(line)
        #         except:
        #             pass


        print(await scrape_pred_data('/film/the-lord-of-the-rings-2003/', 1, session))



if __name__ == '__main__':
    # print('Starting. . .')
    asyncio.run(main())
    # asyncio.run(main_v2())
