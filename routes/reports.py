from flask import Blueprint, render_template, Response, flash, redirect, url_for
from database import db
from utils.decorators import login_required, role_required
import csv
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
@role_required(['Administrador'])
def index():
    # 1. Total recaudado por concepto (Completados)
    pipeline_concept = [
        {"$match": {"status": "Completado"}},
        {"$group": {"_id": "$concept", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]
    payments_by_concept = list(db.payments.aggregate(pipeline_concept)) if db is not None else []

    # 2. Distribución de alumnos por categoría
    categories = list(db.categories.find()) if db is not None else []
    cat_counts = []
    for cat in categories:
        count = db.players.count_documents({"category_id": cat['_id'], "status": "Activo"}) if db is not None else 0
        cat_counts.append({"name": cat['name'], "count": count})

    # Alumnos sin categoría asignada
    sin_cat_count = db.players.count_documents({"category_id": None, "status": "Activo"}) if db is not None else 0
    if sin_cat_count > 0:
        cat_counts.append({"name": "Sin Asignar", "count": sin_cat_count})

    # 3. Métricas consolidadas
    total_ingresos = sum(item['total'] for item in payments_by_concept)
    total_cobros_pendientes = db.payments.count_documents({"status": "Pendiente"}) if db is not None else 0
    total_entrenamientos = db.trainings.count_documents({}) if db is not None else 0

    return render_template(
        'reports/index.html',
        payments_by_concept=payments_by_concept,
        cat_counts=cat_counts,
        total_ingresos=total_ingresos,
        total_cobros_pendientes=total_cobros_pendientes,
        total_entrenamientos=total_entrenamientos
    )

@reports_bp.route('/export/payments-csv')
@login_required
@role_required(['Administrador'])
def export_payments_csv():
    payments = list(db.payments.find().sort('payment_date', -1)) if db is not None else []

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Cabecera CSV
    writer.writerow(['Nro Recibo', 'Fecha', 'Jugador', 'Cedula', 'Representante', 'Concepto', 'Mes', 'Monto USD', 'Metodo', 'Estado'])

    for p in payments:
        fecha_str = p['payment_date'].strftime('%Y-%m-%d %H:%M') if p.get('payment_date') else ''
        writer.writerow([
            p.get('receipt_number', ''),
            fecha_str,
            p.get('player_name', ''),
            p.get('identification_id', ''),
            p.get('representative_name', ''),
            p.get('concept', ''),
            p.get('month_covered', ''),
            f"{p.get('amount', 0.0):.2f}",
            p.get('payment_method', ''),
            p.get('status', '')
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_ingresos_escuela_fc.csv"}
    )