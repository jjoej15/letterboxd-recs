# Letterboxd Recommendations

Web app that uses web scraping to give film recommendations using an SVD collaborative filtering model for any Letterboxd user or a recommendation for two using Blend mode. Can include filters such as film popularity, film genre, and films in user's watchlist. Check out deployed website here: https://letterboxdrecs.netlify.app/

## Table of Contents

- [Methods](#methods)
- [Technologies Used](#technologies-used)
- [Installation and Usage of CLI](#installation)
- [Scraping Your Own Data and Building a Model](#scrape-data-and-build-model)

## Methods

### Scraping data
- Scraped ratings data from the 5009 most popular members on Letterboxd. Most of these users had ratings for thousands of films and the total dataset came out to include roughly 13 million ratings.
- Scraped data about every film's popularity ranking on Letterboxd. This was useful for when a user wants to apply popularity filters on their recommendations. This dataset came out to include ~950k films.
- Needed to scrape data in a reasonable amount of time, found writing asynchronous code using the asyncio and aiohttp libraries to be the fastest.

### Building Model
- Decided to use SVD factorization in a collaborative filtering model (popularized for usage in recommendation algorithms by Simon Funk in the [Netflix Prize competition](https://en.wikipedia.org/wiki/Netflix_Prize))
- Usage of the [Surprise](https://surpriselib.com/) scikit package made creating this algorithm surprisingly easy, though due to memory constraints I decided to use random samples of 200 ratings from each user, meaning the trainset used by the model had ~1,000,000 ratings in it.

### Running Application
- Application scrapes user data dynamically when given valid Letterboxd username, includes it in testset with the other user ratings and runs SVD algorithm. Gives 50 recommendations for films user hasn't watched yet based on what films the algorithm predicts the user will rate the highest. 
- When using blend mode, application scrapes data for both users, takes the average of the ratings for films both users have watched. For films that user one has watched and user two hasn't, SVD algorithm predicts what rating user two would give film, and uses that to find average. Then use these ratings with testset as you would if it were a single user.
- When applying filters, program must scrape info about films dynamically. Algorithm gives 1000 top recommendations, then find the 50 highest ones that also meet the filter conditions. 
- This is why applying genre filters can cause program to take a long time to run. 
- When applying popularity filters, most of the work is done already since we have the popularity rankings in films.csv, but some films that weren't listed on Letterboxd's film page can slip through the cracks which is why it's necessary to scrape info about film popularity dynamically as well.
- Also included option to exclude films in user's watchlist. When checked, application scrapes user watchlist and excludes films in it from being recommended. User watchlist must be unprivated.

## Technologies Used

### Front End
- **React.js**
- **Vite**
- **CSS5**
- **Netlify for hosting**

### Back End
- **Python**
- **FastAPI**
- **DockerHub/Railway for hosting API**

### Data Processing
- **Python**
- **asyncio/aiohttp for asynchronous requests**
- **BeautifulSoup4 for parsing HTML**
- **pandas to handle data**
- **Surprise scikit for building model**

## Installation

To use the command line version of the application locally, follow these steps:

1. **Clone the repository:**
   ```sh
   git clone https://github.com/jjoej15/letterboxd-recs.git
   cd letterboxd-recs
   ```
2. **Obtain pickle files and films.csv**
- Either [scrape your own data](#scrape-data-and-build-model)
- or download necessary files [here](https://drive.google.com/file/d/16sAdnrwurwpJiAUzE0lbiS8hO7MV8Vkd/view?usp=sharing). (~213 mb)
- Make sure your data-processing directory looks like this:        
├── data-processing         
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── data      
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── films.csv     
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── pickles     
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── model_df.pkl     
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── rec_model.pkl        
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── (rest of the py files that are in cloned repository)         


3. **Install dependencies**
   ```sh
   cd data-processing
   pip install -r requirements.txt
   ```

3. **Run app**
    ```sh
    py get_recs.py
    ```

## Scrape Data and Build Model

If you want to scrape your own data from Letterboxd and build your own model, follow these steps:

1. **Navigate to data-processing directory**
   ```sh
   cd data-processing
   ```

2. **Install dependences:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Run the script:**
   ```sh
   py scrape_all_data.py
   ```

This process will take several hours to complete (scraping > 200,000 web pages) and all of the data will add up to a size of >1GB (ratings.csv will likely contain over 13 million ratings). 
