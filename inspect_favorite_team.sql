SELECT jsonb_object_keys(raw) AS key
FROM (SELECT raw FROM managers LIMIT 1) sample;

SELECT raw->>'favourite_team' AS favorite_team_id, count(*) AS managers
FROM managers
GROUP BY favorite_team_id
ORDER BY managers DESC NULLS LAST
LIMIT 30;

WITH latest AS (
    SELECT payload
    FROM fpl_bootstrap_snapshots
    ORDER BY fetched_at DESC
    LIMIT 1
)
SELECT
    (team->>'id')::integer AS id,
    team->>'name' AS name,
    team->>'short_name' AS short_name
FROM latest
CROSS JOIN LATERAL jsonb_array_elements(payload->'teams') AS team
ORDER BY id;
