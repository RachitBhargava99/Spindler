import os


class Config:
    SECRET_KEY = '0917b13a9091915d54b6336f45909539cce452b3661b21f386418a257883b30a'
    ENDPOINT_ROUTE = ''
    CURRENT_URL = 'https://thinger.appspot.com/'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'rachitbhargava99@gmail.com'
    MAIL_PASSWORD = 'Ananya88#'
    MAPS_API_KEY = 'AIzaSyAs5sA8X7MR-vbuNNxfJ4a-xSiUeOLtg-U'
    PROJECT_ID = 'thinger'
    DATA_BACKEND = 'cloudsql'
    CLOUDSQL_USER = 'root'
    CLOUDSQL_PASSWORD = ''
    CLOUDSQL_DATABASE = 'thinger_sql'
    CLOUDSQL_CONNECTION_NAME = 'thinger:us-east1:thinger'
    SQLALCHEMY_DATABASE_URI = (
        'mysql+pymysql://{user}:{password}@localhost/{database}?unix_socket=/cloudsql/{connection_name}').format(
        user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD, database=CLOUDSQL_DATABASE,
        connection_name=CLOUDSQL_CONNECTION_NAME)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_URL = 'https://images-api.nasa.gov/'
    SEARCH_URL = 'search'
