Module map for the billing system.

The gateway module imports the auth module and the ledger module. The ledger
module imports the storage module. The storage module imports nothing.

The auth module depends on the session store, which is Redis. The ledger module
depends on Postgres.

The invoicing module imports the ledger module and the templates module. The
templates module imports nothing.

The reporting module imports the ledger module and the invoicing module.

The gateway module is owned by the platform team. The ledger and invoicing
modules are owned by the billing team. The reporting module is owned by the
data team.

The ledger module is on the money path. The storage module is on the data loss
path. Everything else is neither.

Postgres is a hard dependency for the ledger and cannot be swapped. Redis is a
soft dependency for auth and could be replaced by any session store.
