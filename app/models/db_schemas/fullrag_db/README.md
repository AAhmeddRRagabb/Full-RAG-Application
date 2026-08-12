# Alembic Configuration
Configure alembic to migrate data / schema from codebase to the factual database.

### 1.0 install alembic
```bash
pip install alembic>=1.18.5
```


### 2.0 Init Alembic in the database code folder
```bash
cd database_folder
alembic init alembic
```

### 3.0 Configure the database URL in the alembic.ini
```bash
cp alembic.ini.example alembic.ini
```

```py
sqlalchemy.url = your_db_url
```

### 4.0 Configure the target metadata in the alembic/env.py
```py
target_metadata = your_sqlalchemy_parent_model
```


### 5.0 Create New Migration
```bash
alembic revision --autogenerate -m "commit_text"
```

### 6.0 Upgrade the database to the final version
```bash
alembic upgrade head
```