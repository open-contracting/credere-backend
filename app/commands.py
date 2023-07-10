import logging

import typer

from app import background_processes

app = typer.Typer()


@app.command()
def fetch_awards(email_invitation: str = None):
    background_processes.fetcher.fetch_new_awards(email_invitation)


@app.command()
def fetch_new_awards_from_date(date: str, email_invitation: str = None):
    background_processes.fetcher.fetch_new_awards_from_date(date, email_invitation)


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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    app()
