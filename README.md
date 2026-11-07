# Voice Gateway

By GNATOVSKIE. A small HTTP bridge from a voice shortcut to an assistant CLI.
Your phone transcribes speech, sends the text, and reads the returned answer.
The gateway does not perform speech recognition or speech synthesis.

Python 3.11 or newer; no third-party Python packages.

## Run

Create a private token file with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`.
Save its output outside this repository and restrict permissions to 0600.

```sh
export VOICE_TOKEN_FILE=/path/to/token
export VOICE_COMMAND='["claude", "-p"]'
python3 server.py
```

`VOICE_COMMAND` is an argument array, executed without a shell. The question is
sent on stdin; stdout becomes the answer. Use any CLI or wrapper with that
interface. The CLI must be installed and authenticated separately. Its normal
permissions apply: run it as a dedicated user with access only to intended data.
No tools, private context, or messaging integrations are configured by this project.

The default listener is `127.0.0.1:8787`. Optional variables: `VOICE_HOST`,
`VOICE_PORT`, `VOICE_TIMEOUT` (seconds, default 90), `VOICE_WORKDIR`.
Expose it through your own HTTPS reverse proxy; do not send bearer tokens over
an unencrypted external connection. Allow only POST `/ask`, limit request size
and rate at the proxy, and keep the service on loopback.

## Shortcut

In Apple Shortcuts: Dictate Text, Get Contents of URL using POST, then Speak Text.
Send to `https://your-host/ask` with `Authorization: Bearer <your token>` and
`Content-Type: application/json`. Body: `{"q":"the dictated text"}`.
Plain UTF-8 text is also accepted. Each request is independent.

Responses: 200 answer, 400 invalid input, 401 unauthorized, 413 oversized body,
429 two requests already running, 502 CLI error, 504 timeout. Request text and
CLI stderr are not logged or returned on failures. The local CLI may maintain
its own history according to its settings.

## Tests

```sh
python3 -m unittest discover -s tests
```

License: MIT OR Apache-2.0.
