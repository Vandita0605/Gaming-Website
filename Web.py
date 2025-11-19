from flask import Flask, render_template, request
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

DB_FILE = "bookings.db"

# Create bookings table if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return render_template("1vX.html")

@app.route("/book", methods=["POST"])
def book():
    try:
        delete_expired_bookings()
        game_type = request.form["game_type"]
        date_str = request.form["date"]
        time_str = request.form["time"]
        duration = int(request.form["duration"])
        message = request.form.get("message", "")

        # Parse and validate datetime
        booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.now()

        # Constraint 1: No booking for past date/time
        if booking_datetime < now:
            return "❌ You cannot book a past date or time.", 400

        # Constraint 2: Only allow bookings within next 7 days
        if booking_datetime > now + timedelta(days=7):
            return "❌ You can only book within 7 days from today.", 400

        # Constraint 3: Minimum duration of 1 hour
        if duration < 1:
            return "❌ Minimum booking duration is 1 hour.", 400

        # Constraint 4: Only allow bookings on the hour (minutes = 00)
        # Constraint 4: Allow only 30-minute intervals (00 or 30)
        if booking_datetime.minute not in (0, 30):
            return "❌ Booking time must be in 30-minute intervals (e.g., 10:00, 10:30, 11:00, 11:30).", 400


        # Constraint 5: Only between 10:00 AM and 11:00 PM
        if booking_datetime.hour < 10 or booking_datetime.hour >= 23:
            return "❌ Booking allowed only between 10:00 AM and 11:00 PM.", 400

        # Constraint 6: Only 5 bookings per game type at the same time
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM bookings 
            WHERE game_type=? AND date=? AND time=?
        """, (game_type, date_str, time_str))
        count = c.fetchone()[0]

        if count >= 5:
            conn.close()
            return "❌ All 5 slots for this game and time are already booked.", 400

        # If all constraints pass — insert booking
        c.execute("""
            INSERT INTO bookings (game_type, date, time, duration, message)
            VALUES (?, ?, ?, ?, ?)
        """, (game_type, date_str, time_str, duration, message))
        conn.commit()
        conn.close()

        return "✅ Booking successful!"

    except Exception as e:
        print("Error:", e)
        return "⚠️ Something went wrong. Please try again.", 500

def delete_expired_bookings():
    now = datetime.now()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Fetch all bookings
    c.execute("SELECT id, date, time FROM bookings")
    rows = c.fetchall()

    for booking_id, date_str, time_str in rows:
        try:
            booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # If booking is in the past → delete it
            if booking_datetime < now:
                c.execute("DELETE FROM bookings WHERE id=?", (booking_id,))

        except Exception as e:
            print("Error deleting expired:", e)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        init_db()
    delete_expired_bookings()

    app.run(debug=True)