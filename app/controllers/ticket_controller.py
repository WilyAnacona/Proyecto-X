from flask import Blueprint, request, render_template, redirect, url_for, session, abort, flash
from app.models.ticket import Ticket, PriorityEnum, StatusEnum, TICKETS_DB, NOTIFICATIONS_DB, Notification
from app.models.user import RoleEnum, USERS_DB
from app.helpers.security import login_required, role_required

ticket_bp = Blueprint('ticket', __name__)

@ticket_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    role = session.get('user_role')
    if role == RoleEnum.COORDINADOR:
        return redirect(url_for('ticket.list_all_tickets'))
    elif role == RoleEnum.AGENTE:
        return redirect(url_for('ticket.agent_tickets'))
    return redirect(url_for('ticket.my_tickets'))

# --- Crear Solicitud (Solicitante) ---
@ticket_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required
@role_required(RoleEnum.SOLICITANTE)
def create_ticket():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title or not category or not description:
            flash("Todos los campos son obligatorios.", "error")
            return render_template('create_ticket.html')
            
        new_ticket = Ticket(
            title=title,
            description=description,
            category=category,
            owner_id=session['user_id']
        )
        TICKETS_DB[new_ticket.id] = new_ticket
        
        flash("Solicitud creada correctamente.", "success")
        return redirect(url_for('ticket.my_tickets'))
        
    return render_template('create_ticket.html')

# --- HU08: Búsqueda y listado del Solicitante ---
@ticket_bp.route('/my-tickets', methods=['GET'])
@login_required
@role_required(RoleEnum.SOLICITANTE)
def my_tickets():
    user_id = session['user_id']
    search_query = request.args.get('q', '').strip().lower()
    
    user_tickets = [t for t in TICKETS_DB.values() if t.owner_id == user_id]
    
    if search_query:
        user_tickets = [
            t for t in user_tickets 
            if search_query in t.title.lower() or search_query in t.description.lower()
        ]
        
    return render_template('my_tickets.html', tickets=user_tickets, search_query=search_query)

# --- HU05: Asignar agente (Coordinador) ---
@ticket_bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
@role_required(RoleEnum.COORDINADOR)
def assign_ticket(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    agent_id = request.form.get('agent_id', type=int)
    agent = next((u for u in USERS_DB.values() if u.id == agent_id and u.role == RoleEnum.AGENTE), None)
    
    if not agent or not agent.is_active:
        flash("Asignación inválida: El usuario no existe, no es agente o no está activo.", "error")
        return redirect(url_for('ticket.list_all_tickets'))
        
    ticket.assign_agent(agent.id, session['user_id'])
    
    NOTIFICATIONS_DB.append(Notification(
        user_id=agent.id,
        message=f"Se te ha asignado la solicitud #{ticket.id}: '{ticket.title}'"
    ))
    
    flash(f"Solicitud #{ticket.id} asignada a {agent.username}.", "success")
    return redirect(url_for('ticket.list_all_tickets'))

# Priorizar ticket (Coordinador)
@ticket_bp.route('/tickets/<int:ticket_id>/prioritize', methods=['POST'])
@login_required
@role_required(RoleEnum.COORDINADOR)
def prioritize_ticket(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    new_priority = request.form.get('priority')
    if new_priority in PriorityEnum.__members__.values():
        ticket.priority = PriorityEnum(new_priority)
        flash(f"Prioridad del ticket #{ticket.id} actualizada a {new_priority}.", "success")
        
    return redirect(url_for('ticket.list_all_tickets'))

# --- HU06: Comentarios de trabajo ---
@ticket_bp.route('/tickets/<int:ticket_id>/comments', methods=['POST'])
@login_required
def add_comment(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    comment_text = request.form.get('text', '').strip()
    if not comment_text:
        flash("El comentario no puede estar vacío.", "error")
        return redirect(url_for('ticket.get_ticket_detail', ticket_id=ticket.id))
        
    ticket.add_comment(session['user_id'], session['username'], comment_text)
    flash("Comentario agregado correctamente.", "success")
    return redirect(url_for('ticket.get_ticket_detail', ticket_id=ticket.id))

# --- HU07: Transición de estado (Agente) ---
@ticket_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
@role_required(RoleEnum.AGENTE)
def change_status(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
        
    new_status_str = request.form.get('status')
    try:
        new_status = StatusEnum(new_status_str)
        ticket.change_status(new_status, session['user_id'])
        flash(f"Estado de la solicitud #{ticket.id} cambiado a '{new_status.value}'.", "success")
    except ValueError as e:
        flash(str(e), "error")
        
    return redirect(url_for('ticket.get_ticket_detail', ticket_id=ticket.id))

# --- HU08: Confirmar o Reabrir (Solicitante) ---
@ticket_bp.route('/tickets/<int:ticket_id>/resolve-action', methods=['POST'])
@login_required
@role_required(RoleEnum.SOLICITANTE)
def resolve_action(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket or ticket.owner_id != session['user_id']:
        abort(403, description="No tiene permisos sobre esta solicitud.")
        
    action = request.form.get('action')
    reason = request.form.get('reason', '').strip()
    
    try:
        if action == 'confirm':
            ticket.change_status(StatusEnum.CERRADO, session['user_id'])
            flash("Solicitud confirmada y cerrada.", "success")
        elif action == 'reopen':
            if not reason:
                flash("Debe indicar el motivo de la reapertura.", "error")
                return redirect(url_for('ticket.get_ticket_detail', ticket_id=ticket.id))
            ticket.change_status(StatusEnum.REABIERTO, session['user_id'], reason=reason)
            flash("Solicitud reabierta.", "warning")
    except ValueError as e:
        flash(str(e), "error")
        
    return redirect(url_for('ticket.get_ticket_detail', ticket_id=ticket.id))

# Panel de Agentes
@ticket_bp.route('/agent/tickets', methods=['GET'])
@login_required
@role_required(RoleEnum.AGENTE)
def agent_tickets():
    agent_id = session['user_id']
    assigned_tickets = [t for t in TICKETS_DB.values() if t.assigned_agent_id == agent_id]
    user_notifications = [n for n in NOTIFICATIONS_DB if n.user_id == agent_id]
    return render_template('agent_tickets.html', tickets=assigned_tickets, notifications=user_notifications)

# Panel de Coordinador
@ticket_bp.route('/coordinator/tickets', methods=['GET'])
@login_required
@role_required(RoleEnum.COORDINADOR)
def list_all_tickets():
    tickets = list(TICKETS_DB.values())
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'asc')
    
    if sort_by == 'priority':
        priority_order = {PriorityEnum.ALTA: 3, PriorityEnum.MEDIA: 2, PriorityEnum.BAJA: 1}
        tickets.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=(order == 'desc'))
    elif sort_by == 'status':
        tickets.sort(key=lambda x: x.status.value)
    else:
        tickets.sort(key=lambda x: x.created_at, reverse=(order == 'desc'))

    active_agents = [u for u in USERS_DB.values() if u.role == RoleEnum.AGENTE and u.is_active]
    return render_template('coordinator_tickets.html', tickets=tickets, active_agents=active_agents)

# Detalle de Ticket
@ticket_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket_detail(ticket_id):
    ticket = TICKETS_DB.get(ticket_id)
    if not ticket:
        abort(404, description="Solicitud no encontrada.")
    return render_template('ticket_detail.html', ticket=ticket)