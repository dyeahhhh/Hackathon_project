import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = ROOT / 'outbreak_backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description='Outbreak of Lies CLI')
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run the FastAPI application')
    run_parser.add_argument('--host', default='0.0.0.0')
    run_parser.add_argument('--port', type=int, default=8000)
    run_parser.add_argument('--config', default=None)

    args = parser.parse_args()
    if args.command == 'run':
        uvicorn.run('api.main:app', host=args.host, port=args.port, reload=False)
        return

    parser.print_help()


if __name__ == '__main__':
    main()
