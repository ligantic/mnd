import os

from mnd.settings import *  # noqa: F403

DATABASES = {
    name: {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": f"mnd_registration_{name}",
        "HOST": "127.0.0.1",
        "PORT": os.environ["MND_TEST_DB_PORT"],
        "USER": "postgres",
        "PASSWORD": "",
        "TEST": {"MIGRATE": False},
    }
    for name in ("default", "clinical")
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
