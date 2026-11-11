from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "campus_event_secret_key"
DATABASE = "events.db"


def get_connection():
  conn = sqlite3.connect(DATABASE)
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA foreign_keys = ON")
  return conn


def init_db():
  with get_connection() as conn:
    conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                venue TEXT NOT NULL,
                organizer TEXT,
                available_seats INTEGER NOT NULL
            )
        """)
    conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                student_email TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                registered_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                UNIQUE(student_email, event_id)
            )
        """)
    conn.commit()


@app.route("/")
def index():
  with get_connection() as conn:
    events = conn.execute(
        "SELECT * FROM events ORDER BY event_date ASC LIMIT 3"
    ).fetchall()
  return render_template("index.html", events=events)


@app.route("/events")
def events():
  search = request.args.get("search", "")
  with get_connection() as conn:
    if search:
      query = "SELECT * FROM events WHERE name LIKE ? OR description LIKE ? ORDER BY event_date ASC"
      events = conn.execute(query, (f"%{search}%", f"%{search}%")).fetchall()
    else:
      events = conn.execute(
          "SELECT * FROM events ORDER BY event_date ASC"
      ).fetchall()
  return render_template("events.html", events=events, search=search)


@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):
  with get_connection() as conn:
    event = conn.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()

  if not event:
    flash("Event not found.", "danger")
    return redirect(url_for("events"))

  if request.method == "POST":
    student_name = request.form["student_name"]
    student_email = request.form["student_email"]
    registered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
      with get_connection() as conn:
        conn.execute(
            """INSERT INTO registrations (student_name, student_email, event_id, registered_at)
                       VALUES (?, ?, ?, ?)""",
            (student_name, student_email, event_id, registered_at),
        )
        conn.commit()
      flash("Successfully registered for the event!", "success")
      return redirect(url_for("events"))
    except sqlite3.IntegrityError:
      flash(
          "You have already registered for this event using this email.",
          "warning",
      )
      return redirect(url_for("register", event_id=event_id))

  return render_template("register.html", event=event)


@app.route("/admin", methods=["GET", "POST"])
def admin():
  if request.method == "POST":
    action = request.form.get("action")
    if action == "add":
      name = request.form["name"]
      description = request.form["description"]
      event_date = request.form["event_date"]
      venue = request.form["venue"]
      organizer = request.form["organizer"]
      available_seats = int(request.form["available_seats"])

      with get_connection() as conn:
        conn.execute(
            """INSERT INTO events (name, description, event_date, venue, organizer, available_seats)
                       VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name,
                description,
                event_date,
                venue,
                organizer,
                available_seats,
            ),
        )
        conn.commit()
      flash("Event added successfully!", "success")

    elif action == "delete":
      event_id = request.form["event_id"]
      with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
      flash("Event deleted successfully!", "success")

    elif action == "update":
      event_id = request.form["event_id"]
      name = request.form["name"]
      description = request.form["description"]
      event_date = request.form["event_date"]
      venue = request.form["venue"]
      organizer = request.form["organizer"]
      available_seats = int(request.form["available_seats"])

      with get_connection() as conn:
        conn.execute(
            """UPDATE events SET name = ?, description = ?, event_date = ?, venue = ?, organizer = ?, available_seats = ?
                       WHERE id = ?""",
            (
                name,
                description,
                event_date,
                venue,
                organizer,
                available_seats,
                event_id,
            ),
        )
        conn.commit()
      flash("Event updated successfully!", "success")

    return redirect(url_for("admin"))

  with get_connection() as conn:
    events = conn.execute("SELECT * FROM events ORDER BY event_date ASC").fetchall()
  return render_template("admin.html", events=events)


@app.route("/dashboard")
def dashboard():
  today = datetime.now().strftime("%Y-%m-%d")
  with get_connection() as conn:
    total_events = conn.execute(
        "SELECT COUNT(*) FROM events"
    ).fetchone()[0]
    total_registrations = conn.execute(
        "SELECT COUNT(*) FROM registrations"
    ).fetchone()[0]
    upcoming_events = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_date >= ?", (today,)
    ).fetchone()[0]
    completed_events = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_date < ?", (today,)
    ).fetchone()[0]

    event_regs = conn.execute("""
            SELECT e.name, COUNT(r.id) as reg_count 
            FROM events e 
            LEFT JOIN registrations r ON e.id = r.event_id 
            GROUP BY e.id
        """).fetchall()

  return render_template(
      "dashboard.html",
      total_events=total_events,
      total_registrations=total_registrations,
      upcoming_events=upcoming_events,
      completed_events=completed_events,
      event_regs=event_regs,
  )


if __name__ == "__main__":
  init_db()
  app.run(debug=True)