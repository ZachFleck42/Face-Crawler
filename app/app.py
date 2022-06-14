import pandas as pd
import psycopg2
import requests
import sys
from bs4 import BeautifulSoup
from psycopg2 import sql
from urllib.parse import urlparse

# Store the initial URL as a global variable for reference across functions
INITIAL_URL = sys.argv[1]

# Define a 'maximum depth', or how far removed from the main URL the program should explore
MAX_DEPTH = 3

# Create a queue of URLs to visit and collect data from.
# Each URL will also have a corresponding 'depth', or number of links
# removed from the original URL.
# Thus, the queue will be a list of tuples in the form (string URL, int Depth)
urls = []

# Create a list of already-visited links to prevent visiting the same page twice
visitedLinks = []


def getLinks(webpageURL, parsedPage):
    '''
    Accepts a webpage's URL and its BeautifulSoup4 nested data structure.
    Returns a list of links (as strings) discovered on that webpage.

    Links are 'cleaned', meaning page anchor, email address, and telephone links
    are removed. Internal links are expanded to full URLs. Previously-visited 
    URLs, URLs currently in the queue, and links to different domains are also removed.
    '''
    links = []
    for link in parsedPage.find_all('a'):
        if (temp := link.get('href')):
            links.append(temp)

    # Clean the links
    linksClean = []
    for index, link in enumerate(links):
        # Ignore any links to the current page
        if link == '/':
            continue

        # Ignore page anchor links
        if '#' in link:
            continue

        # Ignore email address links
        if link[:7] == "mailto:":
            continue

        # Ignore telephone links
        if link[:4] == "tel:":
            continue

        # Expand internal links
        parsedURL = urlparse(webpageURL)
        if link[0] == '/':
            links[index] = parsedURL.scheme + "://" + parsedURL.hostname + link

        # Ignore links to other domains
        initalHost = (urlparse(INITIAL_URL)).hostname
        linkHost = (urlparse(links[index])).hostname
        if initalHost != linkHost:
            continue

        # Ignore all links to previously-visited URLs
        if links[index] in visitedLinks:
            continue

        # Ignore links that are already in the queue
        inQueue = False
        for url in urls:
            if url[0] == links[index]:
                inQueue = True
                break
        if inQueue:
            continue

        # All filters passed; link is appended to 'clean' list
        linksClean.append(links[index])

    # Remove any duplicate links in the list and return
    return list(set(linksClean))


if __name__ == "__main__":
    # Check for valid number of arguments (2) in the script call.
    if (len(sys.argv) != 2):
        print("FATAL ERROR: Improper number of arguments. "
              "Please call program as: 'python app.py YOUR-URL-HERE'")
        sys.exit()
    else:
        initialURL = sys.argv[1]
        initialHost = urlparse(initialURL).hostname
        urls.append((initialURL, 0))  # Initial URL has a depth of 0

    # Connect to PostgresSQL database and prepare to enter data
    conn = psycopg2.connect(host="postgres-db", database="postgres", user="postgres", password="postgres")
    cur = conn.cursor()

    # Create a new table for the website in the database
    websiteName = []
    for char in initialHost:
        if char == '.':
            break
        websiteName.append(char)
    websiteName = ''.join(websiteName)

    cur.execute(sql.SQL("CREATE TABLE {} (pageURL VARCHAR, pageTitle VARCHAR)")
                .format(sql.Identifier(websiteName)))

    # Initialization is now done; begin processing the queue
    for url in urls:
        # Append current URL to 'visitedLinks' list to prevent visiting again later
        pageURL = url[0]
        visitedLinks.append(pageURL)

        # Use Requests package to obtain a 'Response' object from the webpage,
        # containing page's HTML, connection status, and other useful info.
        pageResponse = requests.get(pageURL)

        # Perform error checking on the URL connection.
        # If webpage can't be properly connected to, an error is raised and
        # program skips to next url in the queue.
        pageStatus = pageResponse.status_code
        if pageStatus != 200:
            print(f"ERROR: {pageURL} could not be accessed. Continuing...")
            continue

        # Parse the webpage into a BeautifulSoup4 data structure
        webpage = BeautifulSoup(pageResponse.text, 'html.parser')

        # Collect some data from webpage
        pageTitle = webpage.title.string

        # Append the wanted data to database
        cur.execute(
            sql.SQL("INSERT INTO {} VALUES (%s, %s)")
            .format(sql.Identifier(websiteName)),
            [pageURL, pageTitle])

        # Get a list of all the links found within a page's <a> tags
        # Returned links will be 'cleaned' (see function docstring)
        pageLinks = getLinks(pageURL, webpage)

        # Append unvisited links to 'urls' list (if their depth does not exceed MAX_DEPTH)
        if (newDepth := url[1] + 1) <= MAX_DEPTH:
            for newURL in pageLinks:
                urls.append((newURL, newDepth))

    # ! Testing
    query = sql.SQL("SELECT * FROM {};").format(sql.Identifier(websiteName))
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        print(row)

    # Append changes to database and close connections
    conn.commit()
    cur.close()
    conn.close()

    # Print some sort of conclusion message (with helpful stats)
    print("------")
    print("Fin")
