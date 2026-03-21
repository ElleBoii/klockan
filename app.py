from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db,
    User,
    Swimmer,
    KlockanSession,
    KlockanResult,
    STROKES,
    EQUIPMENT_OPTIONS,
    POOL_LENGTHS,
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///klockan.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "change-this-to-a-random-secret-key"

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def pool_length_sort_value(pool_length):
    order = {
        "25 m": 25,
        "25 yards": 25.5,
        "50 m": 50
    }
    return order.get(pool_length, 999)


def get_pending_klockan():
    return session.get("pending_klockan", {})


def save_pending_klockan(data):
    session["pending_klockan"] = data


def clear_pending_klockan():
    session.pop("pending_klockan", None)


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            message = "Invalid username or password."

    return render_template("login.html", message=message)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/")
def index():
    selected_swimmer = request.args.get("swimmer", "")
    selected_stroke = request.args.get("stroke", "")
    selected_equipment = request.args.get("equipment", "")
    selected_pool_length = request.args.get("pool_length", "")
    sort_by = request.args.get("sort_by", "")
    sort_order = request.args.get("sort_order", "asc")
    filter_applied = request.args.get("filter_applied", "0") == "1"
    if filter_applied:
        show_only_active = request.args.get("show_only_active", "0") == "1"
    else:
        show_only_active = True

    swimmer_query = Swimmer.query
    if show_only_active:
        swimmer_query = swimmer_query.filter_by(is_active=True)
    swimmers = swimmer_query.order_by(Swimmer.name).all()
    results = KlockanResult.query.join(Swimmer).join(KlockanSession).all()

    filtered_results = results

    if show_only_active:
        filtered_results = [r for r in filtered_results if r.swimmer.is_active]

    if selected_swimmer:
        filtered_results = [
            result for result in filtered_results
            if result.swimmer.name == selected_swimmer
        ]

    if selected_stroke:
        filtered_results = [
            result for result in filtered_results
            if result.stroke == selected_stroke
        ]

    if selected_equipment:
        filtered_results = [
            result for result in filtered_results
            if result.equipment == selected_equipment
        ]

    if selected_pool_length:
        filtered_results = [
            result for result in filtered_results
            if result.session.pool_length == selected_pool_length
        ]

    reverse_sort = sort_order == "desc"

    if sort_by == "stroke":
        filtered_results = sorted(filtered_results, key=lambda x: x.stroke, reverse=reverse_sort)
    elif sort_by == "date":
        filtered_results = sorted(filtered_results, key=lambda x: x.session.date, reverse=reverse_sort)
    elif sort_by == "pool_length":
        filtered_results = sorted(
            filtered_results,
            key=lambda x: pool_length_sort_value(x.session.pool_length),
            reverse=reverse_sort
        )
    elif sort_by == "equipment":
        filtered_results = sorted(filtered_results, key=lambda x: x.equipment, reverse=reverse_sort)
    elif sort_by == "result":
        filtered_results = sorted(filtered_results, key=lambda x: x.failed_start_time, reverse=reverse_sort)

    return render_template(
        "index.html",
        swimmers=swimmers,
        strokes=STROKES,
        equipment_options=EQUIPMENT_OPTIONS,
        pool_lengths=POOL_LENGTHS,
        results=filtered_results,
        selected_swimmer=selected_swimmer,
        selected_stroke=selected_stroke,
        selected_equipment=selected_equipment,
        selected_pool_length=selected_pool_length,
        sort_by=sort_by,
        sort_order=sort_order,
        show_only_active=show_only_active,
    )


@app.route("/add-swimmers")
@login_required
def add_swimmers():
    pending_swimmers = session.get("pending_swimmers", [])
    message = session.pop("swimmer_message", "")
    return render_template(
        "add_swimmers.html",
        pending_swimmers=pending_swimmers,
        message=message
    )


@app.route("/add-swimmers/add", methods=["POST"])
@login_required
def add_swimmer_to_list():
    name = request.form.get("name", "").strip()
    pending_swimmers = session.get("pending_swimmers", [])

    if not name:
        session["swimmer_message"] = "Please enter a swimmer name."
        return redirect(url_for("add_swimmers"))

    existing_lower = [n.lower() for n in pending_swimmers]
    if name.lower() in existing_lower:
        session["swimmer_message"] = f'"{name}" is already in the list.'
        return redirect(url_for("add_swimmers"))

    pending_swimmers.append(name)
    session["pending_swimmers"] = pending_swimmers
    return redirect(url_for("add_swimmers"))


@app.route("/add-swimmers/remove", methods=["POST"])
@login_required
def remove_swimmer_from_list():
    name_to_remove = request.form.get("name", "").strip()
    pending_swimmers = session.get("pending_swimmers", [])
    pending_swimmers = [name for name in pending_swimmers if name != name_to_remove]
    session["pending_swimmers"] = pending_swimmers
    return redirect(url_for("add_swimmers"))


@app.route("/confirm-swimmers")
@login_required
def confirm_swimmers():
    pending_swimmers = session.get("pending_swimmers", [])

    if not pending_swimmers:
        return redirect(url_for("add_swimmers"))

    return render_template("confirm_swimmers.html", pending_swimmers=pending_swimmers)


@app.route("/confirm-swimmers/save", methods=["POST"])
@login_required
def save_confirmed_swimmers():
    pending_swimmers = session.get("pending_swimmers", [])

    if not pending_swimmers:
        return redirect(url_for("add_swimmers"))

    added_names = []
    skipped_names = []

    for name in pending_swimmers:
        existing_swimmer = Swimmer.query.filter_by(name=name).first()
        if existing_swimmer:
            skipped_names.append(name)
        else:
            db.session.add(Swimmer(name=name, is_active=True))
            added_names.append(name)

    db.session.commit()
    session.pop("pending_swimmers", None)

    if added_names and skipped_names:
        session["swimmer_message"] = (
            f"Added: {', '.join(added_names)}. "
            f"Skipped existing: {', '.join(skipped_names)}."
        )
    elif added_names:
        session["swimmer_message"] = f"Added: {', '.join(added_names)}."
    else:
        session["swimmer_message"] = "No swimmers were added because they already exist."

    return redirect(url_for("add_swimmers"))


@app.route("/add-klockan-session", methods=["GET", "POST"])
@login_required
def add_klockan_session():
    message = session.pop("klockan_message", "")

    if request.method == "POST":
        date = request.form.get("date", "").strip()
        pool_length = request.form.get("pool_length", "").strip()
        max_rounds = request.form.get("max_rounds", "").strip()

        if not date or not pool_length or not max_rounds:
            message = "Please fill in all fields."
        else:
            try:
                max_rounds = int(max_rounds)
            except ValueError:
                message = "Max rounds must be an integer."

            if not message and max_rounds not in [1, 2, 3, 4]:
                message = "Max rounds must be between 1 and 4."

            if not message:
                pending = {
                    "date": date,
                    "pool_length": pool_length,
                    "max_rounds": max_rounds,
                    "results": []
                }
                save_pending_klockan(pending)
                return redirect(url_for("add_klockan_round", round_number=1))

    return render_template(
        "add_klockan_session.html",
        pool_lengths=POOL_LENGTHS,
        message=message
    )


@app.route("/add-klockan-round/<int:round_number>")
@login_required
def add_klockan_round(round_number):
    show_only_active = request.args.get("show_only_active", "1") == "1"
    
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    max_rounds = pending["max_rounds"]
    if round_number < 1 or round_number > max_rounds:
        return redirect(url_for("confirm_klockan_session"))

    swimmer_query = Swimmer.query
    if show_only_active:
        swimmer_query = swimmer_query.filter_by(is_active=True)
    swimmers = swimmer_query.order_by(Swimmer.name).all()
    message = session.pop("klockan_message", "")

    swimmer_lookup = {swimmer.id: swimmer.name for swimmer in swimmers}

    current_round_results = []
    for result in pending["results"]:
        if result["round_number"] == round_number:
            current_round_results.append({
                "swimmer_id": result["swimmer_id"],
                "swimmer_name": swimmer_lookup.get(result["swimmer_id"], "Unknown"),
                "stroke": result["stroke"],
                "equipment": result["equipment"],
                "failed_start_time": result["failed_start_time"]
            })

    return render_template(
        "add_klockan_round.html",
        round_number=round_number,
        max_rounds=max_rounds,
        swimmers=swimmers,
        strokes=STROKES,
        equipment_options=EQUIPMENT_OPTIONS,
        session_info=pending,
        current_round_results=current_round_results,
        message=message,
        show_only_active=show_only_active,
    )


@app.route("/add-klockan-round/<int:round_number>/add", methods=["POST"])
@login_required
def add_klockan_round_result(round_number):
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    swimmer_id = request.form.get("swimmer_id", "").strip()
    stroke = request.form.get("stroke", "").strip()
    equipment = request.form.get("equipment", "").strip()
    failed_start_time = request.form.get("failed_start_time", "").strip()

    if not swimmer_id or not stroke or not equipment or not failed_start_time:
        session["klockan_message"] = "Please fill in all fields."
        return redirect(url_for("add_klockan_round", round_number=round_number))

    try:
        swimmer_id = int(swimmer_id)
        failed_start_time = int(failed_start_time)
    except ValueError:
        session["klockan_message"] = "Failed start time must be an integer."
        return redirect(url_for("add_klockan_round", round_number=round_number))

    round_results = [
        result for result in pending["results"]
        if result["round_number"] == round_number
    ]

    if any(result["swimmer_id"] == swimmer_id for result in round_results):
        session["klockan_message"] = "That swimmer has already been added in this round."
        return redirect(url_for("add_klockan_round", round_number=round_number))

    pending["results"].append({
        "round_number": round_number,
        "swimmer_id": swimmer_id,
        "stroke": stroke,
        "equipment": equipment,
        "failed_start_time": failed_start_time
    })
    save_pending_klockan(pending)

    return redirect(url_for("add_klockan_round", round_number=round_number))


@app.route("/add-klockan-round/<int:round_number>/remove", methods=["POST"])
@login_required
def remove_klockan_round_result(round_number):
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    swimmer_id = request.form.get("swimmer_id", "").strip()

    try:
        swimmer_id = int(swimmer_id)
    except ValueError:
        return redirect(url_for("add_klockan_round", round_number=round_number))

    pending["results"] = [
        result for result in pending["results"]
        if not (result["round_number"] == round_number and result["swimmer_id"] == swimmer_id)
    ]

    save_pending_klockan(pending)
    return redirect(url_for("add_klockan_round", round_number=round_number))


@app.route("/add-klockan-round/<int:round_number>/next", methods=["POST"])
@login_required
def next_klockan_round(round_number):
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    if round_number < pending["max_rounds"]:
        return redirect(url_for("add_klockan_round", round_number=round_number + 1))

    return redirect(url_for("confirm_klockan_session"))


@app.route("/confirm-klockan-session")
@login_required
def confirm_klockan_session():
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    swimmers = {swimmer.id: swimmer.name for swimmer in Swimmer.query.all()}

    results_by_round = {}
    for round_number in range(1, pending["max_rounds"] + 1):
        results_by_round[round_number] = []

    for result in pending["results"]:
        results_by_round[result["round_number"]].append({
            "swimmer_name": swimmers.get(result["swimmer_id"], "Unknown"),
            "stroke": result["stroke"],
            "equipment": result["equipment"],
            "failed_start_time": result["failed_start_time"],
            "swimmer_id": result["swimmer_id"]
        })

    return render_template(
        "confirm_klockan_session.html",
        session_info=pending,
        results_by_round=results_by_round
    )


@app.route("/manage-swimmers")
@login_required
def manage_swimmers():
    swimmers = Swimmer.query.order_by(Swimmer.name).all()
    message = session.pop("manage_swimmer_message", "")
    return render_template("manage_swimmers.html", swimmers=swimmers, message=message)


@app.route("/manage-swimmers/toggle", methods=["POST"])
@login_required
def toggle_swimmer_active():
    swimmer_id = request.form.get("swimmer_id", "").strip()

    try:
        swimmer_id = int(swimmer_id)
    except ValueError:
        return redirect(url_for("manage_swimmers"))

    swimmer = Swimmer.query.get(swimmer_id)
    if swimmer:
        swimmer.is_active = not swimmer.is_active
        db.session.commit()
        status = "active" if swimmer.is_active else "inactive"
        session["manage_swimmer_message"] = f'"{swimmer.name}" is now {status}.'

    return redirect(url_for("manage_swimmers"))


@app.route("/manage-sessions")
@login_required
def manage_sessions():
    sessions = KlockanSession.query.order_by(KlockanSession.date.desc()).all()
    message = session.pop("manage_session_message", "")
    return render_template("manage_sessions.html", sessions=sessions, message=message)


@app.route("/manage-sessions/confirm-delete/<int:session_id>")
@login_required
def confirm_delete_session(session_id):
    klockan_session = KlockanSession.query.get(session_id)
    if not klockan_session:
        return redirect(url_for("manage_sessions"))

    results_by_round = {}
    for i in range(1, klockan_session.max_rounds + 1):
        results_by_round[i] = []
    for result in klockan_session.results:
        results_by_round[result.round_number].append(result)

    return render_template(
        "confirm_delete_session.html",
        klockan_session=klockan_session,
        results_by_round=results_by_round
    )


@app.route("/manage-sessions/delete", methods=["POST"])
@login_required
def delete_session():
    session_id = request.form.get("session_id", "").strip()

    try:
        session_id = int(session_id)
    except ValueError:
        return redirect(url_for("manage_sessions"))

    klockan_session = KlockanSession.query.get(session_id)
    if klockan_session:
        label = f"{klockan_session.date} — {klockan_session.pool_length}"
        db.session.delete(klockan_session)
        db.session.commit()
        session["manage_session_message"] = f'Session "{label}" and all its results have been deleted.'

    return redirect(url_for("manage_sessions"))


@app.route("/manage-sessions/edit/<int:session_id>")
@login_required
def edit_session(session_id):
    klockan_session = KlockanSession.query.get(session_id)
    if not klockan_session:
        return redirect(url_for("manage_sessions"))

    swimmers = Swimmer.query.order_by(Swimmer.name).all()
    message = session.pop("edit_session_message", "")
    error = session.pop("edit_session_error", "")

    results_by_round = {}
    for i in range(1, klockan_session.max_rounds + 1):
        results_by_round[i] = []
    for result in klockan_session.results:
        results_by_round[result.round_number].append(result)

    return render_template(
        "edit_session.html",
        klockan_session=klockan_session,
        results_by_round=results_by_round,
        swimmers=swimmers,
        strokes=STROKES,
        equipment_options=EQUIPMENT_OPTIONS,
        pool_lengths=POOL_LENGTHS,
        message=message,
        error=error
    )


@app.route("/manage-sessions/<int:session_id>/save-info", methods=["POST"])
@login_required
def save_session_info(session_id):
    klockan_session = KlockanSession.query.get(session_id)
    if not klockan_session:
        return redirect(url_for("manage_sessions"))

    date = request.form.get("date", "").strip()
    pool_length = request.form.get("pool_length", "").strip()

    if not date or not pool_length:
        session["edit_session_error"] = "Please fill in all fields."
        return redirect(url_for("edit_session", session_id=session_id))

    klockan_session.date = date
    klockan_session.pool_length = pool_length
    db.session.commit()
    session["edit_session_message"] = "Session info updated."
    return redirect(url_for("edit_session", session_id=session_id))


@app.route("/manage-sessions/<int:session_id>/delete-result", methods=["POST"])
@login_required
def delete_session_result(session_id):
    result_id = request.form.get("result_id", "").strip()

    try:
        result_id = int(result_id)
    except ValueError:
        return redirect(url_for("edit_session", session_id=session_id))

    result = KlockanResult.query.get(result_id)
    if result and result.session_id == session_id:
        db.session.delete(result)
        db.session.commit()
        session["edit_session_message"] = "Result deleted."

    return redirect(url_for("edit_session", session_id=session_id))


@app.route("/manage-sessions/<int:session_id>/add-result", methods=["POST"])
@login_required
def add_session_result(session_id):
    klockan_session = KlockanSession.query.get(session_id)
    if not klockan_session:
        return redirect(url_for("manage_sessions"))

    swimmer_id = request.form.get("swimmer_id", "").strip()
    round_number = request.form.get("round_number", "").strip()
    stroke = request.form.get("stroke", "").strip()
    equipment = request.form.get("equipment", "").strip()
    failed_start_time = request.form.get("failed_start_time", "").strip()

    if not swimmer_id or not round_number or not stroke or not equipment or not failed_start_time:
        session["edit_session_error"] = "Please fill in all fields."
        return redirect(url_for("edit_session", session_id=session_id))

    try:
        swimmer_id = int(swimmer_id)
        round_number = int(round_number)
        failed_start_time = int(failed_start_time)
    except ValueError:
        session["edit_session_error"] = "Invalid input."
        return redirect(url_for("edit_session", session_id=session_id))

    if round_number < 1 or round_number > klockan_session.max_rounds:
        session["edit_session_error"] = f"Round must be between 1 and {klockan_session.max_rounds}."
        return redirect(url_for("edit_session", session_id=session_id))

    existing = KlockanResult.query.filter_by(
        session_id=session_id,
        round_number=round_number,
        swimmer_id=swimmer_id
    ).first()
    if existing:
        session["edit_session_error"] = "That swimmer already has a result in that round."
        return redirect(url_for("edit_session", session_id=session_id))

    db.session.add(KlockanResult(
        session_id=session_id,
        round_number=round_number,
        swimmer_id=swimmer_id,
        stroke=stroke,
        equipment=equipment,
        failed_start_time=failed_start_time
    ))
    db.session.commit()
    session["edit_session_message"] = "Result added."
    return redirect(url_for("edit_session", session_id=session_id))


@app.route("/confirm-klockan-session/save", methods=["POST"])
@login_required
def save_klockan_session():
    pending = get_pending_klockan()

    if not pending:
        return redirect(url_for("add_klockan_session"))

    new_session = KlockanSession(
        date=pending["date"],
        pool_length=pending["pool_length"],
        max_rounds=pending["max_rounds"]
    )
    db.session.add(new_session)
    db.session.commit()

    for result in pending["results"]:
        db.session.add(KlockanResult(
            session_id=new_session.id,
            round_number=result["round_number"],
            swimmer_id=result["swimmer_id"],
            stroke=result["stroke"],
            equipment=result["equipment"],
            failed_start_time=result["failed_start_time"]
        ))

    db.session.commit()
    clear_pending_klockan()
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)