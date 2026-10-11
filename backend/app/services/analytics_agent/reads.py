"""Worker-owned snapshots with cancellation and a deadline before every SQL query."""
from contextlib import contextmanager
from threading import Timer
from time import monotonic

from sqlalchemy import event, text
from sqlalchemy.orm import Session


@contextmanager
def analytical_session(factory, context, exploration=True):
    if context.remaining(exploration) <= 0:
        raise TimeoutError('Analytical phase expired')
    with factory() as session:
        connection = session.connection()
        driver = connection.connection.driver_connection
        deadline = context.started + (45 if exploration else 60)

        def before_query(conn, cursor, statement, parameters, execution_context, executemany):
            milliseconds = int((deadline - monotonic()) * 1000)
            if milliseconds <= 0:
                raise TimeoutError('Analytical phase expired')
            if statement.startswith('SET TRANSACTION'):
                return
            cursor.execute("SELECT set_config('statement_timeout', %s, true), set_config('lock_timeout', %s, true)", (str(min(5000, milliseconds)), str(min(1000, milliseconds))))

        timer = Timer(max(0, deadline - monotonic()), driver.cancel)
        timer.daemon = True
        event.listen(connection, 'before_cursor_execute', before_query)
        timer.start()
        try:
            session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            yield session
        finally:
            timer.cancel()
            timer.join()
            event.remove(connection, 'before_cursor_execute', before_query)
            session.rollback()
