const net = require('net');

const client = new net.Socket();
client.connect(8080, '127.0.0.1', () => {
    console.log('Connected to server');
});

client.on('data', (data) => {
    console.log('Received: ' + data);
    client.destroy(); // Close the connection after receiving data
});
