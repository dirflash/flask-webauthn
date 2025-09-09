
from flask import Blueprint, render_template, request
from models import User, db

dbm = Blueprint("dbm", __name__, url_prefix="/dbm", template_folder="templates")


# DB Management Portal Route
@dbm.route("/", methods=["GET", "POST"])
def dbm_portal():
    result = None
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        file = request.form.get("file")
        if action == "view_users":
            users = User.query.all()
            result = "\n".join([
                f"{user.id}: {user.username} ({user.email})" for user in users
            ]) or "No users found."
        elif action == "add_user" and username:
            # Add user logic (simplified, add more fields as needed)
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
            result = f"User '{username}' added."
        elif action == "delete_user" and username:
            user = User.query.filter_by(username=username).first()
            if user:
                db.session.delete(user)
                db.session.commit()
                result = f"User '{username}' deleted."
            else:
                result = f"User '{username}' not found."
        elif action == "backup_db":
            # Placeholder for backup logic
            result = "Database backup completed (not implemented)."
        elif action == "restore_db" and file:
            # Placeholder for restore logic
            result = f"Database restored from '{file}' (not implemented)."
        else:
            result = "Invalid action or missing parameters."
    return render_template("dbm_portal.html", result=result)


@dbm.route("/health")
def health_check():
    """
    Health check endpoint to verify that the application is running.
    Returns a simple JSON response indicating the status.
    """
    return {"status": "ok"}


@dbm.route("/reset-database")
def reset_database():
    """
    Endpoint to reset the database by dropping all tables and recreating them.
    This is useful for development and testing purposes.
    """
    User.query.delete()
    db.session.commit()
    return {"status": "database reset successfully"}


@dbm.route("/users")
def list_users():
    """
    Endpoint to list all users in the database.
    Returns a JSON response with user details.
    """
    users = User.query.all()
    user_list = [
        {
            "id": user.id,
            "uid": user.uid,
            "username": user.username,
            "name": user.name,
            "email": user.email,
        }
        for user in users
    ]
    return {"users": user_list}