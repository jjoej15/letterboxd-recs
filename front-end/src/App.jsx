import { useState } from 'react'
import axios from 'axios';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCaretDown, faCheck } from '@fortawesome/free-solid-svg-icons'
import githubLogo from './assets/github-mark.svg';
import './css/App.css'
import GenreDropdown from './components/GenreDropdown'


function App() {
  const [mode, setMode] = useState('solo');
  const [excludeWatchlist, setExcludeWatchlist] = useState(true);
  const [popularityFilter, setPopularityFilter] = useState();
  const [genreFilters, setGenreFilters] = useState([]);
  const [user1, setUser1] = useState();
  const [user2, setUser2] = useState();
  const [isLoading, setIsLoading] = useState(false);
  const [recs, setRecs] = useState();
  const [errOccured, setErrOccured] = useState(false);
  const [clicked, setClicked] = useState(false);
  const [usersFetching, setUsersFetching] = useState([]);

  const handlePopularityClick = (pop) => {
    if (popularityFilter === pop) {
      setPopularityFilter(null)
    }

    else {
      setPopularityFilter(pop)
    }
  }

  const handleSubmit = async() => {
    try {
      if (!user1 || (mode === 'blend' && !user2)) {
        throw Error('Undefined usernames');
      }

      mode === 'blend' ? setUsersFetching([user1, user2]) : setUsersFetching([user1])
      setRecs(null)
      setIsLoading(true);
      setErrOccured(false);
      setClicked(true);

      const api_url = `https://clever-ambition-production.up.railway.app/api/?users=${mode === 'blend' ? `${user1},${user2}` : user1}&excludeWatchlist=${excludeWatchlist}&popFilter=${popularityFilter}&genreFilters=${genreFilters}`

      const response = await fetch(api_url);
      const data = await response.json(); 
      setRecs(data)  

    } catch (error) {
      console.error(error);
      setErrOccured(true);
      setRecs(null);

    } finally {
      setClicked(false);
      setIsLoading(false);
      setUsersFetching([]);
    }
  }
  
  return (
    <div className='app'>
      <div className='app-flexbox'>
        <h1 className='app-title'>Letterboxd Recommendations</h1>

        <p className='credits'>Project by Joe Anderson <a href="https://github.com/jjoej15" target="_blank"><img src={githubLogo} className='github-logo' alt='github logo' /></a>. 
          Source code located <a href="https://github.com/jjoej15/letterboxd-recs" target="_blank">here</a>.</p>
      
        <p className='app-desc'>Get film recomendations for any Letterboxd user. 
          Find a film to watch with a friend using Blend mode. Watchlists must be public to exclude films in watchlist. 
          May experience delays when applying genre filters. </p>


        <div className='mode-buttons'>
          <button className={mode === 'solo' ? 'mode-btn-clicked' : 'mode-btn'} id='solo-mode-btn' onClick={() => setMode('solo')}>
            Solo</button>

          <button className={mode === 'blend' ? 'mode-btn-clicked' : 'mode-btn'} id='blend-mode-btn' onClick={() => setMode('blend')}>
            Blend</button>
        </div> 

        <div className='form' >
          <div className='users'>
            <input type='text' className='user-input' placeholder='Enter Username' spellCheck='false' onChange={(u) => setUser1(u.target.value.trim().toLowerCase())} />

            {mode === 'blend' && <input type='text' className='user-input'  placeholder='Enter Username' spellCheck='false' onChange={(u) => setUser2(u.target.value.trim().toLowerCase())} />}         
          </div>

          <div id='exclude-btn'>
            <label>
              <input type='checkbox' name='exclude-watchlist-btn' onClick={(e) => setExcludeWatchlist(e.target.checked)} defaultChecked></input> 
              <p>Exclude films in watchlist</p>
            </label> 
          </div>

          <div className='filters'>
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

          <button type='submit' className='submit-btn' onClick={user1 !== undefined && !clicked ? handleSubmit : undefined}>Get Recs</button>
        </div>

        <div className='results'>
          {isLoading && 
          <div className='process-status'>
            {isLoading && <div className="loading" />}

            <p>Gathering recs for {usersFetching[1] ? `${usersFetching[0]} and ${usersFetching[1]}` : usersFetching[0]}</p>
          </div>}

          {errOccured && 
          <div className='process-status'>
            <p>Error occured. Please make sure {mode === 'blend' ? 'usernames are' : 'username is'} spelled correctly and try again.</p>
          </div>}

          {recs && 
          <div className='rec-container'>
            <h3 className='rec-header'>Recommendations</h3>

            <ul className='rec-list'>
              {recs.map((rec) => <li key={rec['Link']}><a href={rec['Link']} target="_blank">{rec['Film']}</a></li>)}
            </ul>
          </div>}        
        </div>

        <div className='spacer' />
      </div>
    </div>
  );
}

export default App;
