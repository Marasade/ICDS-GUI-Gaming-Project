# Copilot Instructions for simple_gui

This file gives concise, actionable guidance for AI coding agents working on this repository.

## Big picture
- **Purpose**: A simple socket-based chat system with a Tkinter GUI client and a central server. It supports login, peer connect/chat, search of per-user chat history, and retrieving sonnets (from `AllSonnets.txt`).
- **Major components**:
  - `chat_server.py`: single-process server, main loop in `Server.run()`. Handles JSON actions from clients.
  - `chat_client_class.py` + `GUI.py`: client entrypoint and Tkinter GUI. Client uses `client_state_machine.ClientSM` for chat logic.
  - `client_state_machine.py`: implements client state machine and command parsing (states: `S_OFFLINE`, `S_LOGGEDIN`, `S_CHATTING`).
  - `chat_utils.py`: transport helpers (`mysend`, `myrecv`), constants (`SIZE_SPEC`, `CHAT_PORT`), and `menu` text.
  - `indexer.py` / `indexer_good.py`: used by server to index/search sonnets and per-user chat history.
  - `chat_group.py`: group membership and simple peer connection logic.

## Communication protocol (critical)
- All messages are JSON strings prefixed by a 5-byte decimal size header (see `chat_utils.SIZE_SPEC = 5`). Use `mysend`/`myrecv` to respect this framing.
- Primary client→server actions (examples seen in `client_state_machine.py`):
  - Login: `{"action":"login", "name": "alice"}` → server responds `{"action":"login", "status":"ok"}` or `"duplicate"`.
  - Connect: `{"action":"connect", "target":"bob"}` → server response contains `status` (`success`/`busy`/`self`/`no-user`).
  - Exchange: `{"action":"exchange", "from":"[alice]", "message":"hi"}` → server forwards `{"action":"exchange","from":...,"message":...}` to peers.
  - List/time/search/poem/disconnect: `{"action":"list"}`, `{"action":"time"}`, `{"action":"search","target":"term"}`, `{"action":"poem","target":<num>}`, `{"action":"disconnect"}`.
- Server responses use keys `action`, `results`, `status`, and sometimes `from` for peer messages (see `chat_server.handle_msg`).

## Data flows and persistence
- Per-user chat indices are kept in-memory in `Server.indices` and persisted as pickles named `<username>.idx`. The server loads them on login and dumps on logout.
- Sonnet data is provided via `AllSonnets.txt` and wrapped by `indexer.PIndex("AllSonnets.txt")` in `chat_server.py`.

## Conventions & patterns
- Use `mysend` / `myrecv` for all socket I/O to preserve size prefix framing. Direct socket `send`/`recv` without framing will break the protocol.
- Messages exchanged between peers (through server) are plain JSON with fields `action`, `from`, `message`, or `results`.
- The GUI runs a receiver thread (`GUI.proc`) that polls the socket with `select` and calls `sm.proc(my_msg, peer_msg)`. State transitions are handled inside `client_state_machine.ClientSM`.

## How to run & debug (developer workflow)
- Start server (foreground):
  - `python3 chat_server.py`
- Run a client (GUI):
  - `python3 chat_client_class.py` (optionally `-d <server_host>` to connect to remote server)
- Helpful debugging tips:
  - Server prints login/connect/search actions to stdout. Add prints near `Server.handle_msg` for more visibility.
  - To test transport framing, unit-test `mysend`/`myrecv` with a pair of connected sockets.
  - On macOS, ensure Tkinter is installed and GUI can open windows.

## Files to inspect when changing behavior
- Socket framing / constants: `chat_utils.py` (`SIZE_SPEC`, `mysend`, `myrecv`).
- Client state/command grammar: `client_state_machine.py` (search handling, `c`, `?`, `p`, `time`, `who`, `q`).
- Server command switch: `chat_server.py:handle_msg()` (where actions are interpreted and routed).
- GUI integration: `GUI.py` — `goAhead`, `proc`, and `sendButton` show how user input becomes `sm.proc` calls.
- Group/peer logic: `chat_group.py` (peer membership, connect/disconnect semantics).
- Indexing/search: `indexer.py` / `indexer_good.py` and `AllSonnets.txt`.

## Quick examples you may need
- Example login exchange:
  - Client -> Server: `{"action":"login","name":"alice"}`
  - Server -> Client: `{"action":"login","status":"ok"}`
- Example chat send (from client):
  - `{"action":"exchange","from":"[alice]","message":"hello"}`

## Notes / gotchas
- The server uses pickles for per-user indices (`<username>.idx`) — when modifying indexer internals, ensure backward compatibility or handle missing index files gracefully.
- `CHAT_IP` in `chat_utils.py` is `''` by default (binds to all interfaces). Change cautiously for local-only testing.
- No automated tests provided; be conservative with API changes and run manual client+server sessions.

If anything above is unclear or you want a different level of detail (e.g., more examples, test harness, or CI commands), tell me which part and I will iterate.
