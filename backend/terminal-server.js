const WebSocket = require('ws');
const server = new WebSocket.Server({ port: 3000 });

server.on('connection', (ws) => {
    ws.on('message', (message) => {
        const data = JSON.parse(message);
        if (data.type === 'stderr') {
            process.stderr.write(data.text);
        } else {
            process.stdout.write(data.text);
        }
    });
}); 