# Face-Finding-Web-Crawler
Crawl the web. Find the faces.

Program crawls a domain (using Requests package, BS4 html parser, and Selenium headless browsers), takes screenshots of each page, and analyzes the screenshots for faces.
Screenshots are modified to highlight faces (those without faces are deleted), and total face-count is tallied. 
Celery and RabbitMQ are used to queue image processing tasks and asynchronously exeucte the tasks, significantly reducing program runtime.
Data scraped from each webpage (including page face count) is stored in a PostgresSQL database directly from script (via Psycopg).

Project makes use of Docker to control development environment and enable easy setup/use for other users/computers.

<br>

## Installation/Use:
1. Download repository into a local directory
2. Run ```docker-compose up``` in the directory
3. Run ```docker-compose exec app bash``` to enter into the main app container
4. Call the script as ```python crawler.py <URL> <MAX-DEPTH>```, where URL is a link to a webpage on the domain you'd like to crawl, and MAX-DEPTH is the 'distance' or number of links removed from the URL you'd like the crawler to explore.
5. Screenshots will be stored locally in a newly-created 'app/imgs/' directory. Website face count will be displayed once program has finished running. 
6. To view individual page data, you will have to enter the PostgresSQL container via ```docker-compose exec postgres bash```, followed by ```psql -U postgres``` and ```\c faceCrawler``` within the container.
