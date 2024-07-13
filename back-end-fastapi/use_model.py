'''
    For usage of recommmendation model. 
'''

import scraping
import pandas as pd
import aiohttp
import asyncio
import pickle
import functools


popularity_filter_map = {
    # Key represents user input. Value is tuple where first index is the min popularity ranking that
    # the film can be, second index is the max num. of users who've viewed the film can be. 
    '1': (1000, 800000),
    '2': (7200, 25000),
    '3': (17929, 7500)
}


async def apply_filters(pred_list, filters, n):
    '''
        Takes in list of film predictions, dict of filters to apply, number of films to return.
        Returns list of filtered film predictions.
    '''

    if 'Genre' in filters or 'Popularity' in filters:
        filtered_list = []
        max_viewers = popularity_filter_map[filters['Popularity']][1] if 'Popularity' in filters else float('inf')
        genres_to_choose = filters['Genre'] if 'Genre' in filters else scraping.genres

        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 0
            while i < len(pred_list) and len(filtered_list) < n:
                tasks.append(scraping.scrape_pred_data(pred_list[i].iid, i, filters, session))

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

async def main(parameters):
    '''
        Takes in dict with values representing the query parameters sent to API.
        Returns list of dicts including film recs and their corresponding links.
    '''

    with open("pickles/model_df.pkl", 'rb') as pkl:
        ratings_df = pickle.load(pkl)
    with open("pickles/rec_model.pkl", 'rb') as pkl:
        algo = pickle.load(pkl)

    blend_mode = parameters['blended']
    user_1 = f'/{parameters["users"].split(',')[0]}/'
    user_2 = f'/{parameters["users"].split(',')[1]}/' if blend_mode else None
    exclude_watchlist = parameters['excludeWatchlist'] == 'True'
    
    filter_dict = {}
    if parameters['popFilter'] != 'null' and parameters['popFilter'] != 'undefined':
        filter_dict['Popularity'] = parameters['popFilter']

    if parameters['genreFilters']:
        filter_dict['Genre'] = parameters['genreFilters']
  
    (ratings, user_1_watchlist) = await scraping.scrape_user_data(user_1, exclude_watchlist)
    watchlists = [user_1_watchlist] if user_1_watchlist else []

    if blend_mode:
        (user_2_ratings, user_2_watchlist) = await scraping.scrape_user_data(user_2, exclude_watchlist)
        watchlists.append(user_2_watchlist)

        ratings = get_blended_ratings(ratings, user_2_ratings, algo)

    filter_dict['Watchlists'] = watchlists

    print(f"Gathering recs for {user_1}{f' and {user_2}' if user_2 else ''}. . .")
    
    user_df = pd.DataFrame(ratings)
    df = pd.concat([user_df, ratings_df])

    recs = await get_top_n_recs(user_1, 50, df, algo, filter_dict)

    print(f"Process finished, sending recommendations for {user_1}{f' and {user_2}' if user_2 else ''}. . .")

    return [{'Film': df[df['Film Link'] == rec[0]]['Film'].unique()[0], 'Link': f'https://letterboxd.com{rec[0]}'} for rec in recs]