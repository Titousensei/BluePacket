const net = require('net');

const server = net.createServer((socket) => {
    socket.write('Hello from server!\n');
    socket.end();
});

server.listen(8080, () => {
    console.log('Server listening on port 8080');
});
