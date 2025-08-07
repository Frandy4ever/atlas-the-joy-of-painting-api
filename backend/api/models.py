from flask_sqlalchemy import SQLAlchemy

# Define a single, unbound SQLAlchemy instance
db = SQLAlchemy()

# Junction tables for many-to-many relationships
episode_colors = db.Table(
    'episode_colors',
    db.Column('episode_id', db.Integer, db.ForeignKey('episodes.id'), primary_key=True),
    db.Column('color_id', db.Integer, db.ForeignKey('colors.id'), primary_key=True),
)

episode_subjects = db.Table(
    'episode_subjects',
    db.Column('episode_id', db.Integer, db.ForeignKey('episodes.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True),
)

class Episode(db.Model):
    __tablename__ = 'episodes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    season = db.Column(db.Integer, nullable=False)
    episode = db.Column(db.Integer, nullable=False)
    air_date = db.Column(db.Date)
    youtube_src = db.Column(db.String(255))
    img_src = db.Column(db.String(255))
    num_colors = db.Column(db.Integer)
    extra_info = db.Column(db.JSON)

    colors = db.relationship(
        'Color',
        secondary=episode_colors,
        lazy='subquery',
        backref=db.backref('episodes', lazy=True),
    )
    subjects = db.relationship(
        'Subject',
        secondary=episode_subjects,
        lazy='subquery',
        backref=db.backref('episodes', lazy=True),
    )

class Color(db.Model):
    __tablename__ = 'colors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    hex = db.Column(db.String(7), unique=True, nullable=False)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
