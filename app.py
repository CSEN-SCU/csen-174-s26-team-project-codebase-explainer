from flask import Flask, request, jsonify
import os
from openai import OpenAI

app = Flask(__name__)


@app.route("/")
def home():
    return "Your app is live!"

@app.route("/ai", methods=["POST"])
def ai():
    try:
        data = request.json
        user_input = data.get("message", "")

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )

        return jsonify({
            "response": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
