from io import BytesIO

from django.core.handlers import base
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict


class ApiGatewayRequest(HttpRequest):
    def __init__(self, event):
        super().__init__()
        self.GET = QueryDict(mutable=True)
        self.POST = QueryDict(mutable=True)
        self.COOKIES = {}
        self.META = {}
        self.FILES = MultiValueDict()
        self.path = event.get('path', '')
        self.path_info = event.get('path', '')
        self.method = event.get('httpMethod')
        self.resolver_match = None
        self.content_type = event.get('headers', {}).get('Content-Type')
        self.content_params = None
        for key, value in event.get('headers', {}).items():
            self.META[f'HTTP_{key.upper().replace("-", "_")}'] = value
        self.META['REQUEST_METHOD'] = self.method
        self.META['PATH_INFO'] = self.path_info
        query_params = event.get('queryStringParameters', {})
        if query_params:
            self.GET = QueryDict(mutable=True)
            for key, value in query_params.items():
                self.GET[key] = value
        body = event.get('body')
        if body and self.content_type == 'application/json':
            import json
            try:
                body_data = json.loads(body)
                self.POST = QueryDict(mutable=True)
                for key, value in body_data.items():
                    self.POST[key] = value
            except json.JSONDecodeError:
                pass

    def _get_scheme(self):
        return 'https'


class APIGatewayHandler(base.BaseHandler):
    request_class = ApiGatewayRequest

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_middleware()

    def __call__(self, event, context=None):
        return self.get_response(self.request_class(event))
