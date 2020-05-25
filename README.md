# Python Distribute Server

Start multiple process using command, and allocate port using client.

### Server

`python -m dist_server.server -c "config.example.json"`

In the config file, use template mode or instance mode.

### Client

`python -m dist_server.client`
