'''
    Scrapes all data and builds model. Will take several hours to complete.
'''

import os
import time

t0 = time.time()

os.system('py members_scraper.py')
os.system('py ratings_scraper.py')
os.system('py film_scraper.py')
os.system('py create_model.py')

t1 = time.time()

print(f'Entire process finished in {(t1-t0)/60/60} hours')