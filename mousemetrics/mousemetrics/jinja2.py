from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils.translation import gettext


def url(viewname, *args, **kwargs):
    return reverse(viewname, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "static": static,
            "url": url,
            "csrf_input": lambda request: '<input type="hidden" name="csrfmiddlewaretoken" value="%s">'
            % get_token(request),
            "_": gettext,
            "gettext": gettext,
        }
    )
    return env
