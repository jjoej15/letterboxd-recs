import pandas as pd
from surprise import SVD, Reader, Dataset, accuracy, dump
import time
import random
from joblib import Parallel, delayed


def sample_ratings(user, user_ratings, n=200):
    print(f'Sampling user {user}. . .')
    
    available_indices = list(range(len(user_ratings)))
    sampled_data = []
    i = 0
    while i < len(user_ratings) and i < n:
        idx = random.choice(available_indices)
        sampled_data.append({
            'User': user,
            'Film': user_ratings[idx][2],
            'Film Link': user_ratings[idx][3],
            'Rating': user_ratings[idx][4]
        })

        available_indices.remove(idx)
        i += 1

    return sampled_data



def main():
    t0 = time.time()

    # Loading data
    full_df = pd.read_csv('data/ratings.csv')
    results = Parallel(n_jobs=-1)(
        delayed(sample_ratings)(user, full_df[full_df['User'] == user].values.tolist())
        for user in full_df['User'].unique()
    )

    data = [rating for result in results for rating in result] 
    df = pd.DataFrame(data)
    df.to_pickle('pickles/model_df.pkl')
    
    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df[["User", "Film Link", "Rating"]], reader)

    # Building trainset
    trainset = data.build_full_trainset()

    # Creating algorithm and training it
    algo = SVD()
    algo.fit(trainset)

    dump.dump('pickles/rec_model.pkl', algo=algo, verbose=1)

    t1 = time.time()
    print((t1-t0)/60, 'mins to build model.')

    # Prompting user to test model's RMSE
    test_model = input('Test model? (Y/N): ').capitalize()
    while (test_model != 'Y' and test_model != 'N'):
        test_model = input('Test model? (Y/N): ').capitalize()
    if test_model == 'Y':
        try:
            predictions_svd = algo.test(trainset.build_anti_testset())
            accuracy.rmse(predictions_svd)

        except Exception as err:
            print(err)



if __name__ == '__main__':
    main()
