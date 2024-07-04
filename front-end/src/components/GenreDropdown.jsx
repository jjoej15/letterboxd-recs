import PropTypes from 'prop-types';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck } from '@fortawesome/free-solid-svg-icons'
import { useEffect } from 'react';

function GenreDropdown(props) {
    const [genreFilters, setGenreFilters] = [props.genreFilters, props.setGenreFilters];

    const handleGenreClick = (genre) => {
      if (!genre) {
        setGenreFilters([])
      } 
      
      else {
        if (!genreFilters || !genreFilters.includes(genre)) {
          setGenreFilters([...genreFilters, genre])
        }
  
        else {
          setGenreFilters(genreFilters.filter(g => g !== genre))
        }
      }
    }

    return(
        <div className='dropdown-content'>
          <button type='button' onClick={() => handleGenreClick(null)}>All {genreFilters.length === 0 && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Action')}>Action {genreFilters && genreFilters.includes('Action') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Adventure')}>Adventure {genreFilters && genreFilters.includes('Adventure') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Animation')}>Animation {genreFilters && genreFilters.includes('Animation') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Comedy')}>Comedy {genreFilters && genreFilters.includes('Comedy') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Crime')}>Crime {genreFilters && genreFilters.includes('Crime') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Documentary')}>Documentary {genreFilters && genreFilters.includes('Documentary') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Drama')}>Drama {genreFilters && genreFilters.includes('Drama') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Family')}>Family {genreFilters && genreFilters.includes('Family') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Fantasy')}>Fantasy {genreFilters && genreFilters.includes('Fantasy') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('History')}>History {genreFilters && genreFilters.includes('History') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Horror')}>Horror {genreFilters && genreFilters.includes('Horror') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Music')}>Music {genreFilters && genreFilters.includes('Music') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Mystery')}>Mystery {genreFilters && genreFilters.includes('Mystery') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Romance')}>Romance {genreFilters && genreFilters.includes('Romance') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Science Fiction')}>Science Fiction {genreFilters && genreFilters.includes('Science Fiction') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Thriller')}>Thriller {genreFilters && genreFilters.includes('Thriller') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('TV Movie')}>TV Movie {genreFilters && genreFilters.includes('TV Movie') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('War')}>War {genreFilters && genreFilters.includes('War') && <FontAwesomeIcon icon={faCheck} />}</button>
          <button type='button' onClick={() => handleGenreClick('Western')}>Western {genreFilters && genreFilters.includes('Western') && <FontAwesomeIcon icon={faCheck} />}</button>
        </div>
    );
}

GenreDropdown.propTypes = {
    genreFilters: PropTypes.array,
    setGenreFilters: PropTypes.func
}

export default GenreDropdown;