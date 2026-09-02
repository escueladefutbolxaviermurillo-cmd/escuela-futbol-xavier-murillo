from flask import Blueprint, render_template, session, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from utils.decorators import login_required, role_required

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

@portal_bp.route('/')
@login_required
@role_required(['Representante'])
def index():
    rep_cedula = session.get('username')
    
    # Buscar todos los alumnos asociados a la cédula del representante
    players = list(db.players.find({
        "$or": [
            {"representative.identification_id": rep_cedula},
            {"identification_id": rep_cedula}
        ],
        "status": "Activo"
    })) if db is not None else []

    if not players:
        flash("No se encontraron alumnos asociados a esta cuenta.", "warning")
        return render_template('portal/index.html', children_data=[])

    children_data = []

    for player in players:
        player_id = player['_id']

        # Obtener Categoría
        category = db.categories.find_one({"_id": player.get("category_id")})
        category_name = category['name'] if category else 'Sin asignar'

        # Pagos del alumno
        payments = list(db.payments.find({"player_id": player_id}).sort('payment_date', -1))
        total_pagado = sum(p.get('amount', 0.0) for p in payments if p.get('status') == 'Completado')
        total_pendiente = sum(p.get('amount', 0.0) for p in payments if p.get('status') == 'Pendiente')

        # Asistencias a entrenamientos
        trainings = list(db.trainings.find({"attendance.player_id": player_id}).sort('scheduled_date', -1))
        attendance_records = []
        presentes = 0

        for t in trainings:
            for att in t.get('attendance', []):
                if str(att.get('player_id')) == str(player_id):
                    status_att = att.get('status', 'Presente')
                    if status_att == 'Presente':
                        presentes += 1
                    attendance_records.append({
                        "date": t.get('scheduled_date'),
                        "topic": t.get('topic') or 'Entrenamiento Técnico',
                        "field": t.get('field'),
                        "status": status_att
                    })

        total_sesiones = len(attendance_records)
        porcentaje_asistencia = round((presentes / total_sesiones * 100), 1) if total_sesiones > 0 else 0

        children_data.append({
            "player": player,
            "category_name": category_name,
            "payments": payments,
            "total_pagado": total_pagado,
            "total_pendiente": total_pendiente,
            "attendance_records": attendance_records,
            "total_sesiones": total_sesiones,
            "porcentaje_asistencia": porcentaje_asistencia
        })

    return render_template('portal/index.html', children_data=children_data)

@portal_bp.route('/datos-bancarios')
@login_required
@role_required(['Representante', 'Administrador'])
def bank_info():
    return render_template('portal/bank_info.html')