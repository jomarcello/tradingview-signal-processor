from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_news():
    data = request.json
    return jsonify({
        "processed": True,
        "items": len(data['articles']),
        "summary": "AI samenvatting van het nieuws"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 