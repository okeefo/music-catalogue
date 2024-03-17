import os
import sqlite3
import configparser


def setup_database():
    # Define the default DB location and name
    default_db_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db')
    # Read the config.ini file
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Check if the [db] section and location field exist, if not, create them
    if 'db' not in config.sections():
        config.add_section('db')

    if 'location' not in config['db']:
        default_db_name = 'music-catalog-v1'

        config['db']['location'] = os.path.join(default_db_location, default_db_name)

    # Save the changes to the config.ini file
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

    # Connect to the SQLite database
    conn = sqlite3.connect(config['db']['location'])
    c = conn.cursor()

    # Check if the release and tracks tables exist, if not, create them
    c.execute('''
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
    ''')

    c.execute('''
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
    ''')

    # Connect to the SQLite database
    conn = sqlite3.connect(config['db']['location'])
    c = conn.cursor()

    # Create the media_types table
    c.execute('''
        CREATE TABLE IF NOT EXISTS media_types
        (
            id INTEGER PRIMARY KEY,
            format TEXT UNIQUE
        )
    ''')

    # Populate the media_types table
    c.execute("INSERT OR IGNORE INTO media_types (format) VALUES ('WAV')")
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


if __name__ == "__main__":
    confirm = input("Are you sure you want to setup the database? (yes/no): ")
    if confirm.lower() == "yes":
        setup_database()
    else:
        print("Database setup cancelled.")
