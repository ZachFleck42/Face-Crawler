import numbers
import face_recognition
import os
import psycopg2
from celery_app import app
from PIL import Image, ImageDraw
from psycopg2 import sql
from urllib.parse import urlparse


def countFaces(imagePath):
    '''
    Accepts a path to an image.
    Returns how many faces were found in the image and their locations.
    '''
    # 'hog' model used as it is faster on CPUs (but less accurate)
    # Switch model to 'cnn' for more accuracy (but significantly slower processing times)
    image = face_recognition.load_image_file(imagePath)
    faceLocations = face_recognition.face_locations(image, number_of_times_to_upsample=2, model='hog')
    faceCount = len(faceLocations)

    return faceCount, faceLocations


def highlightFaces(imagePath, faceLocations):
    '''
    Aceepts a path to an image and the locations of all the faces in the image.
    Uses PIL module to draw boxes around all faces.
    Returns nothing.
    '''
    pilImage = Image.open(imagePath)
    for faceLocation in faceLocations:
        top, right, bottom, left = faceLocation
        shape = [(left, top), (right, bottom)]
        img1 = ImageDraw.Draw(pilImage)
        img1.rectangle(shape, outline="red", width=4)

    pilImage.save(imagePath)
    pilImage.close()


def appendToDatabase(pageURL, pageFaceCount):
    '''
    Accepts a webpage URL and the number of faces detected on the page.
    Appends both to an existing table for the website.
    Returns nothing.
    '''
    # Connect to PostgresSQL database and prepare to enter data
    conn = psycopg2.connect(host='postgres', database='faceCrawler', user='postgres', password='postgres')
    cur = conn.cursor()
    tableName = ((urlparse(pageURL).hostname).replace('.', '')).replace('www', '')

    # Append data to the database
    cur.execute(
        sql.SQL("INSERT INTO {} VALUES (%s, %s)")
        .format(sql.Identifier(tableName)),
        [pageURL, pageFaceCount])

    # Append changes to database and close connections
    conn.commit()
    cur.close()
    conn.close()


@app.task
def processImage(pageURL, imagePath):
    '''
    Accepts a webpage URL and a path to a locally stored screenshot of the page.
    Counts how many faces are on the webpage and modifies the image by drawing
        boxes around each face.
    Deletes any images without faces.
    Appends the page URL and face count to an existing database.
    '''
    pageFaceCount, pageFaceLocations = countFaces(imagePath)
    if pageFaceCount > 0:
        highlightFaces(imagePath, pageFaceLocations)
    else:
        os.remove(imagePath)

    appendToDatabase(pageURL, pageFaceCount)

    return pageFaceCount
