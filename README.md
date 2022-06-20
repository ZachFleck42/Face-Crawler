# Face-Crawler
Crawl the web. Find the faces.

Program crawls a domain (using Requests package, BS4 html parser, and Selenium headless browsers), takes screenshots of each page, and analyzes the screenshots for faces.
Screenshots are modified to highlight faces (those without faces are deleted), and total face-count is tallied. 
Celery and RabbitMQ are used to queue image processing tasks and asynchronously exeucte the tasks, significantly reducing program runtime.
Data scraped from each webpage (including page face count) is stored in a PostgresSQL database directly from script (via Psycopg).

Project makes use of Docker to control development environment and enable easy setup/use for other users/computers.
