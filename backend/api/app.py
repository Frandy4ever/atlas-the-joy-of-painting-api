# Libraries and Dependencies
import os
import json
from datetime import date, datetime, timedelta
import jwt
from functools import wraps
import graphene
from graphql_server.flask import GraphQLView
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import text

# Load env
load_dotenv()

# Init Flask app and extensions
app = Flask(__name__)
CORS(app)
api = Api(app)

# JWT Secret
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'your_jwt_secret_key')

# JWT Auth helper
def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise Exception("Authorization header missing or malformed")

    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return {
            "username": decoded["user"],
            "role": decoded.get("role", "viewer")
        }
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

# Models
from models import db, Episode, Color, Subject

# DB config
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Bind the unbound db instance to the app
db.init_app(app)

# Helper: convert a model instance to a plain dictionary
def to_dict(model):
    result = {}
    for c in model.__table__.columns:
        value = getattr(model, c.name)
        # Convert date/datetime objects to ISO strings so jsonify can handle them
        if isinstance(value, (date, datetime)):
            result[c.name] = value.isoformat()
        else:
            result[c.name] = value
    return result

# ===== JWT Authentication =====

def token_required(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', None)
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    """
    A simple login endpoint that issues JWTs.
    Accepts JSON with 'username' and 'password'.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # Replace this with your own user lookup / password check
    if username != 'admin' or password != 'password':
        return jsonify({'message': 'Bad credentials'}), 401
    token = jwt.encode(
        {
            'user': username,
            'role': 'admin',
            'exp': datetime.utcnow() + timedelta(minutes=30)
        },
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return jsonify({'token': token})

# ===== RESTful resources =====

class EpisodeListResource(Resource):
    @token_required
    def get(self):
        query = Episode.query
        # Optional query parameters (for filtering)
        color_id = request.args.get('color_id', type=int)
        subject_id = request.args.get('subject_id', type=int)
        season = request.args.get('season', type=int)
        episode_num = request.args.get('episode', type=int)
        title_like = request.args.get('title', type=str)

        # Apply filters
        if color_id:
            query = query.join(Episode.colors).filter(Color.id == color_id)
        if subject_id:
            query = query.join(Episode.subjects).filter(Subject.id == subject_id)
        if season:
            query = query.filter(Episode.season == season)
        if episode_num:
            query = query.filter(Episode.episode == episode_num)
        if title_like:
            query = query.filter(Episode.title.ilike(f"%{title_like}%"))

        episodes = query.all()
        result = []
        for ep in episodes:
            ep_dict = to_dict(ep)
            ep_dict['colors'] = [to_dict(c) for c in ep.colors]
            ep_dict['subjects'] = [to_dict(s) for s in ep.subjects]
            result.append(ep_dict)
        return result, 200

    @token_required
    def post(self):
        data = request.get_json()
        episode = Episode(**data)
        db.session.add(episode)
        db.session.commit()
        return to_dict(episode), 201

class EpisodeResource(Resource):
    @token_required
    def get(self, episode_id):
        ep = Episode.query.get_or_404(episode_id)
        return to_dict(ep), 200

    @token_required
    def put(self, episode_id):
        ep = Episode.query.get_or_404(episode_id)
        data = request.get_json()
        for key, value in data.items():
            if key == 'air_date' and value:
                setattr(ep, 'air_date', date.fromisoformat(value))
            elif hasattr(ep, key) and value is not None:
                setattr(ep, key, value)
        db.session.commit()
        return to_dict(ep), 200

    @token_required
    def delete(self, episode_id):
        ep = Episode.query.get_or_404(episode_id)
        db.session.delete(ep)
        db.session.commit()
        return '', 204

class ColorListResource(Resource):
    @token_required
    def get(self):
        colors = Color.query.all()
        return [to_dict(c) for c in colors], 200

    @token_required
    def post(self):
        data = request.get_json()
        color = Color(**data)
        db.session.add(color)
        db.session.commit()
        return to_dict(color), 201

class ColorResource(Resource):
    @token_required
    def get(self, color_id):
        color = Color.query.get_or_404(color_id)
        color_dict = to_dict(color)
        color_dict['episodes'] = [to_dict(ep) for ep in color.episodes]
        return color_dict, 200

    @token_required
    def put(self, color_id):
        color = Color.query.get_or_404(color_id)
        data = request.get_json()
        if 'name' in data:
            color.name = data['name']
        if 'hex' in data:
            color.hex = data['hex']
        db.session.commit()
        return to_dict(color), 200

    @token_required
    def delete(self, color_id):
        color = Color.query.get_or_404(color_id)
        db.session.delete(color)
        db.session.commit()
        return '', 204

class SubjectListResource(Resource):
    @token_required
    def get(self):
        subjects = Subject.query.all()
        return [to_dict(s) for s in subjects], 200

    @token_required
    def post(self):
        data = request.get_json()
        subject = Subject(**data)
        db.session.add(subject)
        db.session.commit()
        return to_dict(subject), 201

class SubjectResource(Resource):
    @token_required
    def get(self, subject_id):
        subject = Subject.query.get_or_404(subject_id)
        subject_dict = to_dict(subject)
        subject_dict['episodes'] = [to_dict(ep) for ep in subject.episodes]
        return subject_dict, 200

    @token_required
    def put(self, subject_id):
        subject = Subject.query.get_or_404(subject_id)
        data = request.get_json()
        if 'name' in data:
            subject.name = data['name']
        db.session.commit()
        return to_dict(subject), 200

    @token_required
    def delete(self, subject_id):
        subject = Subject.query.get_or_404(subject_id)
        db.session.delete(subject)
        db.session.commit()
        return '', 204

# Register REST endpoints
api.add_resource(EpisodeListResource, '/api/episodes')
api.add_resource(EpisodeResource, '/api/episodes/<int:episode_id>')
api.add_resource(ColorListResource, '/api/colors')
api.add_resource(ColorResource, '/api/colors/<int:color_id>')
api.add_resource(SubjectListResource, '/api/subjects')
api.add_resource(SubjectResource, '/api/subjects/<int:subject_id>')

# ===== GraphQL Types =====

class ColorType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    hex = graphene.String()

class SubjectType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()

class EpisodeType(graphene.ObjectType):
    id = graphene.Int()
    title = graphene.String()
    season = graphene.Int()
    episode = graphene.Int()
    air_date = graphene.String()
    youtube_src = graphene.String()
    img_src = graphene.String()
    num_colors = graphene.Int()
    extra_info = graphene.JSONString()
    colors = graphene.List(lambda: ColorType)
    subjects = graphene.List(lambda: SubjectType)

    def resolve_colors(self, info):
        return self.colors

    def resolve_subjects(self, info):
        return self.subjects

# ===== GraphQL Query (pagination & filtering) =====

class Query(graphene.ObjectType):
    all_episodes = graphene.List(
        EpisodeType,
        color_id=graphene.Int(),
        subject_id=graphene.Int(),
        season=graphene.Int(),
        episode_num=graphene.Int(),
        title=graphene.String(),
        limit=graphene.Int(),
        offset=graphene.Int()
    )
    episode = graphene.Field(EpisodeType, id=graphene.Int(required=True))
    all_colors = graphene.List(ColorType)
    color = graphene.Field(ColorType, id=graphene.Int(required=True))
    all_subjects = graphene.List(SubjectType)
    subject = graphene.Field(SubjectType, id=graphene.Int(required=True))

    def resolve_all_episodes(self, info, color_id=None, subject_id=None,
                             season=None, episode_num=None, title=None,
                             limit=None, offset=None):
        query = Episode.query
        if color_id:
            query = query.join(Episode.colors).filter(Color.id == color_id)
        if subject_id:
            query = query.join(Episode.subjects).filter(Subject.id == subject_id)
        if season:
            query = query.filter(Episode.season == season)
        if episode_num:
            query = query.filter(Episode.episode == episode_num)
        if title:
            query = query.filter(Episode.title.ilike(f"%{title}%"))
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.all()

    def resolve_episode(self, info, id):
        return Episode.query.get(id)

    def resolve_all_colors(self, info):
        return Color.query.all()

    def resolve_color(self, info, id):
        return Color.query.get(id)

    def resolve_all_subjects(self, info):
        return Subject.query.all()

    def resolve_subject(self, info, id):
        return Subject.query.get(id)

# ===== GraphQL Mutations (create/update/delete) =====

class CreateEpisode(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        season = graphene.Int(required=True)
        episode = graphene.Int(required=True)
        air_date = graphene.String()
        youtube_src = graphene.String()
        img_src = graphene.String()
        num_colors = graphene.Int()
        extra_info = graphene.JSONString()
        color_ids = graphene.List(graphene.Int)
        subject_ids = graphene.List(graphene.Int)

    episode = graphene.Field(lambda: EpisodeType)

    def mutate(self, info, title, season, episode,
               air_date=None, youtube_src=None, img_src=None,
               num_colors=None, extra_info=None, color_ids=None, subject_ids=None):
        parsed_date = None
        if air_date:
            parsed_date = date.fromisoformat(air_date)
        ep = Episode(
            title=title, season=season, episode=episode,
            air_date=parsed_date, youtube_src=youtube_src,
            img_src=img_src, num_colors=num_colors,
            extra_info=extra_info
        )
        # Attach colors
        if color_ids:
            for cid in color_ids:
                color = Color.query.get(cid)
                if color:
                    ep.colors.append(color)
        # Attach subjects
        if subject_ids:
            for sid in subject_ids:
                subject = Subject.query.get(sid)
                if subject:
                    ep.subjects.append(subject)
        db.session.add(ep)
        db.session.commit()
        return CreateEpisode(episode=ep)

class UpdateEpisode(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        season = graphene.Int()
        episode = graphene.Int()
        air_date = graphene.String()
        youtube_src = graphene.String()
        img_src = graphene.String()
        num_colors = graphene.Int()
        extra_info = graphene.JSONString()
        color_ids = graphene.List(graphene.Int)
        subject_ids = graphene.List(graphene.Int)

    episode = graphene.Field(lambda: EpisodeType)

    def mutate(self, info, id, title=None, season=None, episode=None,
               air_date=None, youtube_src=None, img_src=None,
               num_colors=None, extra_info=None, color_ids=None, subject_ids=None):
        ep = Episode.query.get_or_404(id)
        if title is not None:
            ep.title = title
        if season is not None:
            ep.season = season
        if episode is not None:
            ep.episode = episode
        if air_date is not None:
            ep.air_date = date.fromisoformat(air_date)
        if youtube_src is not None:
            ep.youtube_src = youtube_src
        if img_src is not None:
            ep.img_src = img_src
        if num_colors is not None:
            ep.num_colors = num_colors
        if extra_info is not None:
            ep.extra_info = extra_info
        # Replace color list if provided
        if color_ids is not None:
            ep.colors = [Color.query.get(cid) for cid in color_ids if Color.query.get(cid)]
        # Replace subject list if provided
        if subject_ids is not None:
            ep.subjects = [Subject.query.get(sid) for sid in subject_ids if Subject.query.get(sid)]
        db.session.commit()
        return UpdateEpisode(episode=ep)

class DeleteEpisode(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
    ok = graphene.Boolean()

    def mutate(self, info, id):
        ep = Episode.query.get_or_404(id)
        db.session.delete(ep)
        db.session.commit()
        return DeleteEpisode(ok=True)

class CreateColor(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        hex = graphene.String(required=True)
    color = graphene.Field(lambda: ColorType)

    def mutate(self, info, name, hex):
        color = Color(name=name, hex=hex)
        db.session.add(color)
        db.session.commit()
        return CreateColor(color=color)

class UpdateColor(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        hex = graphene.String()
    color = graphene.Field(lambda: ColorType)

    def mutate(self, info, id, name=None, hex=None):
        color = Color.query.get_or_404(id)
        if name is not None:
            color.name = name
        if hex is not None:
            color.hex = hex
        db.session.commit()
        return UpdateColor(color=color)

class DeleteColor(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
    ok = graphene.Boolean()

    def mutate(self, info, id):
        color = Color.query.get_or_404(id)
        db.session.delete(color)
        db.session.commit()
        return DeleteColor(ok=True)

class CreateSubject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
    subject = graphene.Field(lambda: SubjectType)

    def mutate(self, info, name):
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.commit()
        return CreateSubject(subject=subject)

class UpdateSubject(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
    subject = graphene.Field(lambda: SubjectType)

    def mutate(self, info, id, name=None):
        subject = Subject.query.get_or_404(id)
        if name is not None:
            subject.name = name
        db.session.commit()
        return UpdateSubject(subject=subject)

class DeleteSubject(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
    ok = graphene.Boolean()

    def mutate(self, info, id):
        subject = Subject.query.get_or_404(id)
        db.session.delete(subject)
        db.session.commit()
        return DeleteSubject(ok=True)

class Mutation(graphene.ObjectType):
    create_episode = CreateEpisode.Field()
    update_episode = UpdateEpisode.Field()
    delete_episode = DeleteEpisode.Field()
    create_color = CreateColor.Field()
    update_color = UpdateColor.Field()
    delete_color = DeleteColor.Field()
    create_subject = CreateSubject.Field()
    update_subject = UpdateSubject.Field()
    delete_subject = DeleteSubject.Field()

# Build Query and Mutation
schema = graphene.Schema(query=Query, mutation=Mutation)

# Protect the GraphQL endpoint with JWT authentication
app.add_url_rule(
    '/graphql',
    view_func=token_required(
        GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=True  # Enable GraphiQL UI for development
        )
    )
)

# Health check (SQLAlchemy 2.x requires text() for raw SQL)
@app.route('/health', methods=['GET'])
def health():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({"status": "ok", "database_connection": "successful"}), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "database_connection": f"failed: {e}"
        }), 500

# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(host='0.0.0.0', port=5000, debug=True)
