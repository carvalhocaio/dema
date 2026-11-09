import argparse

import uvicorn

from dema.api.app import create_app
from dema.cli.common import Subparsers


def register(commands: Subparsers) -> None:
    api = commands.add_parser("api", help="serve the results API")
    actions = api.add_subparsers(required=True)
    serve = actions.add_parser("serve", help="run the HTTP server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(handler=_serve)


def _serve(args: argparse.Namespace) -> None:
    uvicorn.run(create_app(), host=args.host, port=args.port)
