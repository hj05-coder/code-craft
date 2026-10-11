from __future__ import annotations

import sys

from codecraft.cli import build_agent, build_arg_parser
from codecraft.tui.app import CodecraftTuiApp


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.prompt:
        print("codecraft-tui does not accept one-shot prompts; start the TUI and type there.", file=sys.stderr)
        return 2
    agent = build_agent(args)
    CodecraftTuiApp(agent).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
