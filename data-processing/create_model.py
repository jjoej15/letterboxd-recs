import pandas as pd
from surprise import SVD, Reader, Dataset, accuracy, dump

def main():
    # Loading data
    df = pd.read_csv('data/ratings.csv')
    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df[["User", "Film Link", "Rating"]], reader)

    # Retrieving trainset
    trainset = data.build_full_trainset()

    # Creating algorithm and training it
    algo = SVD()
    algo.fit(trainset)

    dump.dump('rec_model.pkl', algo=algo, verbose=1)

    # Prompting user to test model's RMSE
    test_model = input('Test model? (Y/N): ').capitalize()
    while (test_model != 'Y' and test_model != 'N'):
        test_model = input('Test model? (Y/N): ').capitalize()
    if test_model == 'Y':
        predictions_svd = algo.test(trainset.build_anti_testset())
        accuracy.rmse(predictions_svd)

if __name__ == '__main__':
    main()
