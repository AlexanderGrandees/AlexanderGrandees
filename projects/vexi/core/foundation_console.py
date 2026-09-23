"""Local text harness; owner-console is a trusted OS-session operator surface.

Never expose stdin, --owner-console, or OwnerAuthority to voice/model/network input.
No network listener or arbitrary tool/shell route is created.
"""
import argparse
import getpass
import json
import time
from pathlib import Path
from foundation_bridge import FoundationBridge
from vexi_foundation.contracts import Actor, SpeakerRole
from vexi_foundation.workspace import WorkspacePolicy
from version import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--owner-console", action="store_true")
    args = parser.parse_args()
    bridge = FoundationBridge({"browser_name": "Chrome"})
    actor = bridge.actor
    if args.owner_console:
        # An explicit launch from the trusted local OS session is the approval surface;
        # it does not authenticate anyone speaking into the microphone.
        actor = Actor(getpass.getuser(), "local-console", SpeakerRole.OWNER)
        bridge.authority.bind_owner(actor, bridge.scope, time.monotonic() + 1800)
    if args.workspace:
        args.workspace.mkdir(parents=True, exist_ok=True)
        bridge.workspace = WorkspacePolicy("console", bridge.scope, args.workspace.resolve())
    print(json.dumps({"event": "READY", "version": __version__, "ingress": "text",
                      "role": actor.role.value}, ensure_ascii=False), flush=True)
    for text in iter(input, "exit"):
        if bridge.accept(True, actor=actor):
            handled, answer = bridge.execute(text, actor=actor)
            print(json.dumps({"handled": handled, "answer": answer}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except EOFError:
        pass
