-- Atomic fixed-window velocity counter. The first attempt starts the window;
-- later attempts do not extend it. A transfer decision still belongs in SQL.
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {n, redis.call('TTL', KEYS[1])}
