#!/bin/bash
set -euo pipefail
CID=epp-pg-disposable

docker rm -f "$CID" > /dev/null 2>&1 || true
docker run -d --name "$CID" -p 127.0.0.1:15433:5432 -e POSTGRES_PASSWORD=postgres postgres:17 > /dev/null
until docker exec "$CID" pg_isready -U postgres > /dev/null 2>&1; do sleep 1; done

docker exec -i "$CID" psql -v ON_ERROR_STOP=1 -U postgres -d postgres < supabase/ci-only/01_roles_bootstrap.sql
docker exec -i "$CID" psql -v ON_ERROR_STOP=1 -U postgres -d postgres < supabase/migrations/20260819_0001_init_schema.sql
docker exec -i "$CID" psql -v ON_ERROR_STOP=1 -U postgres -d postgres < supabase/ci-only/00_auth_stub.sql

uygulanan=1
for f in $(ls supabase/migrations/*.sql | sort); do
  if [[ "$f" == *"20260819_0001_init_schema.sql" ]]; then
    continue
  fi
  docker exec -i "$CID" psql -v ON_ERROR_STOP=1 -U postgres -d postgres < "$f"
  uygulanan=$((uygulanan + 1))
done
toplam=$(ls supabase/migrations/*.sql | wc -l)
echo "applied $uygulanan / total $toplam"
