from flask import Blueprint, request, render_template, redirect, url_for, session, abort, flash
from app.models.ticket import Ticket, PriorityEnum, StatusEnum, TICKETS_DB
from app.models.user import RoleEnum
from app.helpers.security import login_required, role_required

ticket_bp = Blueprint('ticket', __name__)

@ticket_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    if session.get('user_role') == RoleEnum.COORDINADOR:
        return redirect(url_for('ticket.list_all_tickets'))
    return redirect(url_for('ticket.my_tickets'))

@ticket_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required
@role_required(RoleEnum.SOLICITANTE)
def create_ticket():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        
        if not title or not description or not category:
            flash("Título, descripción y categoría son campos obligatorios.", "error")
            return render_template('create_ticket.html'), 400
            
        ticket = Ticket(
            title=title,
            description=description,
            category=category,
            owner_id=session['user_id']
        )
        TICKETS_DB[ticket.id] = ticket
        flash(f"Solicitud #{ticket.id} creada con éxito.", "success")
        return redirect(url_for('ticket.my_tickets'))
        
    return render_template('create_ticket.html')

@ticket_bp.route('/my-tickets', methods=['GET'])
@login_required
@role_required(RoleEnum.SOLICITANTE)
def my_tickets():
    user_id = session['user_id']
    user_tickets = [t for t in TICKETS_DB.values() if t.owner_id == user_id]
    return render_template('my_tickets.html', tickets=user_tickets)

@ticket_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket_detail(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    if session['user_role'] == RoleEnum.SOLICITANTE and ticket.owner_id != session['user_id']:
        abort(403, description="No tiene permisos para ver esta solicitud.")
        
    return render_template('ticket_detail.html', ticket=ticket)

@ticket_bp.route('/coordinator/tickets', methods=['GET'])
@login_required
@role_required(RoleEnum.COORDINADOR)
def list_all_tickets():
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'asc')
    
    tickets = list(TICKETS_DB.values())
    priority_order = {PriorityEnum.BAJA: 1, PriorityEnum.MEDIA: 2, PriorityEnum.ALTA: 3}
    
    if sort_by == 'priority':
        tickets.sort(key=lambda x: priority_order[x.priority], reverse=(order == 'desc'))
    elif sort_by == 'status':
        tickets.sort(key=lambda x: x.status, reverse=(order == 'desc'))
    else:
        tickets.sort(key=lambda x: x.created_at, reverse=(order == 'desc'))
        
    return render_template('coordinator_tickets.html', tickets=tickets)

@ticket_bp.route('/tickets/<int:ticket_id>/prioritize', methods=['POST'])
@login_required
@role_required(RoleEnum.COORDINADOR)
def prioritize_ticket(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    new_priority = request.form.get('priority')
    
    if new_priority not in [p.value for p in PriorityEnum]:
        flash("Prioridad no válida.", "error")
        return redirect(url_for('ticket.list_all_tickets'))
        
    ticket.update_priority(PriorityEnum(new_priority), session['user_id'])
    flash(f"Prioridad del ticket #{ticket.id} actualizada.", "success")
    return redirect(url_for('ticket.list_all_tickets'))
