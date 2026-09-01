from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from bson.objectid import ObjectId
from utils.decorators import login_required, role_required
from datetime import datetime

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
@login_required
@role_required(['Administrador'])
def index():
    status_filter = request.args.get('status', '')
    concept_filter = request.args.get('concept', '')
    search_query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = {}

    # Filtro por estado
    if status_filter:
        query['status'] = status_filter

    # Filtro por concepto
    if concept_filter:
        query['concept'] = concept_filter

    # Búsqueda por nombre de jugador, número de recibo o cédula
    if search_query:
        query['$or'] = [
            {'player_name': {'$regex': search_query, '$options': 'i'}},
            {'receipt_number': {'$regex': search_query, '$options': 'i'}},
            {'identification_id': {'$regex': search_query, '$options': 'i'}}
        ]

    # Filtro seguro por rango de fechas
    date_query = {}
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            date_query['$gte'] = dt_from
        except ValueError:
            flash("Formato de fecha inicial inválido.", "warning")
            date_from = ""

    if date_to:
        try:
            dt_to = datetime.strptime(date_to + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            date_query['$lte'] = dt_to
        except ValueError:
            flash("Formato de fecha final inválido.", "warning")
            date_to = ""

    if date_query:
        query['payment_date'] = date_query

    payments = list(db.payments.find(query).sort('payment_date', -1)) if db is not None else []
    total_recaudado = sum(p.get('amount', 0.0) for p in payments if p.get('status') == 'Completado')

    return render_template(
        'payments/index.html',
        payments=payments,
        total_recaudado=total_recaudado,
        selected_status=status_filter,
        selected_concept=concept_filter,
        q=search_query,
        date_from=date_from,
        date_to=date_to
    )

@payments_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required(['Administrador'])
def create():
    players = list(db.players.find({"status": "Activo"}).sort('last_name', 1)) if db is not None else []

    if request.method == 'POST':
        player_id = request.form.get('player_id')
        concept = request.form.get('concept')
        amount = float(request.form.get('amount', 0))
        month_covered = request.form.get('month_covered', '')
        payment_method = request.form.get('payment_method', 'Efectivo')
        transaction_ref = request.form.get('transaction_ref', '').strip()
        status = request.form.get('status', 'Completado')
        notes = request.form.get('notes', '').strip()

        if not player_id or not concept or amount <= 0:
            flash("Selecciona un jugador, concepto y un monto válido.", "danger")
            return render_template('payments/create.html', players=players)

        player = db.players.find_one({"_id": ObjectId(player_id)})
        if not player:
            flash("Jugador no encontrado.", "danger")
            return redirect(url_for('payments.index'))

        # Generar correlativo de recibo (REC-00001)
        count_payments = db.payments.count_documents({}) + 1
        receipt_number = f"REC-{count_payments:05d}"

        new_payment = {
            "receipt_number": receipt_number,
            "player_id": ObjectId(player_id),
            "player_name": f"{player['last_name']} {player['first_name']}",
            "identification_id": player.get('identification_id', ''),
            "representative_name": player.get('representative', {}).get('full_name', ''),
            "concept": concept,
            "amount": amount,
            "month_covered": month_covered,
            "payment_method": payment_method,
            "transaction_ref": transaction_ref,
            "status": status,
            "notes": notes,
            "payment_date": datetime.utcnow()
        }

        db.payments.insert_one(new_payment)
        flash(f"Pago registrado con éxito. Comprobante: {receipt_number}", "success")
        return redirect(url_for('payments.index'))

    return render_template('payments/create.html', players=players)

@payments_bp.route('/receipt/<payment_id>')
@login_required
def receipt(payment_id):
    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        flash("Comprobante no encontrado.", "danger")
        return redirect(url_for('payments.index'))

    return render_template('payments/receipt.html', p=payment)

@payments_bp.route('/<payment_id>/mark-completed', methods=['POST'])
@login_required
@role_required(['Administrador'])
def mark_completed(payment_id):
    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        flash("Pago no encontrado.", "danger")
        return redirect(url_for('payments.index'))

    db.payments.update_one(
        {"_id": ObjectId(payment_id)},
        {"$set": {"status": "Completado", "payment_date": datetime.utcnow()}}
    )
    flash(f"El recibo {payment.get('receipt_number')} ha sido marcado como Completado.", "success")
    return redirect(url_for('payments.index'))