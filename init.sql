-- init.sql (runs automatically on first container start)
SELECT 'CREATE DATABASE pakistan_route_ai'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'pakistan_route_ai'
)\gexec