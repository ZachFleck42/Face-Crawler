import face_recognition
import os
import psycopg2
import requests
import sys
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
MAX_DEPTH = 3

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
    Returns the file's path as a string.s
    """
    # Assign and create a path and filename for the screenshot
    # Directory will be './imgs/<URL-hostname>/<URL-path>'
    path = "./imgs/" + urlparse(url).hostname
    if not os.path.exists(path):
        os.makedirs(path)

    # Assign a filename for the screenshot using the URL's path
    if not (filename := urlparse(url).path):
        filename = "index.png"
    else:
        filename = filename[1:].replace("/", "_") + ".png"

    # Resize the (headless) window to screenshot without scrolling
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


def countFaces(path):
    '''
    Fuction accepts a path to an image.
    Returns a dictionary with key values of {"filename": no. of faces in image}.
    '''
    image = face_recognition.load_image_file(path)
    face_locations = face_recognition.face_locations(image)

    return len(face_locations)


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

    cur.execute(sql.SQL("CREATE TABLE {} (page_url VARCHAR, face_count INT)")
                .format(sql.Identifier(websiteName)))

    # Initialize and run a headless Chrome web driver
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('window-size=1920x1080')
    webdriver_service = Service("/app/chromedriver/stable/chromedriver")
    driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)

    # Initialization is now done; begin processing the queue
    websiteFaceCount = 0
    for url in urls:
        # Append current URL to 'visitedLinks' list to prevent visiting again later
        pageURL = url[0]
        visitedLinks.append(pageURL)

        # Use Requests package to obtain a 'Response' object from the webpage,
        # containing page's HTML, connection status, and other useful info.
        pageResponse = requests.get(pageURL, header=headers)

        # Perform error checking on the URL connection.
        # If webpage can't be properly connected to, an error is raised and
        # program skips to next url in the queue.
        # TODO: Check more page status codes
        pageStatus = pageResponse.status_code
        if pageStatus != 200:
            print(f"ERROR: {pageURL} could not be accessed. Continuing...")
            continue

        # Parse the webpage into a BeautifulSoup4 nested data structure
        webpage = BeautifulSoup(pageResponse.text, 'html.parser')

        # Save a screenshot of the webpage and get its path
        pageScreenshot = getScreenshot(driver, pageURL)

        # Count how many faces are on the page #!
        pageFaceCount = countFaces(pageScreenshot)
        websiteFaceCount += pageFaceCount

        # Append data to the database
        cur.execute(
            sql.SQL("INSERT INTO {} VALUES (%s, %s)")
            .format(sql.Identifier(websiteName)),
            [pageURL, pageFaceCount])

        # Get a list of all the links found within a page's <a> tags
        # Returned links will be 'cleaned' (see function docstring)
        pageLinks = getLinks(pageURL, webpage)

        # Append unvisited links to 'urls' list (if their depth does not exceed MAX_DEPTH)
        if (newDepth := url[1] + 1) <= MAX_DEPTH:
            for newURL in pageLinks:
                urls.append((newURL, newDepth))

    # Print results to terminal
    query = sql.SQL("SELECT * FROM {};").format(sql.Identifier(websiteName))
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        print(row)

    # Append changes to database and close connections
    conn.commit()
    cur.close()
    conn.close()

    # Print a conclusion message to indicate successful termination
    print("------")
    print(f"Total faces found on website: {websiteFaceCount}")
