from django.apps import AppConfig


class RondonopolisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rondonopolis'

    def ready(self):
        import rondonopolis.signals
