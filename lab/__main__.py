"""python -m lab --config PATH: serve the Lab (uvicorn, under the configured root path): an MCP server at mcp/."""
import argparse


def main():
    parser = argparse.ArgumentParser(prog='python -m lab')
    parser.add_argument('--config', help='the Lab config (JSON); see lab/config.example.json')
    args = parser.parse_args()
    if not args.config:
        parser.error('--config is required')
    import uvicorn
    from .app import create_app
    from .config import load
    config = load(args.config)
    uvicorn.run(create_app(config), host=config['host'], port=config['port'], root_path=config['rootPath'])


main()
