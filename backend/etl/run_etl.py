# backend/etl/run_etl.py
import pandas as pd
import re
import ast
from datetime import datetime
import json
import mysql.connector
from mysql.connector import errorcode
import os
import time

from dotenv import load_dotenv

# Load env
load_dotenv()

# --- Database Connection Configuration ---
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', 3307))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root_password')
DB_NAME = os.getenv('DB_NAME', 'atlas_the_joy_of_painting_db')

def get_db_connection(database=DB_NAME):
    try:
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=database
        )
        return cnx
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def wait_for_db(retries=10, delay=5):
    """
    Waits for the MySQL database to be ready by attempting to connect.
    """
    print(f"Waiting for MySQL database to become available...")
    for i in range(retries):
        try:
            cnx = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD
            )
            print("Database is available!")
            cnx.close()
            return True
        except mysql.connector.Error as err:
            print(f"Attempt {i+1}/{retries}: Connection failed. Retrying in {delay} seconds...")
            time.sleep(delay)
    print("❌ Failed to connect to the database after multiple retries.")
    return False

def create_database_schema():
    """
    Connects to MySQL and executes the SQL script to create the database and tables.
    """
    print("...Checking for database schema...")
    if not wait_for_db():
        return False

    try:
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = cnx.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
        return False

    try:
        cnx = get_db_connection()
        if not cnx:
            return False
        cursor = cnx.cursor()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_script_path = os.path.join(script_dir, '..', 'db', 'init.sql')

        with open(sql_script_path, 'r') as f:
            sql_commands = f.read()
        
        commands = [cmd for cmd in sql_commands.split(';') if cmd.strip()]
        for command in commands:
            cursor.execute(command)
        
        cnx.commit()
        cursor.close()
        cnx.close()
        print("...Database schema created successfully.")
        return True
    except mysql.connector.Error as err:
        print(f"Error executing SQL script: {err}")
        return False

def parse_date(date_str):
    """
    Parses a date string from the format like 'January 11, 1983'
    and handles extra text after the date.
    """
    date_part = date_str.split(')')[0]
    formats = [
        "%B %d, %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_part, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    print(f"⚠️ Could not parse date: {date_str}")
    return None

def get_episode_data(file_path):
    """
    Extracts and cleans episode titles and dates from the raw text file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()
    
    episodes = []
    pattern = re.compile(r'^\"(?P<title>.+?)\"\s+\((?P<date>.+?)\)(?:\s+-\s+(?P<notes>.+))?$')
    
    for line in raw_lines:
        match = pattern.match(line.strip())
        if match:
            date_str = match.group("date")
            if date_str.endswith(')'):
                date_str = date_str[:-1]

            episodes.append({
                "title": match.group("title"),
                "air_date": parse_date(date_str),
                "notes": match.group("notes") or ""
            })
    return episodes

def get_color_data(file_path):
    """
    Extracts and cleans color information.
    """
    colors_df = pd.read_csv(file_path, quotechar='"', skipinitialspace=True)
    return colors_df

def get_subject_data(file_path):
    """
    Extracts and cleans subject matter information.
    """
    subject_df = pd.read_csv(file_path, quotechar='"', skipinitialspace=True)
    subject_df["TITLE"] = subject_df["TITLE"].str.replace('"', '', regex=False).str.strip()
    return subject_df

def run_etl():
    """
    Main ETL function to orchestrate the process.
    """
    print("🚀 Starting ETL process...")

    if not create_database_schema():
        return

    print("...Extracting data from files...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(script_dir, '..', 'data', 'raw_data')
    clean_data_dir = os.path.join(script_dir, '..', 'data', 'clean_data')
    
    os.makedirs(clean_data_dir, exist_ok=True)
    
    episode_dates_path = os.path.join(raw_data_dir, "The Joy Of Painting - Episode Dates")
    colors_used_path = os.path.join(raw_data_dir, "The Joy Of Painiting - Colors Used")
    subject_matter_path = os.path.join(raw_data_dir, "The Joy Of Painiting - Subject Matter")

    episode_dates = get_episode_data(episode_dates_path)
    colors_df = get_color_data(colors_used_path)
    subject_df = get_subject_data(subject_matter_path)

    for i, ep in enumerate(episode_dates, 1):
        ep['season'] = (i - 1) // 13 + 1
        ep['episode'] = (i - 1) % 13 + 1

    print("...Transforming and sanitizing data...")
    all_colors = {}
    all_subjects = {}
    
    special_episodes = {
        58: {"guest": "Steve Ross", "relationship": "son"},
        61: {"guest": "Steve Ross", "relationship": "son"},
        201: {"guest": "Steve Ross", "relationship": "son"},
        205: {"guest": "Steve Ross", "relationship": "son"},
        370: {"guest": "Steve Ross", "relationship": "son"},
        386: {"guest": "Steve Ross", "relationship": "son"},
        206: {"special": "Two-part episode"},
        352: {"special": "Christmas special"},
        401: {"special": "Memorial episode"}
    }

    processed_episodes = []
    episode_colors_set = set()
    episode_subjects_set = set()

    for i, row in colors_df.iterrows():
        episode_number = i + 1
        season = row['season']
        episode_in_season = row['episode']
        
        episode_info = next((ep for ep in episode_dates if ep['season'] == season and ep['episode'] == episode_in_season), None)

        if not episode_info:
            print(f"⚠️ Could not find episode {season}-{episode_in_season} in dates list. Skipping.")
            continue

        extra_info = special_episodes.get(episode_number, None)
        episode_record = {
            'id': episode_number,
            'title': episode_info['title'],
            'season': season,
            'episode': episode_in_season,
            'air_date': episode_info['air_date'],
            'youtube_src': row['youtube_src'],
            'img_src': row['img_src'],
            'num_colors': row['num_colors'],
            'extra_info': json.dumps(extra_info) if extra_info else None
        }
        processed_episodes.append(episode_record)

        color_names = ast.literal_eval(row['colors'])
        color_hexes = ast.literal_eval(row['color_hex'])
        for name, hex_code in zip(color_names, color_hexes):
            name = name.strip()
            hex_code = hex_code.strip()
            if hex_code not in all_colors:
                all_colors[hex_code] = {'id': len(all_colors) + 1, 'name': name, 'hex': hex_code}
            
            episode_colors_set.add((episode_number, all_colors[hex_code]['id']))

        subject_row = subject_df[(subject_df['EPISODE'].str.contains(f"S{season:02d}E{episode_in_season:02d}")) | (subject_df['TITLE'] == episode_info['title'])].iloc[0]
        for subject_name, value in subject_row.iloc[2:].items():
            if value == 1:
                subject_name = subject_name.strip().replace('_', ' ').title()
                if subject_name not in all_subjects:
                    all_subjects[subject_name] = {'id': len(all_subjects) + 1}
                
                episode_subjects_set.add((episode_number, all_subjects[subject_name]['id']))

    episode_colors_map = list(episode_colors_set)
    episode_subjects_map = list(episode_subjects_set)

    pd.DataFrame(processed_episodes).to_csv(os.path.join(clean_data_dir, "episodes.csv"), index=False)
    pd.DataFrame(all_colors.values()).to_csv(os.path.join(clean_data_dir, "colors.csv"), index=False)
    pd.DataFrame(all_subjects.values()).to_csv(os.path.join(clean_data_dir, "subjects.csv"), index=False)
    pd.DataFrame(episode_colors_map, columns=['episode_id', 'color_id']).to_csv(os.path.join(clean_data_dir, "episode_colors.csv"), index=False)
    pd.DataFrame(episode_subjects_map, columns=['episode_id', 'subject_id']).to_csv(os.path.join(clean_data_dir, "episode_subjects.csv"), index=False)
    print("Cleaned data saved to 'backend/data/clean_data' directory.")

    # --- 3. LOAD ---
    print("...Loading data into MySQL database...")
    cnx = get_db_connection()
    if not cnx:
        return
    cursor = cnx.cursor()

    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE episode_colors;")
        cursor.execute("TRUNCATE TABLE episode_subjects;")
        cursor.execute("TRUNCATE TABLE episodes;")
        cursor.execute("TRUNCATE TABLE colors;")
        cursor.execute("TRUNCATE TABLE subjects;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        cnx.commit()
        print("Existing data truncated.")

        insert_color_query = "INSERT INTO colors (id, name, hex) VALUES (%s, %s, %s)"
        color_list = [(data['id'], data['name'], data['hex']) for data in all_colors.values()]
        cursor.executemany(insert_color_query, color_list)
        cnx.commit()

        insert_subject_query = "INSERT INTO subjects (id, name) VALUES (%s, %s)"
        subject_list = [(data['id'], name) for name, data in all_subjects.items()]
        cursor.executemany(insert_subject_query, subject_list)
        cnx.commit()

        insert_episode_query = """
            INSERT INTO episodes (id, title, season, episode, air_date, youtube_src, img_src, num_colors, extra_info)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        episode_list = [
            (ep['id'], ep['title'], ep['season'], ep['episode'], ep['air_date'],
             ep['youtube_src'], ep['img_src'], ep['num_colors'], ep['extra_info'])
            for ep in processed_episodes
        ]
        cursor.executemany(insert_episode_query, episode_list)
        cnx.commit()

        insert_ep_color_query = "INSERT INTO episode_colors (episode_id, color_id) VALUES (%s, %s)"
        cursor.executemany(insert_ep_color_query, episode_colors_map)
        cnx.commit()

        insert_ep_subject_query = "INSERT INTO episode_subjects (episode_id, subject_id) VALUES (%s, %s)"
        cursor.executemany(insert_ep_subject_query, episode_subjects_map)
        cnx.commit()

        print("✅ ETL process completed successfully!")

    except mysql.connector.Error as err:
        print(f"Error during data loading: {err}")
        cnx.rollback()
    finally:
        cursor.close()
        cnx.close()

if __name__ == "__main__":
    run_etl()