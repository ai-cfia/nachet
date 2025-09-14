# Building an Up to Date Database from Scratch

<https://alembic.sqlalchemy.org/en/latest/cookbook.html>
There’s a theory of database migrations that says that the revisions in existence for a database should be able to go from an entirely blank schema to the finished product, and back again. Alembic can roll this way. Though we think it’s kind of overkill, considering that SQLAlchemy itself can emit the full CREATE statements for any given model using create_all(). If you check out a copy of an application, running this will give you the entire database in one shot, without the need to run through all those migration files, which are instead tailored towards applying incremental changes to an existing database.

Alembic can integrate with a create_all() script quite easily. After running the create operation, tell Alembic to create a new version table, and to stamp it with the most recent revision (i.e. head):

```python
# inside of a "create the database" script, first create
# tables:
my_metadata.create_all(engine)

# then, load the Alembic configuration and generate the
# version table, "stamping" it with the most recent rev:
from alembic.config import Config
from alembic import command
alembic_cfg = Config("/path/to/yourapp/alembic.ini")
command.stamp(alembic_cfg, "head")
```

When this approach is used, the application can generate the database using normal SQLAlchemy techniques instead of iterating through hundreds of migration scripts. Now, the purpose of the migration scripts is relegated just to movement between versions on out-of-date databases, not new databases. You can now remove old migration files that are no longer represented on any existing environments.

To prune old migration files, simply delete the files. Then, in the earliest, still-remaining migration file, set down_revision to None:

```text
# replace this:
#down_revision = '290696571ad2'

# with this:
down_revision = None
```

That file now becomes the “base” of the migration series.
