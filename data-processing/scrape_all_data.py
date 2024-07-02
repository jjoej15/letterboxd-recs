import os
import time

t0 = time.time()

os.system('py members_scraper.py')
os.system('py ratings_scraper.py')
os.system('py film_scraper.py')

t1 = time.time()

print(f'Process finished in {(t1-t0)/60/60} hours')