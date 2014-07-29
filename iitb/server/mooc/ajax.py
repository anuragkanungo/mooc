from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register

@dajaxice_register
def updatecombo(request, option):
    dajax = Dajax()
    options = [['Madrid', 'Barcelona', 'Vitoria', 'Burgos'],
               ['Paris', 'Evreux', 'Le Havre', 'Reims'],
               ['London', 'Birmingham', 'Bristol', 'Cardiff']]
    out = []
    for option in options[int(option)]:
        out.append("<option value='#'>%s</option>" % option)

    dajax.assign('#combo2', 'innerHTML', ''.join(out))
    return dajax.json()

@dajaxice_register
def ajax_test:
    str = 'Hello World'
    dajax = Dajax()
    dajax.assign('#combo2', 'innerHTML', str)
    return dajax.json()
