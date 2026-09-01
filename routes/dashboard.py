from flask import Blueprint, render_template
from utils.decorators import login_required
from database import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # Conteos generales
    total_players = db.players.count_documents({"status": "Activo"}) if db is not None else 0
    total_trainers = db.users.count_documents({"role": "Entrenador", "is_active": True}) if db is not None else 0
    total_categories = db.categories.count_documents({}) if db is not None else 0
    
    # Pagos pendientes
    pending_payments = db.payments.count_documents({"status": "Pendiente"}) if db is not None else 0

    # Próximos entrenamientos (últimos 5 programados)
    upcoming_trainings = list(db.trainings.find().sort("scheduled_date", -1).limit(5)) if db is not None else []

    return render_template(
        'dashboard.html',
        total_players=total_players,
        total_trainers=total_trainers,
        total_categories=total_categories,
        pending_payments=pending_payments,
        upcoming_trainings=upcoming_trainings
    )