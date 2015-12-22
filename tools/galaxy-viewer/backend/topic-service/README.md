# Galaxy Viewer service API
This is the backend web service exposing an API used by the GalaxyViewer front end application.
The web service retrieves the data from a 'linked' MongoDB database.

## Available API calls
**Note:** All the API calls below support [JSONP](https://en.wikipedia.org/wiki/JSONP) via a `callback=...` query string
(useful for clients not supporting [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing)).
CORS support is already enabled, and currently allows requests from anywhere (but see *Security Note* below).


* **`GET /datasets`**
  * Retrieves metadata about each dataset available in the linked MongoDB database
  * Example response:
  ```
  {"datasets": [{"name": "My Dataset", "id": "567820331ea2a76ed9bcecea"}]}
  ```
* **`GET /datasets/<dataset_id>/topics/data?content=...`**
  * Convenience method for retrieving a number of attributes in 'bulk'
  * `content` contains a comma-separated list of attributes
  * possible attributes: `mean`, `trend`, `alpha`, `first_word`, `topic_dist`, `center_dist`
* **`GET /datasets/<dataset_id>/topics/topic_distances`**
  * Retrieves inter-topic distances as an upper-triangular matrix encoded as a one-dimensional vector
  * use the function below to index into this vector to retrieve the distance between two topics x and y:
  ```
  def get_distance(num_topics, distances, topic_x, topic_y):
    """Indexing method into the upper-triangular matrix representing inter-topic distances

    :param num_topics: The number of topics
    :param distances: The upper-triangular matrix representing inter-topic distances
    :param topic_x: The id of the first topic
    :param topic_y: The id of the second topic
    :return: The distance between topic_x and topic_y
    """
    if topic_x == topic_y:
        return 0

    x = min(topic_x, topic_y)
    y = max(topic_x, topic_y)
    n = num_topics

    i = int((2 * x * n - x ** 2 + 2 * y - 3 * x - 2) / 2)

    return distances[i]
  ```
  * Example response:
  ```
  {"topic_dist": [349.0352144900994, 365.89325695660506, 364.42617903787686, ...]}
  ```
* **`GET /datasets/<dataset_id>/topics/center_distances`**
  * Retrieves the distances of the topics from 'center'
  * Example response:
  ```
  {"center_dist": [272.2338703886017, 213.55525467547483, 253.43233558120545, ...]}
  ```
* **`GET /datasets/<dataset_id>/token_counts_by_year`**
  * Retrieves the token counts by year at the corpus level
  * Example response (note that `-1` is a placeholder for documents with missing `year` metadata.):
  ```
  {"-1": 6464, "1800": 3452, "1812": 7668, "1820": 937, "1821": 5415, ...}
  ```
* **`GET /datasets/<dataset_id>/doc_counts_by_year`**
  * Retrieves the corpus-level document counts by year
  * Example response:
  ```
  {"-1": 3, "1800": 2, "1812": 1, "1820": 1, "1821": 1, "1822": 1, "1834": 1, ...}
  ```
* **`GET /datasets/<dataset_id>/topics/<topic_id>/token_counts`**
  * Retrieves the token counts for the top words for the given topic_id, maintaining the order of the top words.
  * Example response:
  ```
  {"token_counts": [["earth", 608], ["find", 503], ["past", 467], ["voice", 440], ...]}
  ```
* **`GET /datasets/<dataset_id>/topics/<topic_id>/doc_prominence[?limit=N]`**
  * Retrieves the rank-ordered list of documents based on their prominence in the given topic,
    optionally limiting the number of results returned
  * Example response:
  ```
  {"doc_prominence": [
     {"prominence": 0.1335640480651474, "source": "/data/mdp.39015039688257.txt",
      "publishDate": "1875-01-01T00:00:00", "volid": "mdp.39015039688257", "author": "[Richmond, Cora Linn Victoria
      Scott], 1840-1923.", "title": "Discourses through the mediumship of Mrs. Cora L. V. Tappan. The new science.
      Spiritual ethics."},
     {"prominence": 0.09917932600751334, "source": "/data/mdp.39015063544186.txt", "publishDate": "1889-01-01T00:00:00",
      "volid": "mdp.39015063544186", "author": "Street, J. C.", "title": "The hidden way across the threshold; or,
      The mystery which hath been hidden for ages and from generations. An explanation of the concealed forces in
      every man to open the temple of the soul and to learn the guidance of the unseen hand. Illustrated and made
      plain with as few occult phrases as possible, by J. C. Street."},
     ...
  ]}
  ```
* **`GET /datasets/<dataset_id>/topics/<topic_id>/token_counts_by_year`**
  * Retrieves the topic-level token counts by year for the given topic_id
  * Example response:
  ```
  {"1896": {"find": 2, "eye": 2, "thoughts": 1, "air": 1},
   "1870": {"hand": 2, "sun": 6, "air": 2, "dead": 4, "eyes": 1, "universe": 2, "ages": 3, "find": 8, "white": 1,
            "past": 2, "feet": 1, "dark": 1},
   ...}
  ```

# Running the service
The service is using the default BottlePy web server which is not meant to be used in production.
For deployment options, and switching to a different server backend, please see the
[BottlePy deployment documentation](http://bottlepy.org/docs/dev/deployment.html).

**Security note:** The code is currently running in development mode, and as such the CORS permissions are set to allow
cross-origin API requests from anywhere. In production it is *highly advised* to restrict access to only the specific
hosts from where the requests are expected to come from. This can be done by customizing the response headers defined
in `topic-service.py` in the `EnableCors` plugin class.

To start the Galaxy Viewer web service:
```
usage: topic-service.py [-h] [--host host] [--port port] [--db-host host]
                        [--db name] [--debug]

Galaxy Viewer topic service API backend

optional arguments:
  -h, --help      show this help message and exit
  --host host     Hostname or IP address for the service to bind to (default:
                  localhost)
  --port port     Port number to listen on (default: 8080)
  --db-host host  The hostname or IP address of the MongoDB server to connect
                  to (default: localhost)
  --db name       The name of the database containing the GalaxyViewer data
                  (default: galaxyviewer)
  --debug         Enable debug mode (default: False)
```