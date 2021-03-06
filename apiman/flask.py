import typing

from flask import Flask, jsonify, Response
from jinja2 import Template

from .openapi import OpenApi


class Extension(OpenApi):
    def __init__(
        self,
        *args,
        app: typing.Optional[Flask] = None,
        decorators: typing.Sequence[
            typing.Callable[[typing.Callable], typing.Callable]
        ] = tuple(),
        **kwargs,
    ):
        """Flask extension

        >>> app = Flask(__name__)
        >>> openapi = Extension(
        ...     template="./examples/docs/dog_template.yml", decorators=(lambda f: f,)
        ... )
        >>> openapi.init_app(app)
        >>> openapi.add_schema(
        ...     "Dog",
        ...     {
        ...         "properties": {
        ...             "id": {"description": "global unique", "type": "integer"},
        ...             "name": {"type": "string"},
        ...             "age": {"type": "integer"},
        ...         },
        ...         "type": "object",
        ...     },
        ... )
        >>> @app.route("/dogs/", methods=["GET"])
        ... @openapi.from_file("./examples/docs/dogs_get.yml")
        ... def list_dogs():
        ...     return jsonify(list(DOGS.values()))
        """
        super().__init__(*args, **kwargs)
        self.app = app
        self.decorators = decorators
        self.init_app(self.app) if self.app else None

    def init_app(self, app: Flask):
        app.extensions["apiman"] = self

        self.config.update(app.config.get_namespace("OPENAPI_", lowercase=True))

        if self.config["swagger_template"] and self.config["swagger_url"]:
            swagger_html = Template(
                open(self.config["swagger_template"]).read()
            ).render(self.config)
            self.route(
                app,
                self.config["swagger_url"],
                "swagger_ui",
                lambda: Response(swagger_html),
            )
        if self.config["redoc_template"] and self.config["redoc_url"]:
            redoc_html = Template(open(self.config["redoc_template"]).read()).render(
                self.config
            )
            self.route(
                app, self.config["redoc_url"], "redoc_ui", lambda: Response(redoc_html)
            )
        if self.config["specification_url"]:
            self.route(
                app,
                self.config["specification_url"],
                "openapi_specification",
                lambda: jsonify(self.load_specification(app)),
            )

    def load_specification(self, app: Flask) -> typing.Dict:
        if not self.loaded:
            for route in app.url_map.iter_rules():
                func = app.view_functions[route.endpoint]
                if hasattr(func, "view_class"):  # view class
                    # from class
                    specification = self.from_func(func.view_class)
                    self._load_specification(route.rule, specification)
                    # from class methods
                    for method in route.methods:
                        _func = getattr(func.view_class, method.lower(), None)
                        if _func:
                            specification = self.from_func(_func)
                            if specification:
                                self._load_specification(
                                    route.rule, specification, method=method
                                )
                else:  # view function
                    specification = self.from_func(func)
                    if not specification:
                        continue
                    if (
                        set(specification.keys()) & self.HTTP_METHODS
                    ):  # multi method description
                        self._load_specification(route.rule, specification)
                    else:
                        for method in route.methods:
                            if method.lower() in self.HTTP_METHODS:
                                self._load_specification(
                                    route.rule, specification, method=method
                                )
            self.loaded = True
            return self.specification
        else:
            return self.specification

    def route(self, app: Flask, url: str, endpoint: str, func):
        for decorator in self.decorators:
            func = decorator(func)
        app.route(url, endpoint=endpoint, methods=["GET"])(func)

    def _load_specification(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        # covert flask variable rules, eg "/path/<int:id>" to "/path/{id}"
        _subs = []
        for _sub in path.split("/"):
            if _sub.startswith("<") and _sub.endswith(">"):
                _subs.append(f"{{{_sub[1:-1].split(':')[-1]}}}")
            else:
                _subs.append(_sub)

        return super()._load_specification(
            "/".join(_subs), specification, method=method
        )
