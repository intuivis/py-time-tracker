import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


# =========================================================
# Configuration
# =========================================================

TASKS_FILE = Path("data/tasks.json")
TIME_ENTRIES_FILE = Path("data/time_entries.json")


# =========================================================
# Data Storage
# =========================================================

def load_json(filename, default):
    """Load JSON data from a file."""
    if not filename.exists():
        return default

    try:
        with filename.open("r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError:
        print(f"\nError: {filename} contains invalid JSON.")
        print("Starting with empty data.")
        return default

    except OSError as error:
        print(f"\nError reading {filename}: {error}")
        return default


def save_json(filename, data):
    """Save data to a JSON file."""
    try:
        with filename.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    except OSError as error:
        print(f"\nError saving {filename}: {error}")


def load_tasks():
    return load_json(TASKS_FILE, [])


def save_tasks(tasks):
    save_json(TASKS_FILE, tasks)


def load_time_entries():
    return load_json(TIME_ENTRIES_FILE, [])


def save_time_entries(entries):
    save_json(TIME_ENTRIES_FILE, entries)


# =========================================================
# Utility Functions
# =========================================================

def current_time():
    """Return the current time as an ISO-formatted UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def format_duration(seconds):
    """Convert seconds into a friendly duration."""
    seconds = int(seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def get_local_datetime(timestamp):
    """Convert an ISO timestamp to the system's local timezone."""
    return datetime.fromisoformat(timestamp).astimezone()


def get_week_start(date_value):
    """Return the Sunday that starts the calendar week containing date_value."""
    return date_value - timedelta(days=(date_value.weekday() + 1) % 7)


def get_entry_segments(entry):
    """
    Return (local_date, seconds) segments for an entry, splitting time at
    local midnight so daily reports remain clean.
    """
    start = get_local_datetime(entry["start_time"])

    if entry["end_time"] is None:
        end = datetime.now(timezone.utc).astimezone()
    else:
        end = get_local_datetime(entry["end_time"])

    if end <= start:
        return []

    segments = []
    cursor = start

    while cursor.date() < end.date():
        next_midnight = datetime.combine(
            cursor.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=cursor.tzinfo,
        )
        seconds = (next_midnight - cursor).total_seconds()
        segments.append((cursor.date(), seconds))
        cursor = next_midnight

    segments.append((cursor.date(), (end - cursor).total_seconds()))
    return segments


def get_report_weeks(entries):
    """Return sorted Sunday week-start dates containing recorded time."""
    weeks = set()

    for entry in entries:
        for local_date, seconds in get_entry_segments(entry):
            if seconds > 0:
                weeks.add(get_week_start(local_date))

    return sorted(weeks)


def format_report_duration(seconds):
    """Format report durations as zero-padded HH:MM for vertical alignment."""
    total_minutes = int(seconds // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def get_next_task_id(tasks):
    """Return the next available task ID."""
    if not tasks:
        return 1

    return max(task["id"] for task in tasks) + 1


def find_task(tasks, task_id):
    """Find an activity by ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task

    return None


def get_running_entry(entries):
    """Return the currently running time entry, if there is one."""
    for entry in entries:
        if entry["end_time"] is None:
            return entry

    return None


def pause():
    """Wait for the user before returning to the menu."""
    input("\n[Enter] Return to Menu")


def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


# =========================================================
# Activity Management
# =========================================================

def list_tasks():
    """Display all activities."""
    tasks = load_tasks()
    entries = load_time_entries()

    clear_screen()

    print("=" * 50)
    print("                 ACTIVITIES")
    print("=" * 50)

    if not tasks:
        print("\nNo activities have been added yet.")
        return

    running_entry = get_running_entry(entries)

    print()

    for task in tasks:
        status = ""

        if running_entry and running_entry["task_id"] == task["id"]:
            status = "  <TRACKING>"

        print(f"  {task['id']}. {task['name']}{status}")

    print()


def add_task():
    """Prompt the user to add a new activity."""
    clear_screen()

    print("=" * 50)
    print("                 ADD ACTIVITY")
    print("=" * 50)

    name = input("\nEnter the activity name: ").strip()

    if not name:
        print("\nActivity name cannot be empty.")
        pause()
        return

    tasks = load_tasks()

    # Prevent duplicate activity names.
    for task in tasks:
        if task["name"].lower() == name.lower():
            print(f"\nAn activity named '{task['name']}' already exists.")
            pause()
            return

    new_task = {
        "id": get_next_task_id(tasks),
        "name": name
    }

    tasks.append(new_task)
    save_tasks(tasks)

    print(f"\nActivity '{name}' was added successfully.")

    pause()


def edit_task():
    """Prompt the user to edit an existing activity."""
    clear_screen()

    print("=" * 50)
    print("                 EDIT ACTIVITY")
    print("=" * 50)

    tasks = load_tasks()

    if not tasks:
        print("\nNo activities have been added yet.")
        pause()
        return

    # Display activities.
    print()

    for task in tasks:
        print(f"  {task['id']}. {task['name']}")

    print()

    try:
        task_id = int(input("Enter the ID of the activity to edit: "))
    except ValueError:
        print("\nPlease enter a valid number.")
        pause()
        return

    task = find_task(tasks, task_id)

    if task is None:
        print(f"\nActivity {task_id} does not exist.")
        pause()
        return

    print(f"\nCurrent name: {task['name']}")

    new_name = input("Enter the new name: ").strip()

    if not new_name:
        print("\nActivity name cannot be empty.")
        pause()
        return

    # Prevent duplicate names.
    for other_task in tasks:
        if (
            other_task["id"] != task_id
            and other_task["name"].lower() == new_name.lower()
        ):
            print(f"\nAn activity named '{other_task['name']}' already exists.")
            pause()
            return

    old_name = task["name"]
    task["name"] = new_name

    save_tasks(tasks)

    print(f"\n'{old_name}' was renamed to '{new_name}'.")

    pause()


# =========================================================
# Time Tracking
# =========================================================

def start_tracking():
    """Start tracking time for an activity."""
    clear_screen()

    print("=" * 50)
    print("                 START TRACKING")
    print("=" * 50)

    tasks = load_tasks()
    entries = load_time_entries()

    if not tasks:
        print("\nNo activities have been added yet.")
        print("Add an activity before starting the timer.")
        pause()
        return

    running_entry = get_running_entry(entries)

    if running_entry is not None:
        running_task = find_task(tasks, running_entry["task_id"])

        if running_task:
            print(
                f"\nThe {running_task['name']} activity is already being tracked."
            )
        else:
            print("\nAn activity is already being tracked.")

        pause()
        return

    # Display activities.
    print()

    for task in tasks:
        print(f"  {task['id']}. {task['name']}")

    print()

    try:
        task_id = int(input("Select an activity: "))
    except ValueError:
        print("\nPlease enter a valid number.")
        pause()
        return

    task = find_task(tasks, task_id)

    if task is None:
        print("\nThat activity does not exist.")
        pause()
        return

    new_entry = {
        "id": len(entries) + 1,
        "task_id": task_id,
        "start_time": current_time(),
        "end_time": None
    }

    entries.append(new_entry)
    save_time_entries(entries)

    print(f"\nStarted tracking: {task['name']}")

    pause()


def stop_tracking():
    """Stop the currently running activity."""
    clear_screen()

    print("=" * 50)
    print("                  STOP TRACKING")
    print("=" * 50)

    tasks = load_tasks()
    entries = load_time_entries()

    running_entry = get_running_entry(entries)

    if running_entry is None:
        print("\nNo activity is currently being tracked.")
        pause()
        return

    running_task = find_task(tasks, running_entry["task_id"])

    running_entry["end_time"] = current_time()

    save_time_entries(entries)

    if running_task:
        start = datetime.fromisoformat(running_entry["start_time"])
        end = datetime.fromisoformat(running_entry["end_time"])

        duration = (end - start).total_seconds()

        print(f"\nStopped tracking: {running_task['name']}")
        print(f"Session duration: {format_duration(duration)}")
    else:
        print("\nTracking stopped.")

    pause()


# =========================================================
# Reporting
# =========================================================

def show_report():
    """Display weekly tracked time by activity and day."""
    clear_screen()

    tasks = load_tasks()
    entries = load_time_entries()

    if not tasks:
        print("\nNo activities have been added yet.")
        pause()
        return

    weeks = get_report_weeks(entries)

    if not weeks:
        print("\nNo time has been captured yet.")
        pause()
        return

    # Always open on the current calendar week when entering the report.
    current_local_date = datetime.now().astimezone().date()
    current_week = get_week_start(current_local_date)

    # If the current week has no captured time, show the most recent week that does.
    if current_week in weeks:
        selected_index = weeks.index(current_week)
    else:
        selected_index = len(weeks) - 1

    # Report dimensions.
    report_width = 104
    activity_width = 28
    day_width = 9
    week_width = 10

    while True:
        clear_screen()

        week_start = weeks[selected_index]
        week_dates = [
            week_start + timedelta(days=i)
            for i in range(7)
        ]
        week_end = week_dates[-1]

        print("=" * report_width)
        print(f"{'TIME REPORT':^{report_width}}")
        print("=" * report_width)
        print("=" * report_width)
        print(f"{'WEEK REPORTING':^{report_width}}")
        print(
            f"{(week_start.strftime('%b %d, %Y') + ' - ' + week_end.strftime('%b %d, %Y')):^{report_width}}"
        )
        print("=" * report_width)
        print()

        # Aggregate each entry by activity and local calendar date.
        totals = {
            task["id"]: {day: 0 for day in week_dates}
            for task in tasks
        }

        for entry in entries:
            task_id = entry["task_id"]
            if task_id not in totals:
                continue

            for local_date, seconds in get_entry_segments(entry):
                if local_date in totals[task_id]:
                    totals[task_id][local_date] += seconds

        # Two-line column headings: weekday/date, then TOTAL under Week.
        print(
            f"  {'Activity':<{activity_width}}"
            + "".join(
                f"{day.strftime('%a'):>{day_width}}"
                for day in week_dates
            )
            + f"{'Week':>{week_width}}"
        )
        print(
            f"  {'':<{activity_width}}"
            + "".join(
                f"{day.strftime('%m/%d'):>{day_width}}"
                for day in week_dates
            )
            + f"{'TOTAL':>{week_width}}"
        )
        print("-" * report_width)

        weekly_totals = {day: 0 for day in week_dates}
        grand_total = 0

        for task in tasks:
            task_total = 0
            day_values = []

            for day in week_dates:
                seconds = totals[task["id"]][day]
                weekly_totals[day] += seconds
                task_total += seconds
                day_values.append(format_report_duration(seconds))

            grand_total += task_total

            print(
                f"  {task['name']:<{activity_width}}"
                + "".join(f"{value:>{day_width}}" for value in day_values)
                + f"{format_report_duration(task_total):>{week_width}}"
            )

        print("-" * report_width)

        day_total_values = [
            format_report_duration(weekly_totals[day])
            for day in week_dates
        ]

        print(
            f"  {'TOTAL':<{activity_width}}"
            + "".join(f"{value:>{day_width}}" for value in day_total_values)
            + f"{format_report_duration(grand_total):>{week_width}}"
        )

        print()
        # Keep navigation at the bottom, with Back on the left and week
        # navigation grouped toward the right as shown in the requested layout.
        back_text = "[Enter] Return to Menu"
        navigation_text = "[b] Previous    [n] Next"
        gap = max(1, report_width - len(back_text) - len(navigation_text))
        print(f"{back_text}{' ' * gap}{navigation_text}")
        print("=" * report_width)

        choice = input(" ").strip().lower()

        if choice == "b":
            if selected_index > 0:
                selected_index -= 1
            else:
                print("\n No earlier week has captured time.")
                input(" Press Enter to continue...")
        elif choice == "n":
            if selected_index < len(weeks) - 1:
                selected_index += 1
            else:
                print("\n No later week has captured time.")
                input(" Press Enter to continue...")
        elif choice == "":
            return
        else:
            print("\n Press 'b' for the previous week, 'n' for the next week, or Enter to return.")
            input(" Press Enter to continue...")


# =========================================================
# Main Menu
# =========================================================

def show_menu():
    """Display the main menu."""
    clear_screen()

    print("=" * 50)
    print("                 TIME TRACKER")
    print("=" * 50)

    # Show currently running activity.
    tasks = load_tasks()
    entries = load_time_entries()

    running_entry = get_running_entry(entries)

    if running_entry:
        running_task = find_task(tasks, running_entry["task_id"])

        if running_task:
            start = datetime.fromisoformat(running_entry["start_time"])
            now = datetime.now(timezone.utc)
            duration = (now - start).total_seconds()

            print()
            print(
                f"  Tracking Activity: \t\t {running_task['name']}"
            )
            print(
                f"  Duration:  \t\t\t {format_duration(duration)}"
            )

    ### print("\n" + "-" * 50)

    print("""
  1. List Activities
  2. Add Activity
  3. Edit Activity
  4. Start Tracking
  5. Stop Tracking
  6. View Time Report
  7. Exit
""")


def main():
    """Run the application."""
    while True:
        show_menu()

        choice = input("Select an option: ").strip()

        if choice == "1":
            list_tasks()
            pause()

        elif choice == "2":
            add_task()

        elif choice == "3":
            edit_task()

        elif choice == "4":
            start_tracking()

        elif choice == "5":
            stop_tracking()

        elif choice == "6":
            show_report()

        elif choice == "7":
            clear_screen()
            print("Thank you for using Time Tracker!")
            print()
            break

        else:
            print("\nInvalid selection. Please choose 1-7.")
            pause()


if __name__ == "__main__":
    main()
