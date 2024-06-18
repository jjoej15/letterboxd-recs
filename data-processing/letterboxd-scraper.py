from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import time
import json
import threading
import asyncio

def set_browser():
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    return webdriver.Firefox(options=options)

def scrape_popular_members(page, browser):
    url = "https://letterboxd.com/members/popular/" if page == 1 else f"https://letterboxd.com/members/popular/page/{page}/"
    browser.get(url)
    data = []

    try:
        WebDriverWait(browser, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "table-person")))
        html = browser.page_source
        soup = BeautifulSoup(html, 'lxml')
        if soup.title.text != "Letterboxd - Not Found":
            members = soup.find_all("div", class_="person-summary")

            for member in members:
                item = {}
                item['userHref'] = member.find('a').attrs['href']
                data.append(item)

            # Removing featured popular reviewers on right side of screen on webpage
            data = data[:-5]
            print(f'Page #{page} successfully scraped')   
        else:
            print(f"Page #{page} not found")

    except Exception as err:
        print(f"Error scraping page #{page}: {err}")

    finally:
        return data
    

def main():
    curr_page = 1
    num_pages = 167
    data = []
    browser = set_browser()
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for curr_page in range(1, num_pages+1):
            futures.append(executor.submit(scrape_popular_members, curr_page, browser))
        
        for future in futures:
            data += future.result()

    browser.quit()
    t1=time.time()
    print(f"{(t1-t0)/60} minutes to scrape data")

    df = pd.DataFrame(data)
    df.to_csv("members.csv")

    print("Process finished")


if __name__ == '__main__':
    main()