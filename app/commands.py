import typer

from app import background_processes

app = typer.Typer()


@app.command()
def fetch_awards():
    background_processes.fetcher.fetch_new_awards()


@app.command()
def fetch_contracts_from_date(from_date: str, until_date: str):
    background_processes.fetcher.fetch_contracts_from_date(from_date, until_date)


@app.command()
def remove_dated_application_data():
    background_processes.remove_data.remove_dated_data()


@app.command()
def update_applications_to_lapsed():
    background_processes.lapsed_applications.set_lapsed_applications()


@app.command()
def send_reminders():
    background_processes.send_reminder.send_reminders()


@app.command()
def update_statistics():
    background_processes.update_statistic.update_statistics()


@app.command()
def SLA_overdue_applications():
    background_processes.SLA_overdue_applications.SLA_overdue_applications()


if __name__ == "__main__":
    app()
