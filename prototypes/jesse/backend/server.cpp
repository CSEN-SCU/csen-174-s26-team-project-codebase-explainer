#include <iostream>
#include <unistd.h>
#include <netinet/in.h>
#include <string>
#include <vector>
#include <regex>
#include <sqlite3.h>
#include <cstdlib>

using namespace std;


vector<string> extractFunctions(const string& code) {
    vector<string> funcs;
    regex r(R"((int|void|string|float|double)\s+(\w+)\s*\()");

    auto it = sregex_iterator(code.begin(), code.end(), r);
    for (; it != sregex_iterator(); ++it) {
        funcs.push_back((*it)[2]);
    }
    return funcs;
}


string callAI(const string& code) {
    const char* key = getenv("OPENAI_API_KEY");
    if (!key) return "No API key set.";

    
    string safe = code;
    for (char& c : safe) {
        if (c == '\"') c = '\'';
        if (c == '\n') c = ' ';
    }

    string cmd =
        "curl -s --max-time 5 https://api.openai.com/v1/chat/completions "
        "-H \"Authorization: Bearer " + string(key) + "\" "
        "-H \"Content-Type: application/json\" "
        "-d \"{\\\"model\\\":\\\"gpt-4o-mini\\\","
        "\\\"messages\\\":[{\\\"role\\\":\\\"user\\\","
        "\\\"content\\\":\\\"Explain this code in one sentence: " + safe + "\\\"}]}\"";

    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return "AI call failed";

    char buffer[256];
    string result;

    while (fgets(buffer, sizeof(buffer), pipe)) {
        result += buffer;
    }
    pclose(pipe);

    if (result.empty()) return "AI request failed";

   
    size_t pos = result.find("\"content\": \"");
    if (pos == string::npos) return "AI parse failed";

    pos += 12;
    size_t end = result.find("\"", pos);
    if (end == string::npos) return "AI parse failed";

    return result.substr(pos, end - pos);
}

int main() {
    
    sqlite3* db;
    sqlite3_open("data.db", &db);

    sqlite3_exec(db,
        "CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, input TEXT);",
        0, 0, 0);

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(8080);

    if (::bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("bind failed");
        return 1;
    }

    if (::listen(server_fd, 3) < 0) {
        perror("listen failed");
        return 1;
    }

    cout << "Server running on http://localhost:8080\n";

    while (true) {
        int addrlen = sizeof(address);
        int new_socket = ::accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen);

        char buffer[4096];
        string request = "";
        int bytes;

       
        bytes = read(new_socket, buffer, sizeof(buffer));
        request.append(buffer, bytes);

        size_t header_end = request.find("\r\n\r\n");

        string body = "";

        if (header_end != string::npos) {
            string headers = request.substr(0, header_end);

            size_t pos = headers.find("Content-Length:");
            int content_length = 0;

            if (pos != string::npos) {
                content_length = stoi(headers.substr(pos + 15));
            }

            body = request.substr(header_end + 4);

            while (body.length() < content_length) {
                bytes = read(new_socket, buffer, sizeof(buffer));
                body.append(buffer, bytes);
            }
        }

        cout << "BODY: " << body << endl;

        
        string sql = "INSERT INTO logs (input) VALUES ('" + body + "');";
        sqlite3_exec(db, sql.c_str(), 0, 0, 0);

  
        vector<string> funcs = extractFunctions(body);

        // ===== AI =====
        string ai = callAI(body);


        string json = "{";

        json += "\"functions\":[";
        for (int i = 0; i < funcs.size(); i++) {
            if (i) json += ",";
            json += "\"" + funcs[i] + "\"";
        }
        json += "],";

        json += "\"ai\":\"" + ai + "\"";

        json += "}";

        string response =
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Access-Control-Allow-Origin: *\r\n\r\n" +
            json;

        send(new_socket, response.c_str(), response.size(), 0);
        close(new_socket);
    }
}
