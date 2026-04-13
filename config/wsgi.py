import os
import signal
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_app = get_wsgi_application()

def graceful_shutdown(signum, frame):
    print(f"\nReceived signal {signum}, initiating graceful shutdown...")
    sys.exit(0)

if sys.platform != 'win32':
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)

application = django_app
