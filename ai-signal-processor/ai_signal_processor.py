from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_signal():
    data = request.json
    return jsonify({
        "confidence": 0.95,
        "predicted_price": data['price'] * 1.05
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001) 