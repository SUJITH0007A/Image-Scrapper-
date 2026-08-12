from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS,cross_origin
import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen as uReq
import logging
import pymongo
logging.basicConfig(filename="scrapper.log" , level=logging.INFO)
import os

app = Flask(__name__) # initialising the flask app with the name 'app'  

@app.route("/", methods = ['GET'])
def homepage():
    return render_template("index.html")

@app.route("/review" , methods = ['POST' , 'GET'])
def index():
    if request.method == 'POST':
                try:

                    # query to search for images
                    query = request.form['content'].replace(" ","")

                            # directory to store downloaded images
                    save_directory = "images/"

                            # create the directory if it doesn't exist
                    if not os.path.exists(save_directory):
                        os.makedirs(save_directory)



                            # fake user agent to avoid getting blocked
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}

                    # fetch the search results page from Bing Images (Google now blocks non-JS clients)
                    response = requests.get(f"https://www.bing.com/images/search?q={query}", headers=headers)

                    # parse the HTML using BeautifulSoup
                    soup = BeautifulSoup(response.content, "html.parser")

                    # find all img tags
                    image_tags = soup.find_all("img")

                    # download each image and save it to the specified directory
                    img_data = []
                    valid_count = 0
                    for index, image_tag in enumerate(image_tags):
                        image_url = image_tag.get('src') or image_tag.get('data-src')
                        
                        # Filter out empty URLs, SVGs, or internal tracking pixels
                        if not image_url or not image_url.startswith("http") or image_url.endswith(".svg") or "r.bing.com" in image_url:
                            continue
                            
                        try:
                            # send a request to the image URL and save the image
                            image_data = requests.get(image_url, timeout=5).content
                            mydict = {"Index": valid_count, "Image": image_data}
                            img_data.append(mydict)
                            
                            with open(os.path.join(save_directory, f"{query}_{valid_count}.jpg"), "wb") as f:
                                f.write(image_data)   
                            
                            valid_count += 1
                            if valid_count >= 20: # limit to top 20 images
                                break
                        except Exception as img_err:
                            logging.info(f"Skipped downloading image: {img_err}")
                    # Retrieve the MongoDB URI from environment variables or fallback to default
                    mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority")
                    
                    if mongo_uri and "<password>" not in mongo_uri:
                        try:
                            client = pymongo.MongoClient(mongo_uri)
                            db = client['image_scrap']
                            review_col = db['image_scrap_data']
                            review_col.insert_many(img_data)
                            logging.info("Successfully inserted image binary data to MongoDB.")
                        except Exception as db_err:
                            logging.error(f"MongoDB connection/insertion failed: {db_err}")
                    else:
                        logging.warning("MongoDB URI not configured or contains default '<password>' placeholder. Skipping database insertion.")

                    image_files = [f"{query}_{i}.jpg" for i in range(valid_count)]
                    return render_template("result.html", query=query, images=image_files)
                except Exception as e:
                    logging.info(e)
                    return 'Something is wrong, please try again!'

    else:
        return render_template('index.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('images', filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
