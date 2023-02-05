-- SQLite
SELECT username, start, end FROM session \
INNER JOIN users ON session.userid = users.userid \
WHERE (start BETWEEN '{}' AND '{}') AND (end BETWEEN '{}' AND '{}')