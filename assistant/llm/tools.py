"""Tool definitions for Claude and dispatch registry."""

TOOLS = [
    {
        "name": "search_movies",
        "description": (
            "Search for movies by title or keywords using TMDB. "
            "Use when a user asks to find a movie or wants keyword-based recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Movie title or search keywords",
                },
                "year": {
                    "type": "integer",
                    "description": "Optional: filter by release year",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_movie_details",
        "description": (
            "Get detailed information about a specific movie from TMDB "
            "including plot, genres, runtime, cast, budget, and revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "TMDB movie ID",
                },
            },
            "required": ["movie_id"],
        },
    },
    {
        "name": "get_similar_movies",
        "description": (
            "Get movies similar to a given movie from TMDB. "
            "Use when a user says 'something like X' or asks for similar recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "TMDB movie ID of the reference movie",
                },
            },
            "required": ["movie_id"],
        },
    },
    {
        "name": "get_trending_movies",
        "description": (
            "Get currently trending movies from TMDB. "
            "Use when a user asks what's popular or trending right now."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_window": {
                    "type": "string",
                    "enum": ["day", "week"],
                    "description": "Time window for trending: 'day' or 'week'",
                },
            },
            "required": ["time_window"],
        },
    },
    {
        "name": "get_watch_providers",
        "description": (
            "Get streaming, rental, and purchase platforms for a movie from TMDB. "
            "Shows where a movie is available to watch at home (e.g., Netflix, Apple TV, etc.). "
            "Returns results for Israel first, falling back to US availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "TMDB movie ID",
                },
            },
            "required": ["movie_id"],
        },
    },
    {
        "name": "get_movie_ratings",
        "description": (
            "Get ratings from multiple sources (IMDb, Rotten Tomatoes, Metacritic) "
            "plus box office data and awards information via OMDB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Movie title to look up",
                },
                "imdb_id": {
                    "type": "string",
                    "description": "IMDb ID (e.g. 'tt1234567') for more accurate results",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_nearby_cinemas",
        "description": (
            "Get a list of cinemas, optionally filtered by city. "
            "Use when a user asks where to watch a movie or about local cinemas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name to filter cinemas",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_showtimes",
        "description": (
            "Get movie showtimes at local cinemas. "
            "Can filter by film title, cinema ID, and date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "film_title": {
                    "type": "string",
                    "description": "Title of the film to find showtimes for",
                },
                "cinema_id": {
                    "type": "integer",
                    "description": "Specific cinema ID to filter by",
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
            },
            "required": [],
        },
    },
    {
        "name": "book_tickets",
        "description": (
            "Book movie tickets for a specific showtime. "
            "IMPORTANT: (1) You MUST call get_showtimes in the SAME turn to get a fresh "
            "showtime_id before calling this tool. NEVER reuse a showtime_id from an earlier "
            "turn or from memory — IDs may be stale or misremembered. "
            "(2) Always confirm booking details with the user before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "showtime_id": {
                    "type": "integer",
                    "description": "The showtime ID to book",
                },
                "num_tickets": {
                    "type": "integer",
                    "description": "Number of tickets to book",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer's full name",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Customer's email address",
                },
            },
            "required": ["showtime_id", "num_tickets", "customer_name", "customer_email"],
        },
    },
]

# Maps tool name -> (provider_key, method_name)
TOOL_REGISTRY: dict[str, tuple[str, str]] = {
    "search_movies": ("tmdb", "search_movies"),
    "get_movie_details": ("tmdb", "get_movie_details"),
    "get_similar_movies": ("tmdb", "get_similar_movies"),
    "get_trending_movies": ("tmdb", "get_trending_movies"),
    "get_watch_providers": ("tmdb", "get_watch_providers"),
    "get_movie_ratings": ("omdb", "get_movie_ratings"),
    "get_nearby_cinemas": ("cinema", "get_cinemas"),
    "get_showtimes": ("cinema", "get_showtimes"),
    "book_tickets": ("cinema", "book_tickets"),
}
