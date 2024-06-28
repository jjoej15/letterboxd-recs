import asyncio
import aiohttp
from ratings_scraper import get_num_pages, scrape_member_ratings
from members_scraper import fetch_html
import pandas as pd
from bs4 import BeautifulSoup
from surprise import dump, accuracy
from colorama import Fore
import time

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


# async def fetch_v2(url, session):
#     '''
#     Takes in url and ClientSession object and returns tuple of response status and response text/html
#     '''
#     async with session.get(url) as response:
#         print(response.status)
#         return (response.status, await response.text())
    

async def scrape_user_data(user):
    user_ratings = []

    async with aiohttp.ClientSession() as session:
        print(f'Scraping data for {user}. . .')
        tasks = []
        tasks.append(get_num_pages(user, session))
        pages = (await asyncio.gather(*tasks))[0]

        tasks = [] 
        for page in range(1, pages + 1):
            tasks.append(scrape_member_ratings(user, page, session))
        responses = await asyncio.gather(*tasks)

        for response in responses:
            user_ratings += response

    return user_ratings

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
            # print(film_genres)
            
    finally:
        return film_info
    

async def apply_filters(pred_list, filters, n):
    if filters:
        # film_data_dict = {}
        filtered_list = []
        max_viewers = popularity_filter_map[filters['Popularity']][1] if 'Popularity' in filters else float('inf')
        # genres_to_choose = genres[int(filters['Genre'])-1] if 'Genre' in filters else genres
        genres_to_choose = [genres[int(genre_input)-1] for genre_input in filters['Genre']] if 'Genre' in filters else genres

        print(genres_to_choose)

        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 0
            while i < len(pred_list) and len(filtered_list) < n:
                tasks.append(scrape_pred_data(pred_list[i].iid, i, filters, session))

                if len(tasks) % 25 == 0:
                    responses = await asyncio.gather(*tasks)
                    tasks = []
                    for response in responses:
                        # if 'genres' in response:
                        #     print(response['genre'])
                        if ('viewers' in response and response['viewers'] > max_viewers) or ('genres' in response and not any(genre in genres_to_choose for genre in response['genres'])):
                            pass
                        else:
                            # if 'genres' in response:
                            #     print(response['genres'])
                            # if 'viewers' in response:
                            #     print(response['viewers'])
                            filtered_list.append(pred_list[response['idx']])
                        # film_data_dict.update(response)

                i += 1

        return filtered_list[:n]

        # print(film_data_dict)

    else:
        return pred_list[:n]
        


async def get_top_n_recs(user, n, df, algo, filters={}):
    min_rank = popularity_filter_map[filters['Popularity']][0] if 'Popularity' in filters else 0

    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
    rating_mean = df.loc[:, 'Rating'].mean()

    films_df = pd.read_csv('data/films.csv')

    user_films = set(df[df['User'] == user]['Film Link'].unique())
    all_films = set(df['Film Link'].unique())
    films_too_popular = set(films_df[films_df['Ranking'] < min_rank]['Film Link'].unique())

    # Filtering out films user has seen and films that don't meet popularity filter criteria
    films = list(all_films - user_films - films_too_popular)

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


async def main():
    ratings_df = pd.read_csv('data/ratings.csv')
    _, algo = dump.load('rec_model.pkl')

    user = f'/{input("Enter Letterboxd username for film recommendations: ")}/'

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

    user_ratings = await scrape_user_data(user)

    print(f'Gathering recs for {user}. . .')

    user_df = pd.DataFrame(user_ratings)
    df = pd.concat([user_df, ratings_df])

    recs = await get_top_n_recs(user, 50, df, algo, filter_dict)

    for i, rec in enumerate(recs, 1):
        print(f'{Fore.CYAN}{i}. https://letterboxd.com{rec[0]} {Fore.GREEN}Predicted Rating: {round(rec[1])}{Fore.WHITE}')

    t1 = time.time()
    print(t1-t0)
    # except Exception as err:
    #     print(f'Exception occurred: {err}')

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
