from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "FARMABOL - Sistema de inventarios"

if __name__ == "__main__":
    app.run(debug=True)
