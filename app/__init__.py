from flask import Flask, render_template

def create_app():
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return "Flask werkt!"
        
        # Als bovenstaande werkt, uncomment dan deze regel:
        # return render_template('dashboard/index.html')
    
    return app 