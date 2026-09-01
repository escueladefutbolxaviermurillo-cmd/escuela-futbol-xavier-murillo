from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from utils.decorators import login_required, role_required
from datetime import datetime

trainings_bp = Blueprint('trainings', __name__, url_prefix='/trainings')

@trainings_bp.route('/')
@login_required
def index():
    trainings = list(db.trainings.find().sort('scheduled_date', -1)) if db is not None else []
    categories = list(db.categories.find()) if db is not None else []
    cat_map = {str(c['_id']): c['name'] for c in categories}
    
    for t in trainings:
        t['category_name'] = cat_map.get(str(t.get('category_id')), 'General')
        t['total_attendees'] = len(t.get('attendance', []))

    return render_template('trainings/index.html', trainings=trainings, categories=categories)

@trainings_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador', 'Entrenador'])
def create():
    categories = list(db.categories.find()) if db is not None else []

    if request.method == 'POST':
        category_id = request.form.get('category_id')
        shift = request.form.get('shift', 'Mañana').strip()
        date_str = request.form.get('scheduled_date')
        field = request.form.get('field', 'Cancha Principal').strip()
        topic = request.form.get('topic', '').strip()

        if not category_id or not date_str:
            flash("Debes seleccionar categoría, jornada y fecha para la sesión.", "danger")
            return render_template('trainings/create.html', categories=categories)

        try:
            scheduled_dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Formato de fecha u hora no válido.", "danger")
            return render_template('trainings/create.html', categories=categories)

        # Filtrar jugadores activos según categoría y jornada
        player_query = {"status": "Activo"}
        
        if category_id != "all":
            player_query["category_id"] = ObjectId(category_id)
            
        if shift in ["Mañana", "Tarde"]:
            player_query["shift"] = shift

        active_players = list(db.players.find(player_query).sort("last_name", 1))

        # Estructura inicial de asistencia
        initial_attendance = [
            {
                "player_id": p['_id'],
                "player_name": f"{p['last_name']} {p['first_name']}",
                "status": "Presente"
            }
            for p in active_players
        ]

        new_training = {
            "category_id": ObjectId(category_id) if category_id != "all" else None,
            "shift": shift,
            "scheduled_date": scheduled_dt,
            "field": field,
            "topic": topic,
            "status": "Programado",
            "attendance": initial_attendance,
            "created_at": datetime.utcnow()
        }

        db.trainings.insert_one(new_training)
        flash(f"Entrenamiento programado para la jornada {shift} ({len(initial_attendance)} jugadores asignados).", "success")
        return redirect(url_for('trainings.index'))

    return render_template('trainings/create.html', categories=categories)

@trainings_bp.route('/<training_id>/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador', 'Entrenador'])
def take_attendance(training_id):
    training = db.trainings.find_one({"_id": ObjectId(training_id)})
    if not training:
        flash("Sesión no encontrada.", "danger")
        return redirect(url_for('trainings.index'))

    category = db.categories.find_one({"_id": training.get("category_id")})
    training['category_name'] = category['name'] if category else 'General'

    if request.method == 'POST':
        updated_attendance = []
        for att in training.get('attendance', []):
            p_id = str(att['player_id'])
            status_val = request.form.get(f"status_{p_id}", "Presente")
            updated_attendance.append({
                "player_id": att['player_id'],
                "player_name": att['player_name'],
                "status": status_val
            })

        db.trainings.update_one(
            {"_id": ObjectId(training_id)},
            {"$set": {"attendance": updated_attendance, "status": "Completado"}}
        )
        flash("Asistencia guardada exitosamente.", "success")
        return redirect(url_for('trainings.index'))

    return render_template('trainings/attendance.html', training=training)