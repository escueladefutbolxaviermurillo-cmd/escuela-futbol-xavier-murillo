from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from utils.decorators import login_required, role_required
from datetime import datetime

players_bp = Blueprint('players', __name__, url_prefix='/players')

@players_bp.route('/')
@login_required
def index():
    categories = list(db.categories.find()) if db is not None else []
    cat_filter = request.args.get('category_id')
    shift_filter = request.args.get('shift')
    search_query = request.args.get('q', '').strip()
    
    query = {}
    if cat_filter:
        query['category_id'] = ObjectId(cat_filter)
    if shift_filter:
        query['shift'] = shift_filter
    if search_query:
        query['$or'] = [
            {'first_name': {'$regex': search_query, '$options': 'i'}},
            {'last_name': {'$regex': search_query, '$options': 'i'}},
            {'identification_id': {'$regex': search_query, '$options': 'i'}}
        ]
        
    players = list(db.players.find(query).sort('last_name', 1)) if db is not None else []
    cat_map = {str(c['_id']): c['name'] for c in categories}
    for p in players:
        p['category_name'] = cat_map.get(str(p.get('category_id')), 'Sin asignar')

    return render_template(
        'players/index.html',
        players=players,
        categories=categories,
        selected_cat=cat_filter,
        selected_shift=shift_filter,
        q=search_query
    )

@players_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador'])
def create():
    categories = list(db.categories.find()) if db is not None else []
    
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        birth_date = request.form.get('birth_date')
        id_card = request.form.get('identification_id', '').strip()
        category_id = request.form.get('category_id')
        shift = request.form.get('shift', 'Mañana').strip()
        medical_notes = request.form.get('medical_notes', '').strip()
        
        rep_name = request.form.get('rep_name', '').strip()
        rep_id = request.form.get('rep_id', '').strip()
        rep_phone = request.form.get('rep_phone', '').strip()
        rep_email = request.form.get('rep_email', '').strip()

        if not first_name or not last_name or not id_card:
            flash("Los datos principales del jugador son obligatorios.", "danger")
            return render_template('players/create.html', categories=categories)

        new_player = {
            "first_name": first_name,
            "last_name": last_name,
            "identification_id": id_card,
            "birth_date": birth_date,
            "category_id": ObjectId(category_id) if category_id else None,
            "shift": shift,
            "status": "Activo",
            "medical_notes": medical_notes,
            "representative": {
                "full_name": rep_name,
                "identification_id": rep_id,
                "phone": rep_phone,
                "email": rep_email
            },
            "created_at": datetime.utcnow()
        }

        db.players.insert_one(new_player)

        # Habilitar o vincular cuenta del Representante
        if rep_id:
            existing_user = db.users.find_one({"username": rep_id})
            if not existing_user:
                db.users.insert_one({
                    "username": rep_id,
                    "full_name": rep_name or f"Rep. {last_name}",
                    "role": "Representante",
                    "password_hash": generate_password_hash(rep_id),
                    "is_active": True,
                    "created_at": datetime.utcnow()
                })

        flash("Jugador registrado exitosamente. Acceso de representante habilitado.", "success")
        return redirect(url_for('players.index'))

    return render_template('players/create.html', categories=categories)

@players_bp.route('/<player_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador'])
def edit(player_id):
    player = db.players.find_one({"_id": ObjectId(player_id)})
    if not player:
        flash("Jugador no encontrado.", "danger")
        return redirect(url_for('players.index'))
        
    categories = list(db.categories.find()) if db is not None else []

    if request.method == 'POST':
        category_val = request.form.get('category_id')
        new_first_name = request.form.get('first_name', '').strip()
        new_last_name = request.form.get('last_name', '').strip()

        new_rep_name = request.form.get('rep_name', '').strip()
        new_rep_id = request.form.get('rep_id', '').strip()
        new_rep_phone = request.form.get('rep_phone', '').strip()
        new_rep_email = request.form.get('rep_email', '').strip()

        old_rep_id = player.get('representative', {}).get('identification_id', '').strip()

        # 1. Actualizar datos del jugador
        update_data = {
            "first_name": new_first_name,
            "last_name": new_last_name,
            "identification_id": request.form.get('identification_id', '').strip(),
            "birth_date": request.form.get('birth_date'),
            "category_id": ObjectId(category_val) if category_val else None,
            "shift": request.form.get('shift', 'Mañana').strip(),
            "status": request.form.get('status', 'Activo'),
            "medical_notes": request.form.get('medical_notes', '').strip(),
            "representative.full_name": new_rep_name,
            "representative.identification_id": new_rep_id,
            "representative.phone": new_rep_phone,
            "representative.email": new_rep_email
        }
        db.players.update_one({"_id": ObjectId(player_id)}, {"$set": update_data})

        # 2. Sincronizar nombre del jugador en asistencias previas
        full_player_name = f"{new_last_name} {new_first_name}"
        db.trainings.update_many(
            {"attendance.player_id": ObjectId(player_id)},
            {"$set": {"attendance.$[elem].player_name": full_player_name}},
            array_filters=[{"elem.player_id": ObjectId(player_id)}]
        )

        # 3. Sincronizar cuenta de usuario del representante
        if old_rep_id and new_rep_id:
            user_account = db.users.find_one({"username": old_rep_id, "role": "Representante"})
            
            if user_account:
                user_updates = {"full_name": new_rep_name}
                if old_rep_id != new_rep_id:
                    user_updates["username"] = new_rep_id
                    # Actualizar cédula en los demás hijos registrados
                    db.players.update_many(
                        {"representative.identification_id": old_rep_id},
                        {"$set": {
                            "representative.identification_id": new_rep_id,
                            "representative.full_name": new_rep_name,
                            "representative.phone": new_rep_phone,
                            "representative.email": new_rep_email
                        }}
                    )
                db.users.update_one({"_id": user_account['_id']}, {"$set": user_updates})
            else:
                if not db.users.find_one({"username": new_rep_id}):
                    db.users.insert_one({
                        "username": new_rep_id,
                        "full_name": new_rep_name or f"Rep. {new_last_name}",
                        "role": "Representante",
                        "password_hash": generate_password_hash(new_rep_id),
                        "is_active": True,
                        "created_at": datetime.utcnow()
                    })

        flash("Información del jugador y cuenta del representante sincronizadas correctamente.", "success")
        return redirect(url_for('players.index'))

    return render_template('players/edit.html', player=player, categories=categories)

@players_bp.route('/<player_id>/delete', methods=['POST'])
@login_required
@role_required(['Administrador'])
def delete(player_id):
    player = db.players.find_one({"_id": ObjectId(player_id)})
    if not player:
        flash("El jugador no existe o ya fue eliminado.", "danger")
        return redirect(url_for('players.index'))

    rep_id = player.get('representative', {}).get('identification_id')

    # 1. Eliminar jugador
    db.players.delete_one({"_id": ObjectId(player_id)})

    # 2. Retirar jugador de listas de asistencias
    db.trainings.update_many(
        {},
        {"$pull": {"attendance": {"player_id": ObjectId(player_id)}}}
    )

    # 3. Eliminar pagos y recibos asociados
    db.payments.delete_many({"player_id": ObjectId(player_id)})

    # 4. Comprobar si el representante tiene otros hijos inscritos
    if rep_id:
        remaining_children = db.players.count_documents({"representative.identification_id": rep_id})
        if remaining_children == 0:
            db.users.delete_one({"username": rep_id, "role": "Representante"})
            flash("Jugador eliminado y usuario del representante retirado (sin otros alumnos vinculados).", "info")
        else:
            flash(f"Jugador eliminado. La cuenta del representante permanece activa ({remaining_children} alumno(s) aún a su cargo).", "info")
    else:
        flash("Jugador eliminado exitosamente.", "success")

    return redirect(url_for('players.index'))

@players_bp.route('/<player_id>')
@login_required
def detail(player_id):
    player = db.players.find_one({"_id": ObjectId(player_id)})
    if not player:
        flash("Jugador no encontrado.", "danger")
        return redirect(url_for('players.index'))

    category = db.categories.find_one({"_id": player.get("category_id")})
    player['category_name'] = category['name'] if category else 'Sin asignar'

    payments = list(db.payments.find({"player_id": ObjectId(player_id)}).sort('payment_date', -1)) if db is not None else []
    total_pagado = sum(p.get('amount', 0.0) for p in payments if p.get('status') == 'Completado')
    total_pendiente = sum(p.get('amount', 0.0) for p in payments if p.get('status') == 'Pendiente')

    trainings = list(db.trainings.find({"attendance.player_id": ObjectId(player_id)}).sort('scheduled_date', -1)) if db is not None else []
    attendance_history = []
    total_presentes = 0

    for t in trainings:
        for att in t.get('attendance', []):
            if str(att.get('player_id')) == str(player_id):
                status_att = att.get('status', 'Presente')
                if status_att == 'Presente':
                    total_presentes += 1
                attendance_history.append({
                    "date": t.get('scheduled_date'),
                    "topic": t.get('topic') or 'Sesión General',
                    "field": t.get('field'),
                    "status": status_att
                })

    total_sesiones = len(attendance_history)
    porcentaje_asistencia = round((total_presentes / total_sesiones * 100), 1) if total_sesiones > 0 else 0

    return render_template(
        'players/detail.html',
        player=player,
        payments=payments,
        total_pagado=total_pagado,
        total_pendiente=total_pendiente,
        attendance_history=attendance_history,
        total_sesiones=total_sesiones,
        porcentaje_asistencia=porcentaje_asistencia
    )