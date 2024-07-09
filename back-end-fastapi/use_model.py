import scraping
import pandas as pd
import functools
import pickle
import aiohttp
import asyncio

popularity_filter_map = {
    # Key represents user input. Value is tuple where first index is the min popularity ranking that
    # the film can be, second index is the max num. of users who've viewed the film can be. 
    '1': (1000, 800000),
    '2': (7200, 25000),
    '3': (17929, 7500)
}


async def apply_filters(pred_list, filters, n):
    if filters:
        filtered_list = []
        max_viewers = popularity_filter_map[filters['Popularity']][1] if 'Popularity' in filters else float('inf')
        genres_to_choose = [scraping.genres[int(genre_input)-1] for genre_input in filters['Genre']] if 'Genre' in filters else scraping.genres

        async with aiohttp.ClientSession() as session:
            tasks = []
            i = 0
            while i < len(pred_list) and len(filtered_list) < n:
                tasks.append(scraping.scrape_pred_data(pred_list[i].iid, i, filters, session))

                if len(tasks) % 25 == 0:
                    responses = await asyncio.gather(*tasks)
                    tasks = []
                    for response in responses:
                        if not ('viewers' in response and response['viewers'] > max_viewers) or ('genres' in response and not any(genre in genres_to_choose for genre in response['genres'])):
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
    films_df['Ranking'] = pd.to_numeric(films_df['Ranking'], errors='coerce')

    user_films = set(df[df['User'] == user]['Film Link'].unique())
    all_films = set(df['Film Link'].unique())
    films_too_popular = set(films_df[films_df['Ranking'] < min_rank]['Film Link'].unique())
    films_in_watchlists = set(functools.reduce((lambda a, b : set(a).union(set(b))), filters['Watchlists'])) if filters['Watchlists'] else set()
    
    # Filtering out films user has seen, films that don't meet popularity filter criteria, 
    # and films in user watchlists (if user opted to ignore films in watchlists)
    films = list(all_films - user_films - films_too_popular - films_in_watchlists)

    user_film_pairs = [(user, film, rating_mean) for film in films]
    predictions = algo.test(user_film_pairs)

    top_1000_recs = sorted(predictions, key=(lambda x : x.est), reverse=True)[:1000]

    print('Applying filters. . .')

    filtered_recs = await apply_filters(top_1000_recs, filters, n)

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