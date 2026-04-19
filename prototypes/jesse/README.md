# Jesse's Prototype

## Description
This prototype analyzes code structure and uses AI to generate explanations.

## How to run

1. Set API key:
export OPENAI_API_KEY=your_key

2. Compile backend:
g++ server.cpp -lsqlite3 -o server

3. Run backend:
./server

4. Run frontend:
python3 -m http.server 3000

5. Open browser:
http://localhost:3000
