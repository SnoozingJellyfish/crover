from flask_script import Manager
from crover import create_app
from crover.scripts.db import InitDB, DropDB

if __name__ == "__main__":
    manager = Manager(create_app)
    manager.add_command('init_db', InitDB())
    manager.add_command('drop_db', DropDB())
    manager.run()
