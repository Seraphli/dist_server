# Python Distribute Server

Start multiple process using command, and allocate port using client.

### Server

`python -m dist_server.server -c "config.example.json"`

In the config file, use template mode or instance mode.

### Client

`python -m dist_server.client`

### Commands

While running, use h or help to get available commands.

```
Available Commands:
    exit or e: Exit
    query or q: Query available ports
    list or l: List all connections
    reset or r: Reset used ports
    help or h: This message
```
