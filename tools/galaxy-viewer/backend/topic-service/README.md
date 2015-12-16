# Galaxy Viewer service API
This is the backend web service exposing an API used by the GalaxyViewer front end application.
The web service retrieves the data from a 'linked' MongoDB database.

## Available API calls
* `GET /datasets`
  * Retrieves metadata about each dataset available in the linked MongoDB database
* `GET /datasets/<dataset_id>/topics/data?content=...`
  * Convenience method for retrieving a number of attributes in 'bulk'
  * `content` contains a comma-separated list of attributes
  * possible attributes: `mean`, `trend`, `alpha`, `first_word`, `topic_dist`, `center_dist`
* `GET /datasets/<dataset_id>/topics/topic_distances`
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
* `GET /datasets/<dataset_id>/topics/center_distances`
  * Retrieves the distances of the topics from 'center'
* `GET /datasets/<dataset_id>/token_counts_by_year`
  * Retrieves the token counts by year at the corpus level
* `GET /datasets/<dataset_id>/doc_counts_by_year`
  * Retrieves the corpus-level document counts by year
* `GET /datasets/<dataset_id>/topics/<topic_id>/token_counts`
  * Retrieves the token counts for the given topic_id
* `GET /datasets/<dataset_id>/topics/<topic_id>/doc_prominence`
  * Retrieves the topic-level document prominence for a given topic_id
* `GET /datasets/<dataset_id>/topics/<topic_id>/token_counts_by_year`
  * Retrieves the topic-level token counts by year for the given topic_id

# Running the service
The service is using the default BottlePy web server which is not meant to be used in production.
For deployment options, and switching to a different server backend, please see the
[BottlePy deployment documentation](http://bottlepy.org/docs/dev/deployment.html).

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