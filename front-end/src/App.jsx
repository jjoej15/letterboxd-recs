import { useEffect, useState } from 'react'
import './css/App.css'
import GenreDropdown from './components/GenreDropdown'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCaretDown, faCheck } from '@fortawesome/free-solid-svg-icons'
import githubLogo from './assets/github-mark.svg';

function App() {
  const [mode, setMode] = useState('solo')
  const [excludeWatchlist, setExcludeWatchlist] = useState(true)
  const [popularityFilter, setPopularityFilter] = useState()
  const [genreFilters, setGenreFilters] = useState([])

  const handlePopularityClick = (pop) => {
    if (popularityFilter === pop) {
      setPopularityFilter(null)
    }

    else {
      setPopularityFilter(pop)
    }
  }
  
  return (
    <div className='app'>
      <div className='app-flexbox'>
        <h1 className='app-title'>Letterboxd Recommendations</h1>

        <p className='app-desc'>Get film recomendations for any Letterboxd user. 
          Find a film to watch with a friend using Blend mode. Watchlists must be public to exclude films in watchlist. 
          May experience delays when applying genre filters. </p>


        <div className='mode-buttons'>
          <button className={mode === 'solo' ? 'mode-btn-clicked' : 'mode-btn'} id='solo-mode-btn' onClick={() => setMode('solo')}>
            {mode === 'solo' ? <u>Solo</u> : 'Solo'}</button>

          <button className={mode === 'blend' ? 'mode-btn-clicked' : 'mode-btn'} id='blend-mode-btn' onClick={() => setMode('blend')}>
            {mode === 'blend' ? <u>Blend</u> : 'Blend'}</button>
        </div> 

        <form className='form'>
          <div className='users'>
            <input type='text' className='user-input' placeholder='Enter Username' />

            {mode === 'blend' && <input type='text' className='user-input' placeholder='Enter Username' />}         
          </div>

          <div id='exclude-btn'>
            <label>
              <input type='checkbox' name='exclude-watchlist-btn' defaultChecked></input> 
              <p>Exclude films in watchlist</p>
            </label> 
          </div>

          <div className='filters'>
            {/* <label htmlFor='filter-dropdowns'>Filters: </label> */}

            <div className='dropdown'>
              <button className='filter-dropdown-title'>
                <p>Popularity</p>
                <FontAwesomeIcon icon={faCaretDown} />
              </button>

              <div className='dropdown-content'>
                <button type='button' onClick={() => handlePopularityClick(null)}>All {!popularityFilter && <FontAwesomeIcon icon={faCheck} />}</button>
                <button type='button' onClick={() => handlePopularityClick('1')}>Lesser Known Films {popularityFilter == '1' && <FontAwesomeIcon icon={faCheck} />}</button>
                <button type='button' onClick={() => handlePopularityClick('2')}>Even Lesser Known Films {popularityFilter == '2' && <FontAwesomeIcon icon={faCheck} />}</button>
                <button type='button' onClick={() => handlePopularityClick('3')}>Unknown Films {popularityFilter == '3' && <FontAwesomeIcon icon={faCheck} />}</button>
              </div>
            </div>

            <div className='dropdown'>
              <button className='filter-dropdown-title'>
                <p>Genre</p>
                <FontAwesomeIcon icon={faCaretDown} />
              </button>

              <GenreDropdown genreFilters={genreFilters} setGenreFilters={setGenreFilters} />
            </div>
          </div>

          <button type='submit' className='submit-btn'>Get Recs</button>
        </form>

        {/* <p className='process-status'>
          Scraping data for jjoejj. . .
        </p>

        <div className='rec-container'>
          <h3 className='rec-header'>Recommendations</h3>

          <ul className='rec-list'>
            <li>shawshank redemption</li>
            <li>parasite</li>
          </ul>
        </div> */}
      </div>

      {/* <p className='app-desc'>Lorem ipsum dolor sit amet consectetur adipisicing elit. Necessitatibus illo consequuntur voluptate aut sint iste ea, dolor doloribus. Necessitatibus exercitationem ratione nam corrupti sint fugit velit distinctio voluptates impedit deleniti.</p> */}


      <footer className="footer">
          <p>Project by Joe Anderson <a href="https://github.com/jjoej15" target="_blank"><img src={githubLogo} className='github-logo' alt='github logo' /></a>. 
            Source code located <a href="https://github.com/jjoej15/letterboxd-recs" target="_blank">here</a>.</p>
      </footer> 
    </div>

  );
}

export default App;
