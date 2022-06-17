import os
import psycopg2
import sys
import requests
from tasks import processImage
from bs4 import BeautifulSoup
from psycopg2 import sql
from Screenshot import Screenshot_Clipping
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib.parse import urlparse


# Create a queue of URLs to visit and collect data from.
# Each URL will also have a corresponding 'depth', or number of links removed from the original URL.
# Thus, the queue will be a list of tuples in the form (string URL, int Depth)
urls = []

# Store the initial URL as a global variable for reference across functions
INITIAL_URL = sys.argv[1]

# Define a 'maximum depth', or how far removed from the main URL the program should explore
MAX_DEPTH = int(sys.argv[2])

# Create a list of already-visited links to prevent visiting the same page twice
visitedLinks = []


def getLinks(pageResponse):
    '''
    Accepts a webpage in the form of a 'response object' from the Requests package.
    Returns a list of links (as strings) discovered on that webpage.

    Links are 'cleaned', meaning page anchor, email address, and telephone links
    are removed. Internal links are expanded to full URLs. Previously-visited 
    URLs, URLs currently in the queue, and links to different domains are also removed.
    '''
    webpageURL = pageResponse.url
    parsedPage = BeautifulSoup(pageResponse.text, 'html.parser')

    # Find all valid links (not NoneType) from the <a> tags on the webpage
    links = []
    for link in parsedPage.find_all('a'):
        if (temp := link.get('href')):
            links.append(temp)

    # 'Clean' the links (see function docstring)
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

        # Remove any dangling '/'s
        links[index] = links[index].rstrip('/')

        # All filters passed; link is appended to 'clean' list
        linksClean.append(links[index])

    # Remove any duplicate links in the list and return
    return list(set(linksClean))


def getScreenshot(driver, url):
    """
    Accepts a web driver and a URL.
    Takes a screenshot of the full webpage and stores it in a local directory. 
    Returns the file's path as a string.
    """
    # Assign and create a path and filename for the screenshot
    # Directory format: './imgs/<URL-hostname>/<URL-path>'
    path = "./imgs/" + urlparse(url).hostname
    if not os.path.exists(path):
        os.makedirs(path)

    # Assign a filename for the screenshot using the URL's path
    if not (filename := urlparse(url).path):
        filename = "index.png"
    else:
        filename = filename[1:].replace("/", "_") + ".png"

    # Resize the (headless) window to screenshot the page without scrolling
    # This helps avoid persistent nav/infobars, cookie notifications, and other alerts
    driver.get(url)
    originalSize = driver.get_window_size()
    required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
    required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
    driver.set_window_size(required_width, required_height)

    # Take the screenshot, save it to the assigned path, and return the path
    ss = Screenshot_Clipping.Screenshot()
    imagePath = ss.full_Screenshot(driver, save_path=path, image_name=filename)

    # Return the window to original size
    driver.set_window_size(originalSize['width'], originalSize['height'])

    return imagePath


if __name__ == "__main__":
    # Check for valid number of arguments (2) in the script call.
    if (len(sys.argv) != 3):
        print("FATAL ERROR: Improper number of arguments. "
              "Please call program as: 'python app.py <URL> <MAX_DEPTH>")
        sys.exit()
    else:
        initialURL = sys.argv[1]
        initialHost = urlparse(initialURL).hostname
        urls.append((initialURL, 0))  # Initial URL has a depth of 0

    # Initialize and run a headless Chrome web driver
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('window-size=1280x720')
    webdriver_service = Service("/app/chromedriver/stable/chromedriver")
    driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)

    # Connect to PostgresSQL database and prepare to enter data
    conn = psycopg2.connect(host='postgres', database='faceCrawler', user='postgres', password='postgres')
    cur = conn.cursor()
    tableName = (urlparse(initialURL).hostname).replace('.', '')
    cur.execute(sql.SQL("CREATE TABLE {} (page_url VARCHAR, face_count INT)")
                .format(sql.Identifier(tableName)))
    conn.commit()
    cur.close()
    conn.close()

    # Initialization is now done; begin processing the queue
    websiteFaceCount = 0
    for url in urls:
        # Append current URL to 'visitedLinks' list to prevent visiting again later
        pageURL = url[0]
        visitedLinks.append(pageURL)
        print(f"Attempting to connect to URL: {pageURL}")

        # Use Requests package to obtain a 'Response' object from the webpage,
        # containing page's HTML, connection status, and other useful info.
        pageResponse = requests.get(pageURL, headers=headers)

        # Perform error checking on the URL connection.
        # If webpage can't be properly connected to, an error is raised and
        # program skips to next url in the queue.
        pageStatus = pageResponse.status_code
        if pageStatus != 200:
            print(f"ERROR: {pageURL} could not be accessed. Continuing...")
            continue
        else:
            print("Connected. Taking screenshot...")

        # If the current webpage is not at MAX_DEPTH, get a list of links found
        # in the page's <a> tags. Links will be 'cleaned' (see function docstring)
        if url[1] < MAX_DEPTH:
            pageLinks = getLinks(pageResponse)
            for link in pageLinks:
                urls.append((link, url[1] + 1))

        # Save a screenshot of the webpage and get its path
        pageScreenshot = getScreenshot(driver, pageURL)
        print("Screenshot saved. Sending to Celery worker for processing...")

        # Do the thing # !!!
        thing = processImage.delay(pageURL, pageScreenshot)  # !!!
