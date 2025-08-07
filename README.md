# ETL: The Joy Of Coding

![Project Structure](image-1.png)

# 🎨 The Joy of Painting API (Backend)

This backend powers the *Joy of Painting* project, providing both **REST** and **GraphQL** APIs to access Bob Ross episode data, associated colors, and subject matter. It uses **Flask**, **SQLAlchemy**, **Graphene**, and **JWT authentication**.

---

## 📦 Technologies Used

- Python 3.11+
- Flask
- SQLAlchemy
- MySQL (via mysql-connector)
- GraphQL (via Graphene)
- Flask-RESTful
- Flask-CORS
- JWT for authentication
- Docker (optional)

---

## 📁 Project Structure

backend/
├── api/
│ ├── app.py # Main Flask application
│ ├── models.py # SQLAlchemy models
├── data/
│ ├── raw_data_source/ # Raw original files
│ ├── sterilized_data/ # Cleaned, transformed CSVs
│ ├── etl/ # Python scripts for cleaning
├── .env # Environment config
├── requirements.txt # Python dependencies


---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/atlas-the-joy-of-painting-api.git
cd atlas-the-joy-of-painting-api/backend

Create .env file
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=joy_of_painting

JWT_SECRET=your_jwt_secret_key

 Install dependencies
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

Start MySQL and create the database
CREATE DATABASE joy_of_painting;

Run the server
python app.py


Server will run at:
REST API: http://localhost:5000/api
GraphQL UI: http://localhost:5000/graphql
Health Check: http://localhost:5000/health

🔐 Authentication
Obtain JWT Token
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin", "password":"password"}'


Response:
{
  "token": "<your_jwt_token>"
}

Use this token in the Authorization header for protected endpoints:
| Method | Endpoint           | Description                        |
| ------ | ------------------ | ---------------------------------- |
| GET    | /api/episodes      | List all episodes (filterable)     |
| GET    | /api/episodes/\:id | Get episode by ID                  |
| POST   | /api/episodes      | Create new episode (auth required) |
| PUT    | /api/episodes/\:id | Update an episode                  |
| DELETE | /api/episodes/\:id | Delete an episode                  |
| GET    | /api/colors        | List all colors                    |
| GET    | /api/colors/\:id   | Color details & related episodes   |
| GET    | /api/subjects      | List all subjects                  |
| GET    | /api/subjects/\:id | Subject details & related episodes |

🧠 GraphQL Support
GraphQL available at: http://localhost:5000/graphql

Example Query
query {
  allEpisodes {
    id
    title
    season
    episode
    air_date
  }
}

Example Mutation (create)
mutation {
  createEpisode(
    title: "Mountain Lake",
    season: 3,
    episode: 7,
    airDate: "1983-04-17"
  ) {
    episode {
      id
      title
    }
  }
}


🚧 Role-Based Access (Coming Soon)
Future enhancements will include:

Admin/User roles

Fine-grained permissions per role

🐳 Docker Support (Optional)
Coming soon: docker-compose.yml for local DB + API.

🧼 ETL Data Processing
See data/etl/ for scripts to clean and align raw data from:

Episode metadata

Colors used

Subjects painted

🧪 Health Check
curl http://localhost:5000/health

🤝 Contributing
Fork the repo

Create a feature branch

Open a PR

📜 License
MIT


Let me know if you'd like a `docker-compose.yml`, an ER diagram, or to generate the frontend README next.
