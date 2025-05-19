## Core Requirements

* A Docker Compose file is provided; you need to connect to PostgreSQL and create the necessary fields/tables.
* Scrape all campground data from the US map interface and store it in the database.
* Validate the data with Pydantic. You can check the required fields in `src/models/campground.py` (these are the fields that must be stored in the DB).
* **Scheduling**: Set up cron-like scheduling for regular updates. (15p)
* **Update**: Update existing records if they already exist. (10p)
* **Error Handling**: Handle errors in your code, especially HTTP errors, and add retries if necessary.

## Bonus

* **Database**: Use an ORM for PostgreSQL operations.
* **Logging**: Implement a comprehensive logging system.
* **API Endpoint**: Provide a Flask/FastAPI endpoint to trigger/control the scraper.
  *(Hint: You can implement this in an asynchronous way.)*
* **Performance**: Use multithreading or asynchronous implementation.
* **Reverse Geocoding**: Get the address from latitude/longitude coordinates.
* Feel free to get creative — every additional field is appreciated!

---

## Scraper Optimization and Grid System

In this project, a **grid system approach** is used to collect all campground data across the United States. The grid system works as follows:

* The entire geographical area of the United States is divided into a 20x25 (500) grid of cells.
* For each grid cell, API requests are made to collect campground data for that specific region.
* Pages are processed one by one for each grid cell, retrieving 500 campgrounds per page.
* Grid state is saved so that if the process is interrupted, it can resume from where it left off.
* Delays are added between requests to avoid rate limiting and hitting API restrictions.

---

## Usage

To run the system:

```bash
# For the initial setup
docker-compose up -d --build

# Start Docker containers
docker-compose up -d

# Trigger the scraper via API endpoint
curl -X POST http://localhost:8000/scrape/

# View statistics
curl http://localhost:8000/stats/
```

You can monitor the scraper’s progress via terminal output:

```
docker-compose logs -f
```

---

## Resetting the Database

To completely reset the database:

```bash
docker-compose down -v
docker-compose up -d
```

