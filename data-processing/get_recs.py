'''
    For usage of recommendation algorithm in a local environment.
'''

from ratings_scraper import get_num_film_pages, scrape_member_ratings
from members_scraper import fetch_html
import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from colorama import Fore
import time
import functools
import pickle


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
    '''
        Takes in string representing Letterboxd user and aiohttp.ClientSession() object.
        Returns number of pages in user's watchlist.
    '''

    url = f'https://letterboxd.com{user}watchlist/'
    resp_code, html = await fetch_html(url, session)

    if resp_code in (204, 403): # If this happens, user likely has watchlist privated
        return None
    
    # If some other server response error continue attempting to fetch html
    elif resp_code != 200:
        attempts = 1
        while resp_code != 200 and attempts < 100:
            resp_code, html = await fetch_html(url, session)
            attempts += 1

    try:
        # Parsing data using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        paginate_pages = soup.find_all("li", class_="paginate-page")
        return int(paginate_pages[-1].find('a').text) if paginate_pages else 1
    
    except Exception as err:
        print(f"Error finding number of pages to scrape for user watchlist: {err}")


async def scrape_watchlist(user, page, session):
    '''
        Takes in string representing Letterboxd user, integer representing page number, and aiohttp.ClientSession() object.
        Returns list of film hrefs from user's watchlist on given page.
    '''

    url = f'https://letterboxd.com{user}watchlist/page/{page}/'
    resp_code, html = await fetch_html(url, session)

    attempts = 1
    while resp_code != 200 and attempts < 100:
        resp_code, html = await fetch_html(url, session)
        attempts += 1

    film_links = []

    try:
        # Getting film info using BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        films = soup.find_all('li', class_='poster-container')
        for film in films:
            film_links.append(film.find('div').attrs['data-target-link'])

    except Exception as err:
        print(f"Error scraping {user} watchlist page #{page}: {err}")

    finally:
        return film_links


async def scrape_user_data(user, exclude_watchlist):
    '''
        Takes in string representing Letterboxd user and boolean indicating whether to exclude films in user's watchlist.
        Returns tuple with list of dicts representing user ratings and list of film href's from user's watchlist respectively.
    '''

    user_ratings = []
    user_watchlist = []

    # Asynchronously scraping user data
    async with aiohttp.ClientSession() as session:
        print(f'Scraping data for {user}. . .')
        tasks = []

        # Getting number of pages user has filled with ratings
        tasks.append(get_num_film_pages(user, session))
        pages = (await asyncio.gather(*tasks))[0]

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
                    unrated_data[i]['Ratings'] = 10

                user_ratings += unrated_data

        if exclude_watchlist:
            tasks = []
            tasks.append(get_num_watchlist_pages(user, session))
            pages = (await asyncio.gather(*tasks))[0]
            if not pages:
                print(f"Couldn't scrape user {user}'s watchlist. Please try unprivating watchlist.")
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
            resp_code, html = await fetch_html(url, session)

            attempts = 1
            while resp_code != 200 and attempts < 100:
                resp_code, html = await fetch_html(url, session)
                attempts += 1

            soup = BeautifulSoup(html, 'lxml')
            num_viewers = int(soup.find('li', class_='js-route-watches').find('a').attrs['title'].split()[0].replace(',', ''))
            film_info['viewers'] = num_viewers

        # Getting genre of film
        if 'Genre' in filters:
            url = f'https://letterboxd.com{film_link}genres/'
            resp_code, html = await fetch_html(url, session)

            attempts = 1
            while resp_code != 200 and attempts < 100:
                resp_code, html = await fetch_html(url, session)
                attempts += 1

            soup = BeautifulSoup(html, 'lxml')
            film_genres = [genre.text for genre in soup.find('div', id="tab-genres").find_all('a') if genre.text in genres]
            film_info['genres'] = film_genres
            
    finally:
        return film_info
    

async def apply_filters(pred_list, filters, n):
    '''
        Takes in list of film predictions, dict of filters to apply, number of films to return.
        Returns list of filtered film predictions.
    '''

    if 'Genre' in filters or 'Popularity' in filters:
        filtered_list = []
        max_viewers = popularity_filter_map[filters['Popularity']][1] if 'Popularity' in filters else float('inf')
        genres_to_choose = [genres[int(genre_input)-1] for genre_input in filters['Genre']] if 'Genre' in filters else genres

        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 0
            while i < len(pred_list) and len(filtered_list) < n:
                tasks.append(scrape_pred_data(pred_list[i].iid, i, filters, session))

                if len(tasks) % 50 == 0:
                    responses = await asyncio.gather(*tasks)
                    tasks = []
                    for response in responses:
                        if not ('viewers' in response and response['viewers'] > max_viewers) and (not ('genres' in response) or any(film_genre in genres_to_choose for film_genre in response['genres'])):
                            filtered_list.append(pred_list[response['idx']])

                i += 1

        return sorted(filtered_list, key=(lambda x : x.est), reverse=True)[:n]

    else:
        return pred_list[:n]
        

async def get_top_n_recs(user, n, df, algo, filters):
    '''
        Takes in string representing Letterboxd user, number of recommendations to return, pandas.DataFrame object with info about user's ratings
        and ratings used in trained model, trained surprise.SVD algorithm, and dict containing necessary filters to apply.
        Returns list of n tuples containing prediction href and estimated rating for prediction respectively.
    '''

    # All films must have higher popularity ranking than min_rank to be recommended
    min_rank = popularity_filter_map[filters['Popularity']][0] if 'Popularity' in filters else 0

    # Finding mean of all ratings in df to be used to fill missing values when getting predictions from model
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
    rating_mean = df.loc[:, 'Rating'].mean()

    films_df = pd.read_csv('data/films.csv')
    films_df['Ranking'] = pd.to_numeric(films_df['Ranking'], errors='coerce')

    user_films = set(df[df['User'] == user]['Film Link'].unique())
    all_films = set(df['Film Link'].unique())
    films_too_popular = set(films_df[films_df['Ranking'] < min_rank]['Film Link'].unique())
    # Getting union of users' watchlists (useful when multiple watchlists to exclude like when using blend mode)
    films_in_watchlists = set(functools.reduce((lambda a, b : set(a).union(set(b))), filters['Watchlists'])) if filters['Watchlists'] else set()
    
    # Filtering out films user has seen, films that don't meet popularity filter criteria, 
    # and films in user watchlists (if user opted to ignore films in watchlists)
    films = list(all_films - user_films - films_too_popular - films_in_watchlists)

    # Using mean of all ratings in df to fill missing values when getting predictions from model, which is what 3rd item of tuple is used for
    user_film_pairs = [(user, film, rating_mean) for film in films]
    predictions = algo.test(user_film_pairs)

    top_1000_recs = sorted(predictions, key=(lambda x : x.est), reverse=True)[:1000]

    print('Applying filters. . .')

    filtered_recs = await apply_filters(top_1000_recs, filters, n)

    return [(pred.iid, pred.est) for pred in filtered_recs]


def get_blended_ratings(user_1_ratings, user_2_ratings, algo): 
    '''
        Takes in list of user 1's ratings, a list of user 2's ratings, and trained surprise.SVD algorithm.
        Return list of dicts corresponding to average of the ratings for each film. If 1 user has rated a film the
        other user hasn't, predict what the other user would rate it, then use the first user's actual rating and the other user's
        predicted rating to find average.
    '''

    user_1 = user_1_ratings[0]['User']
    user_2 = user_2_ratings[0]['User']

    to_predict = [] # Will be used as test set for algorithm to predict
    combined_ratings = []
    films_in_common_dict = {}

    user_1_total_score = 0
    for user_1_rating in user_1_ratings:
        user_1_total_score += int(user_1_rating['Rating'])

        for user_2_rating in user_2_ratings:
            if user_1_rating['Film Link'] == user_2_rating['Film Link']:
                combined_ratings.append(user_1_rating)

                # Change rating of film to be average of 2 user's ratings
                combined_ratings[-1]['Rating'] = str(round((int(user_1_rating['Rating']) + int(user_2_rating['Rating']))/2, 2))
                films_in_common_dict[user_1_rating['Film Link']] = True
                break

        # If user 2 hasn't seen film, add to test set
        if user_1_rating['Film Link'] not in films_in_common_dict:
            to_predict.append((user_2, user_1_rating['Film Link']))

    user_1_rating_mean = round(user_1_total_score / len(user_1_ratings), 2)

    user_2_total_score = 0
    for user_2_rating in user_2_ratings:
        user_2_total_score += int(user_2_rating['Rating'])

        # If user 1 hasn't seen film, add to test set
        if user_2_rating['Film Link'] not in films_in_common_dict:
            to_predict.append((user_1, user_2_rating['Film Link']))

    user_2_rating_mean = round(user_2_total_score / len(user_2_ratings), 2)

    # Predicting ratings for films one of the users hasn't rated
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
    with open("pickles/model_df.pkl", 'rb') as pkl:
        ratings_df = pickle.load(pkl)
    with open("pickles/rec_model.pkl", 'rb') as pkl:
        algo = pickle.load(pkl)

    blend_mode = input('Blend mode? (Y/N): ').capitalize()
    while blend_mode not in ('Y', 'N'):
        blend_mode = input('Blend mode? (Y/N): ').capitalize()
    blend_mode = blend_mode == 'Y'

    user_1 = f'/{input("Enter Letterboxd username for film recommendations: ")}/'

    user_2 = f'/{input("Enter 2nd Letterboxd username for blend mode: ")}/' if blend_mode else None

    try:
        exclude_watchlist = input('Exclude films in watchlist? (Y/N): ').capitalize()
        while exclude_watchlist not in ('Y', 'N'):
            exclude_watchlist = input('Blend mode? (Y/N): ').capitalize()
        exclude_watchlist = exclude_watchlist == 'Y'

        filter_dict = {}
        filters = input("""Would you like any filters? (seperate filters by commas e.g. "g,p" if want genre and popularity filters)
        "n" - no
        "p" - popularity filter
        "g" - genre filter\n""").split(',')

        if 'p' in filters:
            filter_dict['Popularity'] = input("""What popularity filter? (1/2/3)
        "1" - less known films
        "2" - even lesser known films
        "3" - unknown films\n""")
            
        if 'g' in filters:
            filter_dict['Genre'] = input("""What genres? (seperate by commas if want multiple e.g. "3,9,12" if want Animation, Fantasy, and Music genres)
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

        ratings, user_1_watchlist = await scrape_user_data(user_1, exclude_watchlist)
        watchlists = [user_1_watchlist] if user_1_watchlist else []

        if blend_mode:
            user_2_ratings, user_2_watchlist = await scrape_user_data(user_2, exclude_watchlist)
            watchlists.append(user_2_watchlist)

            ratings = get_blended_ratings(ratings, user_2_ratings, algo)

        filter_dict['Watchlists'] = watchlists

        print(f'Gathering recs. . .')
        
        user_df = pd.DataFrame(ratings)
        df = pd.concat([user_df, ratings_df])

        recs = await get_top_n_recs(user_1, 50, df, algo, filter_dict)

        print('Recommendations: ')
        for rec in recs:
            film_name = df[df['Film Link'] == rec[0]]['Film'].unique()[0]

            print(f'{Fore.YELLOW}{film_name} {Fore.CYAN}https://letterboxd.com{rec[0]} {Fore.GREEN}{Fore.WHITE}')

        t1 = time.time()
        print(f'Process finished in {t1-t0} seconds.')

    except Exception as err:
        print(f"Couldn't get recommendations for {user_1}{f" and {user_2}" if user_2 else ''}. Make sure usernames are correct and try again. {err}")


if __name__ == '__main__':
    asyncio.run(main())
