from .models import SobreONG


def sobre_ong(request):
    return {'sobre_ong': SobreONG.get_solo()}
