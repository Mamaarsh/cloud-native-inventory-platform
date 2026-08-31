bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"

timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"

capture_output = True