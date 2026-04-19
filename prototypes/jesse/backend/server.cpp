#include "httplib.h"
#include <iostream>
#include <string>

using namespace httplib;
using namespace std;

int main() {
    Server svr;

    svr.Post("/analyze", [](const Request& req, Response& res) {

   
        string result =
            "📦 Project Overview:\n"
            "This is a sample project structure.\n\n"

            "🧱 Main Modules:\n"
            "- src/\n"
            "- components/\n"
            "- utils/\n\n"

            "🔗 Relationships:\n"
            "- main uses components\n"
            "- components use utils\n\n"

            "🚀 Where to Start:\n"
            "Start with main.cpp or app entry point.\n";

        string json = "{ \"result\": \"" + result + "\" }";

        res.set_content(json, "application/json");
    });

    cout << "Server running at http://localhost:8080\n";
    svr.listen("0.0.0.0", 8080);
}
