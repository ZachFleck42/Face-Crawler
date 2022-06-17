import face_recognition
import psycopg2
from celery_app import app
from PIL import Image, ImageDraw
from psycopg2 import sql
from urllib.parse import urlparse


def countFaces(path):
    '''
    Accepts a path to an image.
    Returns how many faces were found in the image and their locations.
    '''
    print(f"Analyzing image: {path}")
    image = face_recognition.load_image_file(path)
    faceLocations = face_recognition.face_locations(image)
    faceCount = len(faceLocations)

    return faceCount, faceLocations


def highlightFaces(path, faceLocations):
    '''
    Aceepts a path to an image and the locations of all the faces in the image.
    Uses PIL module to draw boxes around all faces.
    Returns nothing.
    '''
    pilImage = Image.open(path)
    for faceLocation in faceLocations:
        top, right, bottom, left = faceLocation
        shape = [(left, top), (right, bottom)]
        img1 = ImageDraw.Draw(pilImage)

        img1.rectangle(shape, outline="red", width=4)

    pilImage.save(path)


def appendToDb(pageURL, pageFaceCount):
    # Connect to PostgresSQL database and prepare to enter data
    conn = psycopg2.connect(host='postgres', database='faceCrawler', user='postgres', password='postgres')
    tableName = (urlparse(pageURL).hostname).replace('.', '')
    cur = conn.cursor()

    print(f"{pageURL} received by appendToDb and connection established (?)")
    # Append data to the database
    cur.execute(
        sql.SQL("INSERT INTO {} VALUES (%s, %s)")
        .format(sql.Identifier(tableName)),
        [pageURL, pageFaceCount])

    # Append changes to database and close connections
    conn.commit()
    cur.close()
    conn.close()
    print("Allegedly, a change was made to the database...")


@app.task
def processImage(pageURL, imagePath):
    print(f"tasks.py activated for {pageURL}")
    pageFaceCount, pageFaceLocations = countFaces(imagePath)
    print(f"Fouond {pageFaceCount} faces on {pageURL}")
    if pageFaceCount:
        highlightFaces(imagePath, pageFaceLocations)

    print(f"Sending {pageURL} to appdendToDb...")
    appendToDb(pageURL, pageFaceCount)
