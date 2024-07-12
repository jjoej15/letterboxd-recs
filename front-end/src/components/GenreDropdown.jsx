import PropTypes from 'prop-types';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck } from '@fortawesome/free-solid-svg-icons'


function GenreDropdown(props) {
    const [genreFilters, setGenreFilters] = [props.genreFilters, props.setGenreFilters];

    const handleGenreClick = (genre) => {
      if (!genre) {
        setGenreFilters([])
      } 
      
      else {
        if (!genreFilters || !genreFilters.includes(genre)) { // Adding genre to genreFilters
          setGenreFilters([...genreFilters, genre])
        }
  
        else {
          setGenreFilters(genreFilters.filter(g => g !== genre)) // Removing genre from genreFilters
        }
      }
    }

    const genres = [
      "Action",
      "Adventure",
      "Animation",
      "Comedy",
      "Crime",
      "Documentary",
      "Drama",
      "Family",
      "Fantasy",
      "History",
      "Horror",
      "Music",
      "Mystery",
      "Romance",
      "Science Fiction",
      "Thriller",
      "TV Movie",
      "War",
      "Western"
    ];

    return(
        <div className='dropdown-content'>
          <button type='button' onClick={() => handleGenreClick(null)}>All {genreFilters.length === 0 && <FontAwesomeIcon icon={faCheck} />}</button>
          {genres.map((genre) => <button type='button' key={genre} onClick={() => handleGenreClick(genre)}>{genre} {genreFilters && genreFilters.includes(genre) && <FontAwesomeIcon icon={faCheck} />}</button>)}

        </div>
    );
}

GenreDropdown.propTypes = {
    genreFilters: PropTypes.array,
    setGenreFilters: PropTypes.func
}

export default GenreDropdown;