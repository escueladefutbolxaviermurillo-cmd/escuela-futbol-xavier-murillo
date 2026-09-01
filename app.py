import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.players import players_bp
from routes.trainings import trainings_bp
from routes.payments import payments_bp
from routes.users import users_bp
from routes.reports import reports_bp
from routes.categories import categories_bp
from routes.portal import portal_bp

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave_dev_1234')

# Registrar Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(players_bp)
app.register_blueprint(trainings_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(users_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(categories_bp)
app.register_blueprint(portal_bp)


@app.route('/')
def root():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)