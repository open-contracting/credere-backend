import logging

import typer

from app.background_processes import fetcher, send_reminder

app = typer.Typer()


@app.command()
def fetch_awards():
    fetcher.fetch_new_awards()


@app.command()
def fetch_new_awards_from_date(date: str):
    fetcher.fetch_new_awards_from_date(date)


@app.command()
def send_reminders():
    send_reminder.send_reminders()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    app()
