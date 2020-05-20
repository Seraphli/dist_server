namespace py pyrpc

service pyrpc {
    void ping()
    string version()
    i32 acquire_port()
    void release_port(1: i32 port)
}
