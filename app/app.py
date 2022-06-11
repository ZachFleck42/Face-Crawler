import pandas as pd
# import psycopg2
# import re
import requests
import sys
from bs4 import BeautifulSoup
# from celery import Celery
from urllib.parse import urlparse

MAX_DEPTH = 10


def parseWebpage(url):
    '''
    Parses a webpage from its URL.

    Parameters
    ----------
        url : A website url (string)

    Returns
    -------
        A parsed HTML webpage data stucture from BeautifulSoup4
    '''
    webpage = requests.get(url)
    webpageHTMLDoc = webpage.text

    return BeautifulSoup(webpageHTMLDoc, 'html.parser')


def getLinks(parsedPage):
    '''
    Finda all the URLs found on a webpage and stores them in a list.

    Parameters
    ----------
        parsedPage: A parsed HTML webpage data structure from BeautifulSoup4

    Returns
    -------
        links: A list of all links found in that webpage's <a> tags
    '''
    links = []
    for link in parsedPage.find_all('a'):
        links.append(link)

    return links


def cleanLinks(sourceWebpageURL, webpageLinks, visitedLinks=[]):
    '''
    Removes page anchors and expands internal links from a list of links.
    Optionally removes URLs that have already been visited.

    Parameters
    ----------
        sourceWebpageURL: The URL of the source webpage
        webpageLinks: A raw list of all the links pulled from the source webpage
        (Optional) visitedLinks: A list of URLs that have already been visited

    Returns
    -------
        ???: A 'cleaned' list of URLs
    '''
    # TODO: Implement function
    pass


if __name__ == "__main__":
    # Create empty list of tuples containing URL strings and their 'depths'
    # The 'depth' of all initial URLs will be '0'
    urls = []

    # Check for valid number of arguments (1 or 2)
    # If only 1 argument (the script name only), ask user to input a URL
    if (len(sys.argv) > 2):
        # TODO: Add error for improper number of arguments
        pass
    elif (len(sys.argv) < 2):
        print("No file input. Enter a website URL (or enter 'q' to quit): ")
        # TODO: If 'q' input, exit program
        # TODO: Use RegEx to verify valid URL input?
        pass
    else:
        # Indentify file extension and read file accordingly
        fileExtension = (sys.argv[1]).rstrip[-4:]

        if (fileExtension == ".csv"):
            # TODO: Read URLs from .csv files
            pass
        elif (fileExtension == ".xlsx"):
            # TODO: Read URLs from Excel files
            pass
        elif (fileExtension == ".???"):
            pass
        else:
            # TODO: Add error for unknown/unsupported file types
            pass

    # Create a list of already-visited links to prevent visiting the same page twice
    visitedLinks = []

    for url in urls:
        # Parse the webpage into a BeautifulSoup4 data structure
        # TODO: Check for errors (using code returned from 'request'?)
        webpage = parseWebpage(url[0])

        # Get a list of all the links found within a page's <a> tags
        webpageLinksRaw = getLinks(webpage)

        # Remove anchor, internal, and already-visited links
        webpageLinksClean = cleanLinks(url[0], webpageLinksRaw, visitedLinks)

        # Add depths to all unvisited URLs and append the tuple to 'urls' list
        for newURL in webpageLinksClean:
            # If the URL is on the same domain as the current URL
            if urlparse(newURL).netloc == urlparse(url[0]).netloc:
                urls.append((newURL, url[1]))
            # Otherwise, check that the new depth does not exceed MAX_DEPTH
            elif ((linkDepth := url[1] + 1) <= MAX_DEPTH):
                urls.append((newURL, linkDepth))
            else:
                continue

        # TODO: Collect requested data from webpage

        # TODO: Append the wanted data to database

        # Add webpage to visited URLs list
        visitedLinks.append(url[0])

    # TODO: Print some sort of conclusion message (with helpful stats)
