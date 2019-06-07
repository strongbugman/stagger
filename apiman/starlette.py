import typing

from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.schemas import SchemaGenerator
from jinja2 import Template

from .openapi import OpenApi


EndpointFunc = typing.Callable[
    [Request], typing.Union[Response, typing.Coroutine[None, None, Response]]
]


class Extension(OpenApi):
    def __init__(
        self,
        decorators: typing.Sequence[
            typing.Callable[[EndpointFunc], EndpointFunc]
        ] = tuple(),
        **config
    ):
        super().__init__(**config)
        self.decorators = decorators

    def init_app(self, app: Starlette):
        if self.config["swagger_template"] and self.config["swagger_url"]:
            swagger_html = Template(
                open(self.config["swagger_template"]).read()
            ).render(self.config)
            self.route(
                app, self.config["swagger_url"], lambda _: Response(swagger_html)
            )
        if self.config["redoc_template"] and self.config["redoc_url"]:
            redoc_html = Template(open(self.config["redoc_template"]).read()).render(
                self.config
            )
            self.route(app, self.config["redoc_url"], lambda _: Response(redoc_html))
        if self.config["specification_url"]:
            self.route(
                app,
                self.config["specification_url"],
                lambda _: JSONResponse(self.load_specification(app)),
            )

    def load_specification(self, app: Starlette) -> typing.Dict:
        if app.debug or not self.loaded:
            for endpoint in SchemaGenerator({}).get_endpoints(app.routes):
                specification = self.from_func(endpoint.func)
                if specification:
                    self._load_specification(
                        endpoint.path, endpoint.http_method, specification
                    )
            self.loaded = True
            return self.specification
        else:
            return self.specification

    def route(self, app: Starlette, url: str, func: EndpointFunc):
        for decorator in self.decorators:
            func = decorator(func)
        app.add_route(url, func, methods=["GET"], include_in_schema=False)
