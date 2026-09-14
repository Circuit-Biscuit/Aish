Review of the pull request.

In src/api/handlers.py the new endpoint does not validate the page size
parameter, so a client can request a million rows and exhaust memory. This
should be capped at 100.

In src/api/handlers.py the database session is opened outside the try block, so
if the query raises the session is never closed. Move it inside or use a
context manager.

In src/db/queries.py the new query builds SQL with string formatting using the
sort column from user input. That is a SQL injection risk. Use a whitelist of
allowed column names.

In tests/test_api.py there is no test for the error path of the new endpoint.
Coverage of the happy path only.

Minor: the docstring on fetch_page says it returns a list but it returns a
generator.
