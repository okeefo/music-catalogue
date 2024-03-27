import os
import sqlite3
import configparser
from src.log_config import get_logger

logger = get_logger(__name__)


def setup_database():
    logger.info("Setting up the database: reading config.ini file and creating tables if they do not exist.")
    # Read the config.ini file
    config = configparser.ConfigParser()
    config.read('config.ini')
    config_updated = False
    # Check if the [db] section and location field exist, if not, create them
    if 'db' not in config.sections():
        logger.info("db section not found in config.ini file, creating it.")
        config.add_section('db')
        config_updated = True

    if 'name' not in config['db']:
        logger.info("name field not found in db section of config.ini file, creating it.")
        default_db_name = 'music-catalog-v1'
        config['db']['name'] = default_db_name
        config_updated = True

    if 'location' not in config['db']:
        logger.info("location field not found in db section of config.ini file, creating it.")
        default_db_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db')
        config['db']['location'] = default_db_location
        config_updated = True

    if config_updated:
        # Save the changes to the config.ini file
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

    db_location = os.path.join(config['db']['location'],config['db']['name'])
    logger.info(f"Connecting to database: {db_location}")
    conn = sqlite3.connect(db_location)
    c = __create_db_tables(
        conn,
        '''
        CREATE TABLE IF NOT EXISTS release
        (
            release_id INTEGER PRIMARY KEY,
            name TEXT,
            artist TEXT,
            label TEXT,
            catalogue_number TEXT,
            media TEXT,
            style TEXT,
            genre TEXT,
            date TEXT,
            country TEXT,
            url TEXT
        )
    ''',
        '''
        CREATE TABLE IF NOT EXISTS tracks
        (
            release_id INTEGER,
            track_number INTEGER,
            name TEXT,
            artist TEXT,
            side TEXT,
            duration INTEGER,
            FOREIGN KEY(release_id) REFERENCES release(release_id),
            PRIMARY KEY(release_id, track_number)
        )
    ''',
    )
    # Connect to the SQLite database
    conn = sqlite3.connect(config['db']['location'])
    c = __create_db_tables(
        conn,
        '''
        CREATE TABLE IF NOT EXISTS media_types
        (
            id INTEGER PRIMARY KEY,
            format TEXT UNIQUE
        )
    ''',
        "INSERT OR IGNORE INTO media_types (format) VALUES ('WAV')",
    )
    c.execute("INSERT OR IGNORE INTO media_types (format) VALUES ('MP3')")
    c.execute("INSERT OR IGNORE INTO media_types (format) VALUES ('VINYL')")

    c.execute('''
        CREATE TABLE IF NOT EXISTS Media
        (
            id INTEGER PRIMARY KEY,
            format INTEGER,
            location TEXT,
            release_id INTEGER,
            track_number INTEGER,
            FOREIGN KEY(format) REFERENCES media_types(id),
            FOREIGN KEY(release_id) REFERENCES release(release_id)
        )
    ''')

    # Commit the changes
    conn.commit()
    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def __create_db_tables(conn, arg1, arg2):
    result = conn.cursor()

    # Check if the release and tracks tables exist, if not, create them
    result.execute(arg1)

    result.execute(arg2)

    return result


if __name__ == "__main__":
    confirm = input("Are you sure you want to setup the database? (yes/no): ")
    if confirm.lower() == "yes":
        setup_database()
    else:
        print("Database setup cancelled.")
