CREATE TABLE Episodes (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  season INTEGER NOT NULL,
  episode_number INTEGER NOT NULL,
  air_date DATE,
  youtube_url VARCHAR(255),
  image_url VARCHAR(255)
);

CREATE TABLE Colors (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  hex_code VARCHAR(7)
);

CREATE TABLE Subjects (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL
);

-- Junction table for Episodes and Colors (many-to-many)
CREATE TABLE EpisodeColors (
  episode_id INTEGER REFERENCE Episodes(id) ON DELETE CASCADE,
  color_id INTEGER REFERENCE Colors(id) ON DELETE CASCADE,
  PRIMARY KEY (episode_id, color_id)
)

-- Junction table for Episodes and Subjects (many-to-many)
CREATE TABLE EpisodeSubjects (
  episode_id INTEGER REFERENCE Episodes(id) ON DELETE CASCADE,
  Subject_id INTEGER REFERENCE Subjects(id) ON DELETE CASCADE,
  PRIMARY KEY (episode_id, Subject_id)
);