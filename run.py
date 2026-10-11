from app.database import init_db
from app.cli import main


if __name__ == "__main__":

    init_db()
    main()